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

# Import Lambda handlers
from src.handlers import spotify_auth

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
    
    # Regular JSON response
    return JSONResponse(
        content=body if isinstance(body, dict) else eval(body) if body else {},
        status_code=status_code,
        headers=headers
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
    event = {
        "httpMethod": "POST",
        "headers": dict(request.headers),
        "body": await request.body(),
        "queryStringParameters": dict(request.query_params)
    }
    
    lambda_response = spotify_auth.login_handler(event, None)
    return lambda_to_fastapi_response(lambda_response)


@app.get("/auth/spotify/callback")
async def spotify_callback(request: Request):
    """Handle Spotify OAuth callback"""
    event = {
        "httpMethod": "GET",
        "headers": dict(request.headers),
        "queryStringParameters": dict(request.query_params)
    }
    
    lambda_response = spotify_auth.callback_handler(event, None)
    return lambda_to_fastapi_response(lambda_response)


@app.post("/auth/spotify/refresh")
async def spotify_refresh(request: Request):
    """Refresh Spotify access token"""
    body = await request.body()
    
    event = {
        "httpMethod": "POST",
        "headers": dict(request.headers),
        "body": body.decode() if body else '{}',
        "queryStringParameters": dict(request.query_params)
    }
    
    lambda_response = spotify_auth.refresh_handler(event, None)
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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)