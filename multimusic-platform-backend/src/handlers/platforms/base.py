"""
Base platform handler for music service connections
"""
import os
from typing import Any, Dict, Optional
from datetime import datetime

from aws_lambda_powertools import Logger

from src.services.token_service import TokenService
from src.services.dynamodb_service import DynamoDBService
from src.services.jwt_service import JWTService

logger = Logger()

token_service = TokenService()
db_service = DynamoDBService()
jwt_service = JWTService()


class BasePlatformHandler:
    """Base class for music platform connection handlers"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.token_service = token_service
        self.db_service = db_service
        self.jwt_service = jwt_service
    
    def get_user_from_session(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract and verify user ID from session token
        
        Args:
            event: Lambda event object
            
        Returns:
            Internal user ID if valid, None otherwise
        """
        # Try Authorization header first
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization') or ''
        
        session_token = None
        if auth_header and auth_header.startswith('Bearer '):
            session_token = auth_header[7:]
        
        # Fall back to body
        if not session_token:
            try:
                body = event.get('body', '{}')
                if isinstance(body, str):
                    import json
                    body = json.loads(body)
                session_token = body.get('sessionToken')
            except Exception:
                pass
        
        if not session_token:
            return None
        
        # Verify JWT and get user ID
        user_id = self.jwt_service.verify_token(session_token)
        return user_id
    
    def store_platform_tokens(
        self,
        user_id: str,
        platform_user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        scope: str = ''
    ) -> None:
        """
        Store encrypted platform tokens in DynamoDB
        
        Args:
            user_id: Internal user ID
            platform_user_id: Platform's user ID
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration time in seconds
            scope: OAuth scopes
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Encrypt tokens
        encrypted_access_token = self.token_service.encrypt_token(access_token)
        encrypted_refresh_token = self.token_service.encrypt_token(refresh_token)
        
        # Store in DynamoDB
        self.db_service.put_item({
            'userId': user_id,
            'sk': f'platform#{self.platform_name}',
            'platformUserId': platform_user_id,
            'accessToken': encrypted_access_token,
            'refreshToken': encrypted_refresh_token,
            'expiresAt': timestamp,  # Will be calculated properly
            'expiresIn': expires_in,
            'scope': scope,
            'connectedAt': timestamp
        })
        
        logger.info(f"Stored {self.platform_name} tokens for user {user_id}")
    
    def get_platform_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get platform tokens for user
        
        Args:
            user_id: Internal user ID
            
        Returns:
            Token data if found, None otherwise
        """
        return self.db_service.get_item(
            user_id=user_id,
            sk=f'platform#{self.platform_name}'
        )
    
    def update_access_token(
        self,
        user_id: str,
        access_token: str,
        expires_in: int
    ) -> None:
        """
        Update platform access token
        
        Args:
            user_id: Internal user ID
            access_token: New access token
            expires_in: Token expiration time in seconds
        """
        encrypted_token = self.token_service.encrypt_token(access_token)
        timestamp = datetime.utcnow().isoformat()
        
        self.db_service.update_item(
            user_id=user_id,
            sk=f'platform#{self.platform_name}',
            updates={
                'accessToken': encrypted_token,
                'expiresAt': timestamp,
                'expiresIn': expires_in
            }
        )
