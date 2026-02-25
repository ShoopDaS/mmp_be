"""
Create DynamoDB tables for the custom playlists feature.

Tables created:
    mmp_custom_playlists  - User playlist metadata (PK: userId, SK: playlistId)
    mmp_playlist_tracks   - Tracks within each playlist (PK: playlistId, SK: order#trackId)

Usage:
    python scripts/create_custom_playlists_tables.py
"""
import boto3
import sys

DYNAMODB_ENDPOINT = "http://127.0.0.1:8000"
REGION = "eu-west-1"
PLAYLISTS_TABLE = "mmp_custom_playlists"
TRACKS_TABLE = "mmp_playlist_tracks"


def create_custom_playlists_table(client):
    """
    mmp_custom_playlists
    PK: userId (String) — internal MMP user ID
    SK: playlistId (String) — UUID generated on creation
    """
    try:
        client.describe_table(TableName=PLAYLISTS_TABLE)
        print(f"Table '{PLAYLISTS_TABLE}' already exists.")
        return
    except client.exceptions.ResourceNotFoundException:
        pass

    print(f"Creating table '{PLAYLISTS_TABLE}'...")
    client.create_table(
        TableName=PLAYLISTS_TABLE,
        KeySchema=[
            {"AttributeName": "userId", "KeyType": "HASH"},
            {"AttributeName": "playlistId", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "userId", "AttributeType": "S"},
            {"AttributeName": "playlistId", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=PLAYLISTS_TABLE)
    print(f"Table '{PLAYLISTS_TABLE}' created.")


def create_playlist_tracks_table(client):
    """
    mmp_playlist_tracks
    PK: playlistId (String)
    SK: order#trackId (String) — e.g. '0000001000#abc123'
         Zero-padded order (10 digits) + '#' + platform-native trackId
    """
    try:
        client.describe_table(TableName=TRACKS_TABLE)
        print(f"Table '{TRACKS_TABLE}' already exists.")
        return
    except client.exceptions.ResourceNotFoundException:
        pass

    print(f"Creating table '{TRACKS_TABLE}'...")
    client.create_table(
        TableName=TRACKS_TABLE,
        KeySchema=[
            {"AttributeName": "playlistId", "KeyType": "HASH"},
            {"AttributeName": "order#trackId", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "playlistId", "AttributeType": "S"},
            {"AttributeName": "order#trackId", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=TRACKS_TABLE)
    print(f"Table '{TRACKS_TABLE}' created.")


def verify_tables(client):
    for table_name in [PLAYLISTS_TABLE, TRACKS_TABLE]:
        try:
            desc = client.describe_table(TableName=table_name)
            status = desc["Table"]["TableStatus"]
            keys = [
                f"{k['AttributeName']} ({k['KeyType']})"
                for k in desc["Table"]["KeySchema"]
            ]
            print(f"  {table_name}: {status} — keys: {', '.join(keys)}")
        except Exception as e:
            print(f"  {table_name}: ERROR — {e}")


if __name__ == "__main__":
    try:
        client = boto3.client(
            "dynamodb",
            endpoint_url=DYNAMODB_ENDPOINT,
            region_name=REGION,
        )
        print("Verifying connection to DynamoDB Local...")
        client.list_tables()
        print("Connected.\n")

        create_custom_playlists_table(client)
        create_playlist_tracks_table(client)

        print("\nVerifying tables:")
        verify_tables(client)
        print("\nDone! Both tables are ready.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure DynamoDB Local is running on http://127.0.0.1:8000")
        sys.exit(1)
