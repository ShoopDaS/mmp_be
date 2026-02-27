"""
Playlist filter utilities.

Each function accepts a raw API response list and returns a cleaned list.
All filter logic is centralised here — no filtering scattered across handlers.

Note: filter_spotify_playlists is defined here for completeness but is used
browser-side only. The backend does not fetch Spotify playlists.
"""

SPOTIFY_EXCLUDED_NAMES = {
    "Discover Weekly",
    "Release Radar",
    "Daily Mix 1",
    "Daily Mix 2",
    "Daily Mix 3",
    "Daily Mix 4",
    "Daily Mix 5",
    "Daily Mix 6",
}

YOUTUBE_EXCLUDED_PREFIXES = {"LL", "WL", "FL"}

SOUNDCLOUD_EXCLUDED_PATTERNS = ["Station", "Mix for"]


def filter_spotify_playlists(playlists: list) -> list:
    """
    Remove Spotify-owned algorithmic playlists from raw /me/playlists items.

    Excludes entries where owner.id is 'spotify' AND name matches a known
    algorithmic playlist name (Daily Mix 1-6, Discover Weekly, Release Radar).
    User-created playlists and followed playlists from other owners are kept.
    """
    return [
        p for p in playlists
        if not (
            p.get("owner", {}).get("id") == "spotify"
            and p.get("name") in SPOTIFY_EXCLUDED_NAMES
        )
    ]


def filter_youtube_playlists(playlists: list) -> list:
    """
    Remove system playlists from raw YouTube Data API items.

    Excludes playlists whose ID starts with a known system prefix:
      LL — Liked Music
      WL — Watch Later
      FL — Favorites (legacy)
    """
    return [
        p for p in playlists
        if not any(
            p.get("id", "").startswith(prefix)
            for prefix in YOUTUBE_EXCLUDED_PREFIXES
        )
    ]


def filter_soundcloud_playlists(playlists: list) -> list:
    """
    Remove algorithmically generated entries from raw SoundCloud API items.

    Excludes playlists whose title contains 'Station' or 'Mix for', which
    are patterns used by SoundCloud for auto-generated stations and mixes.
    """
    return [
        p for p in playlists
        if not any(
            pattern in p.get("title", "")
            for pattern in SOUNDCLOUD_EXCLUDED_PATTERNS
        )
    ]
