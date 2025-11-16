"""
SoundCloud Platform Connection Handlers
"""
import base64
import hashlib
import json
import os
import secrets
from typing import Any, Dict
from urllib.parse import urlencode
import httpx

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.handlers.platforms.base import BasePlatformHandler
from src.utils.responses import success_response, error_response, redirect_response

logger = Logger()

# Configuration
SOUNDCLOUD_CLIENT_ID = os.environ.get('SOUNDCLOUD_CLIENT_ID')
SOUNDCLOUD_CLIENT_SECRET = os.environ.get('SOUNDCLOUD_CLIENT_SECRET')
SOUNDCLOUD_REDIRECT_URI = os.environ.get('SOUNDCLOUD_REDIRECT_URI', 'http://127.0.0.1:8080/platforms/soundcloud/callback')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Handler instance
platform_handler = BasePlatformHandler('soundcloud')


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge pair
    Returns: (code_verifier, code_challenge)
    """
    # Generate code verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(64)

    # Generate code challenge (SHA256 hash of verifier, base64url encoded)
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

    return code_verifier, code_challenge


@logger.inject_lambda_context
def connect_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate SoundCloud connection for logged-in user
    
    Requires valid session token in Authorization header
    """
    try:
        logger.info("Initiating SoundCloud platform connection")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"User {user_id} connecting SoundCloud")
        
        # Check if SoundCloud already connected
        existing_tokens = platform_handler.get_platform_tokens(user_id)
        if existing_tokens:
            logger.info(f"SoundCloud already connected for user {user_id}")
            return success_response({
                'message': 'SoundCloud already connected',
                'connected': True
            })
        
        # Generate PKCE pair for OAuth 2.1
        code_verifier, code_challenge = generate_pkce_pair()

        # Generate state for CSRF protection (include user_id and code_verifier)
        # Format: user_id:random_string:code_verifier
        state = f"{user_id}:{secrets.token_urlsafe(16)}:{code_verifier}"

        # Build SoundCloud authorization URL (OAuth 2.1 with PKCE)
        auth_params = {
            'client_id': SOUNDCLOUD_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'scope': 'non-expiring'
        }

        auth_url = f"https://secure.soundcloud.com/authorize?{urlencode(auth_params)}"

        return success_response({
            'authUrl': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.exception("Error in SoundCloud connect")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle SoundCloud OAuth callback
    
    Links SoundCloud account to authenticated MultiMusic user
    """
    try:
        logger.info("Processing SoundCloud OAuth callback")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {})
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=soundcloud_{error}",
                302
            )
        
        if not code or not state:
            logger.error("Missing code or state")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=soundcloud_invalid_callback",
                302
            )
        
        # Extract user ID and code_verifier from state
        # Format: user_id:random_string:code_verifier
        try:
            parts = state.split(':', 2)
            if len(parts) != 3:
                raise ValueError("Invalid state format")
            user_id = parts[0]
            code_verifier = parts[2]
        except (ValueError, IndexError):
            logger.error("Invalid state format")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=soundcloud_invalid_state",
                302
            )

        # Exchange code for token (with PKCE code_verifier)
        logger.info("Exchanging code for access token")
        token_data = exchange_code_for_token(code, code_verifier)
        
        # Get SoundCloud user info
        soundcloud_user_info = get_soundcloud_user_info(token_data['access_token'])
        soundcloud_user_id = str(soundcloud_user_info['id'])
        soundcloud_username = soundcloud_user_info.get('username', 'Unknown User')
        
        logger.info(f"Linking SoundCloud user {soundcloud_user_id} to {user_id}")
        
        # Store platform tokens
        platform_handler.store_platform_tokens(
            user_id=user_id,
            platform_user_id=soundcloud_user_id,
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=token_data.get('expires_in', 31536000),
            scope=token_data.get('scope', 'non-expiring')
        )
        
        # Also store username for display purposes
        from src.services.dynamodb_service import DynamoDBService
        db_service = DynamoDBService()
        db_service.update_item(
            user_id=user_id,
            sk='platform#soundcloud',
            updates={
                'username': soundcloud_username,
                'permalink': soundcloud_user_info.get('permalink', ''),
                'avatarUrl': soundcloud_user_info.get('avatar_url', '')
            }
        )
        
        # Redirect to dashboard with success
        redirect_url = f"{FRONTEND_URL}/dashboard?soundcloud=connected"
        
        return redirect_response(redirect_url, 302)
        
    except Exception as e:
        logger.exception("Error in SoundCloud callback")
        return redirect_response(
            f"{FRONTEND_URL}/dashboard?error=soundcloud_connection_failed",
            302
        )


@logger.inject_lambda_context
def refresh_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Refresh SoundCloud access token
    
    Requires valid session token
    """
    try:
        logger.info("Refreshing SoundCloud access token")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"Refreshing SoundCloud token for user: {user_id}")
        
        # Get token data from DynamoDB
        token_data = platform_handler.get_platform_tokens(user_id)
        if not token_data:
            return error_response("SoundCloud not connected", 404)
        
        encrypted_refresh_token = token_data.get('refreshToken')
        
        if not encrypted_refresh_token:
            # SoundCloud with 'non-expiring' scope may not need refresh
            # Return current access token if still valid
            logger.info("No refresh token found - returning current access token")
            encrypted_access_token = token_data.get('accessToken')
            if encrypted_access_token:
                access_token = platform_handler.token_service.decrypt_token(encrypted_access_token)
                return success_response({
                    'accessToken': access_token,
                    'expiresIn': token_data.get('expiresIn', 31536000)
                })
            else:
                return error_response("No access token available - please reconnect SoundCloud", 400)
        
        refresh_token = platform_handler.token_service.decrypt_token(encrypted_refresh_token)

        # Request new access token from SoundCloud
        new_token_data = refresh_access_token(refresh_token)

        # Update stored tokens (both access and refresh)
        # Note: SoundCloud refresh tokens are one-time use, so we must update the refresh token too
        encrypted_new_access = platform_handler.token_service.encrypt_token(new_token_data['access_token'])

        updates = {
            'accessToken': encrypted_new_access,
            'expiresIn': new_token_data.get('expires_in', 31536000)
        }

        # Update refresh token if a new one is provided (one-time use tokens)
        if 'refresh_token' in new_token_data:
            encrypted_new_refresh = platform_handler.token_service.encrypt_token(new_token_data['refresh_token'])
            updates['refreshToken'] = encrypted_new_refresh
            logger.info("Updated refresh token (one-time use)")

        from src.services.dynamodb_service import DynamoDBService
        db_service = DynamoDBService()
        db_service.update_item(
            user_id=user_id,
            sk='platform#soundcloud',
            updates=updates
        )

        # Return new access token (decrypted)
        return success_response({
            'accessToken': new_token_data['access_token'],
            'expiresIn': new_token_data.get('expires_in', 31536000)
        })
        
    except Exception as e:
        logger.exception("Error refreshing SoundCloud token")
        return error_response(str(e), 500)


def exchange_code_for_token(code: str, code_verifier: str) -> Dict[str, Any]:
    """Exchange authorization code for access token (OAuth 2.1 with PKCE)"""
    with httpx.Client() as client:
        response = client.post(
            'https://secure.soundcloud.com/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
                'client_id': SOUNDCLOUD_CLIENT_ID,
                'client_secret': SOUNDCLOUD_CLIENT_SECRET,
                'code_verifier': code_verifier
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token (OAuth 2.1)"""
    with httpx.Client() as client:
        response = client.post(
            'https://secure.soundcloud.com/oauth/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': SOUNDCLOUD_CLIENT_ID,
                'client_secret': SOUNDCLOUD_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def get_soundcloud_user_info(access_token: str) -> Dict[str, Any]:
    """Get user information from SoundCloud (OAuth 2.1)"""
    with httpx.Client() as client:
        response = client.get(
            'https://api.soundcloud.com/me',
            headers={
                'Authorization': f'OAuth {access_token}',
                'Accept': 'application/json; charset=utf-8'
            }
        )
        response.raise_for_status()
        return response.json()


def search_soundcloud_tracks(access_token: str, query: str, limit: int = 20) -> Dict[str, Any]:
    """
    Search SoundCloud tracks using API v1

    Args:
        access_token: SoundCloud OAuth access token
        query: Search query string
        limit: Maximum number of results (default: 20)

    Returns:
        List of track objects from SoundCloud API
    """
    with httpx.Client() as client:
        response = client.get(
            'https://api.soundcloud.com/tracks',
            params={
                'q': query,
                'limit': limit,
                'linked_partitioning': 1  # Enable pagination
            },
            headers={
                'Authorization': f'OAuth {access_token}',  # Required by SoundCloud API
                'Accept': 'application/json; charset=utf-8'
            },
            timeout=10
        )
        response.raise_for_status()

        # v1 API returns different structure than v2
        data = response.json()

        # If using linked_partitioning, data has 'collection' key
        # Otherwise it's a direct array
        if isinstance(data, dict) and 'collection' in data:
            return {'collection': data['collection']}
        else:
            return {'collection': data if isinstance(data, list) else []}



@logger.inject_lambda_context
def search_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Search SoundCloud for tracks

    GET /platforms/soundcloud/search?q={query}
    Requires: Authorization header with Bearer token

    Returns normalized track data matching frontend Track interface
    """
    try:
        logger.info("Processing SoundCloud search request")

        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)

        # Get query from query string parameters
        query_params = event.get('queryStringParameters', {}) or {}
        query = query_params.get('q', '').strip()

        if not query:
            return error_response("Query parameter 'q' is required", 400)

        logger.info(f"User {user_id} searching SoundCloud for: {query}")

        # Get user's SoundCloud access token
        token_data = platform_handler.get_platform_tokens(user_id)
        if not token_data:
            return error_response("SoundCloud not connected. Please connect your SoundCloud account first.", 404)

        # Decrypt access token
        encrypted_token = token_data.get('accessToken')
        if not encrypted_token:
            return error_response("No access token found", 500)

        access_token = platform_handler.token_service.decrypt_token(encrypted_token)

        # Search SoundCloud
        logger.info(f"Calling SoundCloud API search with query: {query}")
        search_results = search_soundcloud_tracks(access_token, query)

        # Normalize track data to match frontend Track interface
        tracks = []
        collection = search_results.get('collection', [])

        for item in collection:
            if not item or not item.get('id'):
                continue

            # Get the best quality artwork
            artwork_url = item.get('artwork_url', '')
            if artwork_url:
                # Replace -large with higher quality -t500x500
                artwork_url = artwork_url.replace('-large', '-t500x500')
            elif item.get('user', {}).get('avatar_url'):
                # Fallback to user avatar
                artwork_url = item['user']['avatar_url']

            track = {
                'id': f"soundcloud-{item.get('id')}",
                'platform': 'soundcloud',
                'name': item.get('title', 'Unknown Track'),
                'uri': item.get('permalink_url', ''),
                'artists': [{'name': item.get('user', {}).get('username', 'Unknown Artist')}],
                'album': {
                    'name': item.get('user', {}).get('username', 'Unknown Artist'),
                    'images': [{'url': artwork_url}] if artwork_url else []
                },
                'duration_ms': item.get('duration', 0),  # Already in milliseconds
                'preview_url': item.get('stream_url')
            }
            tracks.append(track)

        logger.info(f"Found {len(tracks)} tracks for query: {query}")

        return success_response({'tracks': tracks})

    except httpx.HTTPStatusError as e:
        logger.error(f"SoundCloud API error: {e.response.status_code} - {e.response.text}")
        return error_response(f"SoundCloud API error: {e.response.status_code}", 500)
    except Exception as e:
        logger.exception("Error searching SoundCloud")
        return error_response(str(e), 500)