import argparse
import logging
import sys
import time
from pathlib import Path

from whisper_video_to_text.convert import supported_media_extensions_display
from whisper_video_to_text.pipeline import TranscriptionRequest, run_transcription


def main() -> None:
    supported_formats = supported_media_extensions_display(with_dots=False)
    supported_formats_with_dots = supported_media_extensions_display()
    parser = argparse.ArgumentParser(
        description="Convert media files to Whisper-ready audio and transcribe to text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Basic usage with local file
  python -m whisper_video_to_text video.mp4
  python -m whisper_video_to_text audio.wav

  # Download from YouTube and transcribe
  python -m whisper_video_to_text "https://youtube.com/watch?v=..." --download

  # Use specific Whisper model and language
  python -m whisper_video_to_text video.mp4 --model large --language en

  # Include timestamps in output
  python -m whisper_video_to_text video.mp4 --timestamps

  # Keep intermediate WAV file
  python -m whisper_video_to_text video.mp4 --keep-audio

  # Export to SRT and VTT
  python -m whisper_video_to_text video.mp4 --format srt --format vtt

Supported local media formats:
  {supported_formats}

Available Whisper models:
  tiny, base, small, medium, large, turbo
        """,
    )

    parser.add_argument(
        "input",
        help=f"Media file path ({supported_formats_with_dots}) or video URL (with --download)",
    )
    parser.add_argument("-o", "--output", help="Output text file (default: input_name.txt)")
    parser.add_argument(
        "-m",
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large", "turbo"],
        help="Whisper model to use (default: base)",
    )
    parser.add_argument("-l", "--language", help="Language code (e.g., en, es, fr)")
    parser.add_argument(
        "-t", "--timestamps", action="store_true", help="Include timestamps in transcription"
    )
    parser.add_argument(
        "-k", "--keep-audio", action="store_true", help="Keep intermediate WAV file"
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

    log_level = logging.INFO if args.verbose else logging.WARNING
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if args.logfile:
        handlers.append(logging.FileHandler(args.logfile, mode="a", encoding="utf-8"))
    logging.basicConfig(
        level=log_level, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers
    )

    try:
        timestamp = int(time.time())
        if args.output:
            output_base = Path(args.output).with_suffix("")
        elif args.download:
            # Downloaded filename isn't known until after yt-dlp runs; use cwd + timestamp.
            output_base = Path.cwd() / f"transcript-{timestamp}"
        else:
            video_path = Path(args.input)
            output_base = video_path.parent / f"{video_path.stem}-transcript-{timestamp}"

        request = TranscriptionRequest(
            source=args.input,
            download=args.download,
            model=args.model,
            language=args.language,
            formats=tuple(set(args.format or ["txt"])),
            include_timestamps=args.timestamps,
            keep_audio=args.keep_audio,
            output_base=output_base,
        )
        run_transcription(request)
        logging.info("✅ Process complete! Output(s) ready for LLM analysis.")

    except KeyboardInterrupt:
        logging.error("✗ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
