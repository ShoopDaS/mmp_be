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

MultiMusic Platform is a multi-provider SSO backend that lets users authenticate with Google or Spotify (Microsoft/GitHub planned), then connect multiple music streaming services (Spotify, YouTube Music, SoundCloud) to a single internal account.

All active development is in `multimusic-platform-backend/`. See its `CLAUDE.md` for dev workflow.
