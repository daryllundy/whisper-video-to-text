import os

from fastapi.testclient import TestClient

from whisper_video_to_text.web.main import app


def test_history_empty_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    response = TestClient(app).get("/api/history")

    assert response.status_code == 200
    assert response.json() == []


def test_history_groups_jobs_and_formats(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    (transcripts_dir / "job-one.txt").write_text("one")
    (transcripts_dir / "job-one.srt").write_text("one")
    (transcripts_dir / "job-two.vtt").write_text("two")

    response = TestClient(app).get("/api/history")

    assert response.status_code == 200
    history = {item["job_id"]: item for item in response.json()}
    assert set(history) == {"job-one", "job-two"}
    assert set(history["job-one"]["formats"]) == {"txt", "srt"}
    assert history["job-two"]["formats"] == ["vtt"]


def test_history_orders_jobs_by_mtime_descending(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    older = transcripts_dir / "older.txt"
    newer = transcripts_dir / "newer.txt"
    older.write_text("older")
    newer.write_text("newer")
    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    response = TestClient(app).get("/api/history")

    assert response.status_code == 200
    assert [item["job_id"] for item in response.json()] == ["newer", "older"]


def test_history_ignores_non_transcript_files(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    (transcripts_dir / "notes.pdf").write_text("notes")
    (transcripts_dir / ".hidden.txt").write_text("hidden")

    response = TestClient(app).get("/api/history")

    assert response.status_code == 200
    assert response.json() == []
