"""F-002: 音声認識モジュール（Moonshine ASR）"""

from __future__ import annotations

import json
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Segment:
    """音声認識結果の1セグメント。"""
    start: float
    end: float
    text: str
    speaker: str | None = None


def _load_audio_as_float(wav_path: Path) -> tuple[list[float], int]:
    """WAVファイルを読み込み、float値のリストとサンプルレートを返す。"""
    import array

    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = array.array("h", raw)
    else:
        raise ValueError(f"サポートされていないサンプル幅: {sampwidth}")

    if n_channels == 2:
        samples = samples[::2]

    max_val = 2 ** (sampwidth * 8 - 1)
    float_samples = [s / max_val for s in samples]
    return float_samples, framerate


def transcribe(
    audio_path: str | Path,
    language: str = "ja",
    chunk_duration: float = 30.0,
    verbose: bool = False,
) -> list[Segment]:
    """音声ファイルを文字起こしする。

    Moonshine ASRモデルを使用してタイムスタンプ付きテキストセグメントを生成する。
    長い音声はチャンク分割して処理する。

    Args:
        audio_path: 入力WAVファイルパス
        language: 音声の言語コード
        chunk_duration: チャンク分割の秒数（デフォルト: 30秒）
        verbose: 詳細ログ出力

    Returns:
        Segmentのリスト
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音声ファイルが見つかりません: {audio_path}")

    try:
        from moonshine_voice import transcribe as moonshine_transcribe
    except ImportError:
        try:
            from moonshine import transcribe as moonshine_transcribe
        except ImportError:
            raise ImportError(
                "Moonshine ASRがインストールされていません。\n"
                "pip install moonshine-voice でインストールしてください。"
            )

    if verbose:
        print(f"[ASR] 音声ファイル読み込み: {audio_path}")

    float_samples, sample_rate = _load_audio_as_float(audio_path)
    total_duration = len(float_samples) / sample_rate

    if verbose:
        print(f"[ASR] 音声長: {total_duration:.1f}秒, サンプルレート: {sample_rate}Hz")

    segments: list[Segment] = []
    chunk_samples = int(chunk_duration * sample_rate)
    offset = 0
    chunk_index = 0

    while offset < len(float_samples):
        chunk = float_samples[offset:offset + chunk_samples]
        chunk_start_time = offset / sample_rate

        if verbose:
            chunk_end_time = min(chunk_start_time + chunk_duration, total_duration)
            print(f"[ASR] チャンク {chunk_index + 1}: {chunk_start_time:.1f}s - {chunk_end_time:.1f}s")

        try:
            result = moonshine_transcribe(chunk, sample_rate=sample_rate, language=language)
        except TypeError:
            result = moonshine_transcribe(chunk)

        if isinstance(result, dict) and "segments" in result:
            for seg in result["segments"]:
                segments.append(Segment(
                    start=seg.get("start", 0.0) + chunk_start_time,
                    end=seg.get("end", 0.0) + chunk_start_time,
                    text=seg.get("text", "").strip(),
                ))
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    segments.append(Segment(
                        start=item.get("start", 0.0) + chunk_start_time,
                        end=item.get("end", 0.0) + chunk_start_time,
                        text=item.get("text", "").strip(),
                    ))
                elif isinstance(item, str) and item.strip():
                    seg_duration = len(chunk) / sample_rate
                    segments.append(Segment(
                        start=chunk_start_time,
                        end=chunk_start_time + seg_duration,
                        text=item.strip(),
                    ))
        elif isinstance(result, str) and result.strip():
            seg_duration = len(chunk) / sample_rate
            segments.append(Segment(
                start=chunk_start_time,
                end=chunk_start_time + seg_duration,
                text=result.strip(),
            ))

        offset += chunk_samples
        chunk_index += 1

    if verbose:
        print(f"[ASR] 合計 {len(segments)} セグメント検出")

    return segments


def segments_to_json(segments: list[Segment], output_path: str | Path) -> Path:
    """セグメントをJSONファイルに保存する。"""
    output_path = Path(output_path)
    data = [asdict(s) for s in segments]
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
