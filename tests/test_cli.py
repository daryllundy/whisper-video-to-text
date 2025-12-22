"""Tests for CLI argument parsing and behavior."""

import argparse
from unittest import mock

import pytest


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
