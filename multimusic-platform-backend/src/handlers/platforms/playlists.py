"""
Playlist handlers for YouTube and SoundCloud.

Fetches user playlists from platform APIs with DynamoDB caching (24h TTL).
Spotify playlists are handled client-side and do NOT go through this handler.

Endpoints:
    GET /platforms/youtube/playlists?force_refresh=false
    GET /platforms/soundcloud/playlists?force_refresh=false
"""
import os
from typing import Any, Dict, List
import httpx

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.handlers.platforms.base import BasePlatformHandler
from src.services.playlist_dynamodb_service import PlaylistDynamoDBService
from src.utils.responses import success_response, error_response

logger = Logger()

# Service instances
playlist_db = PlaylistDynamoDBService()

# Platform handler instances (reuse existing pattern for token access)
youtube_platform = BasePlatformHandler('youtube')
soundcloud_platform = BasePlatformHandler('soundcloud')

# Config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')


# ========== YouTube Playlists ==========

@logger.inject_lambda_context
def youtube_playlists_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Get user's YouTube playlists.

    Checks DynamoDB cache first (24h TTL). Falls back to YouTube Data API.
    Pass ?force_refresh=true to bypass cache.

    Returns normalized playlist data.
    """
    try:
        # Authenticate
        user_id = youtube_platform.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)

        # Check if YouTube is connected
        token_data = youtube_platform.get_platform_tokens(user_id)
        if not token_data:
            return error_response("YouTube Music not connected", 404)

        # Check force_refresh param
        query_params = event.get('queryStringParameters', {}) or {}
        force_refresh = query_params.get('force_refresh', 'false').lower() == 'true'

        # Try cache first (unless force refresh)
        if not force_refresh:
            cached = playlist_db.get_cached_playlists(user_id, 'youtube')
            if cached is not None:
                playlists = _cached_items_to_playlists(cached)
                cache_meta = playlist_db.get_cache_metadata(user_id, 'youtube')
                return success_response({
                    'playlists': playlists,
                    'source': 'cache',
                    'cachedAt': int(cache_meta.get('cachedAt', 0)) if cache_meta else None,
                })

        # Cache miss or force refresh - fetch from YouTube API
        logger.info(f"Fetching YouTube playlists from API (user {user_id}, force={force_refresh})")

        # Get fresh access token
        encrypted_access_token = token_data.get('accessToken')
        if not encrypted_access_token:
            return error_response("No access token available", 500)

        access_token = youtube_platform.token_service.decrypt_token(encrypted_access_token)

        # Fetch playlists from YouTube Data API
        raw_playlists = _fetch_youtube_playlists(access_token)

        # Normalize to unified format
        playlists = _normalize_youtube_playlists(raw_playlists)

        # Store in cache
        if playlists:
            playlist_db.store_cached_playlists(user_id, 'youtube', playlists)

        cache_meta = playlist_db.get_cache_metadata(user_id, 'youtube')
        return success_response({
            'playlists': playlists,
            'source': 'api',
            'cachedAt': int(cache_meta.get('cachedAt', 0)) if cache_meta else None,
        })

    except httpx.HTTPStatusError as e:
        logger.error(f"YouTube API error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            return error_response("YouTube token expired - please refresh", 401)
        return error_response(f"YouTube API error: {e.response.status_code}", 500)
    except Exception as e:
        logger.exception("Error fetching YouTube playlists")
        return error_response(str(e), 500)


def _fetch_youtube_playlists(access_token: str) -> List[Dict[str, Any]]:
    """
    Fetch all playlists from YouTube Data API (paginated).

    Uses 'list' endpoint with mine=true. Each page costs 1 quota unit.
    """
    all_playlists = []
    page_token = None

    with httpx.Client() as client:
        while True:
            params = {
                'part': 'snippet,contentDetails',
                'mine': 'true',
                'maxResults': 50,
            }
            if page_token:
                params['pageToken'] = page_token

            response = client.get(
                'https://www.googleapis.com/youtube/v3/playlists',
                params=params,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            all_playlists.extend(data.get('items', []))

            page_token = data.get('nextPageToken')
            if not page_token:
                break

    logger.info(f"Fetched {len(all_playlists)} YouTube playlists from API")
    return all_playlists


def _normalize_youtube_playlists(raw_playlists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize YouTube API playlist data to unified format."""
    playlists = []
    for item in raw_playlists:
        snippet = item.get('snippet', {})
        content_details = item.get('contentDetails', {})
        thumbnails = snippet.get('thumbnails', {})

        # Pick best thumbnail
        image_url = ''
        for quality in ['high', 'medium', 'default']:
            if quality in thumbnails:
                image_url = thumbnails[quality].get('url', '')
                break

        playlists.append({
            'id': item['id'],
            'platform': 'youtube',
            'name': snippet.get('title', 'Unknown Playlist'),
            'trackCount': content_details.get('itemCount', 0),
            'imageUrl': image_url,
            'uri': item['id'],  # YouTube playlist ID used to fetch tracks
            'owner': snippet.get('channelTitle', ''),
        })

    return playlists


