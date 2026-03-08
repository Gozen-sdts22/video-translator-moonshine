"""設定モジュールのテスト"""

import json
from pathlib import Path

import pytest

from subgen.config import Config


class TestConfig:
    def test_defaults(self):
        config = Config()
        assert config.language == "ja"
        assert config.format == "ass"
        assert config.translate_to is None
        assert config.translate_api == "deepl"
        assert config.num_speakers == "auto"
        assert config.sample_rate == 16000

    def test_save_and_load(self, tmp_path):
        config = Config(language="en", format="srt", translate_to="zh")
        path = tmp_path / "config.json"
        config.save(path)

        loaded = Config.load(path)
        assert loaded.language == "en"
        assert loaded.format == "srt"
        assert loaded.translate_to == "zh"

    def test_load_nonexistent(self, tmp_path):
        config = Config.load(tmp_path / "nonexistent.json")
        assert config.language == "ja"  # デフォルト値

    def test_save_creates_directory(self, tmp_path):
        config = Config()
        path = tmp_path / "subdir" / "config.json"
        config.save(path)
        assert path.exists()
