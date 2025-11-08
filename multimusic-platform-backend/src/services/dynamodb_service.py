"""
DynamoDB service for data operations
Extended to support multi-provider SSO architecture
"""
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger

logger = Logger()


class DynamoDBService:
    """Service for DynamoDB operations"""
    
    def __init__(self):
        dynamodb_endpoint = os.environ.get('DYNAMODB_ENDPOINT')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if dynamodb_endpoint:
            # Local development
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=dynamodb_endpoint,
                region_name=region
            )
        else:
            # Production
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
        
        self.table_name = os.environ.get('DYNAMODB_TABLE', 'multimusic-users')
        self.table = self.dynamodb.Table(self.table_name)
    
    # ========== Generic Operations ==========
    
    def put_item(self, item: Dict[str, Any]) -> None:
        """Put item in DynamoDB"""
        try:
            self.table.put_item(Item=item)
            logger.info(f"Put item: userId={item.get('userId')}, sk={item.get('sk')}")
        except Exception as e:
            logger.error(f"Error putting item: {str(e)}")
            raise
    
    def get_item(self, user_id: str, sk: str) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB"""
        try:
            response = self.table.get_item(
                Key={'userId': user_id, 'sk': sk}
            )
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting item: {str(e)}")
            raise
    
    def delete_item(self, user_id: str, sk: str) -> None:
        """Delete item from DynamoDB"""
        try:
            self.table.delete_item(
                Key={'userId': user_id, 'sk': sk}
            )
            logger.info(f"Deleted item: userId={user_id}, sk={sk}")
        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            raise
    
    def query_by_prefix(self, user_id: str, sk_prefix: str) -> List[Dict[str, Any]]:
        """Query items by SK prefix"""
        try:
            response = self.table.query(
                KeyConditionExpression=Key('userId').eq(user_id) & Key('sk').begins_with(sk_prefix)
            )
            return response.get('Items', [])
        except Exception as e:
            logger.error(f"Error querying by prefix: {str(e)}")
            raise
    
    def update_item(self, user_id: str, sk: str, updates: Dict[str, Any]) -> None:
        """Update item attributes"""
        try:
            # Build update expression
            update_expr = "SET "
            expr_attr_values = {}
            expr_attr_names = {}
            
            for i, (key, value) in enumerate(updates.items()):
                attr_name = f"#attr{i}"
                attr_value = f":val{i}"
                update_expr += f"{attr_name} = {attr_value}, "
                expr_attr_names[attr_name] = key
                expr_attr_values[attr_value] = value
            
            update_expr = update_expr.rstrip(', ')
            
            self.table.update_item(
                Key={'userId': user_id, 'sk': sk},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_attr_names,
                ExpressionAttributeValues=expr_attr_values
            )
            logger.info(f"Updated item: userId={user_id}, sk={sk}")
        except Exception as e:
            logger.error(f"Error updating item: {str(e)}")
            raise
    
    # ========== User Operations ==========
    
    def get_user_by_provider(self, provider: str, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        Find user by auth provider ID
        Uses GSI or scan (implement GSI in production)
        """
        try:
            # For now, scan table (inefficient - use GSI in production)
            response = self.table.scan(
                FilterExpression='sk = :sk AND providerId = :pid',
                ExpressionAttributeValues={
                    ':sk': f'auth#{provider}',
                    ':pid': provider_id
                }
            )
            
            items = response.get('Items', [])
            return items[0] if items else None
            
        except Exception as e:
            logger.error(f"Error finding user by provider: {str(e)}")
            raise
    
    # ========== Legacy Methods (for backward compatibility) ==========
    
    def store_user(self, user_id: str, email: str, display_name: str) -> None:
        """Legacy method - creates basic user profile"""
        timestamp = datetime.utcnow().isoformat()
        
        self.put_item({
            'userId': user_id,
            'sk': 'PROFILE',
            'email': email,
            'displayName': display_name,
            'createdAt': timestamp,
            'updatedAt': timestamp
        })
    
    def store_token(
        self,
        user_id: str,
        platform: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        scope: str = ''
    ) -> None:
        """Legacy method - stores platform tokens"""
        timestamp = datetime.utcnow().isoformat()
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        self.put_item({
            'userId': user_id,
            'sk': f'platform#{platform}',
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'expiresAt': expires_at,
            'expiresIn': expires_in,
            'scope': scope,
            'updatedAt': timestamp
        })
    
    def get_token(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """Legacy method - gets platform tokens"""
        return self.get_item(user_id=user_id, sk=f'platform#{platform}')
    
    def update_access_token(
        self,
        user_id: str,
        platform: str,
        access_token: str,
        expires_in: int
    ) -> None:
        """Legacy method - updates access token"""
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        self.update_item(
            user_id=user_id,
            sk=f'platform#{platform}',
            updates={
                'accessToken': access_token,
                'expiresAt': expires_at,
                'expiresIn': expires_in,
                'updatedAt': datetime.utcnow().isoformat()
            }
        )
