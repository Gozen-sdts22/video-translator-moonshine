"""話者分離モジュールのテスト"""

import struct
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

from subgen.asr import Segment
from subgen.diarization import _diarize_fallback, _find_speaker, diarize


@pytest.fixture
def sample_segments():
    return [
        Segment(start=0.0, end=2.0, text="こんにちは"),
        Segment(start=2.5, end=4.0, text="お元気ですか"),
        Segment(start=4.5, end=6.0, text="元気です"),
    ]


@pytest.fixture
def wav_file(tmp_path):
    """テスト用のWAVファイルを生成する。"""
    path = tmp_path / "test.wav"
    sample_rate = 16000
    duration = 6  # 秒
    n_samples = sample_rate * duration

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # 前半は静か、後半は大きい音
        samples = []
        for i in range(n_samples):
            if i < n_samples // 2:
                samples.append(int(1000 * ((i % 100) / 100)))
            else:
                samples.append(int(10000 * ((i % 100) / 100)))
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return path


class TestFindSpeaker:
    def test_exact_match(self):
        timeline = [(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")]
        assert _find_speaker(0.0, 2.0, timeline) == "Speaker_1"

    def test_overlap_match(self):
        timeline = [(0.0, 3.0, "SPEAKER_00"), (3.0, 6.0, "SPEAKER_01")]
        assert _find_speaker(2.0, 4.0, timeline) == "Speaker_1"  # 0-3と重なりが大きい

    def test_empty_timeline(self):
        assert _find_speaker(0.0, 1.0, []) == "Speaker_1"


class TestDiarizeFallback:
    def test_single_speaker(self, wav_file, sample_segments):
        result = _diarize_fallback(wav_file, sample_segments, num_speakers=1, verbose=False)
        assert all(s.speaker == "Speaker_1" for s in result)

    def test_two_speakers(self, wav_file, sample_segments):
        result = _diarize_fallback(wav_file, sample_segments, num_speakers=2, verbose=False)
        speakers = {s.speaker for s in result}
        assert speakers.issubset({"Speaker_1", "Speaker_2"})

    def test_empty_segments(self, wav_file):
        result = _diarize_fallback(wav_file, [], num_speakers="auto", verbose=False)
        assert result == []


class TestDiarize:
    @patch("subgen.diarization._diarize_with_pyannote", side_effect=ImportError)
    def test_falls_back_when_pyannote_unavailable(self, mock_pyannote, wav_file, sample_segments):
        result = diarize(wav_file, sample_segments, num_speakers=2, verbose=False)
        assert len(result) == 3
        assert all(s.speaker is not None for s in result)
