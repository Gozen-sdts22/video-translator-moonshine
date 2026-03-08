"""F-001: 動画からの音声抽出モジュール"""

import shutil
import subprocess
import tempfile
from pathlib import Path


def check_ffmpeg() -> bool:
    """FFmpegがシステムにインストールされているか確認する。"""
    return shutil.which("ffmpeg") is not None


def extract_audio(
    video_path: str | Path,
    output_path: str | Path | None = None,
    sample_rate: int = 16000,
    verbose: bool = False,
) -> Path:
    """動画ファイルから音声を抽出し、WAVファイルとして保存する。

    Args:
        video_path: 入力動画ファイルパス
        output_path: 出力WAVファイルパス（Noneの場合は自動生成）
        sample_rate: サンプルレート（デフォルト: 16kHz）
        verbose: 詳細ログ出力

    Returns:
        出力WAVファイルのパス
    """
    if not check_ffmpeg():
        raise FileNotFoundError(
            "FFmpegが見つかりません。システムPATHにFFmpegをインストールしてください。"
        )

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {video_path}")

    if output_path is None:
        output_path = Path(
            tempfile.mktemp(suffix=".wav", prefix="subgen_audio_")
        )
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        str(output_path),
    ]

    if verbose:
        print(f"[音声抽出] コマンド: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpegの実行に失敗しました:\n{e.stderr}") from e

    if verbose:
        print(f"[音声抽出] 完了: {output_path}")

    return output_path
