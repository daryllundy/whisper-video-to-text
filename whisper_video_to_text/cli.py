import argparse
import logging
import sys
import time
from pathlib import Path

from whisper_video_to_text.convert import convert_mp4_to_mp3
from whisper_video_to_text.download import download_video
from whisper_video_to_text.transcribe import (
    save_srt,
    save_transcription,
    save_vtt,
    transcribe_audio,
)


def main():
    parser = argparse.ArgumentParser(
        description="Convert MP4 to MP3 and transcribe audio to text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with local file
  python -m whisper_video_to_text video.mp4

  # Download from YouTube and transcribe
  python -m whisper_video_to_text "https://youtube.com/watch?v=..." --download

  # Use specific Whisper model and language
  python -m whisper_video_to_text video.mp4 --model large --language en

  # Include timestamps in output
  python -m whisper_video_to_text video.mp4 --timestamps

  # Keep intermediate MP3 file
  python -m whisper_video_to_text video.mp4 --keep-audio

  # Export to SRT and VTT
  python -m whisper_video_to_text video.mp4 --format srt --format vtt

Available Whisper models:
  tiny, base, small, medium, large
        """,
    )

    parser.add_argument("input", help="MP4 file path or video URL (with --download)")
    parser.add_argument("-o", "--output", help="Output text file (default: input_name.txt)")
    parser.add_argument(
        "-m",
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model to use (default: base)",
    )
    parser.add_argument("-l", "--language", help="Language code (e.g., en, es, fr)")
    parser.add_argument(
        "-t", "--timestamps", action="store_true", help="Include timestamps in transcription"
    )
    parser.add_argument(
        "-k", "--keep-audio", action="store_true", help="Keep intermediate MP3 file"
    )
    parser.add_argument(
        "-d", "--download", action="store_true", help="Download video from URL first"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--logfile", help="Append logs to this file (default: none)", default=None)
    parser.add_argument(
        "--format",
        action="append",
        choices=["txt", "srt", "vtt"],
        default=None,
        help="Output format(s): txt, srt, vtt. Can be specified multiple times. (default: txt)",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    handlers = [logging.StreamHandler(sys.stdout)]
    if args.logfile:
        handlers.append(logging.FileHandler(args.logfile, mode="a", encoding="utf-8"))
    logging.basicConfig(
        level=log_level, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers
    )

    try:
        # Handle video download if needed
        if args.download:
            video_file = download_video(args.input)
        else:
            video_file = args.input

        # Convert MP4 to MP3
        video_path = Path(video_file)
        audio_file = video_path.with_suffix(".mp3")

        convert_mp4_to_mp3(video_file, str(audio_file), verbose=args.verbose)

        # Transcribe audio
        transcription = transcribe_audio(
            str(audio_file), model_name=args.model, language=args.language, verbose=args.verbose
        )

        # Determine output base filename
        if args.output:
            base = Path(args.output).with_suffix("")
        else:
            # Save in ~/research directory with timestamped name
            research_dir = Path.home() / "research"
            research_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())  # Unix epoch seconds
            base = research_dir / f"transcript-{timestamp}"

        formats = args.format if args.format else ["txt"]
        for fmt in set(formats):
            if fmt == "txt":
                save_transcription(
                    transcription, str(base.with_suffix(".txt")), include_timestamps=args.timestamps
                )
            elif fmt == "srt":
                save_srt(transcription, str(base.with_suffix(".srt")))
            elif fmt == "vtt":
                save_vtt(transcription, str(base.with_suffix(".vtt")))

        # Clean up audio file if requested
        if not args.keep_audio and audio_file.exists():
            audio_file.unlink()
            logging.info(f"✓ Removed temporary audio file: {audio_file}")

        logging.info("✅ Process complete! Output(s) ready for LLM analysis.")

    except KeyboardInterrupt:
        logging.error("✗ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
