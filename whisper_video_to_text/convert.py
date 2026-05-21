import logging
import subprocess
from pathlib import Path
from typing import Optional

from tqdm import tqdm

# Optional dependency: ffmpeg-python for progress bar support
try:
    import ffmpeg

    HAS_FFMPEG_PYTHON = True
except ImportError:
    ffmpeg = None
    HAS_FFMPEG_PYTHON = False
    logging.debug("ffmpeg-python not installed; video duration detection disabled")


SUPPORTED_MEDIA_EXTENSIONS = {".mp3", ".wav", ".aif", ".aiff", ".mp4", ".mov"}
WHISPER_AUDIO_SUFFIX = ".wav"


def _get_media_duration(input_path: Path) -> Optional[float]:
    """Return media duration in seconds when ffmpeg-python is available."""
    if not HAS_FFMPEG_PYTHON:
        return None

    try:
        probe = ffmpeg.probe(str(input_path))
        return float(probe["format"]["duration"])
    except Exception:
        logging.debug("Could not probe media duration; progress bar will be disabled")
        return None


def _run_ffmpeg(cmd: list[str], duration: Optional[float]) -> None:
    if duration:
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
        pbar = tqdm(total=duration, unit="sec", desc="ffmpeg", leave=True)
        last_time = 0.0
        if process.stderr:
            for line in process.stderr:
                if "time=" in line:
                    try:
                        time_str = line.split("time=")[-1].split(" ")[0]
                        h, m, s = [float(x) for x in time_str.split(":")]
                        seconds = h * 3600 + m * 60 + s
                        pbar.update(max(0, seconds - last_time))
                        last_time = seconds
                    except Exception:
                        pass
        process.wait()
        pbar.close()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
    else:
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"✗ Error converting file: {e}")
            raise


def _default_whisper_audio_path(input_path: Path) -> Path:
    output_path = input_path.with_suffix(WHISPER_AUDIO_SUFFIX)
    if output_path.resolve() == input_path.resolve():
        return input_path.with_name(f"{input_path.stem}-whisper{WHISPER_AUDIO_SUFFIX}")
    return output_path


def convert_media_to_whisper_audio(
    input_file: str, output_file: Optional[str] = None, verbose: bool = False
) -> Path:
    """
    Normalize supported media to 16 kHz mono PCM WAV for Whisper.

    Args:
        input_file: Path to a supported media file.
        output_file: Path to the output WAV file (optional).
        verbose: If True, show ffmpeg output.

    Returns:
        Path to the output WAV file.
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if input_path.suffix.lower() not in SUPPORTED_MEDIA_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_MEDIA_EXTENSIONS))
        raise ValueError(
            f"Unsupported media format '{input_path.suffix}'. Supported formats: {supported}"
        )

    if output_file is None:
        output_path = _default_whisper_audio_path(input_path)
    else:
        output_path = Path(output_file)

    duration = _get_media_duration(input_path) if HAS_FFMPEG_PYTHON else None

    cmd = ["ffmpeg"]
    if not verbose:
        cmd.extend(["-loglevel", "error"])
    cmd.extend(
        [
            "-i",
            str(input_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-y",
            str(output_path),
        ]
    )

    logging.info(f"Converting {input_path.name} to Whisper WAV...")
    _run_ffmpeg(cmd, duration)
    logging.info(f"✓ Conversion complete: {output_path}")
    return output_path


def convert_mp4_to_mp3(
    input_file: str, output_file: Optional[str] = None, verbose: bool = False
) -> Path:
    """
    Convert MP4 to MP3 using ffmpeg, with a progress bar.

    Args:
        input_file: Path to the input MP4 file.
        output_file: Path to the output MP3 file (optional).
        verbose: If True, show ffmpeg output.

    Returns:
        Path to the output MP3 file.
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if output_file is None:
        output_path = input_path.with_suffix(".mp3")
    else:
        output_path = Path(output_file)

    # Get duration of input file (in seconds) for progress bar
    duration = _get_media_duration(input_path) if HAS_FFMPEG_PYTHON else None

    cmd = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        "-ar",
        "44100",
        "-y",
        str(output_path),
    ]

    if not verbose:
        cmd.extend(["-loglevel", "error"])

    logging.info(f"Converting {input_path.name} to MP3...")
    _run_ffmpeg(cmd, duration)
    logging.info(f"✓ Conversion complete: {output_path}")
    return output_path
