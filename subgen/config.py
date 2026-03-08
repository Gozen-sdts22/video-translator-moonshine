"""設定管理モジュール"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".subgen" / "config.json"


@dataclass
class Config:
    """SubGenの設定。"""
    language: str = "ja"
    format: str = "ass"
    translate_to: str | None = None
    translate_api: str = "deepl"
    num_speakers: str | int = "auto"
    sample_rate: int = 16000
    chunk_duration: float = 30.0
    font_ja: str = "Noto Sans JP"
    font_zh: str = "Noto Sans SC"
    font_size: int = 20

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        """設定ファイルから読み込む。ファイルがなければデフォルト値を使用。"""
        path = Path(path) if path else DEFAULT_CONFIG_PATH
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self, path: str | Path | None = None) -> Path:
        """設定をJSONファイルに保存する。"""
        path = Path(path) if path else DEFAULT_CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        from dataclasses import asdict
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def get_deepl_api_key(self) -> str | None:
        return os.environ.get("DEEPL_API_KEY")

    def get_google_credentials(self) -> str | None:
        return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
