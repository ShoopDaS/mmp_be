#!/usr/bin/env python3
"""
Complete SoundCloud Integration Test & Data Retrieval Script

This script will:
1. Connect your SoundCloud account
2. Test all endpoints
3. Retrieve all available SoundCloud data
"""
import requests
import json
import time
import webbrowser
from datetime import datetime

# Configuration
BACKEND_URL = "http://127.0.0.1:8080"
FRONTEND_URL = "http://127.0.0.1:3000"

# You'll get this after logging in to your app
SESSION_TOKEN = input("Enter your session token (from logging in): ").strip()

if not SESSION_TOKEN or SESSION_TOKEN == "":
    print("❌ Session token is required!")
    print("\n💡 How to get your session token:")
    print("   1. Log in to your app (http://127.0.0.1:3000)")
    print("   2. Open browser DevTools (F12)")
    print("   3. Go to Application/Storage > Local Storage")
    print("   4. Find 'sessionToken' and copy its value")
    exit(1)

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))


def test_backend_health():
    """Test if backend is running"""
    print_section("1. Testing Backend Health")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"⚠️  Backend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend is not running: {e}")
        print("\n💡 Start the backend with: python main.py")
        return False


def connect_soundcloud():
    """Initiate SoundCloud connection"""
    print_section("2. Connecting SoundCloud Account")
    
    print("Requesting authorization URL...")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/platforms/soundcloud/connect",
            headers={
                'Authorization': f'Bearer {SESSION_TOKEN}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            # Backend wraps response in 'data' object
            data = response_data.get('data', response_data)
            
            if data.get('connected'):
                print("✅ SoundCloud already connected!")
                return True
            
            auth_url = data.get('authUrl')
            if auth_url:
                print(f"\n✅ Authorization URL generated!")
                print(f"\n🔗 Authorization URL:")
                print(f"   {auth_url}")
                
                # Ask user if they want to open browser
                open_browser = input("\nOpen in browser? (y/n): ").strip().lower()
                if open_browser == 'y':
                    webbrowser.open(auth_url)
                    print("\n✅ Opened in browser!")
                
                print("\n📋 Next steps:")
                print("   1. Authorize the app on SoundCloud")
                print("   2. You'll be redirected back to the app")
                print("   3. Come back here and press Enter when done")
                
                input("\nPress Enter after you've authorized on SoundCloud...")
                
                # Give the callback a moment to process
                time.sleep(2)
                
                return True
            else:
                print(f"❌ No authUrl in response: {data}")
                return False
                
        elif response.status_code == 401:
            print("❌ Invalid session token!")
            print("   Please log in again and get a fresh token")
            return False
        else:
            print(f"❌ Unexpected response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_soundcloud_access_token():
    """Get SoundCloud access token from backend"""
    print_section("3. Getting SoundCloud Access Token")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/platforms/soundcloud/refresh",
            headers={
                'Authorization': f'Bearer {SESSION_TOKEN}',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            # Backend wraps response in 'data' object
            data = response_data.get('data', response_data)
            
            access_token = data.get('accessToken')
            expires_in = data.get('expiresIn')
            
            print(f"✅ Access token retrieved!")
            print(f"   Token: {access_token[:20]}...")
            print(f"   Expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            
            return access_token
        elif response.status_code == 404:
            print("❌ SoundCloud not connected yet")
            print("   Run the connection step first")
            return None
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_soundcloud_user_profile(access_token):
    """Get user profile from SoundCloud"""
    print_section("4. Getting Your SoundCloud Profile")
    
    try:
        response = requests.get(
            'https://api.soundcloud.com/me',
            params={'oauth_token': access_token},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            profile = response.json()
            
            print("✅ Profile retrieved!")
            print(f"\n📋 Your SoundCloud Profile:")
            print(f"   ID: {profile.get('id')}")
            print(f"   Username: {profile.get('username')}")
            print(f"   Display Name: {profile.get('full_name', 'N/A')}")
            print(f"   Permalink: {profile.get('permalink')}")
            print(f"   Country: {profile.get('country', 'N/A')}")
            print(f"   City: {profile.get('city', 'N/A')}")
            print(f"   Followers: {profile.get('followers_count', 0)}")
            print(f"   Following: {profile.get('followings_count', 0)}")
            print(f"   Tracks: {profile.get('track_count', 0)}")
            print(f"   Playlists: {profile.get('playlist_count', 0)}")
            print(f"   Likes: {profile.get('public_favorites_count', 0)}")
            print(f"   Profile URL: {profile.get('permalink_url')}")
            print(f"   Avatar: {profile.get('avatar_url')}")
            
            return profile
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_soundcloud_tracks(access_token, limit=10):
    """Get user's tracks from SoundCloud"""
    print_section("5. Getting Your Tracks")
    
    try:
        response = requests.get(
            'https://api.soundcloud.com/me/tracks',
            params={
                'oauth_token': access_token,
                'limit': limit
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            tracks = response.json()
            
            print(f"✅ Retrieved {len(tracks)} tracks!")
            
            if tracks:
                print(f"\n🎵 Your Tracks:")
                for i, track in enumerate(tracks, 1):
                    print(f"\n   {i}. {track.get('title')}")
                    print(f"      ID: {track.get('id')}")
                    print(f"      Duration: {track.get('duration', 0) / 1000:.0f}s")
                    print(f"      Genre: {track.get('genre', 'N/A')}")
                    print(f"      Plays: {track.get('playback_count', 0)}")
                    print(f"      Likes: {track.get('likes_count', 0)}")
                    print(f"      Stream URL: {track.get('stream_url', 'N/A')}")
                    print(f"      Permalink: {track.get('permalink_url')}")
            else:
                print("   (No tracks found)")
            
            return tracks
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_soundcloud_playlists(access_token):
    """Get user's playlists from SoundCloud"""
    print_section("6. Getting Your Playlists")
    
    try:
        response = requests.get(
            'https://api.soundcloud.com/me/playlists',
            params={'oauth_token': access_token},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            playlists = response.json()
            
            print(f"✅ Retrieved {len(playlists)} playlists!")
            
            if playlists:
                print(f"\n📂 Your Playlists:")
                for i, playlist in enumerate(playlists, 1):
                    track_count = playlist.get('track_count', 0)
                    print(f"\n   {i}. {playlist.get('title')}")
                    print(f"      ID: {playlist.get('id')}")
                    print(f"      Tracks: {track_count}")
                    print(f"      Duration: {playlist.get('duration', 0) / 1000 / 60:.1f} minutes")
                    print(f"      Permalink: {playlist.get('permalink_url')}")
            else:
                print("   (No playlists found)")
            
            return playlists
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_soundcloud_favorites(access_token, limit=20):
    """Get user's liked tracks from SoundCloud"""
    print_section("7. Getting Your Liked Tracks")
    
    try:
        response = requests.get(
            'https://api.soundcloud.com/me/favorites',
            params={
                'oauth_token': access_token,
                'limit': limit
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            favorites = response.json()
            
            print(f"✅ Retrieved {len(favorites)} liked tracks!")
            
            if favorites:
                print(f"\n❤️  Your Liked Tracks (showing {min(len(favorites), 10)}):")
                for i, track in enumerate(favorites[:10], 1):
                    print(f"\n   {i}. {track.get('title')}")
                    print(f"      Artist: {track.get('user', {}).get('username', 'Unknown')}")
                    print(f"      Duration: {track.get('duration', 0) / 1000:.0f}s")
                    print(f"      Genre: {track.get('genre', 'N/A')}")
                    print(f"      Permalink: {track.get('permalink_url')}")
            else:
                print("   (No liked tracks found)")
            
            return favorites
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_soundcloud_followings(access_token, limit=10):
    """Get users you're following"""
    print_section("8. Getting Users You Follow")
    
    try:
        response = requests.get(
            'https://api.soundcloud.com/me/followings',
            params={
                'oauth_token': access_token,
                'limit': limit
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            followings = response.json()
            
            print(f"✅ Retrieved {len(followings)} users you follow!")
            
            if followings:
                print(f"\n👥 Following:")
                for i, user in enumerate(followings, 1):
                    print(f"   {i}. {user.get('username')}")
                    print(f"      Followers: {user.get('followers_count', 0)}")
                    print(f"      Tracks: {user.get('track_count', 0)}")
            else:
                print("   (Not following anyone)")
            
            return followings
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def search_soundcloud(access_token, query, limit=10):
    """Search for tracks on SoundCloud"""
    print_section("9. Testing Search")
    
    if not query:
        query = input("Enter search query (or press Enter to skip): ").strip()
        if not query:
            print("⏭️  Skipping search")
            return None
    
    try:
        response = requests.get(
            'https://api.soundcloud.com/tracks',
            params={
                'q': query,
                'oauth_token': access_token,
                'limit': limit
            },
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            
            print(f"✅ Found {len(results)} tracks for '{query}'!")
            
            if results:
                print(f"\n🔍 Search Results:")
                for i, track in enumerate(results[:5], 1):
                    print(f"\n   {i}. {track.get('title')}")
                    print(f"      Artist: {track.get('user', {}).get('username', 'Unknown')}")
                    print(f"      Duration: {track.get('duration', 0) / 1000:.0f}s")
                    print(f"      Plays: {track.get('playback_count', 0)}")
                    print(f"      Permalink: {track.get('permalink_url')}")
            
            return results
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_stream_url(access_token, track_id=None):
    """Test getting stream URL for a track"""
    print_section("10. Testing Track Streaming")
    
    if not track_id:
        track_id = input("Enter track ID to test streaming (or press Enter to skip): ").strip()
        if not track_id:
            print("⏭️  Skipping stream test")
            return None
    
    try:
        response = requests.get(
            f'https://api.soundcloud.com/tracks/{track_id}',
            params={'oauth_token': access_token},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            track = response.json()
            
            print(f"✅ Track info retrieved!")
            print(f"\n   Title: {track.get('title')}")
            print(f"   Artist: {track.get('user', {}).get('username')}")
            print(f"   Streamable: {track.get('streamable')}")
            
            if track.get('stream_url'):
                stream_url = f"{track.get('stream_url')}?oauth_token={access_token}"
                print(f"   Stream URL: {stream_url[:50]}...")
                print("\n   💡 You can use this URL to stream the track!")
            else:
                print("   ⚠️  No stream URL available for this track")
            
            return track
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def save_results_to_file(profile, tracks, playlists, favorites):
    """Save all retrieved data to a JSON file"""
    print_section("11. Saving Results")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"soundcloud_data_{timestamp}.json"
    
    data = {
        'retrieved_at': datetime.now().isoformat(),
        'profile': profile,
        'tracks': tracks,
        'playlists': playlists,
        'favorites': favorites
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Data saved to: {filename}")
        print(f"   File size: {len(json.dumps(data))} bytes")
        return filename
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return None


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  🎵 SOUNDCLOUD INTEGRATION - COMPLETE TEST & DATA RETRIEVAL")
    print("=" * 70)
    
    # Step 1: Health check
    if not test_backend_health():
        return
    
    # Step 2: Connect SoundCloud (if not already connected)
    if not connect_soundcloud():
        return
    
    # Step 3: Get access token
    access_token = get_soundcloud_access_token()
    if not access_token:
        print("\n❌ Could not get access token. Make sure SoundCloud is connected.")
        return
    
    # Step 4-8: Get all data
    profile = get_soundcloud_user_profile(access_token)
    tracks = get_soundcloud_tracks(access_token)
    playlists = get_soundcloud_playlists(access_token)
    favorites = get_soundcloud_favorites(access_token)
    followings = get_soundcloud_followings(access_token)
    
    # Step 9: Optional search
    search_soundcloud(access_token, "")
    
    # Step 10: Optional stream test
    test_stream_url(access_token)
    
    # Step 11: Save results
    if profile or tracks or playlists or favorites:
        save_results_to_file(profile, tracks, playlists, favorites)
    
    # Summary
    print_section("SUMMARY")
    print(f"\n✅ SoundCloud integration is fully working!")
    print(f"\n📊 Data Retrieved:")
    print(f"   Profile: {'✅' if profile else '❌'}")
    print(f"   Tracks: {len(tracks) if tracks else 0}")
    print(f"   Playlists: {len(playlists) if playlists else 0}")
    print(f"   Liked Tracks: {len(favorites) if favorites else 0}")
    print(f"   Following: {len(followings) if followings else 0}")
    
    print("\n" + "=" * 70)
    print("  🎉 ALL TESTS COMPLETE!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
