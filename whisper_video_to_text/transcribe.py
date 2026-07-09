import logging
import threading
from pathlib import Path
from typing import Any, Optional

import whisper

_model_cache_lock = threading.Lock()
_model_cache: "dict[str, Any]" = {}  # holds at most one entry: {model_name: model}


def _load_model_cached(model_name: str) -> Any:
    """Return the Whisper model, loading it once and evicting on model switch.

    Single-entry by design: switching models drops the previous one so peak
    memory stays bounded to one loaded model.
    """
    with _model_cache_lock:
        if model_name in _model_cache:
            return _model_cache[model_name]
        _model_cache.clear()
        logging.info(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)
        _model_cache[model_name] = model
        return model


def transcribe_audio(
    audio_file: str, model_name: str = "base", language: Optional[str] = None, verbose: bool = False
) -> dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper.

    Args:
        audio_file: Path to the audio file.
        model_name: Whisper model to use.
        language: Language code (optional).
        verbose: If True, show detailed output.

    Returns:
        Transcription result as a dictionary.
    """
    audio_path = Path(audio_file)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    model = _load_model_cached(model_name)

    logging.info(f"Transcribing {audio_path.name}...")

    result = model.transcribe(str(audio_path), language=language, verbose=verbose, fp16=False)

    logging.info("✓ Transcription complete")
    return result


def render_txt(transcription: dict[str, Any], include_timestamps: bool = False) -> str:
    """Return plain-text transcription, optionally prefixed with segment timestamps."""
    if include_timestamps and transcription.get("segments"):
        lines = []
        for seg in transcription["segments"]:
            start = seg["start"]
            text = seg["text"].strip()
            lines.append(f"[{start:.2f}s] {text}")
        return "\n".join(lines)
    return transcription.get("text", "").strip()


def render_srt(transcription: dict[str, Any]) -> str:
    """Return SRT-formatted subtitle string."""
    lines: list[str] = []
    for i, seg in enumerate(transcription.get("segments", []), 1):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        lines += [str(i), f"{_format_srt_time(start)} --> {_format_srt_time(end)}", text, ""]
    return "\n".join(lines)


def render_vtt(transcription: dict[str, Any]) -> str:
    """Return WebVTT-formatted subtitle string."""
    lines = ["WEBVTT", ""]
    for seg in transcription.get("segments", []):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        lines += [f"{_format_vtt_time(start)} --> {_format_vtt_time(end)}", text, ""]
    return "\n".join(lines)


def _format_time(seconds: float, ms_sep: str = ",") -> str:
    """Format seconds to timestamp string with configurable millisecond separator."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02}{ms_sep}{ms:03}"


def _format_srt_time(seconds: float) -> str:
    return _format_time(seconds, ",")


def _format_vtt_time(seconds: float) -> str:
    return _format_time(seconds, ".")
