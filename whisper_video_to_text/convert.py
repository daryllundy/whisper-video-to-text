from pathlib import Path
import subprocess
import logging
from tqdm import tqdm

def convert_mp4_to_mp3(
    input_file: str,
    output_file: str = None,
    verbose: bool = False
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
        output_path = input_path.with_suffix('.mp3')
    else:
        output_path = Path(output_file)

    # Get duration of input file (in seconds) for progress bar
    try:
        import ffmpeg
        probe = ffmpeg.probe(str(input_path))
        duration = float(probe['format']['duration'])
    except Exception:
        duration = None

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

    if duration:
        # Use tqdm to show progress bar based on ffmpeg output
        import shlex
        import threading

        def run_ffmpeg_with_progress():
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
            pbar = tqdm(total=duration, unit="sec", desc="ffmpeg", leave=True)
            last_time = 0
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
        run_ffmpeg_with_progress()
    else:
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"✗ Error converting file: {e}")
            raise

    logging.info(f"✓ Conversion complete: {output_path}")
    return output_path
