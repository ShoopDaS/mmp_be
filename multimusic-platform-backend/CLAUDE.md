# MultiMusic Platform Backend

Python 3.13 / FastAPI backend with AWS Lambda deployment target. Multi-provider SSO + music platform OAuth connections.

## Quick Start (Local Dev)

```bash
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cd local && docker-compose up -d && cd ..

# First time only — create DynamoDB tables
python scripts/create_tables.py
python scripts/create_playlists_table.py
python scripts/create_custom_playlists_tables.py

python main.py
# → http://127.0.0.1:8080
# → Swagger UI: http://127.0.0.1:8080/docs
# → DynamoDB Admin: http://127.0.0.1:8001
```

## Common Commands

```bash
pytest                              # all tests
pytest --cov=src                    # with coverage
ruff check src/
black src/
mypy src/
```

## Architecture

Users authenticate via SSO (Google or Spotify) → get an internal `mmp_<uuid>` account → connect music platforms as separate linked accounts. **User identity is decoupled from music platforms** — platforms are connections, not identity, even when Spotify login auto-connects the same platform.

All handlers are written for **AWS Lambda** (event/context pattern), wrapped by FastAPI's `main.py` for local dev via Mangum adapter.

```
HTTP Request → FastAPI (local) / API Gateway (prod)
             → src/handlers/
             → src/services/
             → DynamoDB
```

See `src/CLAUDE.md` for handler/service structure and API reference.

## Environment Variables

See `local/.env` for local dev values. Required keys:

```bash
JWT_SECRET=
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
SPOTIFY_AUTH_REDIRECT_URI=http://127.0.0.1:8080/auth/spotify/callback

YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REDIRECT_URI=http://127.0.0.1:8080/platforms/youtube/callback

SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
SOUNDCLOUD_REDIRECT_URI=http://127.0.0.1:8080/platforms/soundcloud/callback
```

## Security Conventions

- **Never** log raw access/refresh tokens — always encrypted form
- **Always** validate Bearer JWT before accessing user data
- CSRF state parameter required in all OAuth initiations
- CORS restricted to `FRONTEND_URL`
- Input sanitized via `src/utils/sanitize.py` before storing playlist names/descriptions
