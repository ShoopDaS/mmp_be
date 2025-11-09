# MultiMusic Platform - Backend (v2.0)

Backend services for the MultiMusic Platform, handling multi-provider SSO authentication and music platform connections.

## Overview

The backend implements a **multi-provider Single Sign-On (SSO)** architecture that separates user authentication from music platform connections. Users log in once with their preferred SSO provider (Google, Microsoft, GitHub) and then connect various music platforms (Spotify, SoundCloud, etc.) to their account.

## Architecture Evolution

### v1.0 (Previous)
```
User → Spotify OAuth → Logged in as Spotify User
       (User ID = Spotify ID)
```

### v2.0 (Current)
```
User → SSO Login (Google/Microsoft/GitHub)
       ↓
    Internal User Account (mmp_<uuid>)
       ↓
    Connect Music Platforms
       ↓
    Spotify, SoundCloud, etc. linked to account
```

**Key Benefits:**
- ✅ Multiple SSO providers supported
- ✅ One account, multiple login methods
- ✅ Music platforms as connections, not identity
- ✅ Easy to add new SSO providers or music services
- ✅ Scalable architecture for enterprise use

## Tech Stack

- **Python 3.13** - Latest Python with enhanced performance
- **FastAPI** - Modern async web framework for local development
- **AWS Lambda** - Serverless compute for production
- **DynamoDB** - NoSQL database for token storage
- **JWT** - Stateless session management
- **Cryptography** - Token encryption at rest
- **httpx** - Modern async HTTP client for OAuth calls

## API Endpoints

### SSO Authentication (Login to MultiMusic)

#### POST /auth/google/login
Initiates Google OAuth flow
- **Authentication**: None required
- **Returns**: Authorization URL with CSRF state
- **Response**:
```json
{
  "data": {
    "authUrl": "https://accounts.google.com/o/oauth2/v2/auth?...",
    "state": "csrf_token_here"
  }
}
```

#### GET /auth/google/callback
Handles OAuth callback from Google
- **Authentication**: None (single-use code in query params)
- **Creates**: Internal user account (mmp_<uuid>)
- **Links**: Google account to user
- **Generates**: JWT session token
- **Redirects**: To frontend with session token

#### Future SSO Providers
- POST /auth/microsoft/login
- GET /auth/microsoft/callback
- POST /auth/github/login
- GET /auth/github/callback

### Music Platform Connections

#### POST /platforms/spotify/connect
Initiates Spotify connection for authenticated user
- **Authentication**: Required (Bearer token)
- **Returns**: Spotify authorization URL
- **Response**:
```json
{
  "data": {
    "authUrl": "https://accounts.spotify.com/authorize?...",
    "state": "user_id:csrf_token"
  }
}
```

#### GET /platforms/spotify/callback
Handles Spotify OAuth callback
- **Authentication**: None (state contains user_id)
- **Links**: Spotify account to user's MultiMusic account
- **Stores**: Encrypted access/refresh tokens
- **Redirects**: To dashboard with success message

#### POST /platforms/spotify/refresh
Refreshes expired Spotify access token
- **Authentication**: Required (Bearer token)
- **Returns**: New access token for client-side API calls
- **Response**:
```json
{
  "data": {
    "accessToken": "BQC...",
    "expiresIn": 3600
  }
}
```

#### Future Platform Connections
- POST /platforms/soundcloud/connect
- GET /platforms/soundcloud/callback
- POST /platforms/soundcloud/refresh

### User Management

#### GET /user/profile
Returns user profile information
- **Authentication**: Required
- **Response**:
```json
{
  "data": {
    "userId": "mmp_abc123",
    "email": "user@gmail.com",
    "displayName": "John Doe",
    "primaryAuthProvider": "google"
  }
}
```

