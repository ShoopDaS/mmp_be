"""
Scheduled Rebalance Job — EventBridge + Lambda.

Fires every 24 hours via an EventBridge rule.

Logic:
  1. Scan mmp_custom_playlists for items where needsRebalance = true  (priority pass).
  2. Scan for playlists where lastRebalancedAt is older than 7 days (safety-net pass).
  3. For each playlist to rebalance:
       a. Query all tracks sorted ascending by SK.
       b. Reassign order = (index + 1) * 1000  →  1000, 2000, 3000 …
       c. Rebuild SK: zero-padded new order + '#' + trackId.
       d. BatchWriteItem (delete old SK, put new item) in groups of 25.
       e. Set needsRebalance = false, lastRebalancedAt = now on playlist metadata.

Conflict strategy: last-write-wins (no locking required for initial build).

AWS EventBridge rule (terraform / CDK / console — not provisioned here):
    schedule_expression = "rate(24 hours)"
    target = this Lambda function ARN
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.services.custom_playlist_service import CustomPlaylistService, _build_track_sk

logger = Logger()

playlist_service = CustomPlaylistService()

# Safety-net window: rebalance playlists not touched in this many days
STALE_DAYS = 7


@logger.inject_lambda_context
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda entry point — invoked by EventBridge on a 24-hour schedule.

    Returns a summary dict with counts of playlists processed and tracks rewritten.
    """
    logger.info("Rebalance job started")

    now_iso = datetime.utcnow().isoformat()
    stale_cutoff = (datetime.utcnow() - timedelta(days=STALE_DAYS)).isoformat()

    # ---- Pass 1: playlists explicitly flagged --------------------------------
    flagged = playlist_service.scan_playlists_needing_rebalance()
    logger.info(f"Found {len(flagged)} playlist(s) flagged needsRebalance=true")

    # ---- Pass 2: playlists that are stale (safety net) ----------------------
    stale = playlist_service.scan_playlists_stale(stale_cutoff)
    logger.info(f"Found {len(stale)} stale playlist(s) (lastRebalancedAt < {stale_cutoff})")

    # Deduplicate by playlistId (flagged takes priority — already included)
    seen_ids = {p["playlistId"] for p in flagged}
    candidates = list(flagged)
    for p in stale:
        if p["playlistId"] not in seen_ids:
            candidates.append(p)
            seen_ids.add(p["playlistId"])

    if not candidates:
        logger.info("No playlists to rebalance — exiting")
        return {"rebalanced": 0, "tracksRewritten": 0}

    total_tracks_rewritten = 0

    for playlist in candidates:
        user_id = playlist["userId"]
        playlist_id = playlist["playlistId"]

        try:
            tracks_rewritten = _rebalance_playlist(user_id, playlist_id, now_iso)
            total_tracks_rewritten += tracks_rewritten
            logger.info(
                f"Rebalanced playlist {playlist_id} "
                f"(user {user_id}, {tracks_rewritten} track(s) rewritten)"
            )
        except Exception:
            logger.exception(
                f"Failed to rebalance playlist {playlist_id} (user {user_id})"
            )
            # Continue with remaining playlists even if one fails

    logger.info(
        f"Rebalance job complete — "
        f"{len(candidates)} playlist(s), {total_tracks_rewritten} track(s) rewritten"
    )
    return {
        "rebalanced": len(candidates),
        "tracksRewritten": total_tracks_rewritten,
    }


def _rebalance_playlist(user_id: str, playlist_id: str, now_iso: str) -> int:
    """
    Rebalance a single playlist.

    Steps:
      - Load all tracks sorted by SK ascending.
      - Reassign order = (index + 1) * 1000.
      - Rebuild SK for each track.
      - BatchWriteItem: delete old SK items, put new ones.
      - Mark playlist as rebalanced.

    Returns the number of tracks rewritten.
    """
    tracks = playlist_service.get_all_tracks(playlist_id)

    if not tracks:
        # Nothing to rebalance — just clear the flag
        playlist_service.mark_playlist_rebalanced(user_id, playlist_id, now_iso)
        return 0

    deletes: List[tuple] = []
    puts: List[Dict[str, Any]] = []

    for index, track in enumerate(tracks):
        new_order = (index + 1) * 1000
        new_sk = _build_track_sk(new_order, track["trackId"])
        old_sk = track["order#trackId"]

        if old_sk == new_sk:
            # Already in the correct position — no write needed
            continue

        deletes.append((playlist_id, old_sk))

        updated = dict(track)
        updated["order"] = new_order
        updated["order#trackId"] = new_sk
        puts.append(updated)

    if deletes or puts:
        playlist_service.batch_write_track_reorder(deletes, puts)

    playlist_service.mark_playlist_rebalanced(user_id, playlist_id, now_iso)

    return len(puts)
