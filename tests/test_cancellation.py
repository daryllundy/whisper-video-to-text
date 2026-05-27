"""Behavior tests for transcription cancellation (pipeline + ffmpeg + web)."""

from __future__ import annotations

import io
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from whisper_video_to_text import convert
from whisper_video_to_text.errors import TranscriptionCancelled

FAKE_TRANSCRIPTION = {
    "text": "Hello world",
    "segments": [{"start": 0.0, "end": 1.5, "text": " Hello world"}],
    "language": "en",
}


@pytest.fixture()
def patched_pipeline(monkeypatch, tmp_path):
    """Same pattern as test_pipeline: patch the heavy steps with cheap fakes."""
    import whisper_video_to_text.pipeline as pm

    audio_file = tmp_path / "input-whisper.wav"
    audio_file.write_bytes(b"fake audio")

    monkeypatch.setattr(pm, "convert_media_to_whisper_audio", lambda *a, **kw: audio_file)
    monkeypatch.setattr(pm, "transcribe_audio", lambda *a, **kw: FAKE_TRANSCRIPTION)
    return tmp_path, audio_file


def _make_input(tmp_path: Path) -> Path:
    f = tmp_path / "input.mp4"
    f.write_bytes(b"fake")
    return f


# ---------------------------------------------------------------------------
# pipeline.run_transcription cancellation
# ---------------------------------------------------------------------------


def test_pipeline_raises_when_cancelled_before_convert(patched_pipeline):
    tmp_path, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    with pytest.raises(TranscriptionCancelled):
        run_transcription(
            TranscriptionRequest(source=str(_make_input(tmp_path))),
            should_cancel=lambda: True,
        )


def test_pipeline_skips_output_writes_when_cancelled_after_transcribe(patched_pipeline, tmp_path):
    """If cancel fires after transcribe but before rendering, no output files appear."""
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    # Pipeline polls should_cancel before convert, transcribe, and render.
    # Cancel on the 3rd poll so we make it past transcribe but bail before writing.
    calls = {"n": 0}

    def should_cancel():
        calls["n"] += 1
        return calls["n"] >= 3

    output_base = tmp_path / "out"
    with pytest.raises(TranscriptionCancelled):
        run_transcription(
            TranscriptionRequest(
                source=str(_make_input(tmp_path)),
                formats=("txt",),
                output_base=output_base,
            ),
            should_cancel=should_cancel,
        )

    assert not (tmp_path / "out.txt").exists()


# ---------------------------------------------------------------------------
# convert._run_ffmpeg cancellation
# ---------------------------------------------------------------------------


class _SlowFakePopen:
    """Popen stand-in that 'runs' until cancellation terminates it."""

    def __init__(self):
        self.stderr = io.StringIO("")
        self.returncode = None
        self.terminated = False
        self.killed = False
        self._terminate_time = None

    def __call__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        return self

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_run_ffmpeg_terminates_process_on_cancel(tmp_path, monkeypatch):
    """When should_cancel becomes True, ffmpeg is terminated and partial output removed."""
    fake = _SlowFakePopen()
    partial = tmp_path / "partial.wav"
    partial.write_bytes(b"incomplete")

    # Speed up the poll loop's sleep so the test doesn't hang.
    monkeypatch.setattr(convert.time, "sleep", lambda s: None)

    cancel_state = {"flag": False}

    def should_cancel():
        cancel_state["flag"] = True
        return True

    with mock.patch("subprocess.Popen", side_effect=fake):
        with pytest.raises(TranscriptionCancelled):
            convert._run_ffmpeg(
                ["ffmpeg", "-y", str(partial)],
                duration=None,
                should_cancel=should_cancel,
                output_path=partial,
            )

    assert fake.terminated
    assert not partial.exists()


def test_run_ffmpeg_no_cancel_completes_cleanly(tmp_path):
    """When should_cancel is None, _run_ffmpeg returns normally on success."""

    class OkPopen:
        def __init__(self, cmd, *a, **kw):
            self.cmd = cmd
            self.stderr = io.StringIO("")
            self.returncode = 0

        def poll(self):
            return 0

        def wait(self, timeout=None):
            return 0

    with mock.patch("subprocess.Popen", side_effect=OkPopen):
        convert._run_ffmpeg(["ffmpeg"], duration=None, should_cancel=None, output_path=None)


# ---------------------------------------------------------------------------
# /api/jobs/{job_id}/cancel endpoint
# ---------------------------------------------------------------------------


def _client_with_clean_jobs():
    """Return a TestClient with an empty job registry."""
    from whisper_video_to_text.web import progress as progress_mod
    from whisper_video_to_text.web.main import app

    progress_mod.jobs.clear()
    return TestClient(app)


def test_cancel_endpoint_returns_404_for_unknown_job():
    client = _client_with_clean_jobs()
    resp = client.post("/api/jobs/does-not-exist/cancel")
    assert resp.status_code == 404


def test_cancel_endpoint_marks_active_job():
    from whisper_video_to_text.web.progress import create_job, is_cancel_requested

    client = _client_with_clean_jobs()
    job_id = create_job()

    resp = client.post(f"/api/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancel_requested"
    assert is_cancel_requested(job_id)


def test_cancel_endpoint_on_terminal_job_returns_current_state():
    from whisper_video_to_text.web.progress import create_job, get_job

    client = _client_with_clean_jobs()
    job_id = create_job()
    job = get_job(job_id)
    assert job is not None
    job.status = "complete"

    resp = client.post(f"/api/jobs/{job_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "complete"


def test_run_transcription_task_emits_cancelled_progress(tmp_path, monkeypatch):
    """When cancellation is requested mid-task, the worker emits a 'cancelled' update."""
    import whisper_video_to_text.web.views as views_mod
    from whisper_video_to_text.errors import TranscriptionCancelled

    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads").mkdir()
    (tmp_path / "transcripts").mkdir()

    progress_events: list[tuple] = []

    def fake_update(jid, pct, status, msg):
        progress_events.append((status, msg))

    def fake_cancelled(jid, message="Cancelled by user"):
        progress_events.append(("cancelled", message))

    def raising_run(request, progress=None, should_cancel=None):
        raise TranscriptionCancelled()

    mock_file = mock.MagicMock()
    mock_file.filename = "clip.mp3"
    mock_file.file = io.BytesIO(b"fake")

    with (
        mock.patch.object(views_mod, "update_progress_sync", side_effect=fake_update),
        mock.patch.object(views_mod, "set_cancelled_sync", side_effect=fake_cancelled),
        mock.patch.object(views_mod, "run_transcription", side_effect=raising_run),
    ):
        views_mod.run_transcription_task("job-xyz", file=mock_file, formats=["txt"])

    statuses = [e[0] for e in progress_events]
    assert "cancelled" in statuses
