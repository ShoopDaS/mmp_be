"""
Unit tests for src/utils/playlist_filters.py
"""
import pytest
from src.utils.playlist_filters import (
    filter_spotify_playlists,
    filter_youtube_playlists,
    filter_soundcloud_playlists,
)


# ========== filter_youtube_playlists ==========

class TestFilterYoutubePlaylists:
    def test_removes_liked_music(self):
        playlists = [{"id": "LLxxxxxxxx", "snippet": {"title": "Liked Music"}}]
        assert filter_youtube_playlists(playlists) == []

    def test_removes_watch_later(self):
        playlists = [{"id": "WLxxxxxxxx", "snippet": {"title": "Watch Later"}}]
        assert filter_youtube_playlists(playlists) == []

    def test_removes_favorites(self):
        playlists = [{"id": "FLxxxxxxxx", "snippet": {"title": "Favorites"}}]
        assert filter_youtube_playlists(playlists) == []

    def test_keeps_user_playlists(self):
        playlist = {"id": "PLabc123", "snippet": {"title": "My Workout Mix"}}
        result = filter_youtube_playlists([playlist])
        assert result == [playlist]

    def test_mixed_list_only_removes_system(self):
        user = {"id": "PLabc123", "snippet": {"title": "Chill Vibes"}}
        liked = {"id": "LLxxxxxxxxx", "snippet": {"title": "Liked Music"}}
        wl = {"id": "WLxxxxxxxxx", "snippet": {"title": "Watch Later"}}
        result = filter_youtube_playlists([user, liked, wl])
        assert result == [user]

    def test_empty_list(self):
        assert filter_youtube_playlists([]) == []

    def test_id_must_start_with_prefix(self):
        # "PLL" starts with "PL", not "LL" — should be kept
        playlist = {"id": "PLLabc123", "snippet": {"title": "A Fine Playlist"}}
        result = filter_youtube_playlists([playlist])
        assert result == [playlist]


# ========== filter_soundcloud_playlists ==========

class TestFilterSoundcloudPlaylists:
    def test_removes_station(self):
        playlists = [{"id": "1", "title": "Rock Station"}]
        assert filter_soundcloud_playlists(playlists) == []

    def test_removes_mix_for(self):
        playlists = [{"id": "2", "title": "Mix for johndoe"}]
        assert filter_soundcloud_playlists(playlists) == []

    def test_keeps_user_playlist(self):
        playlist = {"id": "3", "title": "Late Night Coding"}
        result = filter_soundcloud_playlists([playlist])
        assert result == [playlist]

    def test_mixed_list_only_removes_generated(self):
        user = {"id": "10", "title": "My Favourites"}
        station = {"id": "11", "title": "Indie Station"}
        mix = {"id": "12", "title": "Mix for alice"}
        result = filter_soundcloud_playlists([user, station, mix])
        assert result == [user]

    def test_empty_list(self):
        assert filter_soundcloud_playlists([]) == []

    def test_case_sensitive_pattern_match(self):
        # Patterns are case-sensitive: "station" (lowercase) should be kept
        playlist = {"id": "99", "title": "My station picks"}
        result = filter_soundcloud_playlists([playlist])
        assert result == [playlist]

    def test_missing_title_key_is_kept(self):
        # Items without a title should not be accidentally removed
        playlist = {"id": "50"}
        result = filter_soundcloud_playlists([playlist])
        assert result == [playlist]


# ========== filter_spotify_playlists ==========

class TestFilterSpotifyPlaylists:
    def _spotify_owned(self, name):
        return {"id": "x", "name": name, "owner": {"id": "spotify"}}

    def _user_owned(self, name, owner_id="user123"):
        return {"id": "y", "name": name, "owner": {"id": owner_id}}

    def test_removes_daily_mixes(self):
        for i in range(1, 7):
            playlist = self._spotify_owned(f"Daily Mix {i}")
            assert filter_spotify_playlists([playlist]) == []

    def test_removes_discover_weekly(self):
        playlist = self._spotify_owned("Discover Weekly")
        assert filter_spotify_playlists([playlist]) == []

    def test_removes_release_radar(self):
        playlist = self._spotify_owned("Release Radar")
        assert filter_spotify_playlists([playlist]) == []

    def test_keeps_user_created_playlist(self):
        playlist = self._user_owned("Road Trip 2024")
        result = filter_spotify_playlists([playlist])
        assert result == [playlist]

    def test_keeps_followed_non_spotify_playlist(self):
        # Owned by another user (not Spotify), even if name matches excluded set
        playlist = self._user_owned("Daily Mix 1", owner_id="somebandofficial")
        result = filter_spotify_playlists([playlist])
        assert result == [playlist]

    def test_keeps_spotify_owned_non_excluded_name(self):
        # Spotify owns it but name is not in the excluded set
        playlist = self._spotify_owned("Top Tracks of 2024")
        result = filter_spotify_playlists([playlist])
        assert result == [playlist]

    def test_mixed_list(self):
        user = self._user_owned("My Workout")
        daily = self._spotify_owned("Daily Mix 3")
        radar = self._spotify_owned("Release Radar")
        result = filter_spotify_playlists([user, daily, radar])
        assert result == [user]

    def test_empty_list(self):
        assert filter_spotify_playlists([]) == []

    def test_missing_owner_key_is_kept(self):
        playlist = {"id": "z", "name": "Daily Mix 1"}
        result = filter_spotify_playlists([playlist])
        assert result == [playlist]
