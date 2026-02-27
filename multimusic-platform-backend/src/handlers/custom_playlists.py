"""
Custom Playlist Lambda Handlers.

Endpoints:
    GET    /user/playlists                              — list user playlists
    POST   /user/playlists                              — create playlist
    PUT    /user/playlists/:playlistId                  — update playlist metadata
    DELETE /user/playlists/:playlistId                  — delete playlist + all tracks

    GET    /user/playlists/:playlistId/tracks           — list tracks (full, no client pagination)
    POST   /user/playlists/:playlistId/tracks           — add track
    DELETE /user/playlists/:playlistId/tracks/:trackId  — remove track
    PUT    /user/playlists/:playlistId/tracks/reorder   — reorder tracks

Auth: Bearer session token required for all endpoints.
      userId is ALWAYS taken from the token — never from the request body or URL.
"""
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.constants.playlist import (
    COVER_EMOJI_OPTIONS,
    DEFAULT_COVER,
    PLAYLIST_DESC_MAX_LEN,
    PLAYLIST_NAME_MAX_LEN,
)
from src.services.custom_playlist_service import CustomPlaylistService, _build_track_sk
from src.services.jwt_service import JWTService
from src.utils.responses import error_response, success_response
from src.utils.sanitize import sanitize_text

logger = Logger()

jwt_service = JWTService()
playlist_service = CustomPlaylistService()


# ========== Auth Helper ==========

def _get_user_id(event: Dict[str, Any]) -> str:
    """
    Extract and verify user ID from Bearer token in Authorization header.

    Raises ValueError if token is missing or invalid.
    """
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""

    if not auth_header or not auth_header.startswith("Bearer "):
        raise ValueError("No valid authorization header")

    session_token = auth_header[7:]
    user_id = jwt_service.verify_token(session_token)

    if not user_id:
        raise ValueError("Invalid session token")

    return user_id


# ========== Serialization Helper ==========

def _serialize(obj: Any) -> Any:
    """Recursively convert Decimal to int/float for JSON serialization."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(v) for v in obj]
    return obj


# ========== Ownership Verification ==========

def _verify_ownership(user_id: str, playlist_id: str) -> Optional[Dict[str, Any]]:
    """
    Verify that playlist_id belongs to user_id.

    Returns the playlist item if ownership is confirmed, None otherwise.
    Raises RuntimeError on unexpected DB errors.
    """
    playlist = playlist_service.get_playlist(user_id, playlist_id)
    return playlist  # None means either not found or wrong owner


# ========== Playlist Endpoints ==========

@logger.inject_lambda_context
def get_playlists_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    GET /user/playlists
    Return all custom playlists for the authenticated user.
    """
    try:
        user_id = _get_user_id(event)
        playlists = playlist_service.list_playlists(user_id)
        return success_response({"playlists": _serialize(playlists)})

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception:
        logger.exception("Error listing playlists")
        return error_response("Internal server error", 500)


@logger.inject_lambda_context
def create_playlist_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    POST /user/playlists
    Body: { name: string, coverImage?: string, description?: string }
    """
    try:
        user_id = _get_user_id(event)

        body = json.loads(event.get("body") or "{}")

        # --- name ---
        name = sanitize_text(body.get("name", ""))
        if not name:
            return error_response("name is required", 400)
        if len(name) > PLAYLIST_NAME_MAX_LEN:
            return error_response(
                f"name must be {PLAYLIST_NAME_MAX_LEN} characters or fewer", 400
            )

        # --- coverImage ---
        cover_image_raw = body.get("coverImage")
        if cover_image_raw is None:
            cover_image = DEFAULT_COVER
        elif cover_image_raw not in COVER_EMOJI_OPTIONS:
            return error_response("Invalid coverImage value", 400)
        else:
            cover_image = cover_image_raw

        # --- description ---
        description = sanitize_text(str(body.get("description", "")))
        if len(description) > PLAYLIST_DESC_MAX_LEN:
            return error_response(
                f"description must be {PLAYLIST_DESC_MAX_LEN} characters or fewer", 400
            )

        now = datetime.utcnow().isoformat()
        playlist_id = str(uuid.uuid4())

        item: Dict[str, Any] = {
            "userId": user_id,
            "playlistId": playlist_id,
            "name": name,
            "coverImage": cover_image,
            "description": description,
            "trackCount": 0,
            "needsRebalance": False,
            "createdAt": now,
            "updatedAt": now,
        }

        playlist_service.create_playlist(item)
        return success_response({"playlist": _serialize(item)}, 201)

    except ValueError as e:
        return error_response(str(e), 401)
    except json.JSONDecodeError:
        return error_response("Invalid JSON body", 400)
    except Exception:
        logger.exception("Error creating playlist")
        return error_response("Internal server error", 500)


@logger.inject_lambda_context
def update_playlist_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    PUT /user/playlists/:playlistId
    Body: { name?: string, coverImage?: string, description?: string }
    """
    try:
        user_id = _get_user_id(event)

        path_params = event.get("pathParameters", {}) or {}
        playlist_id = path_params.get("playlistId") or path_params.get("playlist_id")
        if not playlist_id:
            return error_response("playlistId is required", 400)

        # Verify ownership
        existing = _verify_ownership(user_id, playlist_id)
        if not existing:
            return error_response("Playlist not found", 403)

        body = json.loads(event.get("body") or "{}")

        updates: Dict[str, Any] = {"updatedAt": datetime.utcnow().isoformat()}

        if "name" in body:
            name = sanitize_text(str(body["name"]))
            if not name:
                return error_response("name cannot be empty", 400)
            if len(name) > PLAYLIST_NAME_MAX_LEN:
                return error_response(
                    f"name must be {PLAYLIST_NAME_MAX_LEN} characters or fewer", 400
                )
            updates["name"] = name

        if "coverImage" in body:
            if body["coverImage"] not in COVER_EMOJI_OPTIONS:
                return error_response("Invalid coverImage value", 400)
            updates["coverImage"] = body["coverImage"]

        if "description" in body:
            description = sanitize_text(str(body["description"]))
            if len(description) > PLAYLIST_DESC_MAX_LEN:
                return error_response(
                    f"description must be {PLAYLIST_DESC_MAX_LEN} characters or fewer", 400
                )
            updates["description"] = description

        if len(updates) == 1:
            # Only updatedAt — nothing to update
            return success_response({"playlist": _serialize(existing)})

        updated = playlist_service.update_playlist(user_id, playlist_id, updates)
        return success_response({"playlist": _serialize(updated)})

    except ValueError as e:
        return error_response(str(e), 401)
    except json.JSONDecodeError:
        return error_response("Invalid JSON body", 400)
    except Exception:
        logger.exception("Error updating playlist")
        return error_response("Internal server error", 500)


