"""Tests for YouTube API interactions (YouTube Data API v3)."""

import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from playlist_downloader import PlaylistDownloader


# ──────────────────────────────────────────────
# _resolve_channel_id
# ──────────────────────────────────────────────

class TestResolveChannelId:
    def test_handle_format(self, downloader, mock_youtube_api):
        """Test resolving @username format."""
        mock_youtube_api.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'UCresolved123'}]
        }
        result = downloader._resolve_channel_id('@someuser')
        assert result == 'UCresolved123'

    def test_url_with_handle(self, downloader, mock_youtube_api):
        """Test resolving https://youtube.com/@username format."""
        mock_youtube_api.channels.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'UCfromurl456'}]
        }
        result = downloader._resolve_channel_id('https://www.youtube.com/@someuser')
        assert result == 'UCfromurl456'

    def test_raw_channel_id(self, downloader):
        """Test raw channel ID is returned as-is."""
        result = downloader._resolve_channel_id('UCrawid789')
        assert result == 'UCrawid789'

    def test_channel_url(self, downloader):
        """Test channel URL format."""
        result = downloader._resolve_channel_id('https://www.youtube.com/channel/UCchannel999')
        assert result == 'UCchannel999'

    def test_missing_channel_raises(self, downloader, mock_youtube_api):
        """Test that missing channel raises ValueError."""
        mock_youtube_api.channels.return_value.list.return_value.execute.return_value = {
            'items': []
        }
        with pytest.raises(ValueError, match="Could not resolve handle"):
            downloader._resolve_channel_id('@nonexistent')

    def test_unparseable_url_raises(self, downloader):
        """Test that unparseable URL raises ValueError."""
        with pytest.raises(ValueError, match="Could not parse channel URL"):
            downloader._resolve_channel_id('not-a-valid-input')


# ──────────────────────────────────────────────
# get_all_playlists
# ──────────────────────────────────────────────

class TestGetAllPlaylists:
    def test_single_page(self, downloader):
        """Test fetching playlists from a single page."""
        downloader.youtube.playlists.return_value.list.return_value.execute.return_value = {
            'items': [
                {'id': 'PL1', 'snippet': {'title': 'Playlist 1'}},
                {'id': 'PL2', 'snippet': {'title': 'Playlist 2'}},
            ],
        }
        result = downloader.get_all_playlists()
        assert len(result) == 2
        assert result[0]['id'] == 'PL1'
        assert result[0]['title'] == 'Playlist 1'
        assert result[0]['url'] == 'https://www.youtube.com/playlist?list=PL1'
        assert result[1]['id'] == 'PL2'

    def test_pagination(self, downloader):
        """Test pagination with nextPageToken."""
        downloader.youtube.playlists.return_value.list.return_value.execute.side_effect = [
            {
                'items': [{'id': 'PL1', 'snippet': {'title': 'Page 1'}}],
                'nextPageToken': 'token123',
            },
            {
                'items': [{'id': 'PL2', 'snippet': {'title': 'Page 2'}}],
            },
        ]
        result = downloader.get_all_playlists()
        assert len(result) == 2
        assert result[0]['title'] == 'Page 1'
        assert result[1]['title'] == 'Page 2'

    def test_empty_channel(self, downloader):
        """Test channel with no playlists."""
        downloader.youtube.playlists.return_value.list.return_value.execute.return_value = {
            'items': [],
        }
        result = downloader.get_all_playlists()
        assert result == []

    def test_api_error_returns_empty(self, downloader):
        """Test that API errors return empty list."""
        downloader.youtube.playlists.return_value.list.return_value.execute.side_effect = Exception("API error")
        result = downloader.get_all_playlists()
        assert result == []

    def test_no_items_key(self, downloader):
        """Test response without items key."""
        downloader.youtube.playlists.return_value.list.return_value.execute.return_value = {}
        result = downloader.get_all_playlists()
        assert result == []

    def test_url_format(self, downloader):
        """Test that URLs are correctly constructed."""
        downloader.youtube.playlists.return_value.list.return_value.execute.return_value = {
            'items': [{'id': 'PLxyz', 'snippet': {'title': 'T'}}],
        }
        result = downloader.get_all_playlists()
        assert result[0]['url'] == 'https://www.youtube.com/playlist?list=PLxyz'


# ──────────────────────────────────────────────
# get_playlist_videos
# ──────────────────────────────────────────────

