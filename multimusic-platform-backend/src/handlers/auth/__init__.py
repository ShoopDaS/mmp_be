"""
Authentication handlers package
"""
from src.handlers.auth.google import login_handler as google_login_handler
from src.handlers.auth.google import callback_handler as google_callback_handler

__all__ = [
    'google_login_handler',
    'google_callback_handler',
]
