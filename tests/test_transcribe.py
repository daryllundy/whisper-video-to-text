from unittest import mock

import pytest

from whisper_video_to_text import transcribe


@pytest.fixture(autouse=True)
def _clear_model_cache():
    transcribe._model_cache.clear()
    yield
    transcribe._model_cache.clear()


def test_transcribe_audio_success(tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_text("dummy")

    mock_model = mock.Mock()
    mock_model.transcribe.return_value = {"text": "hello", "segments": [], "language": "en"}
    with mock.patch("whisper_video_to_text.transcribe.whisper.load_model", return_value=mock_model):
        result = transcribe.transcribe_audio(str(audio_file), model_name="base")
        assert result["text"] == "hello"
        assert result["language"] == "en"


def test_transcribe_audio_reuses_cached_model(tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_text("dummy")

    mock_model = mock.MagicMock()
    mock_model.transcribe.return_value = {"text": "", "segments": []}
    with mock.patch(
        "whisper_video_to_text.transcribe.whisper.load_model", return_value=mock_model
    ) as load_model:
        transcribe.transcribe_audio(str(audio_file), model_name="base")
        transcribe.transcribe_audio(str(audio_file), model_name="base")

    assert load_model.call_count == 1


def test_transcribe_audio_model_switch_evicts_cached_model(tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_text("dummy")

    mock_model = mock.MagicMock()
    mock_model.transcribe.return_value = {"text": "", "segments": []}
    with mock.patch(
        "whisper_video_to_text.transcribe.whisper.load_model", return_value=mock_model
    ) as load_model:
        transcribe.transcribe_audio(str(audio_file), model_name="base")
        transcribe.transcribe_audio(str(audio_file), model_name="small")

    assert load_model.call_count == 2
    assert list(transcribe._model_cache) == ["small"]


def test_transcribe_audio_missing_file(tmp_path):
    audio_file = tmp_path / "missing.mp3"
    with pytest.raises(FileNotFoundError):
        transcribe.transcribe_audio(str(audio_file))


def test_render_txt_with_timestamps():
    transcription = {
        "text": "hello world",
        "segments": [{"start": 0, "end": 2, "text": "hello world"}],
        "language": "en",
    }

    content = transcribe.render_txt(transcription, include_timestamps=True)

    assert content == "[0.00s] hello world"
