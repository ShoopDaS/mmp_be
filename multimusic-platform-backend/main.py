"""
FastAPI application with updated routing for multi-provider SSO
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Optional: Only needed for AWS Lambda deployment
try:
    from mangum import Mangum
    LAMBDA_AVAILABLE = True
except ImportError:
    LAMBDA_AVAILABLE = False

# Import handlers
from src.handlers.auth import google
from src.handlers.platforms import (
    spotify_connect_handler,
    spotify_callback_handler,
    spotify_refresh_handler,
    youtube_connect_handler,
    youtube_callback_handler,
    youtube_refresh_handler,
)
from src.handlers import user


# Mock Lambda Context for local development
class MockLambdaContext:
    """Mock Lambda context for local development"""
    def __init__(self):
        self.function_name = "local-dev"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:local-dev"
        self.memory_limit_in_mb = 128
        self.aws_request_id = "local-request-id"
        self.log_group_name = "/aws/lambda/local-dev"
        self.log_stream_name = "local-stream"
        self.identity = None
        self.client_context = None
    
    def get_remaining_time_in_millis(self):
        return 300000  # 5 minutes


# Create mock context instance
mock_context = MockLambdaContext()

app = FastAPI(title="MultiMusic Platform API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8081",
        os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== SSO Authentication Routes ==========

@app.post("/auth/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    event = await request_to_event(request)
    lambda_response = google.login_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    event = await request_to_event(request)
    lambda_response = google.callback_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


# ========== Platform Connection Routes ==========

@app.post("/platforms/spotify/connect")
async def spotify_connect(request: Request):
    """Initiate Spotify connection (requires auth)"""
    event = await request_to_event(request)
    lambda_response = spotify_connect_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/platforms/spotify/callback")
async def spotify_callback(request: Request):
    """Handle Spotify OAuth callback"""
    event = await request_to_event(request)
    lambda_response = spotify_callback_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.post("/platforms/spotify/refresh")
async def spotify_refresh(request: Request):
    """Refresh Spotify access token (requires auth)"""
    event = await request_to_event(request)
    lambda_response = spotify_refresh_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.post("/platforms/youtube/connect")
async def youtube_connect(request: Request):
    """Initiate YouTube Music connection (requires auth)"""
    event = await request_to_event(request)
    lambda_response = youtube_connect_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/platforms/youtube/callback")
async def youtube_callback(request: Request):
    """Handle YouTube Music OAuth callback"""
    event = await request_to_event(request)
    lambda_response = youtube_callback_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.post("/platforms/youtube/refresh")
async def youtube_refresh(request: Request):
    """Refresh YouTube Music access token (requires auth)"""
    event = await request_to_event(request)
    lambda_response = youtube_refresh_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


# ========== User Management Routes ==========

@app.get("/user/profile")
async def user_profile(request: Request):
    """Get user profile (requires auth)"""
    event = await request_to_event(request)
    lambda_response = user.profile_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/user/auth-providers")
async def user_auth_providers(request: Request):
    """Get linked auth providers (requires auth)"""
    event = await request_to_event(request)
    lambda_response = user.auth_providers_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/user/platforms")
async def user_platforms(request: Request):
    """Get connected music platforms (requires auth)"""
    event = await request_to_event(request)
    lambda_response = user.platforms_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.delete("/user/platforms/{platform}")
async def delete_platform(request: Request, platform: str):
    """Disconnect music platform (requires auth)"""
    event = await request_to_event(request)
    event['pathParameters'] = {'platform': platform}
    lambda_response = user.delete_platform_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


# ========== Health Check ==========

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# ========== Helper Functions ==========

def lambda_response_to_fastapi(lambda_response: dict):
    """Convert Lambda response format to FastAPI response"""
    from fastapi.responses import JSONResponse, RedirectResponse
    import json
    
    status_code = lambda_response.get('statusCode', 200)
    headers = lambda_response.get('headers', {})
    body = lambda_response.get('body', '')
    
    # Handle redirects
    if 'Location' in headers:
        return RedirectResponse(
            url=headers['Location'],
            status_code=status_code
        )
    
    # Handle JSON responses
    if body:
        try:
            body_data = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            body_data = {'error': 'Invalid response format'}
    else:
        body_data = {}
    
    # Remove CORS headers (FastAPI middleware handles these)
    response_headers = {k: v for k, v in headers.items() 
                       if k not in ['Access-Control-Allow-Origin', 
                                   'Access-Control-Allow-Credentials',
                                   'Content-Type', 'Location']}
    
    return JSONResponse(
        content=body_data,
        status_code=status_code,
        headers=response_headers if response_headers else None
    )


async def request_to_event(request: Request) -> dict:
    """Convert FastAPI request to Lambda event format"""
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
        body = body.decode() if body else "{}"
    
    return {
        "httpMethod": request.method,
        "path": request.url.path,
        "queryStringParameters": dict(request.query_params),
        "headers": dict(request.headers),
        "body": body,
        "pathParameters": request.path_params,
    }


# Lambda handler for AWS (only if mangum is installed)
if LAMBDA_AVAILABLE:
    handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)