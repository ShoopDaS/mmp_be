"""
Create DynamoDB tables for local development
"""
import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to DynamoDB Local
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=os.environ.get('DYNAMODB_ENDPOINT', 'http://localhost:8000'),
    region_name='us-east-1',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)


def create_users_table():
    """Create users table"""
    table_name = os.environ.get('DYNAMODB_TABLE_USERS', 'multimusic-users')
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}       # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")
        
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"⚠️  Table {table_name} already exists")


def create_tokens_table():
    """Create tokens table"""
    table_name = os.environ.get('DYNAMODB_TABLE_TOKENS', 'multimusic-tokens')
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}       # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")
        
        # Note: TTL is not supported in DynamoDB Local
        # In production AWS, you can enable it via console or UpdateTimeToLive API
        
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"⚠️  Table {table_name} already exists")


def list_tables():
    """List all tables"""
    client = dynamodb.meta.client
    response = client.list_tables()
    
    print("\n📋 Existing tables:")
    for table_name in response['TableNames']:
        print(f"  - {table_name}")


if __name__ == '__main__':
    print("Creating DynamoDB tables...\n")
    
    create_users_table()
    create_tokens_table()
    
    list_tables()
    
    print("\n✨ Done!")