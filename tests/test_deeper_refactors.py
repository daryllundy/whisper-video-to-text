"""Tests for deeper refactor tasks from PROJECT_IMPROVEMENTS.md.

These tests verify that all 5 deeper refactor tasks have been implemented correctly:
1. Sync/async cleanup in run_transcription_task
2. formats/timestamps implementation in web API
3. CLI output directory change
4. ffmpeg-python optional dependency handling
5. Type hints in web module
"""

import asyncio
import inspect
from pathlib import Path
from typing import get_type_hints
from unittest import mock

import pytest


class TestSyncAsyncCleanup:
    """Test that run_transcription_task is fully synchronous."""

    def test_run_transcription_task_has_no_async_wrapper(self):
        """Verify the function doesn't use asyncio.run internally."""
        # Read the source file directly to avoid FastAPI import issues
        import pathlib
        views_path = pathlib.Path(__file__).parent.parent / "whisper_video_to_text" / "web" / "views.py"
        source = views_path.read_text()
        
        # The function should not use asyncio.run internally
        # Find the run_transcription_task function and check it doesn't contain asyncio.run
        assert "def run_transcription_task(" in source
        # asyncio.run should not appear after the function definition
        func_start = source.find("def run_transcription_task(")
        func_section = source[func_start:func_start + 3000]  # Get the function body
        assert "asyncio.run" not in func_section, "asyncio.run should not be used inside run_transcription_task"

    def test_progress_sync_functions_exist(self):
        """Verify sync helper functions exist in progress module."""
        from whisper_video_to_text.web import progress

        assert hasattr(progress, "update_progress_sync")
        assert hasattr(progress, "set_result_sync")
        assert callable(progress.update_progress_sync)
        assert callable(progress.set_result_sync)

    def test_views_uses_sync_progress_functions(self):
        """Verify views.py uses sync versions of progress updates."""
        import pathlib
        views_path = pathlib.Path(__file__).parent.parent / "whisper_video_to_text" / "web" / "views.py"
        source = views_path.read_text()
        
        assert "update_progress_sync" in source
        assert "set_result_sync" in source
        # Should not use async versions in the sync function
        assert "await update_progress" not in source
        assert "await set_result" not in source


class TestFormatsTimestampsImplementation:
    """Test that formats and timestamps params are actually implemented."""

    def test_run_transcription_task_uses_formats_param(self):
        """Verify formats parameter is used in the function."""
        import pathlib
        views_path = pathlib.Path(__file__).parent.parent / "whisper_video_to_text" / "web" / "views.py"
        source = views_path.read_text()
        
        # Check that formats are processed
        assert '"srt" in formats' in source or "'srt' in formats" in source
        assert '"vtt" in formats' in source or "'vtt' in formats" in source

    def test_run_transcription_task_uses_timestamps_param(self):
        """Verify timestamps parameter is used in the function."""
        import pathlib
        views_path = pathlib.Path(__file__).parent.parent / "whisper_video_to_text" / "web" / "views.py"
        source = views_path.read_text()
        
        assert "timestamps" in source
        # Should check timestamps condition
        assert "if timestamps" in source

    def test_format_time_functions_exist_in_transcribe(self):
        """Verify SRT/VTT time formatting functions exist in transcribe module."""
        from whisper_video_to_text import transcribe
        
        # The shared _format_time helper should exist
        assert hasattr(transcribe, "_format_time")
        assert hasattr(transcribe, "_format_srt_time")
        assert hasattr(transcribe, "_format_vtt_time")

    def test_format_srt_time_output(self):
        """Test SRT time formatting from transcribe module."""
        from whisper_video_to_text.transcribe import _format_srt_time

        # Test basic formatting
        assert _format_srt_time(0) == "00:00:00,000"
        assert _format_srt_time(1.5) == "00:00:01,500"
        assert _format_srt_time(3661.123) == "01:01:01,123"

    def test_format_vtt_time_output(self):
        """Test VTT time formatting from transcribe module."""
        from whisper_video_to_text.transcribe import _format_vtt_time

        # Test basic formatting - VTT uses . instead of ,
        assert _format_vtt_time(0) == "00:00:00.000"
        assert _format_vtt_time(1.5) == "00:00:01.500"
        assert _format_vtt_time(3661.123) == "01:01:01.123"

    def test_shared_format_time_helper(self):
        """Test the shared _format_time helper with configurable separator."""
        from whisper_video_to_text.transcribe import _format_time

        # Default (SRT style with comma)
        assert _format_time(0) == "00:00:00,000"
        # VTT style with period
        assert _format_time(0, ".") == "00:00:00.000"
        # Custom separator
        assert _format_time(61.5, ":") == "00:01:01:500"


