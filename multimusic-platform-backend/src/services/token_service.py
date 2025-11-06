"""
Token encryption/decryption service
"""
import os
import base64
from cryptography.fernet import Fernet
from aws_lambda_powertools import Logger

logger = Logger()


class TokenService:
    """Service for encrypting and decrypting tokens"""
    
    def __init__(self):
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        # Ensure key is properly formatted
        if len(encryption_key) < 32:
            # Pad key to 32 bytes
            encryption_key = encryption_key.ljust(32, '0')
        
        # Convert to Fernet key format (base64 encoded 32 bytes)
        key_bytes = encryption_key[:32].encode()
        self.fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(self.fernet_key)
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token
        
        Args:
            token: Plain text token
            
        Returns:
            Encrypted token as base64 string
        """
        try:
            encrypted = self.cipher.encrypt(token.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Error encrypting token: {str(e)}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a token
        
        Args:
            encrypted_token: Encrypted token as base64 string
            
        Returns:
            Decrypted plain text token
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_token.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting token: {str(e)}")
            raise