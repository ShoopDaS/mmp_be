"""
Platform connection handlers package
"""
from src.handlers.platforms.spotify import connect_handler as spotify_connect_handler
from src.handlers.platforms.spotify import callback_handler as spotify_callback_handler
from src.handlers.platforms.spotify import refresh_handler as spotify_refresh_handler

from src.handlers.platforms.youtube import connect_handler as youtube_connect_handler
from src.handlers.platforms.youtube import callback_handler as youtube_callback_handler
from src.handlers.platforms.youtube import refresh_handler as youtube_refresh_handler

from src.handlers.platforms.soundcloud import connect_handler as soundcloud_connect_handler
from src.handlers.platforms.soundcloud import callback_handler as soundcloud_callback_handler
from src.handlers.platforms.soundcloud import refresh_handler as soundcloud_refresh_handler

__all__ = [
    'spotify_connect_handler',
    'spotify_callback_handler',
    'spotify_refresh_handler',
    'youtube_connect_handler',
    'youtube_callback_handler',
    'youtube_refresh_handler',
    'soundcloud_connect_handler',
    'soundcloud_callback_handler',
    'soundcloud_refresh_handler',
]