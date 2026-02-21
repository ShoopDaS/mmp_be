"""
Create the multimusic-playlists DynamoDB table for local development.

Usage:
    python scripts/create_playlists_table.py

This creates the table in DynamoDB Local (http://127.0.0.1:8000)
with TTL enabled on the 'ttl' attribute for automatic cache expiry.

Table schema:
    PK: userId (String)     - Internal MMP user ID (mmp_<uuid>)
    SK: sk (String)         - Sort key with prefixes:
        cache#youtube#<playlist_id>       - Cached YouTube playlists (24h TTL)
        cache#soundcloud#<playlist_id>    - Cached SoundCloud playlists (24h TTL)
        custom#<mmp_playlist_id>          - Custom cross-platform playlists (no TTL)
"""
import boto3
import sys


DYNAMODB_ENDPOINT = "http://127.0.0.1:8000"
REGION = "eu-west-1"
TABLE_NAME = "multimusic-playlists"


def create_table():
    """Create the multimusic-playlists table in DynamoDB Local"""
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=REGION,
    )

    # Check if table already exists
    try:
        existing = dynamodb.describe_table(TableName=TABLE_NAME)
        print(f"Table '{TABLE_NAME}' already exists. Status: {existing['Table']['TableStatus']}")

        # Check if TTL is enabled
        ttl_desc = dynamodb.describe_time_to_live(TableName=TABLE_NAME)
        ttl_status = ttl_desc['TimeToLiveDescription']['TimeToLiveStatus']
        print(f"TTL status: {ttl_status}")

        if ttl_status != 'ENABLED':
            enable_ttl(dynamodb)

        return
    except dynamodb.exceptions.ResourceNotFoundException:
        pass

    # Create the table
    print(f"Creating table '{TABLE_NAME}'...")

    dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'userId', 'KeyType': 'HASH'},   # Partition key
            {'AttributeName': 'sk', 'KeyType': 'RANGE'},       # Sort key
        ],
        AttributeDefinitions=[
            {'AttributeName': 'userId', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
        ],
        BillingMode='PAY_PER_REQUEST',
    )

    # Wait for table to become active
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName=TABLE_NAME)
    print(f"Table '{TABLE_NAME}' created successfully.")

    # Enable TTL
    enable_ttl(dynamodb)


def enable_ttl(dynamodb):
    """Enable TTL on the 'ttl' attribute"""
    try:
        dynamodb.update_time_to_live(
            TableName=TABLE_NAME,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl',
            }
        )
        print("TTL enabled on 'ttl' attribute (24h expiry for cached playlists).")
    except Exception as e:
        # DynamoDB Local may not fully support TTL, but we set it anyway
        print(f"TTL configuration note: {e}")
        print("(DynamoDB Local may not enforce TTL deletion, but the attribute is recognized.)")


def verify_table():
    """Verify the table was created correctly"""
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=REGION,
    )

    table = dynamodb.Table(TABLE_NAME)
    print(f"\nTable verification:")
    print(f"  Name: {table.table_name}")
    print(f"  Status: {table.table_status}")
    print(f"  Item count: {table.item_count}")
    print(f"  Key schema: {table.key_schema}")


if __name__ == "__main__":
    try:
        create_table()
        verify_table()
        print(f"\nDone! Table '{TABLE_NAME}' is ready.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure DynamoDB Local is running on http://127.0.0.1:8000")
        sys.exit(1)
