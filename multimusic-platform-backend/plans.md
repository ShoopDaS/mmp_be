# MultiMusic Platform - Backend Structure

## Project Layout

```
multimusic-platform-backend/
├── src/
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── spotify_auth.py      # Spotify OAuth handlers
│   │   ├── soundcloud_auth.py   # SoundCloud OAuth handlers (future)
│   │   └── user.py              # User management handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── oauth_service.py     # OAuth helper functions
│   │   ├── token_service.py     # Token encryption/decryption
│   │   ├── dynamodb_service.py  # Database operations
│   │   └── jwt_service.py       # JWT token management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User data models
│   │   └── token.py             # Token data models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Logging configuration
│       ├── responses.py         # API response helpers
│       └── exceptions.py        # Custom exceptions
├── tests/
│   ├── unit/
│   │   ├── test_spotify_auth.py
│   │   ├── test_token_service.py
│   │   └── test_jwt_service.py
│   └── integration/
│       └── test_oauth_flow.py
├── local/
│   ├── app.py                   # FastAPI app for local dev
│   ├── docker-compose.yml       # DynamoDB local
│   └── .env.example             # Environment variables template
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── pytest.ini                   # Pytest configuration
├── .env.example                 # Environment template
├── .gitignore
└── README.md
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For local development
```

### 3. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Run DynamoDB Local (Optional)

```bash
cd local
docker-compose up -d
```

### 5. Run Local Development Server

```bash
cd local
uvicorn app:app --reload --port 8000
```

### 6. Run Tests

```bash
pytest
pytest --cov=src  # With coverage
```

## Local Development Endpoints

When running locally with FastAPI:

```
POST   http://localhost:8000/auth/spotify/login
GET    http://localhost:8000/auth/spotify/callback
POST   http://localhost:8000/auth/spotify/refresh
GET    http://localhost:8000/user/profile
DELETE http://localhost:8000/user/platforms/{platform}
GET    http://localhost:8000/health
```

## Lambda Handler Format

Each Lambda function follows this structure:

```python
def handler(event, context):
    """
    AWS Lambda handler function
    
    Args:
        event: API Gateway event object
        context: Lambda context object
        
    Returns:
        dict: API Gateway response object
    """
    try:
        # Parse request
        # Business logic
        # Return response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'success': True})
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
```

## Testing Locally vs AWS

**Local Development (FastAPI):**
- Uses FastAPI for routing
- Hot reload on code changes
- Easy debugging
- DynamoDB Local (optional)
- Mock OAuth responses

**AWS Lambda:**
- Uses Lambda runtime
- API Gateway integration
- Real DynamoDB
- Real OAuth flows

The code is written to work in both environments with minimal changes.
