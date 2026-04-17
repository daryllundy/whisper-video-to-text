import logging
import os
import subprocess
from pathlib import Path

from tqdm import tqdm


PROGRESSIVE_MP4_FORMAT = (
    "best[ext=mp4][vcodec!=none][acodec!=none]/"
    "best[vcodec!=none][acodec!=none]/best"
)
ADAPTIVE_FORMAT = "bestvideo*+bestaudio/best"
FORMAT_ATTEMPTS = (
    ("progressive mp4", PROGRESSIVE_MP4_FORMAT),
    ("adaptive best", ADAPTIVE_FORMAT),
)


def _build_yt_dlp_command(url: str, output_dir: str, format_selector: str) -> list[str]:
    return [
        "yt-dlp",
        "-f",
        format_selector,
        "--merge-output-format",
        "mp4",
        "--remote-components",
        "ejs:github",
        "-o",
        os.path.join(output_dir, "%(title)s.%(ext)s"),
        "--no-playlist",
        url,
    ]


def _filename_from_yt_dlp_output(stdout: str, output_dir: str) -> str:
    # First check for merged output
    for line in stdout.split("\n"):
        if "Merging formats into" in line:
            try:
                # Format: [Merger] Merging formats into "filename.mp4"
                filename = line.split('"')[1]
                if os.path.exists(filename):
                    return filename
            except IndexError:
                pass

    # Then check for direct downloads
    for line in stdout.split("\n"):
        if "Destination:" in line or "has already been downloaded" in line:
            if "Destination:" in line:
                filename = line.split("Destination:")[1].strip()
            else:
                filename = line.split("]")[1].strip().split(" has")[0]

            # yt-dlp reports a resolved target filename in these lines.
            # Return it directly so callers can use the path even when the
            # file is mocked in tests or created after post-processing.
            return filename

    # Fallback: look for the most recent .mp4 file
    mp4_files = list(Path(output_dir).glob("*.mp4"))
    if mp4_files:
        return str(max(mp4_files, key=os.path.getctime))

    raise ValueError("Could not determine downloaded filename")


def download_video(url: str, output_dir: str = ".") -> str:
    """
    Download video from URL using yt-dlp, with a progress bar.

    Args:
        url: The video URL.
        output_dir: Directory to save the downloaded file.

    Returns:
        The path to the downloaded MP4 file.
    """
    logging.info(f"Downloading video from: {url}")

    last_error = None
    for attempt_name, format_selector in FORMAT_ATTEMPTS:
        cmd = _build_yt_dlp_command(url, output_dir, format_selector)
        try:
            # Use tqdm to show a spinner while downloading
            bar_format = "{l_bar}{bar} [time left: {remaining}]"
            with tqdm(total=1, desc="yt-dlp", bar_format=bar_format) as pbar:
                logging.info(f"Trying yt-dlp {attempt_name} format selection")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                pbar.update(1)
            return _filename_from_yt_dlp_output(result.stdout, output_dir)
        except subprocess.CalledProcessError as e:
            last_error = e
            logging.warning(f"yt-dlp {attempt_name} format selection failed: {e}")

    if last_error:
        logging.error(f"✗ Error downloading video: {last_error}")
        if last_error.stderr:
            logging.error(f"Suggest looking at stderr: {last_error.stderr}")
        if last_error.stdout:
            logging.error(f"Stdout: {last_error.stdout}")
        raise last_error

    raise ValueError("No yt-dlp format attempts were configured")
