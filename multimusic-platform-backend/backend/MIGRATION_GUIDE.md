# Backend Migration Guide - Multi-Provider SSO

## Overview
This guide covers migrating your backend from direct Spotify auth to multi-provider SSO architecture.

## Architecture Changes

### Before (Old)
```
User → Spotify OAuth → User logged in with Spotify ID
```

### After (New)
```
User → SSO (Google/Microsoft/etc.) → MultiMusic account created
     → Connect Spotify → Spotify linked to MultiMusic account
```

## File Structure

```
multimusic-platform-backend/
├── src/
│   ├── handlers/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # NEW: Shared SSO logic
│   │   │   └── google.py        # NEW: Google OAuth
│   │   ├── platforms/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # NEW: Shared platform logic
│   │   │   └── spotify.py       # REFACTORED: From spotify_auth.py
│   │   └── user.py              # NEW: User management
│   ├── services/
│   │   ├── dynamodb_service.py  # UPDATE with new methods
│   │   ├── jwt_service.py       # No changes needed
│   │   └── token_service.py     # No changes needed
│   └── utils/
│       └── responses.py         # No changes needed
├── main.py                      # UPDATE with new routes
└── .env                         # UPDATE with new variables
```

## Step-by-Step Migration

### Step 1: Update DynamoDB Service

Replace `src/services/dynamodb_service.py` with the new version that includes:
- `put_item()` - Generic put operation
- `get_item()` - Generic get operation
- `query_by_prefix()` - Query by SK prefix
- `get_user_by_provider()` - Find user by OAuth provider
- Legacy methods maintained for backward compatibility

### Step 2: Add New Handler Directories

Create the new handler structure:
```bash
cd ~/Projects/mmp_be/multimusic-platform-backend
mkdir -p src/handlers/auth
mkdir -p src/handlers/platforms
```

### Step 3: Copy New Files

Copy these files to your backend:
- `src/handlers/auth/base.py`
- `src/handlers/auth/google.py`
- `src/handlers/auth/__init__.py`
- `src/handlers/platforms/base.py`
- `src/handlers/platforms/spotify.py`
- `src/handlers/platforms/__init__.py`
- `src/handlers/user.py`
- `main.py` (replaces existing)

### Step 4: Update Environment Variables

Add to your `.env` file:
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8080/auth/google/callback

# Update Spotify redirect
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/platforms/spotify/callback

# Update Frontend URL for Next.js
FRONTEND_URL=http://127.0.0.1:3000
```

### Step 5: Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create/select a project
3. Enable "Google+ API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Application type: "Web application"
6. Authorized redirect URIs: `http://127.0.0.1:8080/auth/google/callback`
7. Copy Client ID and Client Secret to `.env`

### Step 6: Update Spotify OAuth Config

Update your Spotify app settings:
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Edit your app
3. Update Redirect URI to: `http://127.0.0.1:8080/platforms/spotify/callback`
4. Save

## Database Schema

### New Tables Structure

**User Profile:**
```
PK: userId = "mmp_<uuid>"
SK: "PROFILE"
Attributes:
  - email
  - displayName
  - avatarUrl
  - primaryAuthProvider
  - createdAt
  - updatedAt
```

**Auth Provider Links:**
```
PK: userId = "mmp_<uuid>"
SK: "auth#google" | "auth#microsoft" | etc.
Attributes:
  - providerId (provider's user ID)
  - email
  - linked
  - linkedAt
```

**Platform Connections:**
```
PK: userId = "mmp_<uuid>"
SK: "platform#spotify" | "platform#soundcloud" | etc.
Attributes:
  - platformUserId
  - accessToken (encrypted)
  - refreshToken (encrypted)
  - expiresAt
  - expiresIn
  - scope
  - connectedAt
```

## API Endpoint Changes

### New SSO Endpoints
- `POST /auth/google/login` - Initiate Google login
- `GET /auth/google/callback` - Handle Google callback

### Updated Platform Endpoints
- `POST /platforms/spotify/connect` - Connect Spotify (was `/auth/spotify/login`)
- `GET /platforms/spotify/callback` - Spotify callback
- `POST /platforms/spotify/refresh` - Refresh token

### New User Endpoints
- `GET /user/profile` - Get user info
- `GET /user/auth-providers` - List SSO providers
- `GET /user/platforms` - List connected platforms
- `DELETE /user/platforms/{platform}` - Disconnect platform

## Testing the Migration

### Test 1: Google Login
```bash
# Start backend
cd ~/Projects/mmp_be/multimusic-platform-backend
python main.py

# Test login endpoint
curl -X POST http://127.0.0.1:8080/auth/google/login
```

Expected: Returns `authUrl` and `state`

### Test 2: Spotify Connection (Requires Auth)
```bash
# After getting session token from Google login
curl -X POST http://127.0.0.1:8080/platforms/spotify/connect \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Expected: Returns Spotify `authUrl`

### Test 3: User Profile
```bash
curl http://127.0.0.1:8080/user/profile \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Expected: Returns user profile data

## Migration Path for Existing Users

If you have existing Spotify users, you have two options:

### Option 1: Fresh Start
Delete existing DynamoDB data and start fresh with new schema.

### Option 2: Data Migration Script
Create a migration script to:
1. Read existing Spotify user records
2. Create internal user IDs
3. Move Spotify data to platform# items
4. Create auth#google links when users first login with Google

## Troubleshooting

### "User not found" after Google login
- Check DynamoDB to verify user profile was created
- Verify userId format is `mmp_<uuid>`

### Spotify connection fails
- Verify redirect URI matches in Spotify dashboard
- Check session token is being sent in Authorization header
- Verify user_id is extracted from state parameter

### Token refresh fails
- Ensure tokens are properly encrypted/decrypted
- Check DynamoDB has refreshToken stored
- Verify Spotify credentials are correct

## Next Steps

After backend migration:
1. Build Next.js frontend (see Frontend Guide)
2. Test complete user flow
3. Add additional SSO providers (Microsoft, GitHub)
4. Add additional music platforms (SoundCloud)

## Backward Compatibility

The old Spotify endpoints still work if you keep `spotify_auth.py` in `src/handlers/`. However, they use Spotify ID as user ID instead of internal ID. Not recommended for production with multi-provider support.
