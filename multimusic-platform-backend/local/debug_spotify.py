"""
Comprehensive Spotify Connection Debugger
"""
import requests
import json

print("="*70)
print("SPOTIFY CONNECTION DEBUGGER")
print("="*70)

# Get session token
print("\n📋 Instructions:")
print("1. Open http://127.0.0.1:3000 in your browser")
print("2. Press F12 → Application → Local Storage")
print("3. Copy the 'session_token' value")
print()

SESSION_TOKEN = input("Enter your session token: ").strip()

if not SESSION_TOKEN:
    print("❌ No token provided!")
    exit(1)

# Test 1: Get user profile
print("\n" + "="*70)
print("TEST 1: User Profile")
print("="*70)

resp = requests.get(
    'http://127.0.0.1:8080/user/profile',
    headers={'Authorization': f'Bearer {SESSION_TOKEN}'}
)

if resp.status_code == 200:
    profile = resp.json().get('data', {})
    print(f"✅ User Profile Retrieved")
    print(f"   User ID: {profile.get('userId')}")
    print(f"   Email: {profile.get('email')}")
    print(f"   Name: {profile.get('displayName')}")
else:
    print(f"❌ Failed to get profile: {resp.status_code}")
    print(resp.text)
    exit(1)

# Test 2: Check connected platforms
print("\n" + "="*70)
print("TEST 2: Connected Platforms")
print("="*70)

resp = requests.get(
    'http://127.0.0.1:8080/user/platforms',
    headers={'Authorization': f'Bearer {SESSION_TOKEN}'}
)

if resp.status_code == 200:
    platforms = resp.json().get('data', {}).get('platforms', [])
    print(f"✅ Found {len(platforms)} connected platform(s)")
    
    spotify_connected = False
    for platform in platforms:
        print(f"\n   Platform: {platform.get('platform')}")
        print(f"   Platform User ID: {platform.get('platformUserId')}")
        print(f"   Connected At: {platform.get('connectedAt')}")
        print(f"   Scopes: {platform.get('scope')}")
        
        if platform.get('platform') == 'spotify':
            spotify_connected = True
            spotify_user_id = platform.get('platformUserId')
    
    if not spotify_connected:
        print("\n❌ Spotify is NOT connected!")
        print("   Please connect Spotify from the dashboard")
        exit(1)
else:
    print(f"❌ Failed to get platforms: {resp.status_code}")
    exit(1)

# Test 3: Refresh Spotify token
print("\n" + "="*70)
print("TEST 3: Spotify Token Refresh")
print("="*70)

resp = requests.post(
    'http://127.0.0.1:8080/platforms/spotify/refresh',
    headers={'Authorization': f'Bearer {SESSION_TOKEN}'}
)

if resp.status_code == 200:
    token_data = resp.json().get('data', {})
    access_token = token_data.get('accessToken')
    expires_in = token_data.get('expiresIn')
    
    print(f"✅ Token Refresh Successful")
    print(f"   Access Token: {access_token[:20]}...{access_token[-10:]}")
    print(f"   Expires In: {expires_in} seconds ({expires_in/60:.1f} minutes)")
else:
    print(f"❌ Token refresh failed: {resp.status_code}")
    print(resp.text)
    exit(1)

# Test 4: Verify token with Spotify API
print("\n" + "="*70)
print("TEST 4: Spotify API - Current User")
print("="*70)

resp = requests.get(
    'https://api.spotify.com/v1/me',
    headers={'Authorization': f'Bearer {access_token}'}
)

if resp.status_code == 200:
    spotify_user = resp.json()
    print(f"✅ Spotify API Accepts Token")
    print(f"   Spotify User ID: {spotify_user.get('id')}")
    print(f"   Display Name: {spotify_user.get('display_name')}")
    print(f"   Email: {spotify_user.get('email')}")
    print(f"   Country: {spotify_user.get('country')}")
    print(f"   Product: {spotify_user.get('product')} (free/premium/open)")
    
    # Compare user IDs
    print(f"\n   📊 User ID Comparison:")
    print(f"   Stored in DB: {spotify_user_id}")
    print(f"   From Spotify: {spotify_user.get('id')}")
    
    if spotify_user_id == spotify_user.get('id'):
        print(f"   ✅ User IDs MATCH - correct account connected")
    else:
        print(f"   ⚠️  User IDs DON'T MATCH - different Spotify account!")
        print(f"   This might explain why old data doesn't work")
