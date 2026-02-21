"""
DynamoDB service for playlist operations.

Targets the 'multimusic-playlists' table (separate from multimusic-users).
Handles:
    - Cached platform playlists (YouTube, SoundCloud) with 24h TTL
    - Custom MMP playlists (future - cross-platform, no TTL)
"""
import os
import time
from typing import Any, Dict, List, Optional
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger

logger = Logger()

# Cache duration: 24 hours in seconds
CACHE_TTL_SECONDS = 86400


class PlaylistDynamoDBService:
    """Service for playlist DynamoDB operations"""

    def __init__(self):
        dynamodb_endpoint = os.environ.get('DYNAMODB_ENDPOINT')
        region = os.environ.get('AWS_REGION', 'eu-west-1')

        if dynamodb_endpoint:
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=dynamodb_endpoint,
                region_name=region,
            )
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=region)

        self.table_name = os.environ.get('DYNAMODB_PLAYLISTS_TABLE', 'multimusic-playlists')
        self.table = self.dynamodb.Table(self.table_name)

    # ========== Cache Operations ==========

    def get_cached_playlists(
        self,
        user_id: str,
        platform: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached playlists for a platform.

        Returns list of playlists if cache is valid (not expired), None if
        cache is missing or expired.

        Args:
            user_id: Internal MMP user ID
            platform: Platform name ('youtube' or 'soundcloud')

        Returns:
            List of cached playlist dicts, or None if cache miss/expired
        """
        try:
            sk_prefix = f"cache#{platform}#"
            response = self.table.query(
                KeyConditionExpression=(
                    Key('userId').eq(user_id)
                    & Key('sk').begins_with(sk_prefix)
                ),
            )

            items = response.get('Items', [])
            if not items:
                logger.info(f"No cached playlists for {platform} (user {user_id})")
                return None

            # Check if cache is expired using the TTL field
            now = int(time.time())
            # All items share the same cache timestamp, check the first one
            ttl_value = items[0].get('ttl', 0)
            if isinstance(ttl_value, (int, float)):
                ttl_int = int(ttl_value)
            else:
                ttl_int = int(ttl_value) if ttl_value else 0

            if ttl_int <= now:
                logger.info(f"Cache expired for {platform} (user {user_id})")
                return None

            logger.info(f"Cache hit: {len(items)} {platform} playlists (user {user_id})")
            return items

        except Exception as e:
            logger.error(f"Error reading playlist cache: {e}")
            return None

    def store_cached_playlists(
        self,
        user_id: str,
        platform: str,
        playlists: List[Dict[str, Any]],
    ) -> None:
        """
        Store playlists in cache with 24h TTL.

        Replaces any existing cache for this user+platform.

        Args:
            user_id: Internal MMP user ID
            platform: Platform name ('youtube' or 'soundcloud')
            playlists: List of normalized playlist dicts
        """
        try:
            now = int(time.time())
            ttl_value = now + CACHE_TTL_SECONDS

            # First, clear existing cache for this platform
            self.clear_cached_playlists(user_id, platform)

            # Write all playlists
            with self.table.batch_writer() as batch:
                for playlist in playlists:
                    playlist_id = playlist['id']
                    item = {
                        'userId': user_id,
                        'sk': f"cache#{platform}#{playlist_id}",
                        'platform': platform,
                        'playlistId': playlist_id,
                        'name': playlist.get('name', 'Unknown Playlist'),
                        'trackCount': playlist.get('trackCount', 0),
                        'imageUrl': playlist.get('imageUrl', ''),
                        'uri': playlist.get('uri', ''),
                        'owner': playlist.get('owner', ''),
                        'cachedAt': now,
                        'ttl': ttl_value,
                    }
                    batch.put_item(Item=item)

            logger.info(
                f"Cached {len(playlists)} {platform} playlists (user {user_id}), "
                f"TTL: {CACHE_TTL_SECONDS}s"
            )

        except Exception as e:
            logger.error(f"Error storing playlist cache: {e}")
            raise

    def clear_cached_playlists(self, user_id: str, platform: str) -> None:
        """
        Clear all cached playlists for a user+platform.

        Args:
            user_id: Internal MMP user ID
            platform: Platform name
        """
        try:
            sk_prefix = f"cache#{platform}#"
            response = self.table.query(
                KeyConditionExpression=(
                    Key('userId').eq(user_id)
                    & Key('sk').begins_with(sk_prefix)
                ),
                ProjectionExpression='userId, sk',
            )

            items = response.get('Items', [])
            if not items:
                return

            with self.table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={'userId': item['userId'], 'sk': item['sk']}
                    )

            logger.info(f"Cleared {len(items)} cached {platform} playlists (user {user_id})")

        except Exception as e:
            logger.error(f"Error clearing playlist cache: {e}")
            raise

    def get_cache_metadata(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get cache metadata (cached_at timestamp, ttl) without returning full playlist data.
        Useful for showing 'last updated X hours ago' in UI.

        Args:
            user_id: Internal MMP user ID
            platform: Platform name

        Returns:
            Dict with 'cachedAt' and 'ttl', or None if no cache
        """
        try:
            sk_prefix = f"cache#{platform}#"
            response = self.table.query(
                KeyConditionExpression=(
                    Key('userId').eq(user_id)
                    & Key('sk').begins_with(sk_prefix)
                ),
                ProjectionExpression='cachedAt, #t',
                ExpressionAttributeNames={'#t': 'ttl'},
                Limit=1,
            )

            items = response.get('Items', [])
            if not items:
                return None

            return {
                'cachedAt': items[0].get('cachedAt'),
                'ttl': items[0].get('ttl'),
            }

        except Exception as e:
            logger.error(f"Error reading cache metadata: {e}")
            return None

    # ========== Custom Playlist Operations (Future) ==========

    # These methods are stubs for future custom MMP playlist support.
    # Custom playlists use sk prefix "custom#" and have no TTL.

    # def create_custom_playlist(self, user_id, name, tracks=None): ...
    # def get_custom_playlists(self, user_id): ...
    # def add_track_to_custom_playlist(self, user_id, playlist_id, track): ...
    # def remove_track_from_custom_playlist(self, user_id, playlist_id, track_id): ...
    # def delete_custom_playlist(self, user_id, playlist_id): ...: