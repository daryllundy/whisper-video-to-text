"""Behavior tests for web upload handling."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_upload_file(filename: str) -> MagicMock:
    mock = MagicMock()
    mock.filename = filename
    mock.file = io.BytesIO(b"fake media content")
    return mock


def _run_task(job_id: str, file=None, url: str | None = None, formats=None, tmp_path=None):
    """Call run_transcription_task with progress captured in a list."""
    import whisper_video_to_text.web.views as views_mod

    progress_events: list[tuple] = []

    def fake_update(jid, pct, status, msg):
        progress_events.append((pct, status, msg))

    def fake_set_result(jid, result):
        progress_events.append(("result", result))

    with (
        patch.object(views_mod, "update_progress_sync", side_effect=fake_update),
        patch.object(views_mod, "set_result_sync", side_effect=fake_set_result),
    ):
        views_mod.run_transcription_task(
            job_id,
            file=file,
            url=url,
            formats=formats or ["txt"],
        )

    return progress_events


def test_upload_rejects_unsupported_extension(tmp_path):
    """Files with unsupported extensions are rejected before any disk write."""
    upload = _make_upload_file("video.avi")
    events = _run_task("job-bad-ext", file=upload, tmp_path=tmp_path)

    statuses = [e[1] for e in events]
    assert "error" in statuses
    error_msg = next(e[2] for e in events if e[1] == "error")
    assert ".avi" in error_msg
    assert "Supported" in error_msg


def test_upload_rejects_no_extension(tmp_path):
    """Files with no extension are rejected cleanly."""
    upload = _make_upload_file("noextension")
    events = _run_task("job-no-ext", file=upload, tmp_path=tmp_path)

    statuses = [e[1] for e in events]
    assert "error" in statuses


def test_upload_saved_with_job_scoped_name(tmp_path, monkeypatch):
    """Uploaded file is saved as uploads/{job_id}{suffix}, not the original filename."""
    import whisper_video_to_text.web.views as views_mod
    from whisper_video_to_text.pipeline import TranscriptionResult

    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads").mkdir()
    (tmp_path / "transcripts").mkdir()

    upload = _make_upload_file("my-video.mp4")
    captured_source: list[str] = []

    def fake_run(request, progress=None):
        captured_source.append(request.source)
        return TranscriptionResult(text="", language=None, segments=[], rendered={})

    with (
        patch.object(views_mod, "run_transcription", side_effect=fake_run),
        patch.object(views_mod, "update_progress_sync"),
        patch.object(views_mod, "set_result_sync"),
    ):
        views_mod.run_transcription_task("job-abc123", file=upload, formats=["txt"])

    assert len(captured_source) == 1
    saved_path = Path(captured_source[0])
    assert saved_path.name == "job-abc123.mp4"
    assert saved_path.parent.name == "uploads"


def test_upload_supported_extensions_accepted(tmp_path, monkeypatch):
    """All supported media extensions pass validation."""
    import whisper_video_to_text.web.views as views_mod
    from whisper_video_to_text.pipeline import TranscriptionResult

    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads").mkdir()
    (tmp_path / "transcripts").mkdir()

    for ext in [".mp3", ".wav", ".mp4", ".mov", ".aif", ".aiff"]:
        upload = _make_upload_file(f"file{ext}")

        with (
            patch.object(
                views_mod,
                "run_transcription",
                return_value=TranscriptionResult(text="", language=None, segments=[], rendered={}),
            ),
            patch.object(views_mod, "update_progress_sync"),
            patch.object(views_mod, "set_result_sync"),
        ):
            events = _run_task(f"job-{ext[1:]}", file=upload, tmp_path=tmp_path)

        statuses = [e[1] for e in events if isinstance(e[1], str)]
        assert "error" not in statuses, f"Extension {ext} was incorrectly rejected"
