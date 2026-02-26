"""
Inspect mmp_custom_playlists and mmp_playlist_tracks tables in DynamoDB Local.

Usage:
    python local/inspect_custom_playlists.py
"""
import json
import boto3
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://127.0.0.1:8000",
    region_name="eu-west-1",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

SEP = "=" * 70


def scan_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        items = []
        resp = table.scan()
        items.extend(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
        return items
    except Exception as e:
        print(f"  ERROR scanning {table_name}: {e}")
        return []


# ── mmp_custom_playlists ─────────────────────────────────────────────────────
print(SEP)
print("TABLE: mmp_custom_playlists")
print(SEP)

playlists = scan_table("mmp_custom_playlists")
print(f"Total playlists: {len(playlists)}\n")

for p in playlists:
    print(f"  userId     : {p.get('userId')}")
    print(f"  playlistId : {p.get('playlistId')}")
    print(f"  name       : {p.get('name')}")
    print(f"  trackCount : {p.get('trackCount')}")
    print(f"  needsRebal : {p.get('needsRebalance')}")
    print(f"  createdAt  : {p.get('createdAt')}")
    print()

# ── mmp_playlist_tracks ──────────────────────────────────────────────────────
print(SEP)
print("TABLE: mmp_playlist_tracks")
print(SEP)

tracks = scan_table("mmp_playlist_tracks")
print(f"Total tracks: {len(tracks)}\n")

# Group by playlistId
by_playlist: dict = {}
for t in tracks:
    pid = t.get("playlistId", "?")
    by_playlist.setdefault(pid, []).append(t)

for pid, ptracks in by_playlist.items():
    print(f"  playlistId: {pid}  ({len(ptracks)} track(s))")
    for t in sorted(ptracks, key=lambda x: str(x.get("order#trackId", ""))):
        print(f"    SK        : {t.get('order#trackId')}")
        print(f"    trackId   : {t.get('trackId')!r}")
        print(f"    platform  : {t.get('platform')}")
        print(f"    name      : {t.get('name')}")
        print(f"    order     : {t.get('order')}")
        print()
