"""
Platform connection handlers package
"""
from src.handlers.platforms.spotify import connect_handler as spotify_connect_handler
from src.handlers.platforms.spotify import callback_handler as spotify_callback_handler
from src.handlers.platforms.spotify import refresh_handler as spotify_refresh_handler

__all__ = [
    'spotify_connect_handler',
    'spotify_callback_handler',
    'spotify_refresh_handler',
]