class TestGetPlaylistVideos:
    def test_returns_videos_with_positions(self, downloader):
        """Test basic video extraction with positions."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [
                {
                    'snippet': {
                        'resourceId': {'videoId': 'V1'},
                        'title': 'Video 1',
                        'position': 0,
                    },
                    'status': {'privacyStatus': 'public'},
                    'contentDetails': {},
                },
                {
                    'snippet': {
                        'resourceId': {'videoId': 'V2'},
                        'title': 'Video 2',
                        'position': 1,
                    },
                    'status': {'privacyStatus': 'public'},
                    'contentDetails': {},
                },
            ],
        }
        result = downloader.get_playlist_videos('PLtest')
        assert len(result) == 2
        assert result[0]['id'] == 'V1'
        assert result[0]['title'] == 'Video 1'
        assert result[0]['playlist_index'] == 0
        assert result[0]['unavailable'] is False
        assert result[1]['playlist_index'] == 1

    def test_pagination(self, downloader):
        """Test pagination of playlist items."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.side_effect = [
            {
                'items': [{
                    'snippet': {'resourceId': {'videoId': 'V1'}, 'title': 'V1', 'position': 0},
                    'status': {}, 'contentDetails': {},
                }],
                'nextPageToken': 'page2',
            },
            {
                'items': [{
                    'snippet': {'resourceId': {'videoId': 'V2'}, 'title': 'V2', 'position': 1},
                    'status': {}, 'contentDetails': {},
                }],
            },
        ]
        result = downloader.get_playlist_videos('PLtest')
        assert len(result) == 2

    def test_detects_private_video(self, downloader):
        """Test that private videos are flagged as unavailable."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [{
                'snippet': {'resourceId': {'videoId': 'V1'}, 'title': 'Private video', 'position': 0},
                'status': {'privacyStatus': 'private'}, 'contentDetails': {},
            }],
        }
        result = downloader.get_playlist_videos('PLtest')
        assert result[0]['unavailable'] is True

    def test_detects_deleted_video(self, downloader):
        """Test that deleted videos are flagged as unavailable."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [{
                'snippet': {'resourceId': {'videoId': 'V1'}, 'title': 'Deleted video', 'position': 0},
                'status': {}, 'contentDetails': {},
            }],
        }
        result = downloader.get_playlist_videos('PLtest')
        assert result[0]['unavailable'] is True

    def test_empty_playlist(self, downloader):
        """Test empty playlist returns empty list."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [],
        }
        result = downloader.get_playlist_videos('PLtest')
        assert result == []

    def test_api_error_returns_empty(self, downloader):
        """Test that API errors return empty list."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.side_effect = Exception("API error")
        result = downloader.get_playlist_videos('PLtest')
        assert result == []

    def test_url_format(self, downloader):
        """Test that video URLs are correctly constructed."""
        downloader.youtube.playlistItems.return_value.list.return_value.execute.return_value = {
            'items': [{
                'snippet': {'resourceId': {'videoId': 'abc123'}, 'title': 'T', 'position': 0},
                'status': {}, 'contentDetails': {},
            }],
        }
        result = downloader.get_playlist_videos('PLtest')
        assert result[0]['url'] == 'https://www.youtube.com/watch?v=abc123'


# ──────────────────────────────────────────────
# download_video
# ──────────────────────────────────────────────

class TestDownloadVideo:
    @patch("playlist_downloader.os.path.exists")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_success_returns_filename(self, mock_ydl_cls, mock_exists, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "V1", "title": "Test"}
        mock_ydl.prepare_filename.return_value = "/tmp/001 - Test.mp4"
        mock_exists.return_value = True

        result = downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        assert result == "/tmp/001 - Test.mp4"

    @patch("playlist_downloader.time.sleep")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_retries_on_failure(self, mock_ydl_cls, mock_sleep, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("fail")

        result = downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        assert result is None
        assert mock_ydl.extract_info.call_count == 3

    @patch("playlist_downloader.time.sleep")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_returns_none_after_max_retries(self, mock_ydl_cls, mock_sleep, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("fail")

        result = downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        assert result is None

    @patch("playlist_downloader.time.sleep")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_exponential_backoff(self, mock_ydl_cls, mock_sleep, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("fail")

        downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        # Attempts 1,2,3; sleeps after attempts 1 and 2
        assert mock_sleep.call_args_list == [call(2), call(4)]

    @patch("playlist_downloader.os.path.exists")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_alternate_extension_fallback(self, mock_ydl_cls, mock_exists, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "V1", "title": "Test"}
        mock_ydl.prepare_filename.return_value = "/tmp/001 - Test.mp4"

        # Primary filename doesn't exist, but .webm does
        def exists_side_effect(path):
            return path == "/tmp/001 - Test.webm"

        mock_exists.side_effect = exists_side_effect

        result = downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        assert result == "/tmp/001 - Test.webm"

    @patch("playlist_downloader.os.path.exists")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_none_info_handling(self, mock_ydl_cls, mock_exists, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = None

        result = downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        # Returns None because info is None on all 3 attempts
        assert result is None

    @patch("playlist_downloader.os.path.exists")
    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_no_file_found_returns_none(self, mock_ydl_cls, mock_exists, downloader):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {"id": "V1", "title": "Test"}
        mock_ydl.prepare_filename.return_value = "/tmp/001 - Test.mp4"
        mock_exists.return_value = False  # No file found at any extension

        result = downloader.download_video("http://v1", Path("/tmp"), "V1", 0)
        assert result is None

    @patch("playlist_downloader.yt_dlp.YoutubeDL")
    def test_position_in_outtmpl(self, mock_ydl_cls, downloader):
        """Test that position is used in output template."""
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = None

        downloader.download_video("http://v1", Path("/tmp"), "V1", 4)
        # Verify the outtmpl contains the position prefix (position 4 → 005)
        call_args = mock_ydl_cls.call_args
        outtmpl = call_args[0][0]['outtmpl']
        assert '005 - ' in outtmpl
