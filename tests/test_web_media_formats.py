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


def test_web_task_uses_whisper_wav_converter():
    views = ROOT / "whisper_video_to_text" / "web" / "views.py"
    source = views.read_text(encoding="utf-8")

    assert "from whisper_video_to_text.convert import convert_media_to_whisper_audio" in source
    assert "convert_media_to_whisper_audio(" in source
    assert "convert_mp4_to_mp3" not in source
    assert 'Path(tempdir) / f"{Path(media_path).stem}-whisper.wav"' in source
