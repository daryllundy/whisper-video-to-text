from pathlib import Path
import subprocess
import logging

def convert_mp4_to_mp3(
    input_file: str,
    output_file: str = None,
    verbose: bool = False
) -> Path:
    """
    Convert MP4 to MP3 using ffmpeg.

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
        output_path = input_path.with_suffix('.mp3')
    else:
        output_path = Path(output_file)

    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-vn',
        '-acodec', 'libmp3lame',
        '-ab', '192k',
        '-ar', '44100',
        '-y',
        str(output_path)
    ]

    if not verbose:
        cmd.extend(['-loglevel', 'error'])

    logging.info(f"Converting {input_path.name} to MP3...")

    try:
        subprocess.run(cmd, check=True)
        logging.info(f"✓ Conversion complete: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logging.error(f"✗ Error converting file: {e}")
        raise
