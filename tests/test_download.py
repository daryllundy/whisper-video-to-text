import subprocess
from unittest import mock

import pytest

from whisper_video_to_text import download
from whisper_video_to_text.errors import TranscriptionCancelled


def _completed_download(stdout="Destination: test.mp4\n"):
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


class _NeverFinishingPopen:
    def __init__(self):
        self.cmd = None
        self.returncode = None
        self.terminated = False
        self.killed = False
        self.constructions = 0

    def __call__(self, cmd, *args, **kwargs):
        self.cmd = cmd
        self.constructions += 1
        return self

    def communicate(self, timeout=None):
        raise subprocess.TimeoutExpired(self.cmd, timeout)

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_download_video_success(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    with mock.patch.object(download, "_run_yt_dlp", return_value=_completed_download()):
        filename = download.download_video(url, str(output_dir))
        assert filename == "test.mp4"


def test_download_video_prefers_progressive_mp4(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    with mock.patch.object(download, "_run_yt_dlp", return_value=_completed_download()) as run_mock:
        download.download_video(url, str(output_dir))

    cmd = run_mock.call_args.args[0]
    assert cmd[cmd.index("-f") + 1] == download.PROGRESSIVE_MP4_FORMAT


def test_download_video_falls_back_to_adaptive_format(tmp_path):
    url = "http://example.com/video"
    output_dir = tmp_path

    with mock.patch.object(
        download,
        "_run_yt_dlp",
        side_effect=[
            subprocess.CalledProcessError(1, "yt-dlp", stderr="HTTP Error 403: Forbidden"),
            _completed_download(),
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
    with mock.patch.object(
        download,
        "_run_yt_dlp",
        side_effect=subprocess.CalledProcessError(1, "yt-dlp"),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            download.download_video(url, str(output_dir))


def test_run_yt_dlp_terminates_process_on_cancel():
    fake = _NeverFinishingPopen()
    cancel_polls = 0

    def should_cancel():
        nonlocal cancel_polls
        cancel_polls += 1
        return cancel_polls >= 2

    with mock.patch.object(download.subprocess, "Popen", side_effect=fake):
        with pytest.raises(TranscriptionCancelled):
            download._run_yt_dlp(["yt-dlp"], should_cancel=should_cancel)

    assert fake.terminated


def test_run_yt_dlp_terminates_process_on_timeout():
    fake = _NeverFinishingPopen()

    with mock.patch.object(download.subprocess, "Popen", side_effect=fake):
        with pytest.raises(subprocess.TimeoutExpired):
            download._run_yt_dlp(["yt-dlp"], timeout=0.01)

    assert fake.terminated


def test_download_video_does_not_retry_cancelled_download(tmp_path):
    fake = _NeverFinishingPopen()
    cancel_polls = 0

    def should_cancel():
        nonlocal cancel_polls
        cancel_polls += 1
        return cancel_polls >= 2

    with mock.patch.object(download.subprocess, "Popen", side_effect=fake):
        with pytest.raises(TranscriptionCancelled):
            download.download_video(
                "http://example.com/video",
                str(tmp_path),
                should_cancel=should_cancel,
            )

    assert fake.constructions == 1


def test_pipeline_forwards_should_cancel_to_download(tmp_path):
    import whisper_video_to_text.pipeline as pipeline

    should_cancel = mock.Mock(return_value=False)
    downloaded_file = tmp_path / "downloaded.mp4"
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"fake audio")
    transcription = {"text": "done", "segments": [], "language": "en"}

    with (
        mock.patch.object(pipeline, "download_video", return_value=str(downloaded_file)) as spy,
        mock.patch.object(pipeline, "convert_media_to_whisper_audio", return_value=audio_file),
        mock.patch.object(pipeline, "transcribe_audio", return_value=transcription),
    ):
        pipeline.run_transcription(
            pipeline.TranscriptionRequest(
                source="http://example.com/video",
                download=True,
            ),
            should_cancel=should_cancel,
        )

    spy.assert_called_once_with(
        "http://example.com/video",
        output_dir=mock.ANY,
        should_cancel=should_cancel,
    )
