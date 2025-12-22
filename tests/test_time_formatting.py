"""Tests for time formatting utilities - no whisper dependency required."""

import sys
from unittest import mock

# Mock whisper before importing transcribe module
sys.modules["whisper"] = mock.MagicMock()


def test_format_time_helper():
    """Test the shared _format_time helper with different separators."""
    from whisper_video_to_text.transcribe import _format_time

    # Test basic case
    assert _format_time(0.0, ",") == "00:00:00,000"
    assert _format_time(0.0, ".") == "00:00:00.000"

    # Test with minutes and seconds
    assert _format_time(65.5, ",") == "00:01:05,500"
    assert _format_time(65.5, ".") == "00:01:05.500"

    # Test with hours
    assert _format_time(3661.123, ",") == "01:01:01,123"
    assert _format_time(3661.123, ".") == "01:01:01.123"


def test_format_srt_time():
    """Test SRT time formatting uses comma separator."""
    from whisper_video_to_text.transcribe import _format_srt_time

    assert _format_srt_time(0.0) == "00:00:00,000"
    assert _format_srt_time(125.456) == "00:02:05,456"


def test_format_vtt_time():
    """Test VTT time formatting uses dot separator."""
    from whisper_video_to_text.transcribe import _format_vtt_time

    assert _format_vtt_time(0.0) == "00:00:00.000"
    assert _format_vtt_time(125.456) == "00:02:05.456"


def test_srt_vtt_use_shared_helper():
    """Verify SRT and VTT formatters produce different output for same input."""
    from whisper_video_to_text.transcribe import _format_srt_time, _format_vtt_time

    time_val = 90.5

    srt_result = _format_srt_time(time_val)
    vtt_result = _format_vtt_time(time_val)

    # Both should have same time, different separator
    assert srt_result == "00:01:30,500"
    assert vtt_result == "00:01:30.500"
    assert srt_result.replace(",", ".") == vtt_result
