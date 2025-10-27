"""
Unit tests for TokenService
"""
import os
import pytest
from src.services.token_service import TokenService


@pytest.fixture
def token_service():
    """Fixture to create TokenService instance"""
    os.environ['ENCRYPTION_KEY'] = 'test-encryption-key-32-bytes-long'
    return TokenService()


def test_encrypt_decrypt_token(token_service):
    """Test token encryption and decryption"""
    original_token = "test-access-token-12345"
    
    # Encrypt
    encrypted = token_service.encrypt_token(original_token)
    assert encrypted != original_token
    assert isinstance(encrypted, str)
    
    # Decrypt
    decrypted = token_service.decrypt_token(encrypted)
    assert decrypted == original_token


def test_encrypt_different_tokens_produce_different_results(token_service):
    """Test that different tokens produce different encrypted values"""
    token1 = "token-one"
    token2 = "token-two"
    
    encrypted1 = token_service.encrypt_token(token1)
    encrypted2 = token_service.encrypt_token(token2)
    
    assert encrypted1 != encrypted2


def test_decrypt_invalid_token_raises_error(token_service):
    """Test that decrypting invalid token raises error"""
    with pytest.raises(Exception):
        token_service.decrypt_token("invalid-encrypted-token")


def test_token_service_requires_encryption_key():
    """Test that TokenService requires ENCRYPTION_KEY"""
    if 'ENCRYPTION_KEY' in os.environ:
        del os.environ['ENCRYPTION_KEY']
    
    with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
        TokenService()