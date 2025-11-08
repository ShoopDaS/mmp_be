"""
FastAPI application with updated routing for multi-provider SSO
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os

# Import handlers
from src.handlers.auth import google
from src.handlers.platforms import spotify
from src.handlers import user

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
    return google.login_handler(event, None)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    event = await request_to_event(request)
    return google.callback_handler(event, None)


# ========== Platform Connection Routes ==========

@app.post("/platforms/spotify/connect")
async def spotify_connect(request: Request):
    """Initiate Spotify connection (requires auth)"""
    event = await request_to_event(request)
    return spotify.connect_handler(event, None)


@app.get("/platforms/spotify/callback")
async def spotify_callback(request: Request):
    """Handle Spotify OAuth callback"""
    event = await request_to_event(request)
    return spotify.callback_handler(event, None)


@app.post("/platforms/spotify/refresh")
async def spotify_refresh(request: Request):
    """Refresh Spotify access token (requires auth)"""
    event = await request_to_event(request)
    return spotify.refresh_handler(event, None)


# ========== User Management Routes ==========

@app.get("/user/profile")
async def user_profile(request: Request):
    """Get user profile (requires auth)"""
    event = await request_to_event(request)
    return user.profile_handler(event, None)


@app.get("/user/auth-providers")
async def user_auth_providers(request: Request):
    """Get linked auth providers (requires auth)"""
    event = await request_to_event(request)
    return user.auth_providers_handler(event, None)


@app.get("/user/platforms")
async def user_platforms(request: Request):
    """Get connected music platforms (requires auth)"""
    event = await request_to_event(request)
    return user.platforms_handler(event, None)


@app.delete("/user/platforms/{platform}")
async def delete_platform(request: Request, platform: str):
    """Disconnect music platform (requires auth)"""
    event = await request_to_event(request)
    event['pathParameters'] = {'platform': platform}
    return user.delete_platform_handler(event, None)


# ========== Health Check ==========

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# ========== Helper Functions ==========

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


# Lambda handler for AWS
handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
