#!/usr/bin/env python3
"""
MP4 to Text Transcription Script
Converts MP4 video files to MP3 audio, then transcribes to text using Whisper

Requirements:
- yt-dlp (pip install yt-dlp)
- ffmpeg (system installation required)
- openai-whisper (pip install openai-whisper)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import whisper
import warnings
import logging
from typing import Optional, Any, Dict

# Suppress FP16 warning if CUDA is not available
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")


def setup_logging(verbose: bool = False, logfile: Optional[str] = None) -> None:
    """Configure logging to console and optionally to a file (append mode)."""
    log_level = logging.INFO if verbose else logging.WARNING
    handlers = [logging.StreamHandler(sys.stdout)]
    if logfile:
        handlers.append(logging.FileHandler(logfile, mode='a', encoding='utf-8'))
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )


def check_dependencies() -> None:
    """Check if required tools are installed"""
    dependencies: Dict[str, str] = {
        'ffmpeg': 'ffmpeg -version',
        'yt-dlp': 'yt-dlp --version'
    }

    missing: list[str] = []
    for tool, command in dependencies.items():
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool)

    if missing:
        logging.error(f"Missing required tools: {', '.join(missing)}")
        logging.error("Installation instructions:")
        if 'ffmpeg' in missing:
            logging.error("- ffmpeg: Visit https://ffmpeg.org/download.html")
        if 'yt-dlp' in missing:
            logging.error("- yt-dlp: Run 'pip install yt-dlp'")
        sys.exit(1)


def convert_mp4_to_mp3(
    input_file: str,
    output_file: Optional[str] = None,
    verbose: bool = False
) -> Path:
    """Convert MP4 to MP3 using ffmpeg"""
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    if output_file is None:
        output_path = input_path.with_suffix('.mp3')
    else:
        output_path = Path(output_file)

    # Build ffmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-vn',  # No video
        '-acodec', 'libmp3lame',
        '-ab', '192k',  # Audio bitrate
        '-ar', '44100',  # Sample rate
        '-y',  # Overwrite output file
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
        sys.exit(1)


def transcribe_audio(
    audio_file: str,
    model_name: str = "base",
    language: Optional[str] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """Transcribe audio using OpenAI Whisper"""
    audio_path = Path(audio_file)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    logging.info(f"Loading Whisper model '{model_name}'...")
    model = whisper.load_model(model_name)

    logging.info(f"Transcribing {audio_path.name}...")

    # Transcribe with progress callback
    result = model.transcribe(
        str(audio_path),
        language=language,
        verbose=verbose,
        fp16=False  # Use FP32 for CPU compatibility
    )

    logging.info("✓ Transcription complete")
    return result


def save_transcription(
    transcription: Dict[str, Any],
    output_file: str,
    include_timestamps: bool = False
) -> None:
    """Save transcription to text file"""
    output_path = Path(output_file)

    with open(output_path, 'w', encoding='utf-8') as f:
        if include_timestamps:
            # Save with timestamps
            f.write("TRANSCRIPTION WITH TIMESTAMPS\n")
            f.write("="*50 + "\n\n")

            for segment in transcription['segments']:
                start = segment['start']
                end = segment['end']
                text = segment['text'].strip()

                # Format timestamp
                start_time = f"{int(start//60):02d}:{int(start%60):02d}"
                end_time = f"{int(end//60):02d}:{int(end%60):02d}"

                f.write(f"[{start_time} - {end_time}] {text}\n")
        else:
            # Save plain text
            f.write("TRANSCRIPTION\n")
            f.write("="*50 + "\n\n")
            f.write(transcription['text'].strip())

        # Add metadata
        f.write("\n\n" + "="*50 + "\n")
        f.write("METADATA\n")
        f.write(f"Language: {transcription.get('language', 'auto-detected')}\n")
        if 'segments' in transcription:
            f.write(f"Duration: {transcription['segments'][-1]['end']:.1f} seconds\n")

    logging.info(f"✓ Transcription saved to: {output_path}")


def download_video(url: str, output_dir: str = ".") -> str:
    """Download video from URL using yt-dlp"""
    logging.info(f"Downloading video from: {url}")

    cmd = [
        'yt-dlp',
        '-f', 'best[ext=mp4]/best',
        '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
        '--no-playlist',
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Extract filename from yt-dlp output
        for line in result.stdout.split('\n'):
            if 'Destination:' in line or 'has already been downloaded' in line:
                # Extract filename from the output
                if 'Destination:' in line:
                    filename = line.split('Destination:')[1].strip()
                else:
                    filename = line.split(']')[1].strip().split(' has')[0]
                return filename

        # Fallback: look for the most recent .mp4 file
        mp4_files = list(Path(output_dir).glob("*.mp4"))
        if mp4_files:
            return str(max(mp4_files, key=os.path.getctime))

        raise ValueError("Could not determine downloaded filename")
    except subprocess.CalledProcessError as e:
        logging.error(f"✗ Error downloading video: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert MP4 to MP3 and transcribe audio to text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with local file
  python mp4_to_text.py video.mp4

  # Download from YouTube and transcribe
  python mp4_to_text.py "https://youtube.com/watch?v=..." --download

  # Use specific Whisper model and language
  python mp4_to_text.py video.mp4 --model large --language en

  # Include timestamps in output
  python mp4_to_text.py video.mp4 --timestamps

  # Keep intermediate MP3 file
  python mp4_to_text.py video.mp4 --keep-audio

Available Whisper models:
  tiny, base, small, medium, large
        """
    )

    parser.add_argument('input', help='MP4 file path or video URL (with --download)')
    parser.add_argument('-o', '--output', help='Output text file (default: input_name.txt)')
    parser.add_argument('-m', '--model', default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model to use (default: base)')
    parser.add_argument('-l', '--language', help='Language code (e.g., en, es, fr)')
    parser.add_argument('-t', '--timestamps', action='store_true',
                       help='Include timestamps in transcription')
    parser.add_argument('-k', '--keep-audio', action='store_true',
                       help='Keep intermediate MP3 file')
    parser.add_argument('-d', '--download', action='store_true',
                       help='Download video from URL first')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output')
    parser.add_argument('--logfile', help='Append logs to this file (default: none)', default=None)

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose, logfile=args.logfile)

    # Check dependencies
    check_dependencies()

    try:
        # Handle video download if needed
        if args.download:
            video_file = download_video(args.input)
        else:
            video_file = args.input

        # Convert MP4 to MP3
        video_path = Path(video_file)
        audio_file = video_path.with_suffix('.mp3')

        convert_mp4_to_mp3(video_file, str(audio_file), verbose=args.verbose)

        # Transcribe audio
        transcription = transcribe_audio(
            str(audio_file),
            model_name=args.model,
            language=args.language,
            verbose=args.verbose
        )

        # Determine output filename
        if args.output:
            output_file = args.output
        else:
            output_file = str(video_path.with_suffix('.txt'))

        # Save transcription
        save_transcription(transcription, output_file, include_timestamps=args.timestamps)

        # Clean up audio file if requested
        if not args.keep_audio and audio_file.exists():
            audio_file.unlink()
            logging.info(f"✓ Removed temporary audio file: {audio_file}")

        logging.info(f"✅ Process complete! Text file ready for LLM analysis: {output_file}")

    except KeyboardInterrupt:
        logging.error("✗ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
