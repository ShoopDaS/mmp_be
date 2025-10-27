"""
DynamoDB service for data persistence
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

logger = Logger()


class DynamoDBService:
    """Service for DynamoDB operations"""
    
    def __init__(self):
        # Check if we're using DynamoDB Local
        dynamodb_endpoint = os.environ.get('DYNAMODB_ENDPOINT')
        
        if dynamodb_endpoint:
            # Local development
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=dynamodb_endpoint,
                region_name='us-east-1',
                aws_access_key_id='local',
                aws_secret_access_key='local'
            )
        else:
            # Production
            self.dynamodb = boto3.resource('dynamodb')
        
        self.users_table_name = os.environ.get('DYNAMODB_TABLE_USERS', 'multimusic-users')
        self.tokens_table_name = os.environ.get('DYNAMODB_TABLE_TOKENS', 'multimusic-tokens')
        
        self.users_table = self.dynamodb.Table(self.users_table_name)
        self.tokens_table = self.dynamodb.Table(self.tokens_table_name)
    
    def store_user(self, user_id: str, email: str, display_name: str = '') -> None:
        """
        Store user profile
        
        Args:
            user_id: Unique user identifier
            email: User email
            display_name: User display name
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            
            self.users_table.put_item(
                Item={
                    'userId': user_id,
                    'sk': 'PROFILE',
                    'email': email,
                    'displayName': display_name,
                    'createdAt': timestamp,
                    'updatedAt': timestamp
                }
            )
            
            logger.info(f"Stored user profile: {user_id}")
            
        except ClientError as e:
            logger.error(f"Error storing user: {str(e)}")
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile
        
        Args:
            user_id: User identifier
            
        Returns:
            User data or None if not found
        """
        try:
            response = self.users_table.get_item(
                Key={
                    'userId': user_id,
                    'sk': 'PROFILE'
                }
            )
            
            return response.get('Item')
            
        except ClientError as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def store_token(
        self,
        user_id: str,
        platform: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        scope: str = ''
    ) -> None:
        """
        Store OAuth tokens
        
        Args:
            user_id: User identifier
            platform: Platform name (spotify, soundcloud, etc.)
            access_token: Encrypted access token
            refresh_token: Encrypted refresh token
            expires_in: Token expiration time in seconds
            scope: OAuth scope
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            expires_at = timestamp + expires_in
            ttl = timestamp + (30 * 24 * 60 * 60)  # 30 days TTL
            
            self.tokens_table.put_item(
                Item={
                    'userId': user_id,
                    'sk': f'platform#{platform}',
                    'platform': platform,
                    'accessToken': access_token,
                    'refreshToken': refresh_token,
                    'expiresAt': expires_at,
                    'scope': scope,
                    'createdAt': timestamp,
                    'updatedAt': timestamp,
                    'ttl': ttl
                }
            )
            
            logger.info(f"Stored tokens for user {user_id} on {platform}")
            
        except ClientError as e:
            logger.error(f"Error storing tokens: {str(e)}")
            raise
    
    def get_token(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get OAuth tokens for a platform
        
        Args:
            user_id: User identifier
            platform: Platform name
            
        Returns:
            Token data or None if not found
        """
        try:
            response = self.tokens_table.get_item(
                Key={
                    'userId': user_id,
                    'sk': f'platform#{platform}'
                }
            )
            
            return response.get('Item')
            
        except ClientError as e:
            logger.error(f"Error getting tokens: {str(e)}")
            return None
    
    def update_access_token(
        self,
        user_id: str,
        platform: str,
        access_token: str,
        expires_in: int
    ) -> None:
        """
        Update access token after refresh
        
        Args:
            user_id: User identifier
            platform: Platform name
            access_token: New encrypted access token
            expires_in: Token expiration time in seconds
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            expires_at = timestamp + expires_in
            
            self.tokens_table.update_item(
                Key={
                    'userId': user_id,
                    'sk': f'platform#{platform}'
                },
                UpdateExpression='SET accessToken = :token, expiresAt = :exp, updatedAt = :updated',
                ExpressionAttributeValues={
                    ':token': access_token,
                    ':exp': expires_at,
                    ':updated': timestamp
                }
            )
            
            logger.info(f"Updated access token for user {user_id} on {platform}")
            
        except ClientError as e:
            logger.error(f"Error updating access token: {str(e)}")
            raise
    
    def delete_token(self, user_id: str, platform: str) -> None:
        """
        Delete OAuth tokens for a platform
        
        Args:
            user_id: User identifier
            platform: Platform name
        """
        try:
            self.tokens_table.delete_item(
                Key={
                    'userId': user_id,
                    'sk': f'platform#{platform}'
                }
            )
            
            logger.info(f"Deleted tokens for user {user_id} on {platform}")
            
        except ClientError as e:
            logger.error(f"Error deleting tokens: {str(e)}")
            raise