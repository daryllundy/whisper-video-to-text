import io
from unittest import mock

import pytest

from whisper_video_to_text import convert


class _FakePopen:
    """Minimal Popen stand-in that simulates an immediate, successful ffmpeg exit."""

    def __init__(self, returncode: int = 0, stderr_text: str = ""):
        self._returncode = returncode
        self.stderr = io.StringIO(stderr_text)
        self.terminated = False
        self.killed = False

    def __call__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.returncode = self._returncode
        return self

    def poll(self):
        return self._returncode

    def wait(self, timeout=None):
        return self._returncode

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


@pytest.mark.parametrize("suffix", sorted(convert.SUPPORTED_MEDIA_EXTENSIONS))
def test_convert_media_to_whisper_audio_supported_formats(tmp_path, suffix):
    input_file = tmp_path / f"input{suffix}"
    input_file.write_text("dummy")
    output_file = tmp_path / f"output-{suffix.lstrip('.')}.wav"

    fake = _FakePopen()
    with mock.patch("subprocess.Popen", side_effect=fake):
        result = convert.convert_media_to_whisper_audio(
            str(input_file), str(output_file), verbose=False
        )

    assert result == output_file


def test_requested_media_formats_are_supported():
    required_extensions = {".mp3", ".m4a", ".m4p", ".mp4", ".mov"}

    assert required_extensions.issubset(convert.SUPPORTED_MEDIA_EXTENSIONS)


def test_convert_media_to_whisper_audio_ffmpeg_command(tmp_path):
    input_file = tmp_path / "input.mov"
    input_file.write_text("dummy")
    output_file = tmp_path / "output.wav"

    fake = _FakePopen()
    with mock.patch("subprocess.Popen", side_effect=fake):
        convert.convert_media_to_whisper_audio(str(input_file), str(output_file), verbose=False)

    cmd = fake.cmd
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
    input_file = tmp_path / "input.txt"
    input_file.write_text("dummy")

    with pytest.raises(ValueError, match="Unsupported media format"):
        convert.convert_media_to_whisper_audio(str(input_file))


def test_convert_media_to_whisper_audio_default_wav_path_does_not_overwrite_input(tmp_path):
    input_file = tmp_path / "input.wav"
    input_file.write_text("dummy")

    with mock.patch("subprocess.Popen", side_effect=_FakePopen()):
        result = convert.convert_media_to_whisper_audio(str(input_file), verbose=False)

    assert result == tmp_path / "input-whisper.wav"
