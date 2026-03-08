"""F-003: 話者分離モジュール（Speaker Diarization）"""

from __future__ import annotations

from pathlib import Path

from subgen.asr import Segment


def diarize(
    audio_path: str | Path,
    segments: list[Segment],
    num_speakers: int | str = "auto",
    verbose: bool = False,
) -> list[Segment]:
    """音声セグメントに話者IDを付与する。

    pyannote-audioを使用して話者分離を行い、各セグメントにspeaker IDを付与する。
    pyannote-audioが利用できない場合はシンプルなフォールバック処理を行う。

    Args:
        audio_path: 入力WAVファイルパス
        segments: ASRで得られたセグメントリスト
        num_speakers: 話者数（"auto"または整数）
        verbose: 詳細ログ出力

    Returns:
        話者IDが付与されたSegmentのリスト
    """
    audio_path = Path(audio_path)

    if not segments:
        return segments

    try:
        return _diarize_with_pyannote(audio_path, segments, num_speakers, verbose)
    except ImportError:
        if verbose:
            print("[話者分離] pyannote-audioが利用不可。エネルギーベースのフォールバックを使用します。")
        return _diarize_fallback(audio_path, segments, num_speakers, verbose)


def _diarize_with_pyannote(
    audio_path: Path,
    segments: list[Segment],
    num_speakers: int | str,
    verbose: bool,
) -> list[Segment]:
    """pyannote-audioを使用した話者分離。"""
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

    params = {}
    if num_speakers != "auto":
        params["num_speakers"] = int(num_speakers)

    if verbose:
        print("[話者分離] pyannote-audioで処理中...")

    diarization = pipeline(str(audio_path), **params)

    speaker_timeline: list[tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_timeline.append((turn.start, turn.end, speaker))

    for seg in segments:
        seg.speaker = _find_speaker(seg.start, seg.end, speaker_timeline)

    if verbose:
        speakers = {s.speaker for s in segments if s.speaker}
        print(f"[話者分離] {len(speakers)} 人の話者を検出")

    return segments


def _find_speaker(
    start: float, end: float, timeline: list[tuple[float, float, str]]
) -> str:
    """セグメントの時間範囲に最も重なる話者を返す。"""
    best_speaker = "Speaker_1"
    best_overlap = 0.0

    for t_start, t_end, speaker in timeline:
        overlap_start = max(start, t_start)
        overlap_end = min(end, t_end)
        overlap = max(0.0, overlap_end - overlap_start)

        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker

    # pyannoteのラベルをSpeaker_N形式に正規化
    if best_speaker.startswith("SPEAKER_"):
        num = int(best_speaker.split("_")[1]) + 1
        best_speaker = f"Speaker_{num}"
    elif not best_speaker.startswith("Speaker_"):
        best_speaker = f"Speaker_1"

    return best_speaker


def _diarize_fallback(
    audio_path: Path,
    segments: list[Segment],
    num_speakers: int | str,
    verbose: bool,
) -> list[Segment]:
    """pyannote-audioが利用できない場合のエネルギーベースの簡易フォールバック。

    音声のRMSエネルギー特徴を使い、セグメント間の類似度から
    簡易的にクラスタリングする。
    """
    import array
    import wave

    target_speakers = 2 if num_speakers == "auto" else int(num_speakers)

    if target_speakers == 1:
        for seg in segments:
            seg.speaker = "Speaker_1"
        return segments

    # WAVからセグメントごとのRMSエネルギーを計算
    try:
        with wave.open(str(audio_path), "rb") as wf:
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            samples = array.array("h", raw)
            if wf.getnchannels() == 2:
                samples = samples[::2]
    except Exception:
        # WAV読み込み失敗時は均等割り当て
        for i, seg in enumerate(segments):
            seg.speaker = f"Speaker_{(i % target_speakers) + 1}"
        return segments

    energies = []
    for seg in segments:
        start_sample = int(seg.start * framerate)
        end_sample = int(seg.end * framerate)
        start_sample = max(0, min(start_sample, len(samples) - 1))
        end_sample = max(start_sample + 1, min(end_sample, len(samples)))
        chunk = samples[start_sample:end_sample]
        rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5 if chunk else 0.0
        energies.append(rms)

    # エネルギーの中央値で二分割
    if energies:
        sorted_e = sorted(energies)
        median = sorted_e[len(sorted_e) // 2]
        for i, seg in enumerate(segments):
            if target_speakers == 2:
                seg.speaker = "Speaker_1" if energies[i] <= median else "Speaker_2"
            else:
                # N分割: エネルギーを均等にバケット分け
                if max(energies) == min(energies):
                    bucket = i % target_speakers
                else:
                    normalized = (energies[i] - min(energies)) / (max(energies) - min(energies))
                    bucket = min(int(normalized * target_speakers), target_speakers - 1)
                seg.speaker = f"Speaker_{bucket + 1}"

    if verbose:
        speakers = {s.speaker for s in segments if s.speaker}
        print(f"[話者分離] フォールバック: {len(speakers)} 人の話者に分類")

    return segments
