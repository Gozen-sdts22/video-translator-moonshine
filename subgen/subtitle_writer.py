"""F-005: 字幕ファイル生成モジュール（SRT / ASS）"""

from __future__ import annotations

from pathlib import Path

from subgen.asr import Segment

# ASS話者カラーパレット（BGR形式）
SPEAKER_COLORS = {
    "Speaker_1": "&H00FFFFFF",  # 白
    "Speaker_2": "&H0000FFFF",  # 黄
    "Speaker_3": "&H0000FF00",  # 緑
    "Speaker_4": "&H00FF8800",  # 水色
}

DEFAULT_FONT_JA = "Noto Sans JP"
DEFAULT_FONT_ZH = "Noto Sans SC"
DEFAULT_FONT_SIZE = 20


def _format_srt_time(seconds: float) -> str:
    """秒をSRT形式のタイムスタンプに変換する。"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    """秒をASS形式のタイムスタンプに変換する。"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_srt(
    segments: list[Segment],
    output_path: str | Path,
) -> Path:
    """SRT形式の字幕ファイルを生成する。

    Args:
        segments: 字幕セグメントリスト
        output_path: 出力ファイルパス

    Returns:
        出力ファイルパス
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        lines.append(seg.text)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_ass(
    segments: list[Segment],
    output_path: str | Path,
    language: str = "ja",
) -> Path:
    """ASS形式の字幕ファイルを生成する（話者色分け対応）。

    Args:
        segments: 字幕セグメントリスト
        output_path: 出力ファイルパス
        language: 言語コード（フォント選択に使用）

    Returns:
        出力ファイルパス
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font = DEFAULT_FONT_ZH if language == "zh" else DEFAULT_FONT_JA

    # 使用される話者を収集
    speakers = sorted({seg.speaker or "Speaker_1" for seg in segments})

    # ヘッダー
    header = f"""[Script Info]
Title: SubGen Generated Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""

    style_lines = []
    for speaker in speakers:
        color = SPEAKER_COLORS.get(speaker, "&H00FFFFFF")
        style_lines.append(
            f"Style: {speaker},{font},{DEFAULT_FONT_SIZE},{color},&H000000FF,&H00000000,&H80000000,"
            f"0,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1"
        )

    # デフォルトスタイル
    style_lines.append(
        f"Style: Default,{font},{DEFAULT_FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"0,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1"
    )

    # イベント
    events_header = """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    event_lines = []
    for seg in segments:
        style = seg.speaker or "Default"
        start = _format_ass_time(seg.start)
        end = _format_ass_time(seg.end)
        event_lines.append(
            f"Dialogue: 0,{start},{end},{style},,0,0,0,,{seg.text}"
        )

    content = header + "\n".join(style_lines) + events_header + "\n".join(event_lines) + "\n"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def generate_subtitles(
    segments: list[Segment],
    output_dir: str | Path,
    base_name: str,
    language: str = "ja",
    format: str = "ass",
) -> list[Path]:
    """指定形式で字幕ファイルを生成する。

    Args:
        segments: 字幕セグメントリスト
        output_dir: 出力先ディレクトリ
        base_name: ベースファイル名（拡張子なし）
        language: 言語コード
        format: 出力形式（"srt", "ass", "both"）

    Returns:
        生成されたファイルパスのリスト
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    if format in ("srt", "both"):
        srt_path = output_dir / f"{base_name}_{language}.srt"
        generate_srt(segments, srt_path)
        outputs.append(srt_path)

    if format in ("ass", "both"):
        ass_path = output_dir / f"{base_name}_{language}.ass"
        generate_ass(segments, ass_path, language)
        outputs.append(ass_path)

    return outputs
