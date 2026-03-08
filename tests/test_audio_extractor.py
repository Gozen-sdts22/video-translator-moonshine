"""音声抽出モジュールのテスト"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from subgen.audio_extractor import check_ffmpeg, extract_audio


class TestCheckFfmpeg:
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_ffmpeg_found(self, mock_which):
        assert check_ffmpeg() is True

    @patch("shutil.which", return_value=None)
    def test_ffmpeg_not_found(self, mock_which):
        assert check_ffmpeg() is False


class TestExtractAudio:
    @patch("shutil.which", return_value=None)
    def test_raises_when_ffmpeg_missing(self, mock_which, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        with pytest.raises(FileNotFoundError, match="FFmpeg"):
            extract_audio(video)

    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_raises_when_file_not_found(self, mock_which):
        with pytest.raises(FileNotFoundError, match="入力ファイル"):
            extract_audio("/nonexistent/file.mp4")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_successful_extraction(self, mock_which, mock_run, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        output = tmp_path / "output.wav"

        mock_run.return_value = MagicMock(returncode=0)

        result = extract_audio(video, output_path=output)
        assert result == output
        mock_run.assert_called_once()

        cmd = mock_run.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "-ar" in cmd
        assert "16000" in cmd
        assert "-ac" in cmd
        assert "1" in cmd

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="error"))
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_ffmpeg_failure(self, mock_which, mock_run, tmp_path):
        video = tmp_path / "test.mp4"
        video.touch()
        with pytest.raises(RuntimeError, match="FFmpegの実行に失敗"):
            extract_audio(video, output_path=tmp_path / "out.wav")
