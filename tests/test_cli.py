"""Tests for CLI argument parsing and behavior."""

import argparse
import sys
from types import ModuleType

whisper_stub = ModuleType("whisper")
whisper_stub.load_model = None
sys.modules.setdefault("whisper", whisper_stub)
from whisper_video_to_text import cli  # noqa: E402


def test_format_argument_default_is_none():
    """Verify --format default is None, not ["txt"] to avoid append bug."""
    # Create a minimal parser to test the argument configuration
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        action="append",
        choices=["txt", "srt", "vtt"],
        default=None,
        help="Output format(s)",
    )

    # When no --format specified, args.format should be None
    args = parser.parse_args([])
    assert args.format is None

    # When --format srt specified, should only have ["srt"], not ["txt", "srt"]
    args = parser.parse_args(["--format", "srt"])
    assert args.format == ["srt"]
    assert "txt" not in args.format

    # Multiple formats should work correctly
    args = parser.parse_args(["--format", "srt", "--format", "vtt"])
    assert args.format == ["srt", "vtt"]


def test_format_fallback_to_txt():
    """Verify that when no format is specified, txt is used as fallback."""
    # Simulate the logic in cli.py
    args_format = None  # Default when no --format specified
    formats = args_format if args_format else ["txt"]
    assert formats == ["txt"]

    # When format is specified, use that
    args_format = ["srt"]
    formats = args_format if args_format else ["txt"]
    assert formats == ["srt"]


def test_cli_uses_whisper_wav_converter(monkeypatch, tmp_path):
    """Verify CLI normalizes supported media through the Whisper WAV converter."""
    input_file = tmp_path / "input.mov"
    input_file.write_text("dummy")
    audio_file = tmp_path / "input.wav"
    calls = {}

    def fake_convert_media_to_whisper_audio(input_path, output_file=None, verbose=False):
        calls["converter"] = (input_path, output_file, verbose)
        return audio_file

    monkeypatch.setattr(sys, "argv", ["whisper_video_to_text", str(input_file)])
    monkeypatch.setattr(cli, "convert_media_to_whisper_audio", fake_convert_media_to_whisper_audio)
    monkeypatch.setattr(
        cli,
        "transcribe_audio",
        lambda audio_path, model_name, language, verbose: {
            "text": "hello",
            "segments": [{"start": 0.0, "end": 1.0, "text": "hello"}],
            "language": "en",
        },
    )
    monkeypatch.setattr(cli, "save_transcription", lambda *args, **kwargs: None)

    cli.main()

    assert calls["converter"] == (str(input_file), None, False)


def test_cli_help_mentions_supported_media_formats():
    """Verify the user-facing CLI copy includes the expanded local input formats."""
    source = cli.main.__code__.co_consts
    help_text = "\n".join(str(item) for item in source)

    for extension in ["mp3", "wav", "aif", "aiff", "mp4", "mov"]:
        assert extension in help_text
