# CLAUDE.md Files Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create CLAUDE.md files at the repo root and backend project root so Claude Code has full project context in future sessions.

**Architecture:** Two CLAUDE.md files — one at repo root (`/home/matej/Projects/mmp_be/`) with high-level repo overview, one at backend project root (`multimusic-platform-backend/`) with complete dev workflow, architecture, and conventions.

**Tech Stack:** Python 3.13, FastAPI, AWS Lambda, DynamoDB, httpx, JWT, Fernet encryption, pytest, moto, Docker (DynamoDB Local)

---

## Chunk 1: Repo-level CLAUDE.md

### Task 1: Create `/home/matej/Projects/mmp_be/CLAUDE.md`

**Files:**
- Create: `/home/matej/Projects/mmp_be/CLAUDE.md`

This file gives high-level orientation for anyone opening the repo root.

- [ ] **Step 1: Write the file**

```markdown
# MultiMusic Platform — Backend

Monorepo root for the MultiMusic Platform backend.

## Repo Structure

```
mmp_be/
├── multimusic-platform-backend/   # Main backend (FastAPI + AWS Lambda)
│   ├── src/                       # Source code
│   ├── tests/                     # Test suite
│   ├── scripts/                   # Utility & debug scripts
│   ├── local/                     # Local dev tooling (Docker, .env)
│   └── main.py                    # FastAPI dev entry point
└── docs/                          # Plans and documentation
```

## Project

MultiMusic Platform is a multi-provider SSO backend that lets users authenticate with Google (Microsoft/GitHub planned), then connect multiple music streaming services (Spotify, YouTube Music, SoundCloud) to a single internal account.

All active development is in `multimusic-platform-backend/`. See its `CLAUDE.md` for dev workflow.
```

- [ ] **Step 2: Verify file was created**

```bash
cat /home/matej/Projects/mmp_be/CLAUDE.md
```

---

## Chunk 2: Backend project CLAUDE.md

### Task 2: Create `multimusic-platform-backend/CLAUDE.md`

**Files:**
- Create: `/home/matej/Projects/mmp_be/multimusic-platform-backend/CLAUDE.md`

This is the primary CLAUDE.md — it contains everything needed to work on the backend.

- [ ] **Step 1: Write the file**

```markdown
# MultiMusic Platform Backend

Python 3.13 / FastAPI backend with AWS Lambda deployment target. Handles multi-provider SSO and music platform OAuth connections.

## Quick Start (Local Dev)

```bash
# 1. Activate venv
source venv/bin/activate

# 2. Install deps
pip install -r requirements.txt -r requirements-dev.txt

# 3. Start DynamoDB Local
cd local && docker-compose up -d && cd ..

# 4. Create tables (first time only)
python scripts/create_tables.py
python scripts/create_playlists_table.py
python scripts/create_custom_playlists_tables.py

# 5. Start backend
python main.py
# → http://127.0.0.1:8080
# → Swagger UI: http://127.0.0.1:8080/docs
# → DynamoDB Admin: http://127.0.0.1:8001
```

## Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Lint / format
ruff check src/
black src/

# Type check
mypy src/

# Inspect DynamoDB
python local/inspect_dynamdb.py
python local/inspect_custom_playlists.py
```

## Architecture

### Auth Model (v2.0)

Users authenticate via SSO (currently Google) → get an internal `mmp_<uuid>` account → then connect music platforms as separate linked accounts.

```
User → SSO Login (Google)
       ↓
    mmp_<uuid> (internal account)
       ↓
    Platform connections (Spotify / YouTube / SoundCloud)
```

This means **user identity is decoupled from music platforms**. Platforms are connections, not identity.

### Request Lifecycle

All handlers are written for **AWS Lambda** (event/context pattern) but wrapped by FastAPI's `main.py` for local development via Mangum adapter.

```
HTTP Request → FastAPI (local) or API Gateway (prod)
             → Handler (src/handlers/)
             → Service layer (src/services/)
             → DynamoDB
```

### Handler Structure

| Path | Purpose |
|------|---------|
| `src/handlers/auth/` | SSO login flows (Google, future: Microsoft, GitHub) |
| `src/handlers/platforms/` | Music platform OAuth (Spotify, YouTube, SoundCloud) |
| `src/handlers/user.py` | User profile & platform management |
| `src/handlers/custom_playlists.py` | Native MMP playlist CRUD |
| `src/handlers/rebalance_job.py` | Background rebalancing job |

### Service Layer

| File | Purpose |
|------|---------|
| `src/services/dynamodb_service.py` | DynamoDB CRUD, user lookup, SK-prefix queries |
| `src/services/jwt_service.py` | JWT create/verify (HS256, 7-day default) |
| `src/services/token_service.py` | Fernet AES-256 encrypt/decrypt for stored OAuth tokens |
| `src/services/custom_playlist_service.py` | Custom playlist business logic |
| `src/services/playlist_dynamodb_service.py` | DynamoDB wrapper for playlist/track data |

## Database (DynamoDB Single-Table)

**Table:** `multimusic-users` | **PK:** `userId` | **SK:** `sk`

