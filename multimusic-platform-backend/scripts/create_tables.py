"""
Create DynamoDB tables for local development using Docker Compose setup
"""
import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to DynamoDB Local (Docker Compose)
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://127.0.0.1:8000',  # Docker Compose exposes on localhost:8000
    region_name='us-east-1',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)


def create_users_table():
    """
    Create single users table with composite key (userId, sk)
    This table stores everything: user profiles, auth providers, and platform tokens
    """
    table_name = os.environ.get('DYNAMODB_TABLE', 'multimusic-users')
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'userId', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'sk', 'KeyType': 'RANGE'}      # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'userId', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        table.wait_until_exists()
        print(f"✅ Created table: {table_name}")
        print(f"   Primary Key: userId (Hash), sk (Range)")
        print(f"   Purpose: Stores user profiles, auth providers, and platform connections")
        
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"⚠️  Table {table_name} already exists")


def list_tables():
    """List all tables"""
    client = dynamodb.meta.client
    response = client.list_tables()
    
    print("\n📋 Existing tables in DynamoDB Local:")
    if response['TableNames']:
        for table_name in response['TableNames']:
            print(f"  - {table_name}")
    else:
        print("  (none)")


def describe_table():
    """Show table structure"""
    table_name = os.environ.get('DYNAMODB_TABLE', 'multimusic-users')
    
    try:
        client = dynamodb.meta.client
        response = client.describe_table(TableName=table_name)
        
        print(f"\n📊 Table structure for: {table_name}")
        print(f"   Status: {response['Table']['TableStatus']}")
        print(f"   Item count: {response['Table']['ItemCount']}")
        print(f"   Key schema:")
        for key in response['Table']['KeySchema']:
            print(f"     - {key['AttributeName']} ({key['KeyType']})")
            
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        print(f"\n❌ Table {table_name} not found")


def verify_connection():
    """Verify connection to DynamoDB Local"""
    try:
        client = dynamodb.meta.client
        client.list_tables()
        print("✅ Successfully connected to DynamoDB Local at http://127.0.0.1:8000")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to DynamoDB Local: {str(e)}")
        print("\n💡 Make sure Docker Compose is running:")
        print("   cd ~/Projects/mmp_be/multimusic-platform-backend/local")
        print("   docker-compose up -d")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("DynamoDB Local Table Setup (Docker Compose)")
    print("=" * 60)
    print()
    
    # Verify connection first
    if not verify_connection():
        exit(1)
    
    print("\nCreating tables...\n")
    create_users_table()
    
    list_tables()
    describe_table()
    
    print("\n" + "=" * 60)
    print("✨ Setup complete!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Start your backend: python main.py")
    print("   2. View tables in DynamoDB Admin: http://127.0.0.1:8001")
    print()
