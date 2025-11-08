"""
User Management Lambda Handlers
"""
import json
from typing import Any, Dict
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from src.services.dynamodb_service import DynamoDBService
from src.services.jwt_service import JWTService
from src.utils.responses import success_response, error_response

logger = Logger()

db_service = DynamoDBService()
jwt_service = JWTService()


def get_user_from_session(event: Dict[str, Any]) -> str:
    """Extract and verify user ID from session token"""
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization') or headers.get('authorization') or ''
    
    if not auth_header or not auth_header.startswith('Bearer '):
        raise ValueError("No valid authorization header")
    
    session_token = auth_header[7:]
    user_id = jwt_service.verify_token(session_token)
    
    if not user_id:
        raise ValueError("Invalid session token")
    
    return user_id


@logger.inject_lambda_context
def profile_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Get user profile information
    
    GET /user/profile
    Requires: Authorization header with Bearer token
    """
    try:
        user_id = get_user_from_session(event)
        logger.info(f"Getting profile for user: {user_id}")
        
        # Get user profile
        profile = db_service.get_item(user_id=user_id, sk='PROFILE')
        
        if not profile:
            return error_response("User not found", 404)
        
        # Remove internal fields
        profile.pop('sk', None)
        
        return success_response(profile)
        
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.exception("Error getting user profile")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def auth_providers_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Get list of linked SSO auth providers
    
    GET /user/auth-providers
    Requires: Authorization header with Bearer token
    """
    try:
        user_id = get_user_from_session(event)
        logger.info(f"Getting auth providers for user: {user_id}")
        
        # Query all auth# items
        providers = db_service.query_by_prefix(user_id=user_id, sk_prefix='auth#')
        
        # Format response
        provider_list = []
        for item in providers:
            provider_name = item['sk'].replace('auth#', '')
            provider_list.append({
                'provider': provider_name,
                'email': item.get('email', ''),
                'linked': item.get('linked', False),
                'linkedAt': item.get('linkedAt', '')
            })
        
        return success_response({
            'providers': provider_list
        })
        
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.exception("Error getting auth providers")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def platforms_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Get list of connected music platforms
    
    GET /user/platforms
    Requires: Authorization header with Bearer token
    """
    try:
        user_id = get_user_from_session(event)
        logger.info(f"Getting platforms for user: {user_id}")
        
        # Query all platform# items
        platforms = db_service.query_by_prefix(user_id=user_id, sk_prefix='platform#')
        
        # Format response (don't expose tokens)
        platform_list = []
        for item in platforms:
            platform_name = item['sk'].replace('platform#', '')
            platform_list.append({
                'platform': platform_name,
                'platformUserId': item.get('platformUserId', ''),
                'connected': True,
                'connectedAt': item.get('connectedAt', ''),
                'scope': item.get('scope', '')
            })
        
        return success_response({
            'platforms': platform_list
        })
        
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.exception("Error getting platforms")
        return error_response(str(e), 500)


@logger.inject_lambda_context
def delete_platform_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Disconnect a music platform
    
    DELETE /user/platforms/{platform}
    Requires: Authorization header with Bearer token
    """
    try:
        user_id = get_user_from_session(event)
        
        # Get platform from path
        path_params = event.get('pathParameters', {})
        platform = path_params.get('platform')
        
        if not platform:
            return error_response("Platform name required", 400)
        
        logger.info(f"Disconnecting {platform} for user: {user_id}")
        
        # Delete platform connection
        db_service.delete_item(user_id=user_id, sk=f'platform#{platform}')
        
        return success_response({
            'message': f'{platform} disconnected successfully'
        })
        
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.exception("Error deleting platform")
        return error_response(str(e), 500)
