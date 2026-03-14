"""Unit tests for Spotify auth handlers."""
import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


SPOTIFY_USER_INFO = {
    'id': 'spotify_user_abc',
    'email': 'spotify@example.com',
    'display_name': 'Spotify User',
    'images': [{'url': 'https://example.com/avatar.jpg'}],
}

TOKEN_RESPONSE = {
    'access_token': 'acc_123',
    'refresh_token': 'ref_456',
    'expires_in': 3600,
    'scope': 'streaming user-read-private',
}

MOCK_ENV = {
    'ENCRYPTION_KEY': 'test-encryption-key-32-bytes-long',
    'JWT_SECRET': 'test-jwt-secret',
    'JWT_ALGORITHM': 'HS256',
    'AWS_ACCESS_KEY_ID': 'test',
    'AWS_SECRET_ACCESS_KEY': 'test',
    'AWS_REGION': 'us-east-1',
    'DYNAMODB_TABLE': 'multimusic-users',
    'SPOTIFY_CLIENT_ID': 'test_client_id',
    'SPOTIFY_CLIENT_SECRET': 'test_client_secret',
    'SPOTIFY_AUTH_REDIRECT_URI': 'http://localhost:8080/auth/spotify/callback',
    'FRONTEND_URL': 'http://localhost:3000',
}


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    for key, value in MOCK_ENV.items():
        monkeypatch.setenv(key, value)


def load_spotify_module():
    import src.handlers.platforms.base as platform_base_mod
    import src.handlers.auth.base as auth_base_mod
    import src.handlers.platforms.spotify as spotify_platform_mod
    import src.handlers.auth.spotify as spotify_mod

    importlib.reload(platform_base_mod)
    importlib.reload(auth_base_mod)
    importlib.reload(spotify_platform_mod)
    return importlib.reload(spotify_mod)


def test_login_handler_returns_auth_url():
    """login_handler returns a valid Spotify authorization URL."""
    spotify_mod = load_spotify_module()

    response = spotify_mod.login_handler({'headers': {}, 'body': '{}'}, MagicMock())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'authUrl' in body['data']
    assert 'accounts.spotify.com/authorize' in body['data']['authUrl']
    assert 'streaming' in body['data']['authUrl']
    assert 'state' in body['data']


def test_callback_handler_creates_user_and_redirects():
    """callback_handler exchanges code, creates a user, and redirects."""
    spotify_mod = load_spotify_module()

    event = {
        'queryStringParameters': {'code': 'auth_code_123', 'state': 'csrf_state'},
        'headers': {},
    }
    mock_response = MagicMock()
    mock_response.json.return_value = TOKEN_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch('src.handlers.auth.spotify.auth_handler') as mock_auth, \
         patch('src.handlers.auth.spotify.get_spotify_user_info') as mock_user_info, \
         patch('src.handlers.auth.spotify.httpx.Client') as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = mock_client_instance
        mock_client_instance.post.return_value = mock_response

        mock_user_info.return_value = SPOTIFY_USER_INFO
        mock_auth.verify_state.return_value = True
        mock_auth.find_or_create_user_with_platform.return_value = 'mmp_newuser'
        mock_auth.create_session.return_value = 'jwt_token_abc'

        response = spotify_mod.callback_handler(event, MagicMock())

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?session=jwt_token_abc'


def test_callback_handler_redirects_on_oauth_error():
    """callback_handler redirects to the frontend when Spotify returns an error."""
    spotify_mod = load_spotify_module()

    event = {
        'queryStringParameters': {'error': 'access_denied'},
        'headers': {},
    }

    response = spotify_mod.callback_handler(event, MagicMock())

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?error=access_denied'


def test_callback_handler_redirects_when_no_code():
    """callback_handler redirects with an explicit no_code error."""
    spotify_mod = load_spotify_module()

    with patch('src.handlers.auth.spotify.auth_handler') as mock_auth:
        mock_auth.verify_state.return_value = True
        response = spotify_mod.callback_handler(
            {'queryStringParameters': {'state': 'csrf_state'}, 'headers': {}},
            MagicMock(),
        )

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?error=no_code'


def test_callback_handler_redirects_on_invalid_state():
    """callback_handler rejects callbacks with an invalid or missing state token."""
    spotify_mod = load_spotify_module()

    with patch('src.handlers.auth.spotify.auth_handler') as mock_auth:
        mock_auth.verify_state.return_value = False
        response = spotify_mod.callback_handler(
            {
                'queryStringParameters': {
                    'code': 'auth_code_123',
                    'state': 'invalid_state',
                },
                'headers': {},
            },
            MagicMock(),
        )

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?error=invalid_state'
