"""
FastAPI application for local development

This wraps the Lambda handlers to provide a local development server
"""
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Lambda handlers - use explicit imports
from src.handlers.spotify_auth import login_handler, callback_handler, refresh_handler


# Mock Lambda Context for local development
class MockLambdaContext:
    """Mock Lambda context for local development"""
    def __init__(self):
        self.function_name = "local-dev"
        self.memory_limit_in_mb = 128
        self.invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:local-dev"
        self.aws_request_id = "local-request-id"
        self.log_group_name = "/aws/lambda/local-dev"
        self.log_stream_name = "local-stream"

# Create mock context instance
mock_context = MockLambdaContext()


app = FastAPI(
    title="MultiMusic Platform API",
    description="Local development server for MultiMusic Platform backend",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def lambda_to_fastapi_response(lambda_response: dict) -> Response:
    """Convert Lambda response to FastAPI response"""
    status_code = lambda_response.get('statusCode', 200)
    headers = lambda_response.get('headers', {})
    body = lambda_response.get('body', '')
    
    # Check if it's a redirect
    if 'Location' in headers:
        return RedirectResponse(
            url=headers['Location'],
            status_code=status_code
        )
    
    # Parse body if it's a string
    if isinstance(body, str) and body:
        try:
            import json
            body = json.loads(body)
        except:
            pass
    
    # Regular JSON response
    return JSONResponse(
        content=body if body else {},
        status_code=status_code,
        headers={k: v for k, v in headers.items() if k != 'Content-Type'}
    )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "MultiMusic Platform API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Spotify OAuth endpoints
@app.post("/auth/spotify/login")
async def spotify_login(request: Request):
    """Initiate Spotify OAuth login"""
    body = await request.body()
    
    event = {
        "httpMethod": "POST",
        "headers": dict(request.headers),
        "body": body.decode() if body else '{}',
        "queryStringParameters": dict(request.query_params)
    }
    
    lambda_response = login_handler(event, mock_context)
    return lambda_to_fastapi_response(lambda_response)


@app.get("/auth/spotify/callback")
async def spotify_callback(request: Request):
    """Handle Spotify OAuth callback"""
    event = {
        "httpMethod": "GET",
        "headers": dict(request.headers),
        "queryStringParameters": dict(request.query_params)
    }
    
    lambda_response = callback_handler(event, mock_context)
    return lambda_to_fastapi_response(lambda_response)


@app.post("/auth/spotify/refresh")
async def spotify_refresh(request: Request):
    """Refresh Spotify access token"""
    body = await request.body()
    headers_dict = {}
    for key, value in request.headers.items():
        headers_dict[key] = value
        # Also add capitalized version for Lambda compatibility
        headers_dict[key.capitalize()] = value
     
    event = {
        "httpMethod": "POST",
        "headers": dict(request.headers),
        "body": body.decode() if body else '{}',
        "queryStringParameters": dict(request.query_params)
    }
    
    lambda_response = refresh_handler(event, mock_context)
    return lambda_to_fastapi_response(lambda_response)


# User management endpoints (to be implemented)
@app.get("/user/profile")
async def get_user_profile(request: Request):
    """Get user profile"""
    return {"message": "User profile endpoint - to be implemented"}


@app.delete("/user/platforms/{platform}")
async def disconnect_platform(platform: str, request: Request):
    """Disconnect a platform"""
    return {"message": f"Disconnect {platform} - to be implemented"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MultiMusic Platform API on http://localhost:8080")
    print("📊 API docs available at http://localhost:8080/docs")
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)