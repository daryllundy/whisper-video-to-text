import subprocess
from unittest import mock

import pytest

from whisper_video_to_text import convert


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