@logger.inject_lambda_context
def delete_playlist_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    DELETE /user/playlists/:playlistId
    Deletes the playlist metadata and all its track items.
    """
    try:
        user_id = _get_user_id(event)

        path_params = event.get("pathParameters", {}) or {}
        playlist_id = path_params.get("playlistId") or path_params.get("playlist_id")
        if not playlist_id:
            return error_response("playlistId is required", 400)

        # Verify ownership
        existing = _verify_ownership(user_id, playlist_id)
        if not existing:
            return error_response("Playlist not found", 403)

        # Delete all tracks first, then playlist metadata
        playlist_service.delete_all_tracks(playlist_id)
        playlist_service.delete_playlist(user_id, playlist_id)

        return success_response({"message": "Playlist deleted"})

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception:
        logger.exception("Error deleting playlist")
        return error_response("Internal server error", 500)


# ========== Track Endpoints ==========

@logger.inject_lambda_context
def get_tracks_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    GET /user/playlists/:playlistId/tracks
    Returns the full track list in a single response (pagination handled internally).
    """
    try:
        user_id = _get_user_id(event)

        path_params = event.get("pathParameters", {}) or {}
        playlist_id = path_params.get("playlistId") or path_params.get("playlist_id")
        if not playlist_id:
            return error_response("playlistId is required", 400)

        # Verify ownership
        if not _verify_ownership(user_id, playlist_id):
            return error_response("Playlist not found", 403)

        tracks = playlist_service.get_all_tracks(playlist_id)
        return success_response({"tracks": _serialize(tracks)})

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception:
        logger.exception("Error listing tracks")
        return error_response("Internal server error", 500)


