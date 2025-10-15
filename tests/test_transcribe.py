from unittest import mock

import pytest

from whisper_video_to_text import transcribe


def test_transcribe_audio_success(tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_text("dummy")

    mock_model = mock.Mock()
    mock_model.transcribe.return_value = {"text": "hello", "segments": [], "language": "en"}
    with mock.patch("whisper.load_model", return_value=mock_model):
        result = transcribe.transcribe_audio(str(audio_file), model_name="base")
        assert result["text"] == "hello"
        assert result["language"] == "en"


def test_transcribe_audio_missing_file(tmp_path):
    audio_file = tmp_path / "missing.mp3"
    with pytest.raises(FileNotFoundError):
        transcribe.transcribe_audio(str(audio_file))


def test_save_transcription(tmp_path):
    output_file = tmp_path / "out.txt"
    transcription = {
        "text": "hello world",
        "segments": [{"start": 0, "end": 2, "text": "hello world"}],
        "language": "en",
    }
    transcribe.save_transcription(transcription, str(output_file), include_timestamps=True)
    content = output_file.read_text()
    assert "hello world" in content
    assert "TRANSCRIPTION WITH TIMESTAMPS" in content
