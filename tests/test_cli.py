"""CLIのテスト"""

from unittest.mock import patch

import pytest

from subgen.cli import build_parser, main


class TestBuildParser:
    def test_default_values(self):
        parser = build_parser()
        args = parser.parse_args(["input.mp4"])
        assert args.input == "input.mp4"
        assert args.lang == "ja"
        assert args.format == "ass"
        assert args.output is None
        assert args.translate is None
        assert args.api == "deepl"
        assert args.speakers == "auto"
        assert args.verbose is False

    def test_all_options(self):
        parser = build_parser()
        args = parser.parse_args([
            "video.mp4", "-l", "ja", "-f", "both",
            "-o", "./subs", "-t", "zh", "--api", "google",
            "--speakers", "3", "-v",
        ])
        assert args.input == "video.mp4"
        assert args.lang == "ja"
        assert args.format == "both"
        assert args.output == "./subs"
        assert args.translate == "zh"
        assert args.api == "google"
        assert args.speakers == "3"
        assert args.verbose is True


class TestMain:
    def test_file_not_found(self):
        assert main(["/nonexistent/file.mp4"]) == 1

    def test_invalid_speakers(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        assert main([str(video), "--speakers", "abc"]) == 1

    def test_negative_speakers(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        assert main([str(video), "--speakers", "-1"]) == 1
