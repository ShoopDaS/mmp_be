"""
DynamoDB service for custom playlist operations.

Targets two tables:
    mmp_custom_playlists  — playlist metadata (PK: userId, SK: playlistId)
    mmp_playlist_tracks   — track items (PK: playlistId, SK: order#trackId)

SK format for tracks: zero-padded order (10 digits) + '#' + trackId
    e.g. '0000001000#abc123'
"""
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Attr, Key
from aws_lambda_powertools import Logger

logger = Logger()

# How many items per BatchWriteItem call (DynamoDB hard limit)
BATCH_WRITE_LIMIT = 25


def _build_track_sk(order: int, track_id: str) -> str:
    """Build the sort key for a track item: zero-padded order + '#' + trackId."""
    return f"{order:010d}#{track_id}"


class CustomPlaylistService:
    """Service for custom playlist DynamoDB operations."""

    def __init__(self):
        dynamodb_endpoint = os.environ.get("DYNAMODB_ENDPOINT")
        region = os.environ.get("AWS_REGION", "eu-west-1")

        if dynamodb_endpoint:
            self.dynamodb = boto3.resource(
                "dynamodb",
                endpoint_url=dynamodb_endpoint,
                region_name=region,
            )
        else:
            self.dynamodb = boto3.resource("dynamodb", region_name=region)

        playlists_table_name = os.environ.get(
            "DYNAMODB_CUSTOM_PLAYLISTS_TABLE", "mmp_custom_playlists"
        )
        tracks_table_name = os.environ.get(
            "DYNAMODB_PLAYLIST_TRACKS_TABLE", "mmp_playlist_tracks"
        )

        self.playlists_table = self.dynamodb.Table(playlists_table_name)
        self.tracks_table = self.dynamodb.Table(tracks_table_name)

    # ========== Playlist Operations ==========

    def create_playlist(self, item: Dict[str, Any]) -> None:
        """Put a new playlist item into mmp_custom_playlists."""
        self.playlists_table.put_item(Item=item)
        logger.info(
            f"Created playlist {item['playlistId']} for user {item['userId']}"
        )

    def get_playlist(self, user_id: str, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a single playlist by (userId, playlistId). Returns None if not found."""
        response = self.playlists_table.get_item(
            Key={"userId": user_id, "playlistId": playlist_id}
        )
        return response.get("Item")

    def list_playlists(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Return all playlists for a user, sorted by createdAt ascending.

        Paginates internally; returns the full list.
        """
        items: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {
            "KeyConditionExpression": Key("userId").eq(user_id)
        }

        while True:
            response = self.playlists_table.query(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key

        return items

    def update_playlist(
        self, user_id: str, playlist_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update specific attributes on a playlist item.

        Returns the updated item.
        """
        set_parts = []
        expr_names: Dict[str, str] = {}
        expr_values: Dict[str, Any] = {}

        for i, (key, value) in enumerate(updates.items()):
            name_placeholder = f"#attr{i}"
            val_placeholder = f":val{i}"
            set_parts.append(f"{name_placeholder} = {val_placeholder}")
            expr_names[name_placeholder] = key
            expr_values[val_placeholder] = value

        update_expr = "SET " + ", ".join(set_parts)

        response = self.playlists_table.update_item(
            Key={"userId": user_id, "playlistId": playlist_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def delete_playlist(self, user_id: str, playlist_id: str) -> None:
        """Delete a playlist metadata item."""
        self.playlists_table.delete_item(
            Key={"userId": user_id, "playlistId": playlist_id}
        )
        logger.info(f"Deleted playlist {playlist_id} for user {user_id}")

    def set_needs_rebalance(
        self, user_id: str, playlist_id: str, value: bool, updated_at: str
    ) -> None:
        """Set needsRebalance flag on a playlist."""
        self.playlists_table.update_item(
            Key={"userId": user_id, "playlistId": playlist_id},
            UpdateExpression="SET needsRebalance = :v, updatedAt = :ts",
            ExpressionAttributeValues={":v": value, ":ts": updated_at},
        )

    def increment_track_count(self, user_id: str, playlist_id: str, updated_at: str) -> None:
        """Increment trackCount by 1 using ADD and set updatedAt."""
        self.playlists_table.update_item(
            Key={"userId": user_id, "playlistId": playlist_id},
            UpdateExpression="ADD trackCount :one SET updatedAt = :ts",
            ExpressionAttributeValues={":one": 1, ":ts": updated_at},
        )

    def decrement_track_count(self, user_id: str, playlist_id: str, updated_at: str) -> None:
        """
        Decrement trackCount by 1, floored at 0, and set updatedAt.

        Uses a conditional write so the counter never goes negative.
        """
        try:
            self.playlists_table.update_item(
                Key={"userId": user_id, "playlistId": playlist_id},
                UpdateExpression="ADD trackCount :neg SET updatedAt = :ts",
                ConditionExpression="trackCount > :zero",
                ExpressionAttributeValues={":neg": -1, ":ts": updated_at, ":zero": 0},
            )
        except self.playlists_table.meta.client.exceptions.ConditionalCheckFailedException:
            # Already at 0; just update the timestamp
            self.playlists_table.update_item(
                Key={"userId": user_id, "playlistId": playlist_id},
                UpdateExpression="SET updatedAt = :ts",
                ExpressionAttributeValues={":ts": updated_at},
            )

    # ========== Track Operations ==========

    def get_all_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """
        Return all tracks for a playlist, sorted ascending by SK (order#trackId).

        Paginates internally using LastEvaluatedKey; returns the full list.
        """
        items: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {
            "KeyConditionExpression": Key("playlistId").eq(playlist_id),
            "ScanIndexForward": True,
        }

        while True:
            response = self.tracks_table.query(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key

        return items

    def get_last_track(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the last track (highest order) in a playlist.

        Queries with ScanIndexForward=False and Limit=1.
        Returns None if the playlist has no tracks.
        """
        response = self.tracks_table.query(
            KeyConditionExpression=Key("playlistId").eq(playlist_id),
            ScanIndexForward=False,
            Limit=1,
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def add_track(self, item: Dict[str, Any]) -> None:
        """Put a track item into mmp_playlist_tracks."""
        self.tracks_table.put_item(Item=item)
        logger.info(
            f"Added track {item['trackId']} to playlist {item['playlistId']}"
        )

    def find_track_by_track_id(
        self, playlist_id: str, track_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a track item by its trackId attribute.

        Fetches all tracks for the playlist (via get_all_tracks) and filters
        in Python.  A DynamoDB FilterExpression on a non-key attribute can
        silently miss items when the filter eliminates every item on a page,
        so Python-side filtering against the full list is more reliable here.

        Returns the first matching item, or None if not found.
        """
        all_tracks = self.get_all_tracks(playlist_id)
        stored_ids = [t.get("trackId") for t in all_tracks]
        logger.info(
            f"find_track_by_track_id: searching for {track_id!r} "
            f"in playlist {playlist_id} — "
            f"{len(all_tracks)} track(s) stored, ids: {stored_ids}"
        )
        for track in all_tracks:
            if track.get("trackId") == track_id:
                return track
        return None

    def delete_track(self, playlist_id: str, order_track_sk: str) -> None:
        """Delete a track by its full composite key."""
        self.tracks_table.delete_item(
            Key={"playlistId": playlist_id, "order#trackId": order_track_sk}
        )
        logger.info(f"Deleted track SK={order_track_sk} from playlist {playlist_id}")

    def delete_all_tracks(self, playlist_id: str) -> None:
        """
        Delete every track belonging to playlist_id.

        Queries for all track keys, then batch-deletes in groups of 25.
        """
        items: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {
            "KeyConditionExpression": Key("playlistId").eq(playlist_id),
            "ProjectionExpression": "playlistId, #sk",
            "ExpressionAttributeNames": {"#sk": "order#trackId"},
        }

        while True:
            response = self.tracks_table.query(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key

        if not items:
            return

        # Batch delete in groups of BATCH_WRITE_LIMIT
        for i in range(0, len(items), BATCH_WRITE_LIMIT):
            batch = items[i : i + BATCH_WRITE_LIMIT]
            with self.tracks_table.batch_writer() as writer:
                for item in batch:
                    writer.delete_item(
                        Key={
                            "playlistId": item["playlistId"],
                            "order#trackId": item["order#trackId"],
                        }
                    )

        logger.info(f"Deleted {len(items)} tracks for playlist {playlist_id}")

    def batch_write_track_reorder(
        self,
        deletes: List[Tuple[str, str]],
        puts: List[Dict[str, Any]],
    ) -> None:
        """
        Execute a reorder as BatchWriteItem operations.

        Args:
            deletes: List of (playlistId, order#trackId) keys to delete.
            puts: List of full track item dicts to put.

        Sends in batches of BATCH_WRITE_LIMIT (25 items per batch).
        Note: each "reorder" entry is 1 delete + 1 put, so 2 ops each.
        """
        all_ops: List[Dict[str, Any]] = []

        for playlist_id, sk in deletes:
            all_ops.append(
                {
                    "type": "delete",
                    "key": {"playlistId": playlist_id, "order#trackId": sk},
                }
            )
        for item in puts:
            all_ops.append({"type": "put", "item": item})

        for i in range(0, len(all_ops), BATCH_WRITE_LIMIT):
            batch = all_ops[i : i + BATCH_WRITE_LIMIT]
            with self.tracks_table.batch_writer() as writer:
                for op in batch:
                    if op["type"] == "delete":
                        writer.delete_item(Key=op["key"])
                    else:
                        writer.put_item(Item=op["item"])

    # ========== Rebalance Support ==========

    def scan_playlists_needing_rebalance(self) -> List[Dict[str, Any]]:
        """
        Scan mmp_custom_playlists for items where needsRebalance = true.

        Returns the full list (paginates internally).
        """
        items: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {
            "FilterExpression": Attr("needsRebalance").eq(True)
        }

        while True:
            response = self.playlists_table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key

        return items

    def scan_playlists_stale(self, before_iso: str) -> List[Dict[str, Any]]:
        """
        Scan mmp_custom_playlists for items where lastRebalancedAt < before_iso
        (or where lastRebalancedAt is absent — never rebalanced).

        Returns items not yet in the needsRebalance list (to avoid double-processing).
        """
        items: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {
            "FilterExpression": (
                Attr("needsRebalance").ne(True)
                & (
                    Attr("lastRebalancedAt").lt(before_iso)
                    | Attr("lastRebalancedAt").not_exists()
                )
            )
        }

        while True:
            response = self.playlists_table.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key

        return items

    def mark_playlist_rebalanced(
        self, user_id: str, playlist_id: str, rebalanced_at: str
    ) -> None:
        """Clear needsRebalance flag and record lastRebalancedAt."""
        self.playlists_table.update_item(
            Key={"userId": user_id, "playlistId": playlist_id},
            UpdateExpression=(
                "SET needsRebalance = :f, lastRebalancedAt = :ts, updatedAt = :ts"
            ),
            ExpressionAttributeValues={":f": False, ":ts": rebalanced_at},
        )
