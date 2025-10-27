# MultiMusic Platform - Backend Setup Guide

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to backend directory
cd multimusic-platform-backend

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your values
# Required for local development:
# - SPOTIFY_CLIENT_ID
# - SPOTIFY_CLIENT_SECRET
# - JWT_SECRET (generate a random string)
# - ENCRYPTION_KEY (generate a random 32-char string)
```

### 3. Run DynamoDB Local (Optional)

```bash
cd local
docker-compose up -d

# Verify DynamoDB is running
curl http://localhost:8000

# Access DynamoDB Admin UI (optional)
# http://localhost:8001
```

### 4. Create DynamoDB Tables (Local)

```bash
# Run the table creation script
python scripts/create_tables.py
```

### 5. Start Development Server

```bash
cd local
python app.py

# Or use uvicorn directly
uvicorn app:app --reload --port 8000
```

Server will be running at: `http://localhost:8000`

## Testing the API

### Using curl

**1. Initiate Spotify Login**
```bash
curl -X POST http://localhost:8000/auth/spotify/login
```

Response:
```json
{
  "authUrl": "https://accounts.spotify.com/authorize?...",
  "state": "random-state-string"
}
```

**2. Test Health Endpoint**
```bash
curl http://localhost:8000/health
```

### Using the Frontend

1. Start the frontend (from frontend directory)
2. Update frontend to point to `http://localhost:8000` for backend
3. Complete the OAuth flow through the UI

## Project Structure

```
multimusic-platform-backend/
├── src/
│   ├── handlers/           # Lambda function handlers
│   │   ├── spotify_auth.py
│   │   └── user.py
│   ├── services/           # Business logic services
│   │   ├── token_service.py
│   │   ├── jwt_service.py
│   │   └── dynamodb_service.py
│   └── utils/              # Utility functions
│       └── responses.py
├── local/
│   ├── app.py             # FastAPI local development server
│   └── docker-compose.yml # DynamoDB Local
├── tests/
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
└── scripts/
    └── create_tables.py   # DynamoDB table creation
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/unit/test_token_service.py

# Run with verbose output
pytest -v
```

## Local Development Tips

### Using DynamoDB Local

DynamoDB Local allows you to develop without AWS credentials:

```bash
# Start DynamoDB Local
docker-compose up -d

# Check logs
docker-compose logs -f dynamodb-local

# Stop
docker-compose down
```

### Environment Variables for Local Dev

```bash
# .env for local development
ENVIRONMENT=local
DYNAMODB_ENDPOINT=http://localhost:8000
SPOTIFY_REDIRECT_URI=http://localhost:8000/auth/spotify/callback
FRONTEND_URL=http://127.0.0.1:8081
```

### Hot Reload

FastAPI supports hot reload - any code changes will automatically restart the server:

```bash
uvicorn local.app:app --reload
```

## Debugging

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
```

### Using Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use Python 3.7+ breakpoint()
breakpoint()
```

### Check DynamoDB Tables

```bash
# List tables
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Scan a table
aws dynamodb scan \
  --table-name multimusic-tokens \
  --endpoint-url http://localhost:8000
```

## Common Issues

### Issue: "ENCRYPTION_KEY not set"
**Solution:** Add `ENCRYPTION_KEY` to your `.env` file
```bash
ENCRYPTION_KEY=your-32-character-encryption-key-here
```

### Issue: "Cannot connect to DynamoDB"
**Solution:** Make sure DynamoDB Local is running
```bash
docker-compose ps
docker-compose up -d
```

### Issue: "JWT_SECRET not set"
**Solution:** Add `JWT_SECRET` to your `.env` file
```bash
JWT_SECRET=your-super-secret-jwt-key-change-in-production
```

### Issue: "Module not found" errors
**Solution:** Make sure you're in the virtual environment and dependencies are installed
```bash
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Deploying to AWS

See the main README for deployment instructions using Terraform.

The Lambda handlers in `src/handlers/` are designed to work directly as Lambda functions:
- `spotify_auth.login_handler`
- `spotify_auth.callback_handler`
- `spotify_auth.refresh_handler`

## Next Steps

1. ✅ Complete Spotify OAuth flow
2. Add user management endpoints
3. Add SoundCloud OAuth
4. Write integration tests
5. Set up CI/CD pipeline
6. Deploy to AWS

## API Documentation

When running locally, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Getting Help

- Check CloudWatch Logs (when deployed)
- Review test files for usage examples
- Check the main README for architecture details