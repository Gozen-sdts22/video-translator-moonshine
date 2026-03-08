"""字幕生成モジュールのテスト"""

from pathlib import Path

import pytest

from subgen.asr import Segment
from subgen.subtitle_writer import (
    _format_ass_time,
    _format_srt_time,
    generate_ass,
    generate_srt,
    generate_subtitles,
)


class TestTimeFormatting:
    def test_srt_time_zero(self):
        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_srt_time_complex(self):
        # 1時間23分45秒500ミリ秒
        assert _format_srt_time(5025.5) == "01:23:45,500"

    def test_ass_time_zero(self):
        assert _format_ass_time(0.0) == "0:00:00.00"

    def test_ass_time_complex(self):
        assert _format_ass_time(5025.67) == "1:23:45.67"


@pytest.fixture
def sample_segments():
    return [
        Segment(start=0.0, end=2.5, text="こんにちは", speaker="Speaker_1"),
        Segment(start=3.0, end=5.0, text="お元気ですか", speaker="Speaker_2"),
        Segment(start=5.5, end=8.0, text="はい、元気です", speaker="Speaker_1"),
    ]


class TestGenerateSrt:
    def test_basic_srt(self, sample_segments, tmp_path):
        output = tmp_path / "test.srt"
        result = generate_srt(sample_segments, output)

        assert result == output
        assert output.exists()

        content = output.read_text(encoding="utf-8")
        assert "1\n" in content
        assert "こんにちは" in content
        assert "00:00:00,000 --> 00:00:02,500" in content
        assert "お元気ですか" in content

    def test_empty_segments(self, tmp_path):
        output = tmp_path / "empty.srt"
        generate_srt([], output)
        assert output.exists()


class TestGenerateAss:
    def test_basic_ass(self, sample_segments, tmp_path):
        output = tmp_path / "test.ass"
        result = generate_ass(sample_segments, output, language="ja")

        assert result == output
        content = output.read_text(encoding="utf-8")

        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "Speaker_1" in content
        assert "Speaker_2" in content
        assert "こんにちは" in content
        assert "Noto Sans JP" in content

    def test_chinese_font(self, sample_segments, tmp_path):
        output = tmp_path / "test_zh.ass"
        generate_ass(sample_segments, output, language="zh")
        content = output.read_text(encoding="utf-8")
        assert "Noto Sans SC" in content

    def test_speaker_colors(self, sample_segments, tmp_path):
        output = tmp_path / "test.ass"
        generate_ass(sample_segments, output)
        content = output.read_text(encoding="utf-8")
        assert "&H00FFFFFF" in content  # Speaker_1: 白
        assert "&H0000FFFF" in content  # Speaker_2: 黄


class TestGenerateSubtitles:
    def test_srt_only(self, sample_segments, tmp_path):
        files = generate_subtitles(sample_segments, tmp_path, "test", "ja", "srt")
        assert len(files) == 1
        assert files[0].suffix == ".srt"
        assert "_ja" in files[0].name

    def test_ass_only(self, sample_segments, tmp_path):
        files = generate_subtitles(sample_segments, tmp_path, "test", "ja", "ass")
        assert len(files) == 1
        assert files[0].suffix == ".ass"

    def test_both_formats(self, sample_segments, tmp_path):
        files = generate_subtitles(sample_segments, tmp_path, "test", "ja", "both")
        assert len(files) == 2
        suffixes = {f.suffix for f in files}
        assert suffixes == {".srt", ".ass"}
