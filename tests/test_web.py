"""Web UIモジュールのテスト"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from subgen.web import app, _jobs, _jobs_lock, OUTPUT_DIR


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clear_jobs():
    """テスト前後にジョブをクリアする。"""
    with _jobs_lock:
        _jobs.clear()
    yield
    with _jobs_lock:
        _jobs.clear()


class TestIndexPage:
    def test_index_returns_html(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"SubGen" in res.data
        assert b"text/html" in res.content_type.encode()


class TestUploadAPI:
    def test_no_file(self, client):
        res = client.post("/api/upload")
        assert res.status_code == 400
        data = json.loads(res.data)
        assert "error" in data

    def test_upload_starts_job(self, client, tmp_path):
        # パイプラインをモックしてジョブが作成されることを確認
        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake video data")

        with patch("subgen.web._run_pipeline"):
            res = client.post(
                "/api/upload",
                data={
                    "video": (open(str(video), "rb"), "test.mp4"),
                    "language": "ja",
                    "format": "ass",
                    "translate_to": "",
                    "translate_api": "deepl",
                    "num_speakers": "auto",
                },
                content_type="multipart/form-data",
            )

        assert res.status_code == 200
        data = json.loads(res.data)
        assert "job_id" in data
        job_id = data["job_id"]

        with _jobs_lock:
            assert job_id in _jobs
            assert _jobs[job_id]["status"] in ("queued", "processing")


class TestStatusAPI:
    def test_unknown_job(self, client):
        res = client.get("/api/status/nonexistent")
        assert res.status_code == 404

    def test_known_job(self, client):
        with _jobs_lock:
            _jobs["test123"] = {
                "status": "processing",
                "step": "音声認識中...",
                "files": [],
                "error": None,
                "preview": None,
            }

        res = client.get("/api/status/test123")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "processing"
        assert data["step"] == "音声認識中..."


class TestDownloadAPI:
    def test_missing_file(self, client):
        res = client.get("/api/download/fakejob/fake.srt")
        assert res.status_code == 404

    def test_download_existing_file(self, client):
        job_id = "dltest"
        job_dir = OUTPUT_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        test_file = job_dir / "test_ja.srt"
        test_file.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

        res = client.get(f"/api/download/{job_id}/test_ja.srt")
        assert res.status_code == 200
        assert b"Hello" in res.data

        # cleanup
        test_file.unlink()
        job_dir.rmdir()
