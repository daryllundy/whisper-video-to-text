# Project Structure

## Directory Layout
```
whisper-video-to-text/
├── whisper_video_to_text/      # Main package
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Module entry point
│   ├── cli.py                 # Command-line interface
│   ├── convert.py             # Video to audio conversion
│   ├── download.py            # YouTube download functionality
│   ├── transcribe.py          # Whisper transcription
│   └── web/                   # Web interface
│       ├── __init__.py
│       ├── main.py            # FastAPI application entry
│       ├── views.py           # Web route handlers
│       ├── progress.py        # Progress tracking utilities
│       ├── static/            # CSS, JS assets
│       └── templates/         # Jinja2 HTML templates
├── tests/                     # Test suite
│   ├── test_convert.py        # Conversion tests
│   ├── test_download.py       # Download tests
│   └── test_transcribe.py     # Transcription tests
├── examples/                  # Sample files and demos
├── transcripts/               # Default output directory
├── build/                     # Build artifacts
├── .venv/                     # Virtual environment
├── .kiro/                     # Kiro configuration
└── .history/                  # File history tracking
```

## Key Files
- **pyproject.toml**: Project configuration, dependencies, entry points
- **mp4_to_text.py**: Legacy standalone script (kept for compatibility)
- **whisper_video_to_text.py**: Another legacy entry point
- **Dockerfile**: Container configuration
- **README.md**: Comprehensive documentation
- **LICENSE.txt**: MIT license

## Module Organization

### Core Modules
- **cli.py**: Argument parsing, main CLI flow, logging setup
- **download.py**: YouTube video downloading with yt-dlp
- **convert.py**: MP4 to MP3 conversion using ffmpeg
- **transcribe.py**: Whisper model loading and transcription, output formatting

### Web Interface
- **web/main.py**: FastAPI app initialization and startup
- **web/views.py**: HTTP route handlers for upload/transcription
- **web/progress.py**: Real-time progress tracking utilities
- **web/templates/**: HTML templates with modern UI
- **web/static/**: CSS styling and client-side assets

## Naming Conventions
- **Snake_case**: All Python files, functions, variables
- **Package structure**: Flat hierarchy with logical separation
- **Entry points**: Multiple ways to run (CLI scripts, python -m, direct execution)
- **Output files**: Timestamped format `transcript-{unix_timestamp}.{ext}`

## Import Patterns
- Relative imports within package modules
- External dependencies imported at module level
- Optional dependencies (web) handled gracefully
- System dependencies checked at runtime

## Configuration
- **Console scripts**: Defined in pyproject.toml entry points
- **Optional dependencies**: Web features in separate install group
- **Docker**: Multi-stage build with system dependencies
- **Logging**: Configurable verbosity with file output option