#### GET /user/auth-providers
Lists linked SSO providers
- **Authentication**: Required
- **Response**:
```json
{
  "data": {
    "providers": [
      {
        "provider": "google",
        "email": "user@gmail.com",
        "linked": true,
        "linkedAt": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### GET /user/platforms
Lists connected music platforms
- **Authentication**: Required
- **Response**:
```json
{
  "data": {
    "platforms": [
      {
        "platform": "spotify",
        "platformUserId": "spotify_user_123",
        "connected": true,
        "connectedAt": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### DELETE /user/platforms/{platform}
Disconnects a music platform
- **Authentication**: Required
- **Response**:
```json
{
  "data": {
    "message": "spotify disconnected successfully"
  }
}
```

## Database Schema

### Single Table Design (multimusic-users)

DynamoDB table with composite key (userId, sk):

**User Profile:**
```python
{
    'userId': 'mmp_abc123def456',    # PK: Internal user ID
    'sk': 'PROFILE',                  # SK: Record type
    'email': 'user@gmail.com',
    'displayName': 'John Doe',
    'avatarUrl': 'https://...',
    'primaryAuthProvider': 'google',
    'createdAt': '2024-01-01T00:00:00Z',
    'updatedAt': '2024-01-01T00:00:00Z'
}
```

**SSO Provider Links:**
```python
{
    'userId': 'mmp_abc123def456',
    'sk': 'auth#google',             # SK: auth#{provider}
    'providerId': 'google_123456',   # Provider's user ID
    'email': 'user@gmail.com',
    'linked': True,
    'linkedAt': '2024-01-01T00:00:00Z'
}
```

**Music Platform Connections:**
```python
{
    'userId': 'mmp_abc123def456',
    'sk': 'platform#spotify',        # SK: platform#{service}
    'platformUserId': 'spotify_user_123',
    'accessToken': '<encrypted>',     # AES-256 encrypted
    'refreshToken': '<encrypted>',    # AES-256 encrypted
    'expiresAt': '2024-01-01T01:00:00Z',
    'expiresIn': 3600,
    'scope': 'user-read-private streaming...',
    'connectedAt': '2024-01-01T00:00:00Z'
}
```

## Environment Variables

```bash
# JWT & Encryption
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=7
ENCRYPTION_KEY=your-32-char-encryption-key-must-be-exactly-32-chars

# Database
DYNAMODB_ENDPOINT=http://127.0.0.1:8000  # Local dev
DYNAMODB_TABLE=multimusic-users
AWS_REGION=us-east-1

# Frontend
FRONTEND_URL=http://127.0.0.1:3000

# Google OAuth
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GOOGLE_REDIRECT_URI=http://127.0.0.1:8080/auth/google/callback

# Spotify (Platform Connection)
SPOTIFY_CLIENT_ID=xxxxx
SPOTIFY_CLIENT_SECRET=xxxxx
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/platforms/spotify/callback
```

## Local Development Setup

### Prerequisites
- Python 3.13+
- Docker & Docker Compose
- Google Cloud Console account
- Spotify Developer account

### Step-by-Step Setup

1. **Clone and setup environment**
```bash
git clone <your-repo>
cd multimusic-platform-backend

python3.13 -m venv venv
source venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
```

2. **Configure environment**
```bash
cp .env.template .env
# Edit .env with your OAuth credentials
```

3. **Start DynamoDB Local**
```bash
cd local
docker-compose up -d
cd ..
```

4. **Create database tables**
```bash
python scripts/create_tables.py
```

5. **Start backend server**
```bash
python main.py
```

Backend runs at `http://127.0.0.1:8080`

### OAuth Provider Setup

#### Google OAuth
1. [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable Google+ API
3. Credentials → OAuth 2.0 Client ID
4. Authorized redirect: `http://127.0.0.1:8080/auth/google/callback`
5. Copy credentials to `.env`

#### Spotify OAuth
1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create/edit app
3. **Important**: Redirect URI is now `/platforms/spotify/callback`
4. Add: `http://127.0.0.1:8080/platforms/spotify/callback`
5. Scopes needed:
   - `user-read-private`
   - `user-read-email`
   - `streaming`
   - `user-modify-playback-state`
   - `user-read-playback-state`
6. Copy credentials to `.env`

## Migration from v1.0

If you have existing Spotify-only users:

### Option 1: Fresh Start (Development)
```bash
aws dynamodb delete-table \
  --table-name multimusic-users \
  --endpoint-url http://127.0.0.1:8000

python scripts/create_tables.py
```

### Option 2: Inspect and Clean
```bash
# Check for old records
python scripts/inspect_dynamodb.py

# Will show old (spotify_xxx) vs new (mmp_xxx) users
```

## Project Structure

```
backend/
├── src/
│   ├── handlers/
│   │   ├── auth/
│   │   │   ├── base.py          # BaseAuthHandler (SSO logic)
│   │   │   ├── google.py        # Google OAuth implementation
│   │   │   └── __init__.py
│   │   ├── platforms/
│   │   │   ├── base.py          # BasePlatformHandler (platform logic)
│   │   │   ├── spotify.py       # Spotify connection implementation
│   │   │   └── __init__.py
│   │   └── user.py              # User management endpoints
│   ├── services/
│   │   ├── dynamodb_service.py  # Database operations
│   │   ├── jwt_service.py       # JWT token management
│   │   └── token_service.py     # Token encryption/decryption
│   └── utils/
│       └── responses.py         # Lambda response helpers
├── scripts/
│   ├── create_tables.py         # Database setup
│   └── inspect_dynamodb.py      # Database inspection
├── local/
│   ├── docker-compose.yml       # DynamoDB Local + Admin UI
│   └── app.py                   # Legacy local wrapper
├── main.py                      # FastAPI application
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── .env.template               # Environment template
└── README.md                    # This file
```

## User Flows

### New User Registration
```
1. User → Frontend landing page
2. Click "Continue with Google"
3. Backend → Google OAuth
4. Google → User authenticates
5. Backend → Creates mmp_<uuid> account
6. Backend → Links Google account
7. Backend → Generates JWT session
8. Frontend → Dashboard (logged in)
9. User → "Connect Spotify"
10. Backend → Spotify OAuth
11. Spotify → User authorizes
12. Backend → Links Spotify to account
13. Frontend → Search & play music!
```

### Returning User
```
1. User → Frontend
2. Frontend → Detects session token
3. Frontend → Auto-redirects to dashboard
4. User → Already has platforms connected
5. User → Can immediately search music
```

## Security

### Authentication
- JWT tokens with configurable expiration
- CSRF protection via state parameter
- Secure token storage in localStorage
- Session invalidation on logout

### Token Storage
- Access/refresh tokens encrypted at rest (AES-256)
- Tokens only decrypted when needed
- Separate encryption keys per environment
- No tokens in logs or error messages

### API Security
- CORS restricted to frontend domain
- Bearer token authentication
- Request validation
- Rate limiting (production)

## Testing

### Test Google Login
```bash
curl -X POST http://127.0.0.1:8080/auth/google/login
# Returns authUrl - open in browser
```

### Test with Session Token
```bash
# Get session token from browser localStorage
curl http://127.0.0.1:8080/user/profile \
  -H "Authorization: Bearer <your_session_token>"
```

### Verify Database
```bash
python scripts/inspect_dynamodb.py
# Shows all users and their connections
```

## Troubleshooting

### Google OAuth Fails
- **Check**: Redirect URI exactly matches Google Console
- **Verify**: `http://127.0.0.1:8080/auth/google/callback` (no trailing slash)
- **Ensure**: Google+ API is enabled

### Spotify Connection Fails
- **Check**: Redirect URI is `/platforms/spotify/callback` (not `/auth/spotify/callback`)
- **Verify**: All required scopes are requested
- **Ensure**: Client ID/Secret are correct

### Token Refresh Issues
- **Check**: Refresh token exists in DynamoDB
- **Verify**: Token encryption key hasn't changed
- **Ensure**: Spotify credentials are correct

### "No module named 'mangum'"
```bash
pip install mangum
# Or update main.py to make mangum optional (already done)
```

## Deployment

### AWS Lambda (Production)
```bash
# Package with dependencies
pip install -r requirements.txt -t package/
cp -r src package/
cd package && zip -r ../lambda.zip . && cd ..

# Deploy via AWS Console, SAM, or Terraform
```

### Environment Considerations
- Use AWS Secrets Manager for production secrets
- Enable CloudWatch logging
- Configure VPC for DynamoDB access
- Set up API Gateway with proper CORS
- Use CloudFront + WAF for security

## Roadmap

- [x] Multi-provider SSO architecture
- [x] Google OAuth implementation
- [x] Spotify as platform connection
- [x] JWT session management
- [x] Token encryption
- [x] User management endpoints
- [ ] SoundCloud platform
- [ ] Playlists
- [ ] Microsoft OAuth
- [ ] GitHub OAuth
- [ ] YouTube Music platform
- [ ] Token refresh automation
- [ ] Production deployment (Terraform)

## Support

- Check DynamoDB Admin UI: `http://127.0.0.1:8001`
- View backend logs in terminal
- Use debug scripts in `/local` and `/scripts`
- Review this documentation