class TestCliOutputDirectory:
    """Test that CLI default output is video's parent directory."""

    def test_cli_source_uses_video_parent_directory(self):
        """Verify CLI uses video_path.parent instead of ~/research."""
        from whisper_video_to_text import cli

        source = inspect.getsource(cli.main)
        # Should NOT have ~/research
        assert 'Path.home() / "research"' not in source
        assert "research_dir" not in source
        # Should use video_path.parent
        assert "video_path.parent" in source
        assert "video_path.stem" in source

    def test_output_includes_video_stem_in_filename(self):
        """Verify output filename includes the video's stem."""
        from whisper_video_to_text import cli

        source = inspect.getsource(cli.main)
        # Should include video stem in output filename
        assert "video_path.stem" in source


class TestFfmpegOptionalDependency:
    """Test ffmpeg-python optional dependency handling."""

    def test_has_ffmpeg_python_flag_exists(self):
        """Verify HAS_FFMPEG_PYTHON flag exists at module level."""
        from whisper_video_to_text import convert

        assert hasattr(convert, "HAS_FFMPEG_PYTHON")
        assert isinstance(convert.HAS_FFMPEG_PYTHON, bool)

    def test_ffmpeg_import_at_module_level(self):
        """Verify ffmpeg is imported at module level, not inside function."""
        from whisper_video_to_text import convert

        source = inspect.getsource(convert)
        # Find the function source
        func_source = inspect.getsource(convert.convert_mp4_to_mp3)

        # ffmpeg import should be at module level, not in function
        assert "import ffmpeg" in source
        # The function should use the flag, not import ffmpeg
        assert "import ffmpeg" not in func_source
        assert "HAS_FFMPEG_PYTHON" in func_source


class TestWebModuleTypeHints:
    """Test that web module functions have type hints."""

    def test_progress_functions_have_type_hints(self):
        """Verify progress.py functions have type annotations."""
        from whisper_video_to_text.web import progress

        # Check return type hints
        hints = get_type_hints(progress.create_job)
        assert "return" in hints

        hints = get_type_hints(progress.get_job)
        assert "return" in hints

    def test_views_has_type_hints_in_source(self):
        """Verify views.py has type hints (checking source to avoid FastAPI import issues)."""
        import pathlib
        views_path = pathlib.Path(__file__).parent.parent / "whisper_video_to_text" / "web" / "views.py"
        source = views_path.read_text()
        
        # Check that run_transcription_task has type hints
        assert "def run_transcription_task(" in source
        assert "job_id: str" in source
        assert ") -> None:" in source

    def test_main_has_type_hints_in_source(self):
        """Verify main.py has type hints (checking source to avoid FastAPI import issues)."""
        import pathlib
        main_path = pathlib.Path(__file__).parent.parent / "whisper_video_to_text" / "web" / "main.py"
        source = main_path.read_text()
        
        # Check that index has type hints
        assert "async def index(request: Request) -> HTMLResponse:" in source

    def test_job_state_has_type_hints(self):
        """Verify JobState class attributes are typed."""
        from whisper_video_to_text.web.progress import JobState

        job = JobState()
        # Verify attributes exist with expected types
        assert isinstance(job.progress, int)
        assert isinstance(job.status, str)
        assert isinstance(job.message, str)

