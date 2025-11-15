#!/usr/bin/env python3
"""
Test SoundCloud OAuth callback to see what's happening
"""
import requests

print("=" * 70)
print("SOUNDCLOUD OAUTH CALLBACK DIAGNOSTIC")
print("=" * 70)
print()

print("Testing callback endpoint...")
print()

# Simulate what happens when SoundCloud redirects back
test_url = "http://127.0.0.1:8080/platforms/soundcloud/callback"

# Test 1: Missing parameters
print("Test 1: Calling callback with missing parameters")
print("URL:", test_url)
response = requests.get(test_url)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")
print()

# Test 2: With error parameter
print("Test 2: Calling callback with error")
response = requests.get(f"{test_url}?error=access_denied")
print(f"Status: {response.status_code}")
if response.status_code in [301, 302, 303, 307, 308]:
    print(f"Redirects to: {response.headers.get('Location')}")
else:
    print(f"Response: {response.text[:200]}")
print()

# Test 3: Check environment variables
print("Test 3: Checking environment variables")
import os
from dotenv import load_dotenv
load_dotenv()

frontend_url = os.getenv('FRONTEND_URL')
soundcloud_redirect_uri = os.getenv('SOUNDCLOUD_REDIRECT_URI')

print(f"FRONTEND_URL: {frontend_url}")
print(f"SOUNDCLOUD_REDIRECT_URI: {soundcloud_redirect_uri}")
print()

if not frontend_url:
    print("⚠️  WARNING: FRONTEND_URL not set!")
    print("   Callback might redirect to wrong location")
    print("   Add to .env: FRONTEND_URL=http://127.0.0.1:3000")
elif frontend_url and not frontend_url.startswith('http'):
    print("⚠️  WARNING: FRONTEND_URL should include http://")
    print(f"   Current: {frontend_url}")
    print("   Should be: http://127.0.0.1:3000")

print()
print("=" * 70)
print("CHECKING FRONTEND")
print("=" * 70)
print()

if frontend_url:
    print(f"Testing if frontend is running at {frontend_url}...")
    try:
        response = requests.get(frontend_url, timeout=5)
        print(f"✅ Frontend is running!")
        print(f"   Status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Frontend is NOT running at {frontend_url}")
        print(f"   Start your frontend: npm run dev")
    except Exception as e:
        print(f"⚠️  Error checking frontend: {e}")
else:
    print("⚠️  FRONTEND_URL not set - cannot test frontend")

print()
print("=" * 70)
print("EXPECTED OAUTH FLOW")
print("=" * 70)
print()
print("1. User clicks 'Connect SoundCloud' on frontend")
print("2. Frontend calls: POST /platforms/soundcloud/connect")
print("3. Backend returns authUrl")
print("4. Frontend redirects user to authUrl (SoundCloud)")
print("5. User authorizes on SoundCloud")
print("6. SoundCloud redirects to: /platforms/soundcloud/callback?code=...")
print("7. Backend processes callback")
print("8. Backend redirects to: {FRONTEND_URL}/dashboard?soundcloud=connected")
print("9. Frontend shows success message")
print()

print("=" * 70)
print("TROUBLESHOOTING")
print("=" * 70)
print()
print("If you see a blank page:")
print()
print("Issue 1: FRONTEND_URL is wrong")
print("  Solution: Set FRONTEND_URL=http://127.0.0.1:3000 in .env")
print()
print("Issue 2: Frontend not running")
print("  Solution: Start frontend with: npm run dev")
print()
print("Issue 3: Frontend route doesn't exist")
print("  Solution: Make sure /dashboard route exists in your Next.js app")
print()
print("Issue 4: OAuth app redirect URI mismatch")
print("  Solution: In SoundCloud app settings, set redirect URI to:")
print(f"           {soundcloud_redirect_uri or 'http://127.0.0.1:8080/platforms/soundcloud/callback'}")
print()