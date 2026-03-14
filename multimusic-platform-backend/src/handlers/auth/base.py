"""
Base authentication handler with shared OAuth logic
"""
import secrets
import uuid
from typing import Optional
from datetime import datetime, timedelta

import jwt

from aws_lambda_powertools import Logger

from src.handlers.platforms.base import BasePlatformHandler
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
        """Generate a signed CSRF state token."""
        payload = {
            'type': 'oauth_state',
            'provider': self.provider_name,
            'nonce': secrets.token_urlsafe(32),
            'exp': datetime.utcnow() + timedelta(minutes=10),
            'iat': datetime.utcnow()
        }
        return jwt.encode(
            payload,
            self.jwt_service.secret,
            algorithm=self.jwt_service.algorithm
        )

    def verify_state(self, state: str) -> bool:
        """Verify a signed CSRF state token."""
        try:
            payload = jwt.decode(
                state,
                self.jwt_service.secret,
                algorithms=[self.jwt_service.algorithm]
            )
            return (
                payload.get('type') == 'oauth_state'
                and payload.get('provider') == self.provider_name
            )
        except jwt.ExpiredSignatureError:
            logger.warning("OAuth state token expired")
            return False
        except jwt.InvalidTokenError as exc:
            logger.warning(f"Invalid OAuth state token: {str(exc)}")
            return False
        except Exception as exc:
            logger.error(f"Error verifying OAuth state token: {str(exc)}")
            return False
    
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

    def find_or_create_user_with_platform(
        self,
        provider_id: str,
        email: str,
        display_name: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        platform_user_id: str,
        scope: str = '',
        avatar_url: Optional[str] = None
    ) -> str:
        """
        Find or create a user and auto-connect the matching music platform.

        Args:
            provider_id: Provider's unique user ID
            email: User email
            display_name: User's display name
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            expires_in: Token expiration time in seconds
            platform_user_id: Platform's user ID
            scope: Granted OAuth scopes
            avatar_url: Optional avatar URL

        Returns:
            Internal user ID (mmp_xxx)
        """
        user_id = self.find_or_create_user(
            provider_id=provider_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url
        )

        platform_handler = BasePlatformHandler(self.provider_name)
        platform_handler.store_platform_tokens(
            user_id=user_id,
            platform_user_id=platform_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            scope=scope
        )

        logger.info(
            f"User {user_id} created/found with {self.provider_name} platform auto-connected"
        )
        return user_id
    
    def create_session(self, user_id: str) -> str:
        """
        Create JWT session token
        
        Args:
            user_id: Internal user ID
            
        Returns:
            JWT token
        """
        return self.jwt_service.create_token(user_id)
