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
    soundcloud_connect_handler,
    soundcloud_callback_handler,
    soundcloud_refresh_handler,
    soundcloud_search_handler,
    soundcloud_like_track_handler,
    soundcloud_unlike_track_handler,
    youtube_playlists_handler,
    soundcloud_playlists_handler,
    youtube_playlist_detail_handler,
    soundcloud_playlist_detail_handler,
)
from src.handlers import user
from src.handlers import custom_playlists


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


@app.post("/platforms/soundcloud/connect")
async def soundcloud_connect(request: Request):
    """Initiate SoundCloud connection (requires auth)"""
    event = await request_to_event(request)
    lambda_response = soundcloud_connect_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/platforms/soundcloud/callback")
async def soundcloud_callback(request: Request):
    """Handle SoundCloud OAuth callback"""
    event = await request_to_event(request)
    lambda_response = soundcloud_callback_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.post("/platforms/soundcloud/refresh")
async def soundcloud_refresh(request: Request):
    """Refresh SoundCloud access token (requires auth)"""
    event = await request_to_event(request)
    lambda_response = soundcloud_refresh_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)

@app.get("/platforms/soundcloud/search")
async def soundcloud_search(request: Request):
    """Search SoundCloud for tracks (requires auth)"""
    event = await request_to_event(request)
    lambda_response = soundcloud_search_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.put("/platforms/soundcloud/tracks/{track_id}/like")
async def like_soundcloud_track(request: Request, track_id: str):
    """Like a SoundCloud track, synced to SoundCloud (requires auth)"""
    event = await request_to_event(request)
    event['pathParameters'] = {'track_id': track_id}
    return lambda_response_to_fastapi(soundcloud_like_track_handler(event, mock_context))


@app.delete("/platforms/soundcloud/tracks/{track_id}/like")
async def unlike_soundcloud_track(request: Request, track_id: str):
    """Unlike a SoundCloud track, synced to SoundCloud (requires auth)"""
    event = await request_to_event(request)
    event['pathParameters'] = {'track_id': track_id}
    return lambda_response_to_fastapi(soundcloud_unlike_track_handler(event, mock_context))


# ========== Platform Playlist Routes ==========

@app.get("/platforms/youtube/playlists")
async def youtube_playlists(request: Request):
    """Get user's YouTube playlists with caching (requires auth)"""
    event = await request_to_event(request)
    lambda_response = youtube_playlists_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/platforms/soundcloud/playlists")
async def soundcloud_playlists(request: Request):
    """Get user's SoundCloud playlists with caching (requires auth)"""
    event = await request_to_event(request)
    lambda_response = soundcloud_playlists_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/platforms/youtube/playlists/{playlist_id}")
async def youtube_playlist_detail(request: Request, playlist_id: str):
    """Refresh a single YouTube playlist from source (requires auth)"""
    event = await request_to_event(request)
    event['pathParameters'] = {'playlist_id': playlist_id}
    lambda_response = youtube_playlist_detail_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/platforms/soundcloud/playlists/{playlist_id}")
async def soundcloud_playlist_detail(request: Request, playlist_id: str):
    """Refresh a single SoundCloud playlist from source (requires auth)"""
    event = await request_to_event(request)
    event['pathParameters'] = {'playlist_id': playlist_id}
    lambda_response = soundcloud_playlist_detail_handler(event, mock_context)
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


# ========== Custom Playlist Routes ==========

@app.get("/user/playlists")
async def get_playlists(request: Request):
    """List user's custom playlists (requires auth)"""
    event = await request_to_event(request)
    lambda_response = custom_playlists.get_playlists_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.post("/user/playlists")
async def create_playlist(request: Request):
    """Create a new custom playlist (requires auth)"""
    event = await request_to_event(request)
    lambda_response = custom_playlists.create_playlist_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.api_route("/user/playlists/{playlist_id}", methods=["PUT", "PATCH"])
async def update_playlist(request: Request, playlist_id: str):
    """Update custom playlist metadata (requires auth)"""
    event = await request_to_event(request)
    event["pathParameters"] = {"playlistId": playlist_id}
    lambda_response = custom_playlists.update_playlist_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.delete("/user/playlists/{playlist_id}")
async def delete_playlist(request: Request, playlist_id: str):
    """Delete a custom playlist and all its tracks (requires auth)"""
    event = await request_to_event(request)
    event["pathParameters"] = {"playlistId": playlist_id}
    lambda_response = custom_playlists.delete_playlist_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.get("/user/playlists/{playlist_id}/tracks")
async def get_playlist_tracks(request: Request, playlist_id: str):
    """Get all tracks in a custom playlist (requires auth)"""
    event = await request_to_event(request)
    event["pathParameters"] = {"playlistId": playlist_id}
    lambda_response = custom_playlists.get_tracks_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.post("/user/playlists/{playlist_id}/tracks")
async def add_playlist_track(request: Request, playlist_id: str):
    """Add a track to a custom playlist (requires auth)"""
    event = await request_to_event(request)
    event["pathParameters"] = {"playlistId": playlist_id}
    lambda_response = custom_playlists.add_track_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.put("/user/playlists/{playlist_id}/tracks/reorder")
async def reorder_playlist_tracks(request: Request, playlist_id: str):
    """Reorder tracks in a custom playlist (requires auth)"""
    event = await request_to_event(request)
    event["pathParameters"] = {"playlistId": playlist_id}
    lambda_response = custom_playlists.reorder_tracks_handler(event, mock_context)
    return lambda_response_to_fastapi(lambda_response)


@app.delete("/user/playlists/{playlist_id}/tracks/{track_id}")
async def delete_playlist_track(request: Request, playlist_id: str, track_id: str):
    """Remove a track from a custom playlist (requires auth)"""
    event = await request_to_event(request)
    event["pathParameters"] = {"playlistId": playlist_id, "trackId": track_id}
    lambda_response = custom_playlists.delete_track_handler(event, mock_context)
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