"""Unit tests for Google auth handlers."""
import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


GOOGLE_USER_INFO = {
    'sub': 'google_user_123',
    'email': 'google@example.com',
    'name': 'Google User',
    'picture': 'https://example.com/avatar.jpg',
}

TOKEN_RESPONSE = {
    'access_token': 'acc_123',
}

MOCK_ENV = {
    'ENCRYPTION_KEY': 'test-encryption-key-32-bytes-long',
    'JWT_SECRET': 'test-jwt-secret',
    'JWT_ALGORITHM': 'HS256',
    'AWS_ACCESS_KEY_ID': 'test',
    'AWS_SECRET_ACCESS_KEY': 'test',
    'AWS_REGION': 'us-east-1',
    'DYNAMODB_TABLE': 'multimusic-users',
    'GOOGLE_CLIENT_ID': 'test_google_client_id',
    'GOOGLE_CLIENT_SECRET': 'test_google_client_secret',
    'GOOGLE_REDIRECT_URI': 'http://localhost:8080/auth/google/callback',
    'FRONTEND_URL': 'http://localhost:3000',
}


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    for key, value in MOCK_ENV.items():
        monkeypatch.setenv(key, value)


def load_google_module():
    import src.handlers.platforms.base as platform_base_mod
    import src.handlers.auth.base as auth_base_mod
    import src.handlers.auth.google as google_mod

    importlib.reload(platform_base_mod)
    importlib.reload(auth_base_mod)
    return importlib.reload(google_mod)


def test_login_handler_returns_auth_url():
    """login_handler returns a valid Google authorization URL."""
    google_mod = load_google_module()

    response = google_mod.login_handler({'headers': {}, 'body': '{}'}, MagicMock())

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'authUrl' in body['data']
    assert 'accounts.google.com' in body['data']['authUrl']
    assert 'openid' in body['data']['authUrl']
    assert 'state' in body['data']


def test_callback_handler_creates_user_and_redirects():
    """callback_handler exchanges code, creates a user, and redirects with session token."""
    google_mod = load_google_module()

    event = {
        'queryStringParameters': {'code': 'auth_code_123', 'state': 'csrf_state'},
        'headers': {},
    }

    with patch('src.handlers.auth.google.auth_handler') as mock_auth, \
         patch('src.handlers.auth.google.exchange_code_for_token') as mock_exchange, \
         patch('src.handlers.auth.google.get_google_user_info') as mock_user_info:
        mock_exchange.return_value = TOKEN_RESPONSE
        mock_user_info.return_value = GOOGLE_USER_INFO
        mock_auth.verify_state.return_value = True
        mock_auth.find_or_create_user.return_value = 'mmp_newuser'
        mock_auth.create_session.return_value = 'jwt_token_abc'

        response = google_mod.callback_handler(event, MagicMock())

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?session=jwt_token_abc'
    mock_auth.find_or_create_user.assert_called_once_with(
        provider_id='google_user_123',
        email='google@example.com',
        display_name='Google User',
        avatar_url='https://example.com/avatar.jpg',
    )


def test_callback_handler_redirects_on_oauth_error():
    """callback_handler redirects to the frontend when Google returns an error."""
    google_mod = load_google_module()

    event = {
        'queryStringParameters': {'error': 'access_denied'},
        'headers': {},
    }

    response = google_mod.callback_handler(event, MagicMock())

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?error=access_denied'


def test_callback_handler_redirects_on_invalid_state():
    """callback_handler rejects callbacks with an invalid or missing state token."""
    google_mod = load_google_module()

    with patch('src.handlers.auth.google.auth_handler') as mock_auth:
        mock_auth.verify_state.return_value = False
        response = google_mod.callback_handler(
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


def test_callback_handler_redirects_when_no_code():
    """callback_handler redirects with an explicit no_code error."""
    google_mod = load_google_module()

    with patch('src.handlers.auth.google.auth_handler') as mock_auth:
        mock_auth.verify_state.return_value = True
        response = google_mod.callback_handler(
            {'queryStringParameters': {'state': 'csrf_state'}, 'headers': {}},
            MagicMock(),
        )

    assert response['statusCode'] == 302
    assert response['headers']['Location'] == 'http://localhost:3000?error=no_code'
