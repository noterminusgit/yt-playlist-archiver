"""Phase 2: Tests for global index persistence."""

import json
from playlist_downloader import PlaylistDownloader


class TestGlobalIndexInit:
    def test_init_creates_output_directory(self, tmp_path):
        out = tmp_path / "new_dir"
        PlaylistDownloader("https://www.youtube.com/@test", str(out))
        assert out.exists() and out.is_dir()

    def test_init_loads_preexisting_index(self, tmp_path):
        out = tmp_path / "dl"
        out.mkdir()
        index_file = out / "global_video_index.json"
        data = {"vid1": {"title": "V1", "files": ["/a/b.mp4"]}}
        index_file.write_text(json.dumps(data), encoding="utf-8")

        d = PlaylistDownloader("https://www.youtube.com/@test", str(out))
        assert d.global_index == data


class TestLoadGlobalIndex:
    def test_load_returns_empty_dict_when_no_file(self, downloader):
        assert downloader.global_index == {}

    def test_load_reads_existing_json(self, downloader):
        data = {"v1": {"title": "T", "files": []}}
        downloader.global_index_path.write_text(json.dumps(data), encoding="utf-8")
        result = downloader._load_global_index()
        assert result == data


class TestSaveGlobalIndex:
    def test_save_creates_json_file(self, downloader):
        downloader.global_index = {"v1": {"title": "T", "files": []}}
        downloader._save_global_index()
        assert downloader.global_index_path.exists()

    def test_save_roundtrip_fidelity(self, downloader):
        data = {"v1": {"title": "Test", "files": ["/a.mp4"]}, "v2": {"title": "Other", "files": []}}
        downloader.global_index = data
        downloader._save_global_index()
        loaded = json.loads(downloader.global_index_path.read_text(encoding="utf-8"))
        assert loaded == data

    def test_save_overwrites_existing(self, downloader):
        downloader.global_index = {"old": {"title": "Old", "files": []}}
        downloader._save_global_index()
        downloader.global_index = {"new": {"title": "New", "files": []}}
        downloader._save_global_index()
        loaded = json.loads(downloader.global_index_path.read_text(encoding="utf-8"))
        assert "new" in loaded
        assert "old" not in loaded

    def test_unicode_preservation(self, downloader):
        data = {"v1": {"title": "日本語テスト", "files": []}}
        downloader.global_index = data
        downloader._save_global_index()
        loaded = json.loads(downloader.global_index_path.read_text(encoding="utf-8"))
        assert loaded["v1"]["title"] == "日本語テスト"

    def test_load_after_save_matches(self, downloader):
        data = {"v1": {"title": "Round", "files": ["/x.mp4"]}}
        downloader.global_index = data
        downloader._save_global_index()
        result = downloader._load_global_index()
        assert result == data
