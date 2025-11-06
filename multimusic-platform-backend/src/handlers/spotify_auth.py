"""
Spotify OAuth Lambda Handlers
"""
import json
import os
import secrets
from typing import Any, Dict
from urllib.parse import urlencode, parse_qs
import httpx

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.services.token_service import TokenService
from src.services.dynamodb_service import DynamoDBService
from src.services.jwt_service import JWTService
from src.utils.responses import success_response, error_response, redirect_response

logger = Logger()

# Configuration
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Services
token_service = TokenService()
db_service = DynamoDBService()
jwt_service = JWTService()


# After all the imports and configuration section
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

@logger.inject_lambda_context
def login_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate Spotify OAuth login
    
    Returns authorization URL to redirect user to Spotify
    """
    try:
        logger.info("Initiating Spotify OAuth login")
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
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
        logger.exception("Error in Spotify login")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle Spotify OAuth callback
    
    Exchange authorization code for access token and store in DynamoDB
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
                f"{FRONTEND_URL}?error={error}",
                302
            )
        
        if not code:
            logger.error("No authorization code provided")
            return redirect_response(
                f"{FRONTEND_URL}?error=no_code",
                302
            )
        
        # Exchange code for token
        logger.info("Exchanging code for access token")
        token_data = exchange_code_for_token(code)
        
        # Get user info from Spotify
        user_info = get_spotify_user_info(token_data['access_token'])
        user_id = user_info['id']
        
        logger.info(f"User authenticated: {user_id}")
        
        # Store tokens in DynamoDB
        encrypted_access_token = token_service.encrypt_token(token_data['access_token'])
        encrypted_refresh_token = token_service.encrypt_token(token_data['refresh_token'])
        
        db_service.store_token(
            user_id=user_id,
            platform='spotify',
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            expires_in=token_data['expires_in'],
            scope=token_data.get('scope', '')
        )
        
        # Store user profile
        db_service.store_user(
            user_id=user_id,
            email=user_info.get('email', ''),
            display_name=user_info.get('display_name', '')
        )
        
        # Generate JWT session token
        session_token = jwt_service.create_token(user_id)
        
        # Redirect to frontend with session token
        redirect_url = f"{FRONTEND_URL}?session={session_token}"
        
        return redirect_response(redirect_url, 302)
        
    except Exception as e:
        logger.exception("Error in Spotify callback")
        return redirect_response(
            f"{FRONTEND_URL}?error=callback_failed",
            302
        )


@logger.inject_lambda_context
def refresh_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Refresh Spotify access token
    
    Uses refresh token to get new access token
    """
    try:
        logger.info("Refreshing Spotify access token")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        session_token = body.get('sessionToken')

        if not session_token:
            # Try to get from Authorization header
            headers = event.get('headers', {})

            # Try both cases
            auth_header = headers.get('Authorization') or headers.get('authorization') or ''
            
            if auth_header and auth_header.startswith('Bearer '):
                session_token = auth_header[7:]
        
        if not session_token:
            return error_response("No session token provided", 401)
        
        # Verify JWT and get user ID
        user_id = jwt_service.verify_token(session_token)
        if not user_id:
            return error_response("Invalid session token", 401)
        
        logger.info(f"Refreshing token for user: {user_id}")
        
        # Get refresh token from DynamoDB
        token_data = db_service.get_token(user_id, 'spotify')
        if not token_data:
            return error_response("No Spotify account connected", 404)
        
        encrypted_refresh_token = token_data['refreshToken']
        refresh_token = token_service.decrypt_token(encrypted_refresh_token)
        
        # Request new access token from Spotify
        new_token_data = refresh_access_token(refresh_token)
        
        # Store new access token
        encrypted_new_token = token_service.encrypt_token(new_token_data['access_token'])
        
        db_service.update_access_token(
            user_id=user_id,
            platform='spotify',
            access_token=encrypted_new_token,
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