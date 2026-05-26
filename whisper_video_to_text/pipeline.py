from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whisper_video_to_text.convert import convert_media_to_whisper_audio
from whisper_video_to_text.download import download_video
from whisper_video_to_text.errors import TranscriptionCancelled
from whisper_video_to_text.transcribe import (
    render_srt,
    render_txt,
    render_vtt,
    transcribe_audio,
)

__all__ = [
    "TranscriptionCancelled",
    "TranscriptionRequest",
    "TranscriptionResult",
    "run_transcription",
]


@dataclass
class TranscriptionRequest:
    source: str
    download: bool = False
    model: str = "base"
    language: str | None = None
    formats: tuple[str, ...] = ("txt",)
    include_timestamps: bool = False
    keep_audio: bool = False
    output_base: Path | None = None


@dataclass
class TranscriptionResult:
    text: str
    language: str | None
    segments: list[dict[str, Any]]
    rendered: dict[str, str]
    output_files: dict[str, Path] = field(default_factory=dict)


ProgressCallback = Callable[[int, str, str], None]
CancelCheck = Callable[[], bool]


def run_transcription(
    request: TranscriptionRequest,
    progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> TranscriptionResult:
    """Orchestrate download → convert → transcribe → render for both CLI and web."""

    def report(pct: int, status: str, msg: str) -> None:
        if progress:
            progress(pct, status, msg)

    def check_cancelled() -> None:
        if should_cancel and should_cancel():
            raise TranscriptionCancelled()

    tempdir = tempfile.mkdtemp(prefix="wvttmp_")
    try:
        # Acquire source media
        media_path = request.source
        if request.download:
            check_cancelled()
            report(10, "downloading", "Downloading video...")
            media_path = download_video(request.source, output_dir=tempdir)

        # Normalize to 16 kHz mono WAV
        check_cancelled()
        report(30, "converting", "Extracting audio...")
        audio_out = Path(tempdir) / f"{Path(media_path).stem}-whisper.wav"
        audio_path = convert_media_to_whisper_audio(
            media_path, output_file=str(audio_out), should_cancel=should_cancel
        )

        # Transcribe (blocking; cancellation only takes effect after it returns)
        check_cancelled()
        report(60, "transcribing", "Transcribing audio...")
        result = transcribe_audio(
            str(audio_path), model_name=request.model, language=request.language
        )

        # Render requested formats
        check_cancelled()
        report(90, "saving", "Preparing output...")
        rendered: dict[str, str] = {}
        for fmt in request.formats:
            if fmt == "txt":
                rendered["txt"] = render_txt(result, include_timestamps=request.include_timestamps)
            elif fmt == "srt":
                rendered["srt"] = render_srt(result)
            elif fmt == "vtt":
                rendered["vtt"] = render_vtt(result)

        # Write output files
        output_files: dict[str, Path] = {}
        if request.output_base:
            for fmt, content in rendered.items():
                out = request.output_base.with_suffix(f".{fmt}")
                out.write_text(content, encoding="utf-8")
                output_files[fmt] = out

            if request.keep_audio:
                wav_dest = request.output_base.with_suffix(".wav")
                shutil.copy2(str(audio_path), str(wav_dest))

        return TranscriptionResult(
            text=result.get("text", ""),
            language=result.get("language"),
            segments=result.get("segments", []),
            rendered=rendered,
            output_files=output_files,
        )
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
