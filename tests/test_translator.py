"""翻訳モジュールのテスト"""

import os
from unittest.mock import MagicMock, patch

import pytest

from subgen.asr import Segment
from subgen.translator import translate_segments


@pytest.fixture
def sample_segments():
    return [
        Segment(start=0.0, end=2.5, text="こんにちは"),
        Segment(start=3.0, end=5.0, text="ありがとう"),
    ]


class TestTranslateSegments:
    def test_empty_segments(self):
        assert translate_segments([], target_lang="zh") == []

    def test_invalid_api(self, sample_segments):
        with pytest.raises(ValueError, match="不明な翻訳API"):
            translate_segments(sample_segments, api="invalid")

    def test_deepl_missing_api_key(self, sample_segments):
        with patch.dict(os.environ, {}, clear=True):
            # DEEPL_API_KEYが未設定
            env = os.environ.copy()
            env.pop("DEEPL_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ValueError, match="DEEPL_API_KEY"):
                    translate_segments(sample_segments, api="deepl")

    @patch("subgen.translator._translate_deepl")
    def test_deepl_api_called(self, mock_deepl, sample_segments):
        mock_deepl.return_value = ["你好", "谢谢"]
        result = translate_segments(sample_segments, target_lang="zh", api="deepl")

        assert len(result) == 2
        assert result[0].text == "你好"
        assert result[1].text == "谢谢"
        # タイムスタンプが保持されていること
        assert result[0].start == 0.0
        assert result[0].end == 2.5

    @patch("subgen.translator._translate_google")
    def test_google_api_called(self, mock_google, sample_segments):
        mock_google.return_value = ["你好", "谢谢"]
        result = translate_segments(sample_segments, target_lang="zh", api="google")

        assert len(result) == 2
        assert result[0].text == "你好"
