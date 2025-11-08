"""
Response utility functions for Lambda handlers
"""
import json
from typing import Any, Dict


def success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """
    Create a successful Lambda response
    
    Args:
        data: Response data
        status_code: HTTP status code (default 200)
        
    Returns:
        Lambda response dict
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps({'data': data})
    }


def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """
    Create an error Lambda response
    
    Args:
        message: Error message
        status_code: HTTP status code (default 400)
        
    Returns:
        Lambda response dict
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps({'error': message})
    }


def redirect_response(location: str, status_code: int = 302) -> Dict[str, Any]:
    """
    Create a redirect Lambda response
    
    Args:
        location: Redirect URL
        status_code: HTTP status code (default 302)
        
    Returns:
        Lambda response dict
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Location': location,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': ''
    }