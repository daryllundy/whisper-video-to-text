#!/bin/bash
set -e

# Docker entrypoint script for whisper-video-to-text
# Handles both CLI and web server modes

# If the first argument is a whisper-video-to-text option (starts with -) or is empty,
# prepend whisper_video_to_text command
if [ "${1#-}" != "$1" ] || [ $# -eq 0 ]; then
    exec whisper_video_to_text "$@"
# If the first argument is 'uvicorn', run it directly (for web server)
elif [ "$1" = "uvicorn" ]; then
    exec "$@"
# If the first argument is 'whisper_video_to_text', run it directly
elif [ "$1" = "whisper_video_to_text" ]; then
    exec "$@"
# Otherwise, treat it as a shell command
else
    exec "$@"
fi
