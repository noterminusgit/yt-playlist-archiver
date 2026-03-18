import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from playlist_downloader import PlaylistDownloader


@pytest.fixture(autouse=True)
def mock_youtube_api(monkeypatch):
    """Set YOUTUBE_API_KEY and mock the Google API client for all tests."""
    monkeypatch.setenv('YOUTUBE_API_KEY', 'test-api-key')
    mock_service = MagicMock()
    # Setup channel resolution to return a test channel ID
    mock_service.channels.return_value.list.return_value.execute.return_value = {
        'items': [{'id': 'UCtest123'}]
    }
    with patch('playlist_downloader.googleapiclient.discovery.build', return_value=mock_service):
        yield mock_service


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temporary output directory."""
    return tmp_path / "downloads"


@pytest.fixture
def downloader(output_dir):
    """Create a PlaylistDownloader with a temp output directory."""
    return PlaylistDownloader("https://www.youtube.com/@testchannel", str(output_dir))


@pytest.fixture
def downloader_with_index(downloader):
    """Create a downloader with a pre-populated global index."""
    downloader.global_index = {
        "video1": {
            "title": "Test Video 1",
            "files": ["/tmp/playlist_a/video1.mp4"]
        },
        "video2": {
            "title": "Test Video 2",
            "files": ["/tmp/playlist_b/video2.mp4"]
        },
    }
    return downloader


@pytest.fixture
def sample_videos():
    """Sample video list for testing."""
    return [
        {"id": "abc123", "title": "First Video", "url": "https://www.youtube.com/watch?v=abc123", "playlist_index": 0, "unavailable": False},
        {"id": "def456", "title": "Second Video", "url": "https://www.youtube.com/watch?v=def456", "playlist_index": 1, "unavailable": False},
        {"id": "ghi789", "title": "Third Video", "url": "https://www.youtube.com/watch?v=ghi789", "playlist_index": 2, "unavailable": False},
    ]


@pytest.fixture
def sample_playlist():
    """Sample playlist dict for testing."""
    return {
        "id": "PLtest123",
        "title": "Test Playlist",
        "url": "https://www.youtube.com/playlist?list=PLtest123",
    }