else:
    print(f"❌ Spotify API rejected token: {resp.status_code}")
    print(resp.text)
    exit(1)

# Test 5: Search for a specific track
print("\n" + "="*70)
print("TEST 5: Spotify Search")
print("="*70)

search_query = input("\nEnter a song to search for (or press Enter for 'Bohemian Rhapsody'): ").strip()
if not search_query:
    search_query = "Bohemian Rhapsody"

resp = requests.get(
    f'https://api.spotify.com/v1/search?q={search_query}&type=track&limit=10',
    headers={'Authorization': f'Bearer {access_token}'}
)

if resp.status_code == 200:
    results = resp.json()
    tracks = results.get('tracks', {}).get('items', [])
    
    print(f"\n✅ Search Successful - Found {len(tracks)} tracks")
    print(f"\n{'#':<3} {'Track Name':<40} {'Artist':<30} {'Preview':<10}")
    print("-" * 85)
    
    for i, track in enumerate(tracks, 1):
        name = track['name'][:38]
        artist = track['artists'][0]['name'][:28]
        has_preview = "✅ YES" if track.get('preview_url') else "❌ NO"
        
        print(f"{i:<3} {name:<40} {artist:<30} {has_preview:<10}")
        
        if track.get('preview_url'):
            print(f"    Preview URL: {track['preview_url']}")
    
    preview_count = sum(1 for t in tracks if t.get('preview_url'))
    
    print("\n" + "-" * 85)
    print(f"📊 Summary: {preview_count}/{len(tracks)} tracks have preview URLs")
    
    if preview_count == 0:
        print("\n⚠️  WARNING: No tracks have previews!")
        print("   This could indicate:")
        print("   - Regional restrictions")
        print("   - Account type limitations")
        print("   - Spotify catalog changes")
    elif preview_count < len(tracks) / 2:
        print("\n⚠️  Low preview availability")
        print("   This is common for older or less popular tracks")
    else:
        print("\n✅ Good preview availability - system working correctly!")
        
else:
    print(f"❌ Search failed: {resp.status_code}")
    print(resp.text)
    exit(1)

# Test 6: Check specific track by ID (if user wants)
print("\n" + "="*70)
print("TEST 6: Check Specific Track")
print("="*70)

track_id = input("\nEnter a Spotify track ID to check (or press Enter to skip): ").strip()

if track_id:
    resp = requests.get(
        f'https://api.spotify.com/v1/tracks/{track_id}',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    
    if resp.status_code == 200:
        track = resp.json()
        print(f"\n✅ Track Found:")
        print(f"   Name: {track['name']}")
        print(f"   Artist: {track['artists'][0]['name']}")
        print(f"   Album: {track['album']['name']}")
        print(f"   Preview URL: {track.get('preview_url') or '❌ NOT AVAILABLE'}")
    else:
        print(f"❌ Track not found: {resp.status_code}")

# Final Summary
print("\n" + "="*70)
print("FINAL SUMMARY")
print("="*70)
print(f"""
✅ User Profile: OK
✅ Spotify Connected: OK
✅ Token Refresh: OK
✅ Spotify API: OK
✅ Search: OK

Next Steps:
1. If most tracks have NO previews → Try popular recent songs
2. If preview URLs are null → This is normal Spotify behavior
3. If token was rejected → Reconnect Spotify from dashboard
4. If everything works → Your setup is correct!

Note: Preview availability depends on:
- Artist/Label agreements
- Regional restrictions  
- Account type (free/premium)
- Track catalog metadata

Not having previews for ALL tracks is NORMAL.
""")
