#!/bin/bash

# YouTube Integration Setup Diagnostic Script
# Checks if everything is installed correctly

echo "🔍 YouTube Music Integration - Setup Diagnostic"
echo "================================================"
echo ""

BACKEND_DIR="$HOME/Projects/mmp_be/multimusic-platform-backend"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check 1: Backend directory exists
echo "1. Backend Directory"
echo "-------------------"
if [ -d "$BACKEND_DIR" ]; then
    echo -e "${GREEN}✅${NC} Found: $BACKEND_DIR"
else
    echo -e "${RED}❌${NC} Not found: $BACKEND_DIR"
    echo "Please update BACKEND_DIR in this script"
    exit 1
fi
echo ""

# Check 2: YouTube handler file
echo "2. YouTube Handler File"
echo "----------------------"
if [ -f "$BACKEND_DIR/src/handlers/platforms/youtube.py" ]; then
    size=$(stat -f%z "$BACKEND_DIR/src/handlers/platforms/youtube.py" 2>/dev/null || stat -c%s "$BACKEND_DIR/src/handlers/platforms/youtube.py" 2>/dev/null)
    echo -e "${GREEN}✅${NC} youtube.py exists (${size} bytes)"
    
    # Check if it has the required functions
    if grep -q "def connect_handler" "$BACKEND_DIR/src/handlers/platforms/youtube.py"; then
        echo -e "${GREEN}✅${NC} Has connect_handler function"
    else
        echo -e "${RED}❌${NC} Missing connect_handler function"
    fi
    
    if grep -q "def callback_handler" "$BACKEND_DIR/src/handlers/platforms/youtube.py"; then
        echo -e "${GREEN}✅${NC} Has callback_handler function"
    else
        echo -e "${RED}❌${NC} Missing callback_handler function"
    fi
    
    if grep -q "def refresh_handler" "$BACKEND_DIR/src/handlers/platforms/youtube.py"; then
        echo -e "${GREEN}✅${NC} Has refresh_handler function"
    else
        echo -e "${RED}❌${NC} Missing refresh_handler function"
    fi
else
    echo -e "${RED}❌${NC} youtube.py NOT FOUND"
    echo "Copy youtube.py to: $BACKEND_DIR/src/handlers/platforms/"
fi
echo ""

# Check 3: __init__.py
echo "3. Platform __init__.py"
echo "----------------------"
if [ -f "$BACKEND_DIR/src/handlers/platforms/__init__.py" ]; then
    echo -e "${GREEN}✅${NC} __init__.py exists"
    
    # Check for youtube imports
    if grep -q "youtube_connect_handler" "$BACKEND_DIR/src/handlers/platforms/__init__.py"; then
        echo -e "${GREEN}✅${NC} Exports youtube_connect_handler"
    else
        echo -e "${RED}❌${NC} Does NOT export youtube_connect_handler"
        echo "   Update __init__.py with youtube imports"
    fi
    
    if grep -q "youtube_callback_handler" "$BACKEND_DIR/src/handlers/platforms/__init__.py"; then
        echo -e "${GREEN}✅${NC} Exports youtube_callback_handler"
    else
        echo -e "${RED}❌${NC} Does NOT export youtube_callback_handler"
    fi
    
    if grep -q "youtube_refresh_handler" "$BACKEND_DIR/src/handlers/platforms/__init__.py"; then
        echo -e "${GREEN}✅${NC} Exports youtube_refresh_handler"
    else
        echo -e "${RED}❌${NC} Does NOT export youtube_refresh_handler"
    fi
    
    # Show the __all__ export
    echo ""
    echo "Exported handlers:"
    grep -A 10 "__all__" "$BACKEND_DIR/src/handlers/platforms/__init__.py" | head -n 11
else
    echo -e "${RED}❌${NC} __init__.py NOT FOUND"
fi
echo ""

# Check 4: main.py
echo "4. Main Application"
echo "------------------"
if [ -f "$BACKEND_DIR/main.py" ]; then
    echo -e "${GREEN}✅${NC} main.py exists"
    
    # Check for youtube imports
    if grep -q "youtube_connect_handler" "$BACKEND_DIR/main.py"; then
        echo -e "${GREEN}✅${NC} Imports youtube_connect_handler"
    else
        echo -e "${RED}❌${NC} Does NOT import youtube_connect_handler"
        echo "   Update main.py with youtube imports"
    fi
    
    # Check for youtube routes
    if grep -q "/platforms/youtube/connect" "$BACKEND_DIR/main.py"; then
        echo -e "${GREEN}✅${NC} Has /platforms/youtube/connect route"
    else
        echo -e "${RED}❌${NC} Missing /platforms/youtube/connect route"
    fi
    
    if grep -q "/platforms/youtube/callback" "$BACKEND_DIR/main.py"; then
        echo -e "${GREEN}✅${NC} Has /platforms/youtube/callback route"
    else
        echo -e "${RED}❌${NC} Missing /platforms/youtube/callback route"
    fi
    
    if grep -q "/platforms/youtube/refresh" "$BACKEND_DIR/main.py"; then
        echo -e "${GREEN}✅${NC} Has /platforms/youtube/refresh route"
    else
        echo -e "${RED}❌${NC} Missing /platforms/youtube/refresh route"
    fi
else
    echo -e "${RED}❌${NC} main.py NOT FOUND"
