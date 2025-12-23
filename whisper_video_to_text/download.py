import logging
import os
import subprocess
from pathlib import Path

from tqdm import tqdm


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

    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo*+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "--remote-components",
        "ejs:github",
        "-o",
        os.path.join(output_dir, "%(title)s.%(ext)s"),
        "--no-playlist",
        url,
    ]

    try:
        # Use tqdm to show a spinner while downloading
        bar_format = "{l_bar}{bar} [time left: {remaining}]"
        with tqdm(total=1, desc="yt-dlp", bar_format=bar_format) as pbar:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            pbar.update(1)
        # Extract filename from yt-dlp output
        # First check for merged output
        for line in result.stdout.split("\n"):
            if "Merging formats into" in line:
                try:
                    # Format: [Merger] Merging formats into "filename.mp4"
                    filename = line.split('"')[1]
                    if os.path.exists(filename):
                        return filename
                except IndexError:
                    pass

        # Then check for direct downloads
        for line in result.stdout.split("\n"):
            if "Destination:" in line or "has already been downloaded" in line:
                if "Destination:" in line:
                    filename = line.split("Destination:")[1].strip()
                else:
                    filename = line.split("]")[1].strip().split(" has")[0]
                
                # Verified: Intermediate files (like .f401.mp4) are deleted by yt-dlp after merge.
                # So we only return if the file actually exists.
                if os.path.exists(filename):
                    return filename

        # Fallback: look for the most recent .mp4 file
        mp4_files = list(Path(output_dir).glob("*.mp4"))
        if mp4_files:
            return str(max(mp4_files, key=os.path.getctime))

        raise ValueError("Could not determine downloaded filename")
    except subprocess.CalledProcessError as e:
        logging.error(f"✗ Error downloading video: {e}")
        if e.stderr:
            logging.error(f"Suggest looking at stderr: {e.stderr}")
        if e.stdout:
            logging.error(f"Stdout: {e.stdout}")
        raise
