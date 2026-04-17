import subprocess
from unittest import mock

import pytest

from whisper_video_to_text import convert


@pytest.mark.parametrize("suffix", [".mp3", ".wav", ".aif", ".aiff", ".mp4", ".mov"])
def test_convert_media_to_whisper_audio_supported_formats(tmp_path, suffix):
    input_file = tmp_path / f"input{suffix}"
    input_file.write_text("dummy")
    output_file = tmp_path / f"output-{suffix.lstrip('.')}.wav"

    with mock.patch("subprocess.run") as mock_run:
        result = convert.convert_media_to_whisper_audio(
            str(input_file), str(output_file), verbose=False
        )

    assert result == output_file
    mock_run.assert_called_once()


def test_convert_media_to_whisper_audio_ffmpeg_command(tmp_path):
    input_file = tmp_path / "input.mov"
    input_file.write_text("dummy")
    output_file = tmp_path / "output.wav"

    with mock.patch("subprocess.run") as mock_run:
        convert.convert_media_to_whisper_audio(str(input_file), str(output_file), verbose=False)

    cmd = mock_run.call_args.args[0]
    assert cmd[:3] == ["ffmpeg", "-loglevel", "error"]
    assert "-vn" in cmd
    assert cmd[cmd.index("-ac") + 1] == "1"
    assert cmd[cmd.index("-ar") + 1] == "16000"
    assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"
    assert cmd[-1] == str(output_file)


def test_convert_media_to_whisper_audio_missing_file(tmp_path):
    input_file = tmp_path / "missing.wav"

    with pytest.raises(FileNotFoundError):
        convert.convert_media_to_whisper_audio(str(input_file))


def test_convert_media_to_whisper_audio_unsupported_format(tmp_path):
    input_file = tmp_path / "input.flac"
    input_file.write_text("dummy")

    with pytest.raises(ValueError, match="Unsupported media format"):
        convert.convert_media_to_whisper_audio(str(input_file))


def test_convert_media_to_whisper_audio_default_wav_path_does_not_overwrite_input(tmp_path):
    input_file = tmp_path / "input.wav"
    input_file.write_text("dummy")

    with mock.patch("subprocess.run"):
        result = convert.convert_media_to_whisper_audio(str(input_file), verbose=False)

    assert result == tmp_path / "input-whisper.wav"


def test_convert_mp4_to_mp3_success(tmp_path):
    input_file = tmp_path / "input.mp4"
    input_file.write_text("dummy")  # create dummy file

    output_file = tmp_path / "output.mp3"

    with mock.patch("subprocess.run") as mock_run:
        result = convert.convert_mp4_to_mp3(str(input_file), str(output_file), verbose=False)
        assert result == output_file
        mock_run.assert_called_once()


def test_convert_mp4_to_mp3_missing_file(tmp_path):
    input_file = tmp_path / "missing.mp4"
    with pytest.raises(FileNotFoundError):
        convert.convert_mp4_to_mp3(str(input_file))


def test_convert_mp4_to_mp3_failure(tmp_path):
    input_file = tmp_path / "input.mp4"
    input_file.write_text("dummy")
    output_file = tmp_path / "output.mp3"

    with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg")):
        with pytest.raises(subprocess.CalledProcessError):
            convert.convert_mp4_to_mp3(str(input_file), str(output_file))
