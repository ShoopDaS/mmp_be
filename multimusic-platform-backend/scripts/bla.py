#!/usr/bin/env python3
"""
Simple check - is FastAPI backend actually on port 8080?
"""
import requests

print("=" * 70)
print("BACKEND VERIFICATION")
print("=" * 70)
print()

print("Testing port 8080...")
print()

# Test 1: Health endpoint (FastAPI)
print("1. Testing /health endpoint (FastAPI specific):")
try:
    response = requests.get('http://127.0.0.1:8080/health', timeout=2)
    print(f"   Status: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type')}")
    print(f"   Response: {response.text}")
    
    if response.status_code == 200 and 'application/json' in response.headers.get('content-type', ''):
        data = response.json()
        if data.get('status') == 'healthy':
            print("   ✅ FastAPI backend IS running on port 8080")
        else:
            print("   ⚠️  Got JSON but unexpected response")
    else:
        print("   ❌ This is NOT the FastAPI backend!")
        if 'text/html' in response.headers.get('content-type', ''):
            print("   This looks like Next.js frontend")
            
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 2: Check server header
print("2. Checking server header:")
try:
    response = requests.get('http://127.0.0.1:8080/health', timeout=2)
    server = response.headers.get('server', 'Not set')
    print(f"   Server header: {server}")
    
    if 'uvicorn' in server.lower():
        print("   ✅ This is Uvicorn (FastAPI)")
    elif 'next' in server.lower() or not server or server == 'Not set':
        print("   ❌ This is NOT Uvicorn (probably Next.js)")
    else:
        print(f"   ⚠️  Unknown server: {server}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 3: Check root endpoint
print("3. Testing root / endpoint:")
try:
    response = requests.get('http://127.0.0.1:8080/', timeout=2)
    print(f"   Status: {response.status_code}")
    content = response.text[:100]
    print(f"   Content (first 100 chars): {content}")
    
    if '<!DOCTYPE html>' in content:
        print("   ❌ This is HTML (Next.js frontend)")
    elif 'FastAPI' in content or '{' in content:
        print("   ✅ This looks like FastAPI")
    else:
        print("   ⚠️  Unknown content type")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 70)
print("CONCLUSION")
print("=" * 70)
print()

# Final check
try:
    response = requests.get('http://127.0.0.1:8080/health', timeout=2)
    if response.status_code == 200:
        try:
            data = response.json()
            if data.get('status') == 'healthy':
                print("✅ FastAPI backend IS running correctly on port 8080")
                print()
                print("If OAuth still doesn't work, the issue is elsewhere.")
                print("Check your backend terminal for errors during callback.")
            else:
                print("❌ Port 8080 is responding but not with FastAPI")
                print()
                print("Something else is on port 8080!")
        except:
            print("❌ Port 8080 is returning non-JSON response")
            print()
            print("Backend is NOT running on port 8080")
            print()
            print("Fix:")
            print("1. cd ~/Projects/mmp_be/multimusic-platform-backend")
            print("2. python main.py")
    else:
        print("❌ Port 8080 not responding correctly")
        
except Exception as e:
    print(f"❌ Cannot connect to port 8080: {e}")

print()