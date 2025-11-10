#!/bin/bash

# YouTube Music Integration Test Script
# Tests all YouTube endpoints

echo "🎵 YouTube Music Integration Test Suite"
echo "========================================"
echo ""

BACKEND_URL="http://127.0.0.1:8080"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "Test 1: Health Check"
echo "--------------------"
response=$(curl -s -w "\n%{http_code}" $BACKEND_URL/health)
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Backend is healthy"
    echo "Response: $body"
else
    echo -e "${RED}❌ FAIL${NC} - Backend not responding (HTTP $http_code)"
    exit 1
fi
echo ""

# Test 2: YouTube Connect (without auth - should fail)
echo "Test 2: YouTube Connect (No Auth - Should Return 401)"
echo "-----------------------------------------------------"
response=$(curl -s -w "\n%{http_code}" -X POST $BACKEND_URL/platforms/youtube/connect \
    -H "Content-Type: application/json")
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Correctly requires authentication"
    echo "Response: $body"
else
    echo -e "${RED}❌ FAIL${NC} - Should return 401 without auth (got HTTP $http_code)"
fi
echo ""

# Test 3: YouTube Connect (with auth)
echo "Test 3: YouTube Connect (With Auth)"
echo "-----------------------------------"
echo -e "${YELLOW}⚠️  This test requires a valid session token${NC}"
echo ""
read -p "Enter session token (or press Enter to skip): " SESSION_TOKEN
echo ""

if [ -n "$SESSION_TOKEN" ]; then
    response=$(curl -s -w "\n%{http_code}" -X POST $BACKEND_URL/platforms/youtube/connect \
        -H "Authorization: Bearer $SESSION_TOKEN" \
        -H "Content-Type: application/json")
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ PASS${NC} - Successfully got YouTube authUrl"
        echo "Response: $body"
        echo ""
        
        # Extract authUrl
        auth_url=$(echo "$body" | grep -o '"authUrl":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$auth_url" ]; then
            echo -e "${YELLOW}📋 Next Step: Open this URL in your browser:${NC}"
            echo "$auth_url"
            echo ""
            echo "After completing OAuth, check the callback URL"
        fi
    else
        echo -e "${RED}❌ FAIL${NC} - Expected 200, got HTTP $http_code"
        echo "Response: $body"
    fi
else
    echo -e "${YELLOW}⏭️  SKIPPED${NC} - No session token provided"
fi
echo ""

# Test 4: Check if YouTube module is importable
echo "Test 4: Verify YouTube Handler Module"
echo "--------------------------------------"
python_test=$(python3 << 'PYTHON_EOF'
try:
    import sys
    sys.path.insert(0, '/home/claude/Projects/mmp_be/multimusic-platform-backend')
    from src.handlers.platforms import youtube
    print("✅ YouTube module imports successfully")
    print(f"   - connect_handler: {'✅' if hasattr(youtube, 'connect_handler') else '❌'}")
    print(f"   - callback_handler: {'✅' if hasattr(youtube, 'callback_handler') else '❌'}")
    print(f"   - refresh_handler: {'✅' if hasattr(youtube, 'refresh_handler') else '❌'}")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed to import youtube module: {e}")
    sys.exit(1)
PYTHON_EOF
)
echo "$python_test"
echo ""

# Summary
echo "========================================"
echo "Test Suite Complete"
echo "========================================"
echo ""
echo "📝 Manual Testing Steps:"
echo "1. Get session token by logging in via frontend"
echo "2. Call /platforms/youtube/connect with session token"
echo "3. Open the returned authUrl in browser"
echo "4. Complete Google OAuth flow"
echo "5. Verify redirect to frontend with ?youtube=connected"
echo "6. Check DynamoDB Admin UI: http://127.0.0.1:8001"
echo "7. Look for entry with sk='platform#youtube'"
echo ""
echo "🔧 Useful Commands:"
echo "   Start backend: cd ~/Projects/mmp_be/multimusic-platform-backend && python main.py"
echo "   Check DynamoDB: aws dynamodb scan --table-name multimusic-users --endpoint-url http://127.0.0.1:8000 --region eu-west-1"
echo "   View logs: tail -f ~/Projects/mmp_be/multimusic-platform-backend/logs/app.log"
echo ""
