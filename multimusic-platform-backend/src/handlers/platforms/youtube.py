"""
YouTube Music Platform Connection Handlers
Uses Google OAuth with YouTube-specific scopes
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

# Configuration - Uses Google OAuth credentials
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
YOUTUBE_REDIRECT_URI = os.environ.get('YOUTUBE_REDIRECT_URI', 'http://127.0.0.1:8080/platforms/youtube/callback')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Handler instance
platform_handler = BasePlatformHandler('youtube')


@logger.inject_lambda_context
def connect_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate YouTube Music connection for logged-in user
    
    Requires valid session token in Authorization header
    Uses Google OAuth with YouTube-specific scopes
    """
    try:
        logger.info("Initiating YouTube Music platform connection")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"User {user_id} connecting YouTube Music")
        
        # Check if YouTube already connected
        existing_tokens = platform_handler.get_platform_tokens(user_id)
        if existing_tokens:
            logger.info(f"YouTube Music already connected for user {user_id}")
            return success_response({
                'message': 'YouTube Music already connected',
                'connected': True
            })
        
        # Generate state for CSRF protection (include user_id)
        state = f"{user_id}:{secrets.token_urlsafe(32)}"
        
        # Build Google authorization URL with YouTube-specific scopes
        auth_params = {
            'client_id': GOOGLE_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': YOUTUBE_REDIRECT_URI,
            'state': state,
            'scope': ' '.join([
                'https://www.googleapis.com/auth/youtube.readonly',
                'https://www.googleapis.com/auth/youtube.force-ssl',
                'https://www.googleapis.com/auth/youtubepartner'
            ]),
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent'  # Force consent to get refresh token
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
        
        return success_response({
            'authUrl': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.exception("Error in YouTube Music connect")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle YouTube Music OAuth callback
    
    Links YouTube Music account to authenticated MultiMusic user
    Uses Google OAuth token exchange
    """
    try:
        logger.info("Processing YouTube Music OAuth callback")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {})
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=youtube_{error}",
                302
            )
        
        if not code or not state:
            logger.error("Missing code or state")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=youtube_invalid_callback",
                302
            )
        
        # Extract user ID from state
        try:
            user_id, _ = state.split(':', 1)
        except ValueError:
            logger.error("Invalid state format")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=youtube_invalid_state",
                302
            )
        
        # Exchange code for token
        logger.info("Exchanging code for access token")
        token_data = exchange_code_for_token(code)
        
        # Get YouTube channel info (this is the user's YouTube identity)
        youtube_channel_info = get_youtube_channel_info(token_data['access_token'])
        
        if not youtube_channel_info:
            logger.error("No YouTube channel found for this Google account")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=youtube_no_channel",
                302
            )
        
        youtube_channel_id = youtube_channel_info['id']
        youtube_channel_title = youtube_channel_info.get('title', 'Unknown Channel')
        
        logger.info(f"Linking YouTube channel {youtube_channel_id} to user {user_id}")
        
        # Store platform tokens
        platform_handler.store_platform_tokens(
            user_id=user_id,
            platform_user_id=youtube_channel_id,
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),  # May not always be present
            expires_in=token_data['expires_in'],
            scope=token_data.get('scope', '')
        )
        
        # Also store channel title for display purposes
        from src.services.dynamodb_service import DynamoDBService
        db_service = DynamoDBService()
        db_service.update_item(
            user_id=user_id,
            sk='platform#youtube',
            updates={
                'channelTitle': youtube_channel_title
            }
        )
        
        # Redirect to dashboard with success
        redirect_url = f"{FRONTEND_URL}/dashboard?youtube=connected"
        
        return redirect_response(redirect_url, 302)
        
    except Exception as e:
        logger.exception("Error in YouTube Music callback")
        return redirect_response(
            f"{FRONTEND_URL}/dashboard?error=youtube_connection_failed",
            302
        )


@logger.inject_lambda_context
def refresh_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Refresh YouTube Music access token
    
    Requires valid session token
    Uses Google OAuth token refresh endpoint
    """
    try:
        logger.info("Refreshing YouTube Music access token")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"Refreshing YouTube Music token for user: {user_id}")
        
        # Get refresh token from DynamoDB
        token_data = platform_handler.get_platform_tokens(user_id)
        if not token_data:
            return error_response("YouTube Music not connected", 404)
        
        encrypted_refresh_token = token_data.get('refreshToken')
        if not encrypted_refresh_token:
            logger.error("No refresh token found - user may need to reconnect")
            return error_response("No refresh token available - please reconnect YouTube Music", 400)
        
        refresh_token = platform_handler.token_service.decrypt_token(encrypted_refresh_token)
        
        # Request new access token from Google
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
        logger.exception("Error refreshing YouTube Music token")
        return error_response(str(e), 500)


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token using Google OAuth"""
    with httpx.Client() as client:
        response = client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'redirect_uri': YOUTUBE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token via Google OAuth"""
    with httpx.Client() as client:
        response = client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def get_youtube_channel_info(access_token: str) -> Dict[str, Any]:
    """
    Get user's YouTube channel information
    
    Returns the user's primary YouTube channel details
    This serves as the YouTube user identity
    """
    with httpx.Client() as client:
        response = client.get(
            'https://www.googleapis.com/youtube/v3/channels',
            params={
                'part': 'snippet,contentDetails',
                'mine': 'true'
            },
            headers={'Authorization': f'Bearer {access_token}'}
        )
        response.raise_for_status()
        data = response.json()
        
        items = data.get('items', [])
        if not items:
            logger.warning("No YouTube channel found for this account")
            return None
        
        # Return first channel (primary channel)
        channel = items[0]
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'description': channel['snippet'].get('description', ''),
            'thumbnail': channel['snippet']['thumbnails'].get('default', {}).get('url', '')
        }