| SK pattern | Record type |
|------------|-------------|
| `PROFILE` | User profile (email, displayName, avatarUrl) |
| `auth#google` | Linked SSO provider |
| `platform#spotify` | Connected music platform (encrypted tokens) |

**Playlist tables** (separate):
- Custom playlists table
- Custom playlist tracks table

All access/refresh tokens are **Fernet-encrypted at rest**. Never log or expose raw tokens.

## API Endpoints Summary

### Auth (SSO)
```
POST   /auth/google/login          → Google OAuth initiation
GET    /auth/google/callback       → OAuth callback → creates mmp_ user + JWT
```

### Platform Connections
```
POST   /platforms/{platform}/connect    → initiate OAuth (requires Bearer)
GET    /platforms/{platform}/callback   → OAuth callback → stores encrypted tokens
POST   /platforms/{platform}/refresh    → refresh access token
GET    /platforms/soundcloud/search     → search tracks
```
Platforms: `spotify`, `youtube`, `soundcloud`

### Playlists (Platform-cached)
```
GET    /platforms/{platform}/playlists                  → cached playlist list
GET    /platforms/{platform}/playlists/{playlist_id}    → refresh playlist details
```

### User
```
GET    /user/profile
GET    /user/auth-providers
GET    /user/platforms
DELETE /user/platforms/{platform}
```

### Custom Playlists (Native MMP)
```
GET/POST                     /user/playlists
GET/PUT/PATCH/DELETE         /user/playlists/{playlist_id}
GET/POST                     /user/playlists/{playlist_id}/tracks
DELETE                       /user/playlists/{playlist_id}/tracks/{track_id}
PUT                          /user/playlists/{playlist_id}/tracks/reorder
```

## Environment Variables

See `local/.env` for local dev values. Required keys:

```bash
JWT_SECRET=                    # JWT signing secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DAYS=7
ENCRYPTION_KEY=                # 32-char key for Fernet token encryption

DYNAMODB_ENDPOINT=http://127.0.0.1:8000   # local only; omit in prod
DYNAMODB_TABLE=multimusic-users
AWS_REGION=us-east-1

FRONTEND_URL=http://127.0.0.1:3000

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8080/auth/google/callback

SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/platforms/spotify/callback

YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REDIRECT_URI=http://127.0.0.1:8080/platforms/youtube/callback

SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
SOUNDCLOUD_REDIRECT_URI=http://127.0.0.1:8080/platforms/soundcloud/callback
```

## Security Conventions

- **Never** log raw access/refresh tokens — always use encrypted form
- **Always** validate Bearer JWT before accessing user data
- CSRF state parameter required in all OAuth initiations
- CORS restricted to `FRONTEND_URL`
- Input sanitized via `src/utils/sanitize.py` before storing playlist names/descriptions

## Testing

```bash
pytest                       # all tests
pytest tests/unit/           # unit tests only
pytest --cov=src --cov-report=html   # coverage report
```

Tests use `pytest-asyncio` for async handlers and `moto` for DynamoDB mocking.

Test files live in `tests/unit/` mirroring `src/` structure. Integration tests directory exists but is empty.

## Debugging Tools

```bash
python local/debug_spotify.py         # Spotify OAuth debug
python local/inspect_dynamdb.py       # Dump DynamoDB contents
python local/inspect_custom_playlists.py
python scripts/diagnoseoauth.py       # OAuth flow diagnostic
python scripts/test_soundcloud.py     # SoundCloud integration
```

## Deployment (AWS Lambda)

Production target is AWS Lambda + API Gateway + DynamoDB (on-demand billing).

```bash
# Package
pip install -r requirements.txt -t package/
cp -r src package/
cd package && zip -r ../lambda.zip . && cd ..
# Deploy via AWS SAM / CDK / Terraform
```

Production checklist:
- Use AWS Secrets Manager instead of env vars
- Enable CloudWatch logging
- Remove `DYNAMODB_ENDPOINT` (uses real DynamoDB)
- Configure API Gateway CORS to production frontend URL
- CloudFront + WAF in front of API Gateway

## Roadmap

- [x] Google SSO
- [x] Spotify, YouTube Music, SoundCloud connections
- [x] Custom playlists (CRUD + track reordering)
- [x] Platform playlist caching
- [ ] Microsoft OAuth
- [ ] GitHub OAuth
- [ ] Token refresh automation
- [ ] Terraform deployment
```

- [ ] **Step 2: Verify file was created**

```bash
cat /home/matej/Projects/mmp_be/multimusic-platform-backend/CLAUDE.md
```

- [ ] **Step 3: Commit**

```bash
cd /home/matej/Projects/mmp_be
git add CLAUDE.md multimusic-platform-backend/CLAUDE.md docs/
git commit -m "docs: add CLAUDE.md files with project context for Claude Code"
```

---

## Verification

After both files are created:

- [ ] Open a new Claude Code session in the repo root and confirm it picks up the CLAUDE.md context
- [ ] Verify `multimusic-platform-backend/CLAUDE.md` accurately reflects current endpoints (cross-check with `main.py`)
