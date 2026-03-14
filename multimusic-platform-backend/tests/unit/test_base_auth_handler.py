"""Unit tests for BaseAuthHandler."""
import importlib
from unittest.mock import MagicMock, patch

import pytest

TEST_ENV = {
    'ENCRYPTION_KEY': 'test-encryption-key-32-bytes-long',
    'JWT_SECRET': 'test-jwt-secret',
    'JWT_ALGORITHM': 'HS256',
    'AWS_ACCESS_KEY_ID': 'test',
    'AWS_SECRET_ACCESS_KEY': 'test',
    'AWS_REGION': 'us-east-1',
    'DYNAMODB_TABLE': 'multimusic-users',
}


@pytest.fixture
def auth_handler(monkeypatch):
    """Create BaseAuthHandler with mocked dependencies."""
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)

    import src.handlers.platforms.base as platform_base_mod
    import src.handlers.auth.base as base_mod

    importlib.reload(platform_base_mod)
    importlib.reload(base_mod)

    handler = base_mod.BaseAuthHandler('spotify')
    handler.db_service = MagicMock()
    handler.jwt_service = MagicMock()
    return handler


def test_find_or_create_user_with_platform_creates_auth_and_platform(auth_handler):
    """find_or_create_user_with_platform writes auth and platform items."""
    auth_handler.db_service.get_user_by_provider.return_value = None
    auth_handler.db_service.put_item = MagicMock()

    with patch('src.handlers.auth.base.BasePlatformHandler') as mock_platform_class:
        mock_platform = MagicMock()
        mock_platform_class.return_value = mock_platform

        user_id = auth_handler.find_or_create_user_with_platform(
            provider_id='spotify123',
            email='user@example.com',
            display_name='Test User',
            access_token='acc_token',
            refresh_token='ref_token',
            expires_in=3600,
            platform_user_id='spotify123',
            scope='streaming user-read-private',
        )

    assert user_id.startswith('mmp_')
    assert auth_handler.db_service.put_item.call_count == 2

    mock_platform_class.assert_called_once_with('spotify')
    mock_platform.store_platform_tokens.assert_called_once_with(
        user_id=user_id,
        platform_user_id='spotify123',
        access_token='acc_token',
        refresh_token='ref_token',
        expires_in=3600,
        scope='streaming user-read-private',
    )


def test_find_or_create_user_with_platform_existing_user_updates_tokens(auth_handler):
    """Existing users keep their identity while Spotify tokens refresh."""
    auth_handler.db_service.get_user_by_provider.return_value = {
        'userId': 'mmp_existing',
        'sk': 'auth#spotify',
    }

    with patch('src.handlers.auth.base.BasePlatformHandler') as mock_platform_class:
        mock_platform = MagicMock()
        mock_platform_class.return_value = mock_platform

        user_id = auth_handler.find_or_create_user_with_platform(
            provider_id='spotify123',
            email='user@example.com',
            display_name='Test User',
            access_token='new_acc',
            refresh_token='new_ref',
            expires_in=3600,
            platform_user_id='spotify123',
        )

    assert user_id == 'mmp_existing'
    auth_handler.db_service.put_item.assert_not_called()
    mock_platform.store_platform_tokens.assert_called_once()
