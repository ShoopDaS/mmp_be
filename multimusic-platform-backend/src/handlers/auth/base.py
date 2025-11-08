"""
Base authentication handler with shared OAuth logic
"""
import os
import secrets
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
import httpx

from aws_lambda_powertools import Logger

from src.services.dynamodb_service import DynamoDBService
from src.services.jwt_service import JWTService

logger = Logger()

db_service = DynamoDBService()
jwt_service = JWTService()


class BaseAuthHandler:
    """Base class for SSO authentication handlers"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.db_service = db_service
        self.jwt_service = jwt_service
    
    def generate_state(self) -> str:
        """Generate CSRF state token"""
        return secrets.token_urlsafe(32)
    
    def generate_internal_user_id(self) -> str:
        """Generate internal MultiMusic user ID"""
        return f"mmp_{uuid.uuid4().hex}"
    
    def find_or_create_user(
        self, 
        provider_id: str,
        email: str,
        display_name: str,
        avatar_url: Optional[str] = None
    ) -> str:
        """
        Find existing user by provider ID or create new user
        
        Args:
            provider_id: Provider's unique user ID (e.g., Google sub)
            email: User email
            display_name: User's display name
            avatar_url: Optional avatar URL
            
        Returns:
            Internal user ID (mmp_xxx)
        """
        # Check if auth provider link exists
        existing_user = self.db_service.get_user_by_provider(
            provider=self.provider_name,
            provider_id=provider_id
        )
        
        if existing_user:
            logger.info(f"Existing user found: {existing_user['userId']}")
            return existing_user['userId']
        
        # Create new user
        user_id = self.generate_internal_user_id()
        timestamp = datetime.utcnow().isoformat()
        
        logger.info(f"Creating new user: {user_id}")
        
        # Store user profile
        self.db_service.put_item({
            'userId': user_id,
            'sk': 'PROFILE',
            'email': email,
            'displayName': display_name,
            'avatarUrl': avatar_url or '',
            'primaryAuthProvider': self.provider_name,
            'createdAt': timestamp,
            'updatedAt': timestamp
        })
        
        # Store auth provider link
        self.db_service.put_item({
            'userId': user_id,
            'sk': f'auth#{self.provider_name}',
            'providerId': provider_id,
            'email': email,
            'linked': True,
            'linkedAt': timestamp
        })
        
        return user_id
    
    def link_provider_to_user(
        self,
        user_id: str,
        provider_id: str,
        email: str
    ) -> None:
        """
        Link an additional auth provider to existing user
        
        Args:
            user_id: Internal user ID
            provider_id: Provider's unique user ID
            email: User email
        """
        timestamp = datetime.utcnow().isoformat()
        
        self.db_service.put_item({
            'userId': user_id,
            'sk': f'auth#{self.provider_name}',
            'providerId': provider_id,
            'email': email,
            'linked': True,
            'linkedAt': timestamp
        })
        
        logger.info(f"Linked {self.provider_name} to user {user_id}")
    
    def create_session(self, user_id: str) -> str:
        """
        Create JWT session token
        
        Args:
            user_id: Internal user ID
            
        Returns:
            JWT token
        """
        return self.jwt_service.create_token(user_id)
