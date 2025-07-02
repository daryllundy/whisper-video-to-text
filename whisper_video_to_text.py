#!/usr/bin/env python
"""
Legacy wrapper so the command

    uv run whisper_video_to_text <video.mp4>

continues to work. It immediately delegates to the package CLI.
"""

from whisper_video_to_text.cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
