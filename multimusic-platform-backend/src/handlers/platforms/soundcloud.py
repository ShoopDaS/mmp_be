"""
SoundCloud Platform Connection Handlers
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
SOUNDCLOUD_CLIENT_ID = os.environ.get('SOUNDCLOUD_CLIENT_ID')
SOUNDCLOUD_CLIENT_SECRET = os.environ.get('SOUNDCLOUD_CLIENT_SECRET')
SOUNDCLOUD_REDIRECT_URI = os.environ.get('SOUNDCLOUD_REDIRECT_URI', 'http://127.0.0.1:8080/platforms/soundcloud/callback')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Handler instance
platform_handler = BasePlatformHandler('soundcloud')


@logger.inject_lambda_context
def connect_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate SoundCloud connection for logged-in user
    
    Requires valid session token in Authorization header
    """
    try:
        logger.info("Initiating SoundCloud platform connection")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"User {user_id} connecting SoundCloud")
        
        # Check if SoundCloud already connected
        existing_tokens = platform_handler.get_platform_tokens(user_id)
        if existing_tokens:
            logger.info(f"SoundCloud already connected for user {user_id}")
            return success_response({
                'message': 'SoundCloud already connected',
                'connected': True
            })
        
        # Generate state for CSRF protection (include user_id)
        state = f"{user_id}:{secrets.token_urlsafe(32)}"
        
        # Build SoundCloud authorization URL
        auth_params = {
            'client_id': SOUNDCLOUD_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
            'state': state,
            'scope': 'non-expiring'
        }
        
        auth_url = f"https://soundcloud.com/connect?{urlencode(auth_params)}"
        
        return success_response({
            'authUrl': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.exception("Error in SoundCloud connect")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle SoundCloud OAuth callback
    
    Links SoundCloud account to authenticated MultiMusic user
    """
    try:
        logger.info("Processing SoundCloud OAuth callback")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {})
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=soundcloud_{error}",
                302
            )
        
        if not code or not state:
            logger.error("Missing code or state")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=soundcloud_invalid_callback",
                302
            )
        
        # Extract user ID from state
        try:
            user_id, _ = state.split(':', 1)
        except ValueError:
            logger.error("Invalid state format")
            return redirect_response(
                f"{FRONTEND_URL}/dashboard?error=soundcloud_invalid_state",
                302
            )
        
        # Exchange code for token
        logger.info("Exchanging code for access token")
        token_data = exchange_code_for_token(code)
        
        # Get SoundCloud user info
        soundcloud_user_info = get_soundcloud_user_info(token_data['access_token'])
        soundcloud_user_id = str(soundcloud_user_info['id'])
        soundcloud_username = soundcloud_user_info.get('username', 'Unknown User')
        
        logger.info(f"Linking SoundCloud user {soundcloud_user_id} to {user_id}")
        
        # Store platform tokens
        platform_handler.store_platform_tokens(
            user_id=user_id,
            platform_user_id=soundcloud_user_id,
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token', ''),
            expires_in=token_data.get('expires_in', 31536000),
            scope=token_data.get('scope', 'non-expiring')
        )
        
        # Also store username for display purposes
        from src.services.dynamodb_service import DynamoDBService
        db_service = DynamoDBService()
        db_service.update_item(
            user_id=user_id,
            sk='platform#soundcloud',
            updates={
                'username': soundcloud_username,
                'permalink': soundcloud_user_info.get('permalink', ''),
                'avatarUrl': soundcloud_user_info.get('avatar_url', '')
            }
        )
        
        # Redirect to dashboard with success
        redirect_url = f"{FRONTEND_URL}/dashboard?soundcloud=connected"
        
        return redirect_response(redirect_url, 302)
        
    except Exception as e:
        logger.exception("Error in SoundCloud callback")
        return redirect_response(
            f"{FRONTEND_URL}/dashboard?error=soundcloud_connection_failed",
            302
        )


@logger.inject_lambda_context
def refresh_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Refresh SoundCloud access token
    
    Requires valid session token
    """
    try:
        logger.info("Refreshing SoundCloud access token")
        
        # Verify user is authenticated
        user_id = platform_handler.get_user_from_session(event)
        if not user_id:
            return error_response("Authentication required", 401)
        
        logger.info(f"Refreshing SoundCloud token for user: {user_id}")
        
        # Get token data from DynamoDB
        token_data = platform_handler.get_platform_tokens(user_id)
        if not token_data:
            return error_response("SoundCloud not connected", 404)
        
        encrypted_refresh_token = token_data.get('refreshToken')
        
        if not encrypted_refresh_token:
            # SoundCloud with 'non-expiring' scope may not need refresh
            # Return current access token if still valid
            logger.info("No refresh token found - returning current access token")
            encrypted_access_token = token_data.get('accessToken')
            if encrypted_access_token:
                access_token = platform_handler.token_service.decrypt_token(encrypted_access_token)
                return success_response({
                    'accessToken': access_token,
                    'expiresIn': token_data.get('expiresIn', 31536000)
                })
            else:
                return error_response("No access token available - please reconnect SoundCloud", 400)
        
        refresh_token = platform_handler.token_service.decrypt_token(encrypted_refresh_token)
        
        # Request new access token from SoundCloud
        new_token_data = refresh_access_token(refresh_token)
        
        # Update stored access token
        platform_handler.update_access_token(
            user_id=user_id,
            access_token=new_token_data['access_token'],
            expires_in=new_token_data.get('expires_in', 31536000)
        )
        
        # Return new access token (decrypted)
        return success_response({
            'accessToken': new_token_data['access_token'],
            'expiresIn': new_token_data.get('expires_in', 31536000)
        })
        
    except Exception as e:
        logger.exception("Error refreshing SoundCloud token")
        return error_response(str(e), 500)


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token"""
    with httpx.Client() as client:
        response = client.post(
            'https://api.soundcloud.com/oauth2/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SOUNDCLOUD_REDIRECT_URI,
                'client_id': SOUNDCLOUD_CLIENT_ID,
                'client_secret': SOUNDCLOUD_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token"""
    with httpx.Client() as client:
        response = client.post(
            'https://api.soundcloud.com/oauth2/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': SOUNDCLOUD_CLIENT_ID,
                'client_secret': SOUNDCLOUD_CLIENT_SECRET
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def get_soundcloud_user_info(access_token: str) -> Dict[str, Any]:
    """Get user information from SoundCloud"""
    with httpx.Client() as client:
        response = client.get(
            'https://api.soundcloud.com/me',
            params={'oauth_token': access_token}
        )
        response.raise_for_status()
        return response.json()