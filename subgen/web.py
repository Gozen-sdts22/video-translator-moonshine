"""Web UIバックエンド（Flask）"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

# ジョブ管理（インメモリ）
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "subgen_uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "subgen_outputs"


def _ensure_dirs():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _update_job(job_id: str, **kwargs):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _run_pipeline(job_id: str, video_path: Path, params: dict):
    """バックグラウンドでパイプラインを実行する。"""
    try:
        _update_job(job_id, status="processing", step="音声抽出中...")

        from subgen.audio_extractor import extract_audio
        from subgen.asr import Segment, transcribe
        from subgen.diarization import diarize
        from subgen.subtitle_writer import generate_subtitles
        from subgen.translator import translate_segments

        output_dir = OUTPUT_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = video_path.stem

        # ① 音声抽出
        audio_path = extract_audio(video_path, verbose=False)

        # ② ASR
        _update_job(job_id, step="音声認識中...")
        segments = transcribe(
            audio_path,
            language=params.get("language", "ja"),
            verbose=False,
        )

        if not segments:
            _update_job(job_id, status="error", error="音声認識結果が空です。")
            return

        # ③ 話者分離
        _update_job(job_id, step="話者分離中...")
        segments = diarize(
            audio_path,
            segments,
            num_speakers=params.get("num_speakers", "auto"),
            verbose=False,
        )

        # 一時音声ファイル削除
        if audio_path.name.startswith("subgen_audio_") and audio_path.exists():
            audio_path.unlink()

        # ④ 翻訳（オプション）
        translated_segments = None
        translate_to = params.get("translate_to")
        if translate_to:
            _update_job(job_id, step=f"翻訳中 ({params.get('language', 'ja')} → {translate_to})...")
            translated_segments = translate_segments(
                segments,
                target_lang=translate_to,
                source_lang=params.get("language", "ja"),
                api=params.get("translate_api", "deepl"),
                verbose=False,
            )

        # ⑤ 字幕生成
        _update_job(job_id, step="字幕ファイル生成中...")
        fmt = params.get("format", "ass")
        language = params.get("language", "ja")

        files = generate_subtitles(segments, output_dir, base_name, language=language, format=fmt)

        if translated_segments:
            files += generate_subtitles(
                translated_segments, output_dir, base_name,
                language=translate_to, format=fmt,
            )

        # セグメントデータもJSONで保存（プレビュー用）
        segments_data = []
        for seg in segments:
            segments_data.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "speaker": seg.speaker,
            })

        preview_data = {"original": segments_data}
        if translated_segments:
            preview_data["translated"] = [
                {"start": s.start, "end": s.end, "text": s.text, "speaker": s.speaker}
                for s in translated_segments
            ]

        file_names = [f.name for f in files]
        _update_job(
            job_id,
            status="completed",
            step="完了",
            files=file_names,
            preview=preview_data,
        )

    except Exception as e:
        _update_job(job_id, status="error", error=str(e))
    finally:
        # アップロードファイル削除
        if video_path.exists():
            try:
                video_path.unlink()
            except OSError:
                pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    """動画ファイルをアップロードしてジョブを開始する。"""
    _ensure_dirs()

    file = request.files.get("video")
    if not file or not file.filename:
        return jsonify({"error": "動画ファイルを選択してください"}), 400

    job_id = uuid.uuid4().hex[:12]
    safe_name = f"{job_id}_{file.filename}"
    video_path = UPLOAD_DIR / safe_name
    file.save(str(video_path))

    params = {
        "language": request.form.get("language", "ja"),
        "format": request.form.get("format", "ass"),
        "translate_to": request.form.get("translate_to") or None,
        "translate_api": request.form.get("translate_api", "deepl"),
        "num_speakers": request.form.get("num_speakers", "auto"),
    }

    # 話者数を数値に変換
    if params["num_speakers"] != "auto":
        try:
            params["num_speakers"] = int(params["num_speakers"])
        except ValueError:
            params["num_speakers"] = "auto"

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "step": "待機中...",
            "files": [],
            "error": None,
            "preview": None,
        }

    thread = threading.Thread(target=_run_pipeline, args=(job_id, video_path, params))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id: str):
    """ジョブのステータスを返す。"""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "ジョブが見つかりません"}), 404
    return jsonify(job)


@app.route("/api/download/<job_id>/<filename>")
def download(job_id: str, filename: str):
    """生成された字幕ファイルをダウンロードする。"""
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        return jsonify({"error": "ファイルが見つかりません"}), 404
    return send_file(str(file_path), as_attachment=True)


def main():
    """Web UIサーバーを起動する。"""
    import argparse

    parser = argparse.ArgumentParser(description="SubGen Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="ホスト (デフォルト: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="ポート (デフォルト: 5000)")
    parser.add_argument("--debug", action="store_true", help="デバッグモード")
    args = parser.parse_args()

    print(f"SubGen Web UI を起動中: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