fi
echo ""

# Check 5: .env file
echo "5. Environment Variables"
echo "-----------------------"
if [ -f "$BACKEND_DIR/.env" ]; then
    echo -e "${GREEN}✅${NC} .env exists"
    
    if grep -q "YOUTUBE_REDIRECT_URI" "$BACKEND_DIR/.env"; then
        echo -e "${GREEN}✅${NC} Has YOUTUBE_REDIRECT_URI"
        echo "   Value: $(grep YOUTUBE_REDIRECT_URI $BACKEND_DIR/.env)"
    else
        echo -e "${RED}❌${NC} Missing YOUTUBE_REDIRECT_URI"
        echo "   Add: YOUTUBE_REDIRECT_URI=http://127.0.0.1:8080/platforms/youtube/callback"
    fi
    
    if grep -q "GOOGLE_CLIENT_ID" "$BACKEND_DIR/.env"; then
        echo -e "${GREEN}✅${NC} Has GOOGLE_CLIENT_ID"
    else
        echo -e "${RED}❌${NC} Missing GOOGLE_CLIENT_ID"
    fi
    
    if grep -q "GOOGLE_CLIENT_SECRET" "$BACKEND_DIR/.env"; then
        echo -e "${GREEN}✅${NC} Has GOOGLE_CLIENT_SECRET"
    else
        echo -e "${RED}❌${NC} Missing GOOGLE_CLIENT_SECRET"
    fi
    
    if grep -q "ENCRYPTION_KEY" "$BACKEND_DIR/.env"; then
        echo -e "${GREEN}✅${NC} Has ENCRYPTION_KEY"
    else
        echo -e "${RED}❌${NC} Missing ENCRYPTION_KEY"
    fi
else
    echo -e "${RED}❌${NC} .env NOT FOUND"
fi
echo ""

# Check 6: Python imports (WITH .env loaded - explicit path)
echo "6. Python Import Test"
echo "--------------------"
cd "$BACKEND_DIR"
python_import=$(python3 << PYTHON_EOF
import sys
import os

backend_dir = os.getcwd()
sys.path.insert(0, backend_dir)

# Load environment variables from .env file (explicit path)
from dotenv import load_dotenv
env_path = os.path.join(backend_dir, '.env')
load_dotenv(dotenv_path=env_path)

errors = []
success = []

try:
    from src.handlers.platforms import youtube_connect_handler
    success.append("youtube_connect_handler")
except Exception as e:
    errors.append(f"youtube_connect_handler: {e}")

try:
    from src.handlers.platforms import youtube_callback_handler
    success.append("youtube_callback_handler")
except Exception as e:
    errors.append(f"youtube_callback_handler: {e}")

try:
    from src.handlers.platforms import youtube_refresh_handler
    success.append("youtube_refresh_handler")
except Exception as e:
    errors.append(f"youtube_refresh_handler: {e}")

if errors:
    print("ERRORS")
    for error in errors:
        print(error)
    sys.exit(1)
else:
    print("SUCCESS")
    for item in success:
        print(item)
    sys.exit(0)
PYTHON_EOF
)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅${NC} All imports successful:"
    echo "$python_import" | grep -v SUCCESS | while read line; do
        echo "   - $line"
    done
else
    echo -e "${RED}❌${NC} Import errors:"
    echo "$python_import" | grep -v ERRORS | while read line; do
        echo "   $line"
    done
fi
echo ""

# Check 7: Backend running
echo "7. Backend Status"
echo "----------------"
if curl -s http://127.0.0.1:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} Backend is running on http://127.0.0.1:8080"
    
    # Check if YouTube endpoint exists
    response=$(curl -s -w "%{http_code}" -X POST http://127.0.0.1:8080/platforms/youtube/connect -o /dev/null)
    if [ "$response" = "401" ]; then
        echo -e "${GREEN}✅${NC} YouTube endpoint is accessible (requires auth)"
    elif [ "$response" = "404" ]; then
        echo -e "${RED}❌${NC} YouTube endpoint returns 404 (not found)"
    else
        echo -e "${YELLOW}⚠️${NC} YouTube endpoint returns HTTP $response"
    fi
else
    echo -e "${YELLOW}⚠️${NC} Backend is NOT running"
    echo "   Start with: cd $BACKEND_DIR && python main.py"
fi
echo ""

# Check 8: DynamoDB
echo "8. DynamoDB Status"
echo "-----------------"
if curl -s http://127.0.0.1:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} DynamoDB Local is running on http://127.0.0.1:8000"
else
    echo -e "${YELLOW}⚠️${NC} DynamoDB Local is NOT running"
    echo "   Start with: cd $BACKEND_DIR/local && docker-compose up -d"
fi

if curl -s http://127.0.0.1:8001 > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC} DynamoDB Admin is running on http://127.0.0.1:8001"
else
    echo -e "${YELLOW}⚠️${NC} DynamoDB Admin is NOT running"
fi
echo ""

# Final summary
echo "================================================"
echo "Diagnostic Complete"
echo "================================================"
echo ""

echo "Summary: Review the output above for any ❌ or ⚠️  markers"
echo ""
echo "Next steps:"
echo "1. Fix any issues marked with ❌"
echo "2. Start services marked with ⚠️ (if needed)"
echo "3. Run: bash test_youtube_integration_FIXED.sh"
echo ""