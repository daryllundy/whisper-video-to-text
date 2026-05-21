"""Behavior tests for the shared transcription pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

FAKE_TRANSCRIPTION = {
    "text": "Hello world",
    "segments": [{"start": 0.0, "end": 1.5, "text": " Hello world"}],
    "language": "en",
}


@pytest.fixture()
def patched_pipeline(monkeypatch, tmp_path):
    """Patch pipeline's external calls; return (tmp_path, audio_file)."""
    import whisper_video_to_text.pipeline as pm

    audio_file = tmp_path / "audio-whisper.wav"
    audio_file.write_bytes(b"fake audio")

    monkeypatch.setattr(pm, "convert_media_to_whisper_audio", lambda *a, **kw: audio_file)
    monkeypatch.setattr(pm, "transcribe_audio", lambda *a, **kw: FAKE_TRANSCRIPTION)
    return tmp_path, audio_file


def make_input(tmp_path: Path) -> Path:
    f = tmp_path / "input.mp4"
    f.write_bytes(b"fake")
    return f


def test_pipeline_returns_plain_text(patched_pipeline):
    tmp_path, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    result = run_transcription(TranscriptionRequest(source=str(make_input(tmp_path))))
    assert result.text == "Hello world"
    assert result.language == "en"
    assert result.rendered["txt"] == "Hello world"


def test_pipeline_renders_all_formats(patched_pipeline):
    tmp_path, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    result = run_transcription(
        TranscriptionRequest(source=str(make_input(tmp_path)), formats=("txt", "srt", "vtt"))
    )
    assert "txt" in result.rendered
    assert "-->" in result.rendered["srt"]
    assert "00:00:00,000" in result.rendered["srt"]
    assert "WEBVTT" in result.rendered["vtt"]
    assert "00:00:00.000" in result.rendered["vtt"]


def test_pipeline_txt_with_timestamps(patched_pipeline):
    tmp_path, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    result = run_transcription(
        TranscriptionRequest(
            source=str(make_input(tmp_path)),
            formats=("txt",),
            include_timestamps=True,
        )
    )
    assert "[0.00s]" in result.rendered["txt"]
    assert "Hello world" in result.rendered["txt"]


def test_pipeline_writes_output_files(patched_pipeline, tmp_path):
    _, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    source = make_input(tmp_path)
    output_base = tmp_path / "out"
    result = run_transcription(
        TranscriptionRequest(
            source=str(source),
            formats=("txt", "srt"),
            output_base=output_base,
        )
    )
    assert (tmp_path / "out.txt").exists()
    assert (tmp_path / "out.srt").exists()
    assert result.output_files["txt"] == tmp_path / "out.txt"
    assert result.output_files["srt"] == tmp_path / "out.srt"


def test_pipeline_progress_callback(patched_pipeline):
    tmp_path, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    events: list[tuple[int, str, str]] = []
    run_transcription(
        TranscriptionRequest(source=str(make_input(tmp_path))),
        progress=lambda pct, status, msg: events.append((pct, status, msg)),
    )
    statuses = [e[1] for e in events]
    assert "converting" in statuses
    assert "transcribing" in statuses
    assert "saving" in statuses


def test_pipeline_no_output_base_skips_file_writing(patched_pipeline, tmp_path):
    _, _ = patched_pipeline
    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    result = run_transcription(
        TranscriptionRequest(source=str(make_input(tmp_path)), output_base=None)
    )
    assert result.output_files == {}
