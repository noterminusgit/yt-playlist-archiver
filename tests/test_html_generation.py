"""Phase 5: Tests for generate_html_index."""

from unittest.mock import patch
from datetime import datetime
from pathlib import Path

from playlist_downloader import PlaylistDownloader


class TestGenerateHtmlIndex:
    def test_creates_index_html(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Test Playlist", sample_videos)
        assert (playlist_dir / "index.html").exists()

    def test_contains_playlist_title_in_title_tag(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "My Awesome Playlist", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert "<title>My Awesome Playlist</title>" in html

    def test_contains_playlist_title_in_h1(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "My Awesome Playlist", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert "<h1>My Awesome Playlist</h1>" in html

    def test_contains_video_count(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert "Total Videos:</strong> 3" in html

    @patch("playlist_downloader.datetime")
    def test_deterministic_timestamp(self, mock_dt, downloader, sample_videos):
        mock_dt.now.return_value = datetime(2025, 6, 15, 12, 30, 45)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert "2025-06-15 12:30:45" in html

    def test_video_entries_present(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        for video in sample_videos:
            assert video["title"] in html
            assert f'https://www.youtube.com/watch?v={video["id"]}' in html

    def test_one_based_numbering(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert ">1.<" in html
        assert ">2.<" in html
        assert ">3.<" in html

    def test_downloaded_status_badge(self, downloader):
        videos = [{"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0, "status": "downloaded"}]
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert 'class="status downloaded"' in html

    def test_failed_status_badge(self, downloader):
        videos = [{"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0, "status": "failed"}]
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert 'class="status failed"' in html

    def test_no_badge_for_unknown_status(self, downloader):
        videos = [{"id": "V1", "title": "T", "url": "http://v1", "playlist_index": 0, "status": "unknown"}]
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert 'class="status downloaded"' not in html
        assert 'class="status failed"' not in html

    def test_empty_video_list(self, downloader):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", [])
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert "Total Videos:</strong> 0" in html
        assert "<!DOCTYPE html>" in html

    def test_valid_html_structure(self, downloader, sample_videos):
        playlist_dir = downloader.output_dir / "test_playlist"
        playlist_dir.mkdir(parents=True)
        downloader.generate_html_index(playlist_dir, "Title", sample_videos)
        html = (playlist_dir / "index.html").read_text(encoding="utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html