@logger.inject_lambda_context
def add_track_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    POST /user/playlists/:playlistId/tracks
    Body: { trackId, platform, name, uri, artists, albumName, albumImageUrl,
            duration_ms, preview_url }
    """
    try:
        user_id = _get_user_id(event)

        path_params = event.get("pathParameters", {}) or {}
        playlist_id = path_params.get("playlistId") or path_params.get("playlist_id")
        if not playlist_id:
            return error_response("playlistId is required", 400)

        # Verify ownership
        if not _verify_ownership(user_id, playlist_id):
            return error_response("Playlist not found", 403)

        body = json.loads(event.get("body") or "{}")

        required = ["trackId", "platform", "name", "uri"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return error_response(f"Missing required fields: {', '.join(missing)}", 400)

        platform = body["platform"]
        if platform not in ("spotify", "youtube", "soundcloud"):
            return error_response(
                "platform must be 'spotify', 'youtube', or 'soundcloud'", 400
            )

        # Determine order: last order + 1000, or 1000 if empty
        last_track = playlist_service.get_last_track(playlist_id)
        if last_track:
            last_order = int(last_track.get("order", 0))
            order = last_order + 1000
        else:
            order = 1000

        track_id = body["trackId"]
        sk = _build_track_sk(order, track_id)
        now = datetime.utcnow().isoformat()

        track_item: Dict[str, Any] = {
            "playlistId": playlist_id,
            "order#trackId": sk,
            "order": order,
            "trackId": track_id,
            "platform": platform,
            "name": body["name"],
            "uri": body["uri"],
            "artists": body.get("artists", []),
            "albumName": body.get("albumName", ""),
            "albumImageUrl": body.get("albumImageUrl", ""),
            "duration_ms": body.get("duration_ms", 0),
            "preview_url": body.get("preview_url"),
            "addedAt": now,
        }

        playlist_service.add_track(track_item)
        playlist_service.increment_track_count(user_id, playlist_id, now)

        return success_response({"track": _serialize(track_item)}, 201)

    except ValueError as e:
        return error_response(str(e), 401)
    except json.JSONDecodeError:
        return error_response("Invalid JSON body", 400)
    except Exception:
        logger.exception("Error adding track")
        return error_response("Internal server error", 500)


@logger.inject_lambda_context
def delete_track_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    DELETE /user/playlists/:playlistId/tracks/:trackId
    Finds the track by trackId, deletes it, and decrements trackCount.
    Returns 204 No Content on success.
    """
    try:
        user_id = _get_user_id(event)

        path_params = event.get("pathParameters", {}) or {}
        playlist_id = path_params.get("playlistId") or path_params.get("playlist_id")
        track_id = path_params.get("trackId") or path_params.get("track_id")

        if not playlist_id:
            return error_response("playlistId is required", 400)
        if not track_id:
            return error_response("trackId is required", 400)

        # Verify ownership
        if not _verify_ownership(user_id, playlist_id):
            return error_response("Playlist not found", 403)

        # Find the track's full SK
        track = playlist_service.find_track_by_track_id(playlist_id, track_id)
        if not track:
            return error_response("Track not found in playlist", 404)

        sk = track["order#trackId"]
        playlist_service.delete_track(playlist_id, sk)

        now = datetime.utcnow().isoformat()
        playlist_service.decrement_track_count(user_id, playlist_id, now)

        return success_response(None, 204)

    except ValueError as e:
        return error_response(str(e), 401)
    except Exception:
        logger.exception("Error deleting track")
        return error_response("Internal server error", 500)


@logger.inject_lambda_context
def reorder_tracks_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    PUT /user/playlists/:playlistId/tracks/reorder
    Body: [{ "trackId": string, "order": number }]

    For each entry: updates order field and rebuilds the SK.
    After writing, checks for gaps < 10 and sets needsRebalance if found.
    Uses BatchWriteItem (25 ops per call).
    """
    try:
        user_id = _get_user_id(event)

        path_params = event.get("pathParameters", {}) or {}
        playlist_id = path_params.get("playlistId") or path_params.get("playlist_id")
        if not playlist_id:
            return error_response("playlistId is required", 400)

        # Verify ownership
        if not _verify_ownership(user_id, playlist_id):
            return error_response("Playlist not found", 403)

        body = json.loads(event.get("body") or "[]")
        if not isinstance(body, list) or not body:
            return error_response("Body must be a non-empty array of {trackId, order}", 400)

        # Validate entries
        for entry in body:
            if "trackId" not in entry or "order" not in entry:
                return error_response(
                    "Each entry must have 'trackId' and 'order'", 400
                )
            if not isinstance(entry["order"], (int, float)) or entry["order"] < 0:
                return error_response("order must be a non-negative number", 400)

        # Build a map of trackId -> current track item
        all_current_tracks = playlist_service.get_all_tracks(playlist_id)
        current_map: Dict[str, Dict[str, Any]] = {
            t["trackId"]: t for t in all_current_tracks
        }

        deletes: List[tuple] = []
        puts: List[Dict[str, Any]] = []
        new_orders: List[int] = []

        for entry in body:
            tid = entry["trackId"]
            new_order = int(entry["order"])
            new_orders.append(new_order)

            current = current_map.get(tid)
            if not current:
                logger.warning(
                    f"Track {tid} not found in playlist {playlist_id} — skipping"
                )
                continue

            old_sk = current["order#trackId"]
            new_sk = _build_track_sk(new_order, tid)

            if old_sk == new_sk:
                # Order unchanged — nothing to do for this track
                continue

            deletes.append((playlist_id, old_sk))

            updated = dict(current)
            updated["order"] = new_order
            updated["order#trackId"] = new_sk
            puts.append(updated)

        if deletes or puts:
            playlist_service.batch_write_track_reorder(deletes, puts)

        # Check minimum gap between adjacent new_orders
        now = datetime.utcnow().isoformat()
        if len(new_orders) > 1:
            sorted_orders = sorted(new_orders)
            min_gap = min(
                sorted_orders[i + 1] - sorted_orders[i]
                for i in range(len(sorted_orders) - 1)
            )
            if min_gap < 10:
                playlist_service.set_needs_rebalance(user_id, playlist_id, True, now)
                logger.info(
                    f"Playlist {playlist_id} flagged for rebalance "
                    f"(min gap={min_gap})"
                )

        return success_response({"message": "Tracks reordered"})

    except ValueError as e:
        return error_response(str(e), 401)
    except json.JSONDecodeError:
        return error_response("Invalid JSON body", 400)
    except Exception:
        logger.exception("Error reordering tracks")
        return error_response("Internal server error", 500)
