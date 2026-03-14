"""
Spotify OAuth Lambda Handlers
"""
import os
from typing import Any, Dict
from urllib.parse import urlencode

import httpx

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.handlers.auth.base import BaseAuthHandler
from src.handlers.platforms.spotify import get_spotify_user_info
from src.utils.responses import error_response, redirect_response, success_response

logger = Logger()

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
SPOTIFY_AUTH_REDIRECT_URI = os.environ.get('SPOTIFY_AUTH_REDIRECT_URI')
FRONTEND_URL = os.environ.get('FRONTEND_URL')

AUTH_SCOPES = ' '.join([
    'user-read-private',
    'user-read-email',
    'streaming',
    'user-modify-playback-state',
    'user-read-playback-state',
    'user-library-read',
    'user-library-modify',
    'playlist-read-private',
    'playlist-modify-private',
    'playlist-modify-public',
])

auth_handler = BaseAuthHandler('spotify')


@logger.inject_lambda_context
def login_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Initiate Spotify OAuth login.
    Returns authorization URL to redirect user to Spotify.
    """
    try:
        logger.info("Initiating Spotify OAuth login")

        state = auth_handler.generate_state()
        auth_params = {
            'client_id': SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': SPOTIFY_AUTH_REDIRECT_URI,
            'state': state,
            'scope': AUTH_SCOPES,
        }
        auth_url = f"https://accounts.spotify.com/authorize?{urlencode(auth_params)}"

        return success_response({'authUrl': auth_url, 'state': state})
    except Exception as exc:
        logger.exception("Error in Spotify login")
        return error_response(str(exc), 500)


@logger.inject_lambda_context
def callback_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Handle Spotify OAuth callback.
    Creates or finds the user, stores Spotify tokens, and returns a session JWT.
    """
    try:
        logger.info("Processing Spotify OAuth callback")

        query_params = event.get('queryStringParameters') or {}
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')

        if error:
            logger.error(f"OAuth error from Spotify: {error}")
            return redirect_response(f"{FRONTEND_URL}?error={error}", 302)

        if not state or not auth_handler.verify_state(state):
            logger.error("Invalid or missing OAuth state")
            return redirect_response(f"{FRONTEND_URL}?error=invalid_state", 302)

        if not code:
            logger.error("No authorization code in callback")
            return redirect_response(f"{FRONTEND_URL}?error=no_code", 302)

        token_data = _exchange_code_for_token(code)
        required_fields = ('access_token', 'refresh_token', 'expires_in')
        missing_fields = [field for field in required_fields if field not in token_data]
        if missing_fields:
            raise ValueError(
                f"Missing required Spotify token fields: {', '.join(missing_fields)}"
            )

        user_info = get_spotify_user_info(token_data['access_token'])
        spotify_user_id = user_info['id']
        email = user_info.get('email', '')
        display_name = user_info.get('display_name') or (
            email.split('@')[0] if email else spotify_user_id
        )
        images = user_info.get('images', [])
        avatar_url = images[0]['url'] if images else ''

        logger.info(f"Spotify user authenticated: {spotify_user_id}")

        user_id = auth_handler.find_or_create_user_with_platform(
            provider_id=spotify_user_id,
            email=email,
            display_name=display_name,
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            expires_in=token_data['expires_in'],
            platform_user_id=spotify_user_id,
            scope=token_data.get('scope', ''),
            avatar_url=avatar_url,
        )
        session_token = auth_handler.create_session(user_id)

        return redirect_response(f"{FRONTEND_URL}?session={session_token}", 302)
    except Exception:
        logger.exception("Error in Spotify callback")
        return redirect_response(f"{FRONTEND_URL}?error=callback_failed", 302)


def _exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    with httpx.Client() as client:
        response = client.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': SPOTIFY_AUTH_REDIRECT_URI,
                'client_id': SPOTIFY_CLIENT_ID,
                'client_secret': SPOTIFY_CLIENT_SECRET,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        response.raise_for_status()
        return response.json()
