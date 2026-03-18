"""Tests for process_playlist, position preservation, and run."""

import json
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from datetime import datetime

from playlist_downloader import PlaylistDownloader


class TestProcessPlaylist:
    def test_creates_sanitized_directory(self, downloader, sample_playlist):
        sample_playlist["title"] = "My <Special> Playlist"
        with patch.object(downloader, "get_playlist_videos", return_value=[]), \
             patch.object(downloader, "generate_html_index"):
            downloader.process_playlist(sample_playlist)
        expected_dir = downloader.output_dir / "My _Special_ Playlist"
        assert expected_dir.exists()

    def test_skips_already_downloaded(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            # Pre-create metadata marking V1 as downloaded
            playlist_dir = downloader.output_dir / "Test Playlist"
            playlist_dir.mkdir(parents=True)
            metadata = {
                "playlist_id": "PLtest123",
                "playlist_title": "Test Playlist",
                "playlist_url": "http://pl",
                "videos": {"V1": {"status": "downloaded", "title": "T"}}
            }
            (playlist_dir / "playlist_metadata.json").write_text(json.dumps(metadata))

            downloader.process_playlist(sample_playlist)
            mock_dl.assert_not_called()

    def test_copies_from_global_index(self, downloader, sample_playlist, tmp_path):
        # Set up a source file that exists
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"data")

        downloader.global_index = {"V1": {"title": "T", "files": [str(source_file)]}}

        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            downloader.process_playlist(sample_playlist)
            # Should not download since it was copied
            mock_dl.assert_not_called()

    def test_copies_from_global_index_updates_index(self, downloader, sample_playlist, tmp_path):
        """Copied video found via glob gets added to global index files list."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "001 - V1_title.mp4"
        source_file.write_bytes(b"data")

        downloader.global_index = {"V1": {"title": "T", "files": [str(source_file)]}}

        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            downloader.process_playlist(sample_playlist)
            mock_dl.assert_not_called()

        # The copied file in playlist dir should be added to global index
        playlist_dir = downloader.output_dir / "Test Playlist"
        copied_file = playlist_dir / "001 - V1_title.mp4"
        assert copied_file.exists()
        assert str(copied_file) in downloader.global_index["V1"]["files"]

    def test_downloads_new_videos(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)
            mock_dl.assert_called_once()

    def test_handles_download_failure(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            mock_dl.return_value = None
            downloader.process_playlist(sample_playlist)

        # Check metadata was saved with failed status
        playlist_dir = downloader.output_dir / "Test Playlist"
        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert metadata["videos"]["V1"]["status"] == "failed"

    def test_saves_metadata_after_each_video(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T1", "url": "http://v1", "playlist_index": 0},
                {"id": "V2", "title": "T2", "url": "http://v2", "playlist_index": 1},
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)

        playlist_dir = downloader.output_dir / "Test Playlist"
        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert "V1" in metadata["videos"]
        assert "V2" in metadata["videos"]

    def test_updates_global_index_on_download(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)

        assert "V1" in downloader.global_index
        assert "/tmp/video.mp4" in downloader.global_index["V1"]["files"]

    def test_generates_html_at_end(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos", return_value=[]) as mock_get, \
             patch.object(downloader, "generate_html_index") as mock_html:
            downloader.process_playlist(sample_playlist)
            mock_html.assert_called_once()

    def test_loads_existing_metadata(self, downloader, sample_playlist):
        playlist_dir = downloader.output_dir / "Test Playlist"
        playlist_dir.mkdir(parents=True)
        existing = {
            "playlist_id": "PLtest123",
            "playlist_title": "Test Playlist",
            "playlist_url": "http://pl",
            "videos": {"OLD": {"status": "downloaded", "title": "Old"}}
        }
        (playlist_dir / "playlist_metadata.json").write_text(json.dumps(existing))

        with patch.object(downloader, "get_playlist_videos", return_value=[]), \
             patch.object(downloader, "generate_html_index"):
            downloader.process_playlist(sample_playlist)
        # Just verifies no crash when loading existing metadata

    def test_creates_new_metadata_if_none_exists(self, downloader, sample_playlist):
        with patch.object(downloader, "get_playlist_videos", return_value=[]), \
             patch.object(downloader, "generate_html_index"):
            downloader.process_playlist(sample_playlist)
        # No crash — metadata created fresh

    @patch("playlist_downloader.datetime")
    def test_datetime_in_metadata(self, mock_dt, downloader, sample_playlist):
        mock_dt.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)

        playlist_dir = downloader.output_dir / "Test Playlist"
        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert metadata["videos"]["V1"]["downloaded_at"] == "2025-01-01T12:00:00"


class TestPositionPreservation:
    def test_stored_position_preserved(self, downloader, sample_playlist):
        """Video in metadata keeps stored position even if API returns different position."""
        playlist_dir = downloader.output_dir / "Test Playlist"
        playlist_dir.mkdir(parents=True)
        metadata = {
            "playlist_id": "PLtest123",
            "playlist_title": "Test Playlist",
            "playlist_url": "http://pl",
            "videos": {"V1": {"status": "downloaded", "title": "T", "position": 5}}
        }
        (playlist_dir / "playlist_metadata.json").write_text(json.dumps(metadata))

        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            # API returns position 0, but stored position is 5
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0}
            ]
            downloader.process_playlist(sample_playlist)
            mock_dl.assert_not_called()

        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert metadata["videos"]["V1"]["position"] == 5

    def test_position_conflict_resolution(self, downloader, sample_playlist):
        """New video at occupied position gets reassigned."""
        playlist_dir = downloader.output_dir / "Test Playlist"
        playlist_dir.mkdir(parents=True)
        metadata = {
            "playlist_id": "PLtest123",
            "playlist_title": "Test Playlist",
            "playlist_url": "http://pl",
            "videos": {"V1": {"status": "downloaded", "title": "T1", "position": 0}}
        }
        (playlist_dir / "playlist_metadata.json").write_text(json.dumps(metadata))

        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            # V1 is at position 0, V2 tries to claim position 0
            mock_get.return_value = [
                {"id": "V1", "title": "T1", "url": "http://v1", "playlist_index": 0},
                {"id": "V2", "title": "T2", "url": "http://v2", "playlist_index": 0},
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)

        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert metadata["videos"]["V1"]["position"] == 0
        # V2 should get position 1 (max existing + 1)
        assert metadata["videos"]["V2"]["position"] == 1

    def test_unavailable_video_handling(self, downloader, sample_playlist):
        """Unavailable videos are recorded in metadata with position, no download attempted."""
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "Private video", "url": "http://v1", "playlist_index": 0, "unavailable": True},
            ]
            downloader.process_playlist(sample_playlist)
            mock_dl.assert_not_called()

        playlist_dir = downloader.output_dir / "Test Playlist"
        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert metadata["videos"]["V1"]["status"] == "unavailable"
        assert metadata["videos"]["V1"]["position"] == 0

    def test_gap_preservation(self, downloader, sample_playlist):
        """Numbering has gaps after removal — stored positions are preserved."""
        playlist_dir = downloader.output_dir / "Test Playlist"
        playlist_dir.mkdir(parents=True)
        metadata = {
            "playlist_id": "PLtest123",
            "playlist_title": "Test Playlist",
            "playlist_url": "http://pl",
            "videos": {
                "V1": {"status": "downloaded", "title": "T1", "position": 0},
                "V2": {"status": "downloaded", "title": "T2", "position": 1},
                "V3": {"status": "downloaded", "title": "T3", "position": 2},
            }
        }
        (playlist_dir / "playlist_metadata.json").write_text(json.dumps(metadata))

        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            # V2 is gone from playlist, only V1 and V3 remain
            mock_get.return_value = [
                {"id": "V1", "title": "T1", "url": "http://v1", "playlist_index": 0},
                {"id": "V3", "title": "T3", "url": "http://v3", "playlist_index": 1},
            ]
            downloader.process_playlist(sample_playlist)
            mock_dl.assert_not_called()

        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        # V1 keeps position 0, V3 keeps position 2 (from metadata, not API's 1)
        assert metadata["videos"]["V1"]["position"] == 0
        assert metadata["videos"]["V3"]["position"] == 2

    def test_position_stored_in_metadata_on_download(self, downloader, sample_playlist):
        """Position is stored in metadata when a video is downloaded."""
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 3}
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)

        playlist_dir = downloader.output_dir / "Test Playlist"
        metadata = json.loads((playlist_dir / "playlist_metadata.json").read_text())
        assert metadata["videos"]["V1"]["position"] == 3

    def test_position_passed_to_download_video(self, downloader, sample_playlist):
        """Position is passed to download_video."""
        with patch.object(downloader, "get_playlist_videos") as mock_get, \
             patch.object(downloader, "download_video") as mock_dl, \
             patch.object(downloader, "generate_html_index"):
            mock_get.return_value = [
                {"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 7}
            ]
            mock_dl.return_value = "/tmp/video.mp4"
            downloader.process_playlist(sample_playlist)

        # Verify position was passed to download_video (4th positional arg)
        mock_dl.assert_called_once()
        assert mock_dl.call_args[0][3] == 7


class TestRun:
    def test_fetches_playlists(self, downloader):
        with patch.object(downloader, "get_all_playlists", return_value=[]) as mock_get:
            downloader.run()
            mock_get.assert_called_once()

    def test_processes_each_playlist(self, downloader):
        playlists = [
            {"id": "PL1", "title": "P1", "url": "http://pl1"},
            {"id": "PL2", "title": "P2", "url": "http://pl2"},
        ]
        with patch.object(downloader, "get_all_playlists", return_value=playlists), \
             patch.object(downloader, "process_playlist") as mock_proc:
            downloader.run()
            assert mock_proc.call_count == 2

    def test_returns_early_on_empty(self, downloader):
        with patch.object(downloader, "get_all_playlists", return_value=[]), \
             patch.object(downloader, "process_playlist") as mock_proc:
            downloader.run()
            mock_proc.assert_not_called()

    def test_continues_after_per_playlist_error(self, downloader):
        playlists = [
            {"id": "PL1", "title": "P1", "url": "http://pl1"},
            {"id": "PL2", "title": "P2", "url": "http://pl2"},
        ]
        with patch.object(downloader, "get_all_playlists", return_value=playlists), \
             patch.object(downloader, "process_playlist", side_effect=[Exception("boom"), None]) as mock_proc:
            downloader.run()
            assert mock_proc.call_count == 2
