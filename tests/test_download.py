import subprocess
from unittest import mock

import pytest

from whisper_video_to_text import download


def test_download_video_success(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    # Mock subprocess.run to simulate yt-dlp output
    mock_result = mock.Mock()
    mock_result.stdout = "Destination: test.mp4\n"
    with mock.patch("subprocess.run", return_value=mock_result):
        filename = download.download_video(url, str(output_dir))
        assert filename == "test.mp4"


def test_download_video_prefers_progressive_mp4(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    mock_result = mock.Mock()
    mock_result.stdout = "Destination: test.mp4\n"
    with mock.patch("subprocess.run", return_value=mock_result) as run_mock:
        download.download_video(url, str(output_dir))

    cmd = run_mock.call_args.args[0]
    assert cmd[cmd.index("-f") + 1] == download.PROGRESSIVE_MP4_FORMAT


def test_download_video_falls_back_to_adaptive_format(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    mock_result = mock.Mock()
    mock_result.stdout = "Destination: test.mp4\n"
    with mock.patch(
        "subprocess.run",
        side_effect=[
            subprocess.CalledProcessError(1, "yt-dlp", stderr="HTTP Error 403: Forbidden"),
            mock_result,
        ],
    ) as run_mock:
        filename = download.download_video(url, str(output_dir))

    assert filename == "test.mp4"
    assert run_mock.call_count == 2
    fallback_cmd = run_mock.call_args.args[0]
    assert fallback_cmd[fallback_cmd.index("-f") + 1] == download.ADAPTIVE_FORMAT


def test_download_video_failure(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    # Simulate yt-dlp failure
    with mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "yt-dlp")):
        with pytest.raises(subprocess.CalledProcessError):
            download.download_video(url, str(output_dir))
