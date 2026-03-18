"""Phase 4: Tests for copy_video_from_another_playlist."""

import shutil
from pathlib import Path
from unittest.mock import patch

from playlist_downloader import PlaylistDownloader


class TestCopyVideoFromAnotherPlaylist:
    def test_not_in_global_index_returns_false(self, downloader):
        assert downloader.copy_video_from_another_playlist("nonexistent", Path("/tmp")) is False

    def test_empty_files_list_returns_false(self, downloader):
        downloader.global_index = {"vid1": {"title": "T", "files": []}}
        assert downloader.copy_video_from_another_playlist("vid1", Path("/tmp")) is False

    def test_source_file_missing_returns_false(self, downloader, tmp_path):
        downloader.global_index = {"vid1": {"title": "T", "files": [str(tmp_path / "gone.mp4")]}}
        target = tmp_path / "target"
        target.mkdir()
        assert downloader.copy_video_from_another_playlist("vid1", target) is False

    def test_success_copies_main_file(self, downloader, tmp_path):
        # Create source
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"fake video data")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        downloader.global_index = {"vid1": {"title": "T", "files": [str(source_file)]}}
        result = downloader.copy_video_from_another_playlist("vid1", target_dir)
        assert result is True
        assert (target_dir / "video.mp4").read_bytes() == b"fake video data"

    def test_copies_associated_files(self, downloader, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"video")
        (source_dir / "video.en.vtt").write_text("subtitles")
        (source_dir / "video.jpg").write_bytes(b"thumbnail")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        downloader.global_index = {"vid1": {"title": "T", "files": [str(source_file)]}}
        downloader.copy_video_from_another_playlist("vid1", target_dir)

        assert (target_dir / "video.en.vtt").exists()
        assert (target_dir / "video.jpg").exists()

    def test_skips_other_video_formats(self, downloader, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"video")
        (source_dir / "video.webm").write_bytes(b"webm")
        (source_dir / "video.mkv").write_bytes(b"mkv")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        downloader.global_index = {"vid1": {"title": "T", "files": [str(source_file)]}}
        downloader.copy_video_from_another_playlist("vid1", target_dir)

        assert not (target_dir / "video.webm").exists()
        assert not (target_dir / "video.mkv").exists()

    def test_returns_true_on_success(self, downloader, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"data")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        downloader.global_index = {"vid1": {"title": "T", "files": [str(source_file)]}}
        assert downloader.copy_video_from_another_playlist("vid1", target_dir) is True

    @patch("playlist_downloader.shutil.copy2", side_effect=OSError("disk full"))
    def test_handles_copy_exception_returns_false(self, mock_copy, downloader, tmp_path):
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"data")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        downloader.global_index = {"vid1": {"title": "T", "files": [str(source_file)]}}
        assert downloader.copy_video_from_another_playlist("vid1", target_dir) is False
