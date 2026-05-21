from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_web_upload_accepts_supported_media_formats():
    template = ROOT / "whisper_video_to_text" / "web" / "templates" / "index.html"
    source = template.read_text(encoding="utf-8")

    assert "SOURCE MEDIA FILE" in source
    for extension in [".mp3", ".wav", ".aif", ".aiff", ".mp4", ".mov"]:
        assert extension in source
    assert "audio/mpeg" in source
    assert "video/quicktime" in source


def test_pipeline_uses_whisper_wav_converter(monkeypatch, tmp_path):
    """Pipeline calls convert_media_to_whisper_audio (16 kHz WAV), not convert_mp4_to_mp3."""
    import whisper_video_to_text.pipeline as pipeline_mod

    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"fake")
    audio_file = tmp_path / "audio-whisper.wav"
    audio_file.write_bytes(b"fake audio")

    converter_calls: list[str] = []

    def fake_convert(input_path: str, output_file: str | None = None, verbose: bool = False):
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
