from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from whisper_video_to_text.convert import SUPPORTED_MEDIA_EXTENSIONS
from whisper_video_to_text.web.main import app

ROOT = Path(__file__).parent.parent


def test_web_upload_accepts_supported_media_formats():
    response = TestClient(app).get("/")
    source = response.text

    assert response.status_code == 200
    assert "SOURCE MEDIA FILE" in source
    for extension in sorted(SUPPORTED_MEDIA_EXTENSIONS):
        assert extension in source
    assert "audio/*" in source
    assert "video/*" in source
    assert "audio/mpeg" in source
    assert "video/quicktime" in source


def test_web_page_exposes_drag_and_drop_upload_controls():
    response = TestClient(app).get("/")
    source = response.text

    assert response.status_code == 200
    assert 'id="drop-zone"' in source
    assert 'data-media-extensions="' in source
    assert 'id="drop-overlay"' in source
    assert "DROP MEDIA FILE" in source
    assert ".m4a" in source


def test_web_javascript_binds_drag_and_drop_events():
    source = (ROOT / "whisper_video_to_text" / "web" / "static" / "app.js").read_text(
        encoding="utf-8"
    )

    assert "function handleDrop" in source
    assert "selectMediaFile" in source
    assert "document.addEventListener('dragenter', handleDragEnter)" in source
    assert "document.addEventListener('drop', handleDrop)" in source


def test_pipeline_uses_whisper_wav_converter(monkeypatch, tmp_path):
    """Pipeline calls convert_media_to_whisper_audio (16 kHz WAV), not convert_mp4_to_mp3."""
    import whisper_video_to_text.pipeline as pipeline_mod

    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fake")
    audio_file = tmp_path / "audio-whisper.wav"
    audio_file.write_bytes(b"fake audio")

    converter_calls: list[str] = []

    def fake_convert(input_path: str, output_file: str | None = None, verbose: bool = False, **kwargs):
        converter_calls.append(input_path)
        return audio_file

    monkeypatch.setattr(pipeline_mod, "convert_media_to_whisper_audio", fake_convert)
    monkeypatch.setattr(
        pipeline_mod,
        "transcribe_audio",
        lambda *a, **kw: {"text": "hi", "segments": [], "language": "en"},
    )

    from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription

    run_transcription(TranscriptionRequest(source=str(input_file), formats=("txt",)))

    assert converter_calls == [str(input_file)]
