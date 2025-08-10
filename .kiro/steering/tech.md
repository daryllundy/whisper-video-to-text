# Technology Stack

## Core Dependencies
- **Python**: 3.9+ (project requires >=3.9)
- **OpenAI Whisper**: 20231117 - Speech recognition model
- **yt-dlp**: 2024.5.27 - YouTube video downloading
- **tqdm**: 4.66.4 - Progress bars for CLI operations
- **ffmpeg**: System dependency for audio/video processing

## Web Interface (Optional)
- **FastAPI**: Web framework for REST API
- **Uvicorn**: ASGI server with standard extras
- **Jinja2**: Template engine for HTML rendering
- **python-multipart**: File upload support

## Development Tools
- **pytest**: Testing framework with coverage support
- **uv**: Modern Python package manager (recommended)
- **Docker**: Containerization with Python 3.9-slim base

## System Requirements
- **ffmpeg**: Must be installed system-wide for video conversion
- **Git**: Required for some yt-dlp operations

## Common Commands

### Development Setup
```bash
# Clone and setup
git clone <repo-url>
cd whisper-video-to-text
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install for development
uv pip install -e .

# Install with web dependencies
uv pip install -e .[web]
```

### Running the Application
```bash
# CLI usage
uv run whisper_video_to_text video.mp4
python -m whisper_video_to_text video.mp4

# Web interface
uv run whisper_video_to_text/web/main.py
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=whisper_video_to_text

# Run specific test file
pytest tests/test_transcribe.py
```

### Docker
```bash
# Build container
docker build -t whisper-video-to-text .

# Run with Docker
docker run --rm -v "$PWD:/app" whisper-video-to-text /app/video.mp4
```

## Architecture Notes
- Modular design with separate modules for download, convert, transcribe
- CLI and web interfaces share core functionality
- Progress tracking with tqdm for better UX
- Comprehensive logging with configurable verbosity
- Error handling with graceful failures and cleanup
