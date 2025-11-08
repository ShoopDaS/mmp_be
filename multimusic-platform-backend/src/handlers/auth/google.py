"""
Google OAuth Lambda Handlers
"""
import json
import os
from typing import Any, Dict
from urllib.parse import urlencode
import httpx

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.handlers.auth.base import BaseAuthHandler
from src.utils.responses import success_response, error_response, redirect_response

logger = Logger()

# Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Handler instance
auth_handler = BaseAuthHandler('google')


@logger.inject_lambda_context
def login_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate Google OAuth login
    
    Returns authorization URL to redirect user to Google
    """
    try:
        logger.info("Initiating Google OAuth login")
        
        # Generate state for CSRF protection
        state = auth_handler.generate_state()
        
        # Build Google authorization URL
        auth_params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent'  # Force consent screen to get refresh token
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
        
        return success_response({
            'authUrl': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.exception("Error in Google login")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle Google OAuth callback
    
    Exchange authorization code for access token and create/login user
    """
    try:
        logger.info("Processing Google OAuth callback")
        
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
        
        # Get user info from Google
        user_info = get_google_user_info(token_data['access_token'])
        
        google_user_id = user_info['sub']  # Google's unique user ID
        email = user_info.get('email', '')
        display_name = user_info.get('name', email.split('@')[0])
        avatar_url = user_info.get('picture', '')
        
        logger.info(f"Google user authenticated: {google_user_id}")
        
        # Find or create internal user
        internal_user_id = auth_handler.find_or_create_user(
            provider_id=google_user_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url
        )
        
        # Generate JWT session token
        session_token = auth_handler.create_session(internal_user_id)
        
        # Redirect to frontend with session token
        redirect_url = f"{FRONTEND_URL}?session={session_token}"
        
        return redirect_response(redirect_url, 302)
        
    except Exception as e:
        logger.exception("Error in Google callback")
        return redirect_response(
            f"{FRONTEND_URL}?error=callback_failed",
            302
        )


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access token"""
    with httpx.Client() as client:
        response = client.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'redirect_uri': GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        response.raise_for_status()
        return response.json()


def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """Get user information from Google"""
    with httpx.Client() as client:
        response = client.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        response.raise_for_status()
        return response.json()
