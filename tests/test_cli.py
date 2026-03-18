"""Tests for CLI main() function."""

import sys
from unittest.mock import patch, MagicMock

import pytest

from playlist_downloader import main


class TestCli:
    @patch("playlist_downloader.PlaylistDownloader")
    def test_parses_channel_arg(self, mock_cls):
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        with patch.object(sys, "argv", ["prog", "https://www.youtube.com/@testchannel"]):
            main()
        mock_cls.assert_called_once_with("https://www.youtube.com/@testchannel", "./downloads")

    @patch("playlist_downloader.PlaylistDownloader")
    def test_parses_output_dir_arg(self, mock_cls):
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        with patch.object(sys, "argv", ["prog", "@user", "/custom/path"]):
            main()
        mock_cls.assert_called_once_with("@user", "/custom/path")

    @patch("playlist_downloader.PlaylistDownloader")
    def test_default_output_dir(self, mock_cls):
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        with patch.object(sys, "argv", ["prog", "@user"]):
            main()
        mock_cls.assert_called_once_with("@user", "./downloads")

    def test_missing_channel_raises_system_exit(self):
        with patch.object(sys, "argv", ["prog"]):
            with pytest.raises(SystemExit):
                main()

    @patch("playlist_downloader.PlaylistDownloader")
    def test_calls_run(self, mock_cls):
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        with patch.object(sys, "argv", ["prog", "@user"]):
            main()
        mock_instance.run.assert_called_once()

    def test_missing_api_key_raises_error(self, monkeypatch):
        """Missing YOUTUBE_API_KEY raises ValueError."""
        monkeypatch.delenv('YOUTUBE_API_KEY', raising=False)
        with patch.object(sys, "argv", ["prog", "@user"]):
            with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
                main()
