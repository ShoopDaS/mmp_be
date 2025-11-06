"""
JWT token service for session management
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import jwt
from aws_lambda_powertools import Logger

logger = Logger()


class JWTService:
    """Service for creating and verifying JWT tokens"""
    
    def __init__(self):
        self.secret = os.environ.get('JWT_SECRET')
        if not self.secret:
            raise ValueError("JWT_SECRET environment variable not set")
        
        self.algorithm = os.environ.get('JWT_ALGORITHM', 'HS256')
        self.expiration_days = int(os.environ.get('JWT_EXPIRATION_DAYS', 7))
    
    def create_token(self, user_id: str) -> str:
        """
        Create a JWT token for a user
        
        Args:
            user_id: User ID to encode in token
            
        Returns:
            JWT token string
        """
        try:
            payload = {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(days=self.expiration_days),
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
            return token
            
        except Exception as e:
            logger.error(f"Error creating JWT token: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify a JWT token and return user ID
        
        Args:
            token: JWT token string
            
        Returns:
            User ID if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload.get('user_id')
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying JWT token: {str(e)}")
            return None