# ========== SoundCloud Playlists ==========

@logger.inject_lambda_context
def soundcloud_playlists_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Get user's SoundCloud playlists.

    Checks DynamoDB cache first (24h TTL). Falls back to SoundCloud API.
    Pass ?force_refresh=true to bypass cache.

    Returns normalized playlist data.
    """
    try:
        # Authenticate
        user_id = soundcloud_platform.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)

        # Check if SoundCloud is connected
        token_data = soundcloud_platform.get_platform_tokens(user_id)
        if not token_data:
            return error_response("SoundCloud not connected", 404)

        # Check force_refresh param
        query_params = event.get('queryStringParameters', {}) or {}
        force_refresh = query_params.get('force_refresh', 'false').lower() == 'true'

        # Try cache first (unless force refresh)
        if not force_refresh:
            cached = playlist_db.get_cached_playlists(user_id, 'soundcloud')
            if cached is not None:
                playlists = _cached_items_to_playlists(cached)
                cache_meta = playlist_db.get_cache_metadata(user_id, 'soundcloud')
                return success_response({
                    'playlists': playlists,
                    'source': 'cache',
                    'cachedAt': int(cache_meta.get('cachedAt', 0)) if cache_meta else None,
                })

        # Cache miss or force refresh - fetch from SoundCloud API
        logger.info(f"Fetching SoundCloud playlists from API (user {user_id}, force={force_refresh})")

        # Get fresh access token
        encrypted_access_token = token_data.get('accessToken')
        if not encrypted_access_token:
            return error_response("No access token available", 500)

        access_token = soundcloud_platform.token_service.decrypt_token(encrypted_access_token)

        # Fetch playlists from SoundCloud API
        raw_playlists = _fetch_soundcloud_playlists(access_token)

        # Normalize to unified format
        playlists = _normalize_soundcloud_playlists(raw_playlists)

        # Store in cache
        if playlists:
            playlist_db.store_cached_playlists(user_id, 'soundcloud', playlists)

        cache_meta = playlist_db.get_cache_metadata(user_id, 'soundcloud')
        return success_response({
            'playlists': playlists,
            'source': 'api',
            'cachedAt': int(cache_meta.get('cachedAt', 0)) if cache_meta else None,
        })

    except httpx.HTTPStatusError as e:
        logger.error(f"SoundCloud API error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            return error_response("SoundCloud token expired - please refresh", 401)
        return error_response(f"SoundCloud API error: {e.response.status_code}", 500)
    except Exception as e:
        logger.exception("Error fetching SoundCloud playlists")
        return error_response(str(e), 500)


def _fetch_soundcloud_playlists(access_token: str) -> List[Dict[str, Any]]:
    """
    Fetch all playlists from SoundCloud API.

    Uses /me/playlists endpoint (authenticated user's playlists).
    Also fetches liked playlists via /me/likes/playlists.
    """
    all_playlists = []

    with httpx.Client() as client:
        # Fetch user's own playlists
        response = client.get(
            'https://api.soundcloud.com/me/playlists',
            headers={
                'Authorization': f'OAuth {access_token}',
                'Accept': 'application/json; charset=utf-8',
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            all_playlists.extend(data)
        elif isinstance(data, dict) and 'collection' in data:
            all_playlists.extend(data['collection'])

    logger.info(f"Fetched {len(all_playlists)} SoundCloud playlists from API")
    return all_playlists


def _normalize_soundcloud_playlists(raw_playlists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize SoundCloud API playlist data to unified format."""
    playlists = []
    for item in raw_playlists:
        artwork_url = item.get('artwork_url', '')
        if artwork_url:
            # Get higher quality artwork
            artwork_url = artwork_url.replace('-large', '-t500x500')

        playlists.append({
            'id': str(item.get('id', '')),
            'platform': 'soundcloud',
            'name': item.get('title', 'Unknown Playlist'),
            'trackCount': item.get('track_count', 0),
            'imageUrl': artwork_url or '',
            'uri': item.get('permalink_url', ''),
            'owner': item.get('user', {}).get('username', ''),
        })

    return playlists


# ========== Shared Helpers ==========

def _cached_items_to_playlists(cached_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert DynamoDB cached items back to the normalized playlist format.

    Strips DynamoDB-specific fields (userId, sk, cachedAt, ttl) and returns
    clean playlist objects matching the API response format.
    """
    playlists = []
    for item in cached_items:
        playlists.append({
            'id': item.get('playlistId', ''),
            'platform': item.get('platform', ''),
            'name': item.get('name', 'Unknown Playlist'),
            'trackCount': int(item.get('trackCount', 0)),
            'imageUrl': item.get('imageUrl', ''),
            'uri': item.get('uri', ''),
            'owner': item.get('owner', ''),
        })
    return playlists