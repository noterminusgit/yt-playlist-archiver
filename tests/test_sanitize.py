"""Phase 1: Tests for _sanitize_filename method."""

from playlist_downloader import PlaylistDownloader


def make_downloader(tmp_path):
    return PlaylistDownloader("https://www.youtube.com/@test", str(tmp_path / "dl"))


class TestSanitizeFilename:
    def test_removes_less_than(self, tmp_path):
        d = make_downloader(tmp_path)
        assert "<" not in d._sanitize_filename("file<name")

    def test_removes_greater_than(self, tmp_path):
        d = make_downloader(tmp_path)
        assert ">" not in d._sanitize_filename("file>name")

    def test_removes_colon(self, tmp_path):
        d = make_downloader(tmp_path)
        assert ":" not in d._sanitize_filename("file:name")

    def test_removes_double_quote(self, tmp_path):
        d = make_downloader(tmp_path)
        assert '"' not in d._sanitize_filename('file"name')

    def test_removes_slash(self, tmp_path):
        d = make_downloader(tmp_path)
        assert "/" not in d._sanitize_filename("file/name")

    def test_removes_backslash(self, tmp_path):
        d = make_downloader(tmp_path)
        assert "\\" not in d._sanitize_filename("file\\name")

    def test_removes_pipe(self, tmp_path):
        d = make_downloader(tmp_path)
        assert "|" not in d._sanitize_filename("file|name")

    def test_removes_question_mark(self, tmp_path):
        d = make_downloader(tmp_path)
        assert "?" not in d._sanitize_filename("file?name")

    def test_removes_asterisk(self, tmp_path):
        d = make_downloader(tmp_path)
        assert "*" not in d._sanitize_filename("file*name")

    def test_invalid_chars_replaced_with_underscore(self, tmp_path):
        d = make_downloader(tmp_path)
        assert d._sanitize_filename("a<b>c") == "a_b_c"

    def test_strips_leading_trailing_dots_and_spaces(self, tmp_path):
        d = make_downloader(tmp_path)
        assert d._sanitize_filename("...name...") == "name"

    def test_strips_leading_trailing_spaces(self, tmp_path):
        d = make_downloader(tmp_path)
        assert d._sanitize_filename("  name  ") == "name"

    def test_truncates_to_200_chars(self, tmp_path):
        d = make_downloader(tmp_path)
        result = d._sanitize_filename("a" * 300)
        assert len(result) == 200

    def test_preserves_valid_filename(self, tmp_path):
        d = make_downloader(tmp_path)
        assert d._sanitize_filename("valid_filename") == "valid_filename"

    def test_empty_string(self, tmp_path):
        d = make_downloader(tmp_path)
        assert d._sanitize_filename("") == ""

    def test_unicode_passthrough(self, tmp_path):
        d = make_downloader(tmp_path)
        assert d._sanitize_filename("café résumé") == "café résumé"

    def test_all_invalid_chars(self, tmp_path):
        d = make_downloader(tmp_path)
        result = d._sanitize_filename('<>:"/\\|?*')
        # All replaced with _, then stripped of dots/spaces
        assert result == "_________"
