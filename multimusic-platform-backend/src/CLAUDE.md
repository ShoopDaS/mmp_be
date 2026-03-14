# Source Code Reference

## Handler Structure

| Path | Purpose |
|------|---------|
| `handlers/auth/` | SSO login flows (Google; Microsoft/GitHub planned) |
| `handlers/platforms/` | Music platform OAuth (Spotify, YouTube, SoundCloud) |
| `handlers/user.py` | User profile & platform management |
| `handlers/custom_playlists.py` | Native MMP playlist CRUD |
| `handlers/rebalance_job.py` | Background rebalancing job |

## Service Layer

| File | Purpose |
|------|---------|
| `services/dynamodb_service.py` | DynamoDB CRUD, user lookup, SK-prefix queries |
| `services/jwt_service.py` | JWT create/verify (HS256, 7-day default) |
| `services/token_service.py` | Fernet AES-256 encrypt/decrypt for stored OAuth tokens |
| `services/custom_playlist_service.py` | Custom playlist business logic |
| `services/playlist_dynamodb_service.py` | DynamoDB wrapper for playlist/track data |

## Database (DynamoDB Single-Table)

**Table:** `multimusic-users` | **PK:** `userId` | **SK:** `sk`

| SK pattern | Record type |
|------------|-------------|
| `PROFILE` | User profile (email, displayName, avatarUrl) |
| `auth#google` | Linked SSO provider |
| `platform#spotify` | Connected music platform (encrypted tokens) |

Separate tables for custom playlists and custom playlist tracks.

All access/refresh tokens are **Fernet-encrypted at rest**.

## API Endpoints

### Auth (SSO)
```
POST   /auth/google/login
GET    /auth/google/callback        → creates mmp_ user + JWT
```

### Platform Connections
```
POST   /platforms/{platform}/connect      → initiate OAuth (Bearer required)
GET    /platforms/{platform}/callback     → stores encrypted tokens
POST   /platforms/{platform}/refresh      → refresh access token
GET    /platforms/soundcloud/search       → search tracks
```
Platforms: `spotify`, `youtube`, `soundcloud`

### Playlists (Platform-cached)
```
GET    /platforms/{platform}/playlists
GET    /platforms/{platform}/playlists/{playlist_id}
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
GET/POST                 /user/playlists
GET/PUT/PATCH/DELETE     /user/playlists/{playlist_id}
GET/POST                 /user/playlists/{playlist_id}/tracks
DELETE                   /user/playlists/{playlist_id}/tracks/{track_id}
PUT                      /user/playlists/{playlist_id}/tracks/reorder
```
