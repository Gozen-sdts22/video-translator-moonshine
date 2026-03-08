"""メインパイプライン: 各モジュールを統合して字幕生成を実行する"""

from __future__ import annotations

from pathlib import Path

from subgen.asr import Segment
from subgen.config import Config


def run(
    video_path: str | Path,
    output_dir: str | Path | None = None,
    language: str = "ja",
    format: str = "ass",
    translate_to: str | None = None,
    translate_api: str = "deepl",
    num_speakers: str | int = "auto",
    verbose: bool = False,
) -> list[Path]:
    """字幕生成パイプラインを実行する。

    ① 音声抽出 → ② ASR → ③ 話者分離 → ④ 翻訳（オプション） → ⑤ 字幕ファイル生成

    Returns:
        生成されたファイルパスのリスト
    """
    from subgen.audio_extractor import extract_audio
    from subgen.asr import transcribe
    from subgen.diarization import diarize
    from subgen.subtitle_writer import generate_subtitles
    from subgen.translator import translate_segments

    video_path = Path(video_path)
    if output_dir is None:
        output_dir = video_path.parent
    else:
        output_dir = Path(output_dir)

    base_name = video_path.stem
    generated_files: list[Path] = []
    audio_path: Path | None = None

    try:
        # ① 音声抽出
        if verbose:
            print(f"\n{'='*50}")
            print(f"[Step 1/5] 音声抽出中...")
            print(f"{'='*50}")

        audio_path = extract_audio(video_path, verbose=verbose)

        # ② 音声認識（ASR）
        if verbose:
            print(f"\n{'='*50}")
            print(f"[Step 2/5] 音声認識中...")
            print(f"{'='*50}")

        segments = transcribe(audio_path, language=language, verbose=verbose)

        if not segments:
            print("[警告] 音声認識結果が空です。字幕を生成できません。")
            return []

        # ③ 話者分離
        if verbose:
            print(f"\n{'='*50}")
            print(f"[Step 3/5] 話者分離中...")
            print(f"{'='*50}")

        segments = diarize(
            audio_path, segments,
            num_speakers=num_speakers, verbose=verbose,
        )

        # ④ 翻訳（オプション）
        translated_segments: list[Segment] | None = None
        if translate_to:
            if verbose:
                print(f"\n{'='*50}")
                print(f"[Step 4/5] 翻訳中 ({language} → {translate_to})...")
                print(f"{'='*50}")

            translated_segments = translate_segments(
                segments,
                target_lang=translate_to,
                source_lang=language,
                api=translate_api,
                verbose=verbose,
            )
        elif verbose:
            print(f"\n[Step 4/5] 翻訳: スキップ")

        # ⑤ 字幕ファイル生成
        if verbose:
            print(f"\n{'='*50}")
            print(f"[Step 5/5] 字幕ファイル生成中...")
            print(f"{'='*50}")

        # 原文字幕
        files = generate_subtitles(
            segments, output_dir, base_name,
            language=language, format=format,
        )
        generated_files.extend(files)

        # 翻訳字幕
        if translated_segments:
            files = generate_subtitles(
                translated_segments, output_dir, base_name,
                language=translate_to, format=format,
            )
            generated_files.extend(files)

        if verbose:
            print(f"\n{'='*50}")
            print(f"完了！生成されたファイル:")
            for f in generated_files:
                print(f"  - {f}")
            print(f"{'='*50}")

        return generated_files

    finally:
        # 一時音声ファイルの削除
        if audio_path and audio_path.name.startswith("subgen_audio_") and audio_path.exists():
            audio_path.unlink()
