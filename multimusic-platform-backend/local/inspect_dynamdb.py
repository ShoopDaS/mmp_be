"""
Check DynamoDB for user data
"""
import boto3
import json
from datetime import datetime

# Connect to DynamoDB Local
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://127.0.0.1:8000',
    region_name='us-east-1',
    aws_access_key_id='local',
    aws_secret_access_key='local'
)

table = dynamodb.Table('multimusic-users')

print("="*70)
print("DYNAMODB USER DATA INSPECTOR")
print("="*70)

# Scan all items
print("\nScanning database...")
response = table.scan()
items = response.get('Items', [])

print(f"Found {len(items)} total records\n")

# Group by user
users = {}
for item in items:
    user_id = item.get('userId')
    if user_id not in users:
        users[user_id] = []
    users[user_id].append(item)

# Display each user
for user_id, records in users.items():
    print("="*70)
    print(f"USER: {user_id}")
    print("="*70)
    
    for record in records:
        sk = record.get('sk')
        print(f"\n  Record Type: {sk}")
        
        if sk == 'PROFILE':
            print(f"    Email: {record.get('email')}")
            print(f"    Display Name: {record.get('displayName')}")
            print(f"    Primary Auth: {record.get('primaryAuthProvider')}")
            print(f"    Created: {record.get('createdAt')}")
        
        elif sk.startswith('auth#'):
            provider = sk.replace('auth#', '')
            print(f"    Provider: {provider}")
            print(f"    Provider ID: {record.get('providerId')}")
            print(f"    Email: {record.get('email')}")
            print(f"    Linked: {record.get('linked')}")
            print(f"    Linked At: {record.get('linkedAt')}")
        
        elif sk.startswith('platform#'):
            platform = sk.replace('platform#', '')
            print(f"    Platform: {platform}")
            print(f"    Platform User ID: {record.get('platformUserId')}")
            print(f"    Has Access Token: {'✅' if record.get('accessToken') else '❌'}")
            print(f"    Has Refresh Token: {'✅' if record.get('refreshToken') else '❌'}")
            print(f"    Scopes: {record.get('scope', 'N/A')}")
            print(f"    Connected At: {record.get('connectedAt')}")
            print(f"    Expires At: {record.get('expiresAt')}")
        
        else:
            print(f"    Unknown record type: {sk}")
            print(f"    Data: {json.dumps(record, indent=6, default=str)}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

# Count user types
mmp_users = [uid for uid in users.keys() if uid.startswith('mmp_')]
spotify_users = [uid for uid in users.keys() if not uid.startswith('mmp_')]

print(f"\nNew Architecture Users (mmp_*): {len(mmp_users)}")
for uid in mmp_users:
    print(f"  - {uid}")

if spotify_users:
    print(f"\nOld Architecture Users (spotify_*): {len(spotify_users)}")
    print("⚠️  These are from the old system and won't work with new auth!")
    for uid in spotify_users:
        print(f"  - {uid}")
    
    print("\n💡 Recommendation:")
    print("   Delete old records and reconnect Spotify with new system")
    print("   Run: aws dynamodb delete-item --table-name multimusic-users \\")
    print("        --key '{\"userId\":{\"S\":\"OLD_USER_ID\"},\"sk\":{\"S\":\"platform#spotify\"}}' \\")
    print("        --endpoint-url http://127.0.0.1:8000")

print()
