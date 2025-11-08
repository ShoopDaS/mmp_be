"""
Spotify Platform Connection Handlers
"""
import json
import os
import secrets
from typing import Any, Dict
from urllib.parse import urlencode
import httpx

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.handlers.platforms.base import BasePlatformHandler
from src.utils.responses import success_response, error_response, redirect_response

logger = Logger()

# Configuration
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Handler instance
platform_handler = BasePlatformHandler('spotify')


@logger.inject_lambda_context
def connect_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate Spotify connection for logged-in user
    
    Requires valid session token in Authorization header
    """
    try:
        logger.info("Initiating Spotify platform connection")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"User {user_id} connecting Spotify")
        
        # Generate state for CSRF protection (include user_id)
        state = f"{user_id}:{secrets.token_urlsafe(32)}"
        
        # Build Spotify authorization URL
        auth_params = {
            'client_id': SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': SPOTIFY_REDIRECT_URI,
            'state': state,
            'scope': ' '.join([
                'user-read-private',
                'user-read-email',
                'streaming',
                'user-modify-playback-state',
                'user-read-playback-state'
            ])
        }
        
        auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"
        
        return success_response({
            'authUrl': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.exception("Error in Spotify connect")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle Spotify OAuth callback
    
    Links Spotify account to authenticated MultiMusic user
    """
    try:
        logger.info("Processing Spotify OAuth callback")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {})
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error={error}",
                302
            )
        
        if not code or not state:
            logger.error("Missing code or state")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=invalid_callback",
                302
            )
        
        # Extract user ID from state
        try:
            user_id, _ = state.split(':', 1)
        except ValueError:
            logger.error("Invalid state format")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=invalid_state",
                302
            )
        
        # Exchange code for token
        logger.info("Exchanging code for access token")
        token_data = exchange_code_for_token(code)
        
        # Get Spotify user info
        spotify_user_info = get_spotify_user_info(token_data['access_token'])
        spotify_user_id = spotify_user_info['id']
        
        logger.info(f"Linking Spotify user {spotify_user_id} to {user_id}")
        
        # Store platform tokens
        platform_handler.store_platform_tokens(
            user_id=user_id,
            platform_user_id=spotify_user_id,
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            expires_in=token_data['expires_in'],
            scope=token_data.get('scope', '')
        )
        
        # Redirect to dashboard with success
        redirect_url = f"{FRONTEND_URL}/dashboard?spotify=connected"
        
        return redirect_response(redirect_url, 302)
        
    except Exception as e:
        logger.exception("Error in Spotify callback")
        return redirect_response(
            f"{FRONTEND_URL}/dashboard?error=connection_failed",
            302
        )


@logger.inject_lambda_context
def refresh_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Refresh Spotify access token
    
    Requires valid session token
    """
    try:
        logger.info("Refreshing Spotify access token")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"Refreshing Spotify token for user: {user_id}")
        
        # Get refresh token from DynamoDB
        token_data = platform_handler.get_platform_tokens(user_id)
        if not token_data:
            return error_response("Spotify not connected", 404)
        
        encrypted_refresh_token = token_data['refreshToken']
        refresh_token = platform_handler.token_service.decrypt_token(encrypted_refresh_token)
        
        # Request new access token from Spotify
        new_token_data = refresh_access_token(refresh_token)
        
        # Update stored access token
        platform_handler.update_access_token(
            user_id=user_id,
            access_token=new_token_data['access_token'],
            expires_in=new_token_data['expires_in']
        )
        
        # Return new access token (decrypted)
        return success_response({
            'accessToken': new_token_data['access_token'],
            'expiresIn': new_token_data['expires_in']
        })
        
    except Exception as e:
        logger.exception("Error refreshing Spotify token")
        return error_response(str(e), 500)


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token"""
    with httpx.Client() as client:
        response = client.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SPOTIFY_REDIRECT_URI,
                'client_id': SPOTIFY_CLIENT_ID,
                'client_secret': SPOTIFY_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token"""
    with httpx.Client() as client:
        response = client.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': SPOTIFY_CLIENT_ID,
                'client_secret': SPOTIFY_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def get_spotify_user_info(access_token: str) -> Dict[str, Any]:
    """Get user information from Spotify"""
    with httpx.Client() as client:
        response = client.get(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        response.raise_for_status()
        return response.json()
