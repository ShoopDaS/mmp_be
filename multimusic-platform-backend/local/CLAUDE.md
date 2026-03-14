# Local Dev Tools

## DynamoDB

```bash
docker-compose up -d                        # start DynamoDB Local
python inspect_dynamdb.py                   # dump users table
python inspect_custom_playlists.py          # dump playlists table
```

## Debug Scripts (../scripts/)

```bash
python ../scripts/diagnoseoauth.py          # OAuth flow diagnostic
python ../scripts/test_soundcloud.py        # SoundCloud integration test
python ../local/debug_spotify.py            # Spotify OAuth debug
```

## Table Setup (first time)

```bash
python ../scripts/create_tables.py
python ../scripts/create_playlists_table.py
python ../scripts/create_custom_playlists_tables.py
```

Config lives in `local/.env` — copy from `.env.example` if starting fresh.
