"""
API response utilities
"""
import json
from typing import Any, Dict, Optional


def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """
    Create a successful API Gateway response
    
    Args:
        data: Response data
        status_code: HTTP status code
        
    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(data)
    }


def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """
    Create an error API Gateway response
    
    Args:
        message: Error message
        status_code: HTTP status code
        
    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps({
            'error': message
        })
    }


def redirect_response(location: str, status_code: int = 302) -> Dict[str, Any]:
    """
    Create a redirect response
    
    Args:
        location: Redirect URL
        status_code: HTTP status code (301 or 302)
        
    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Location': location,
            'Access-Control-Allow-Origin': '*'
        },
        'body': ''
    }