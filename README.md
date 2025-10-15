# Whisper Video ► Text 🎥

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE.txt)
[![CI](https://github.com/daryllundy/whisper-video-to-text/actions/workflows/ci.yml/badge.svg)](https://github.com/daryllundy/whisper-video-to-text/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](#docker)
[![GitLab Mirror](https://img.shields.io/badge/gitlab-mirror-orange.svg)](https://gitlab.com/daryllundy/whisper-video-to-text)

<div align="center">

**Convert MP4 video files (local or YouTube) to accurate, timestamped text using OpenAI Whisper. Modern, test-driven, and production-ready.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Table of Contents](#-table-of-contents)

</div>

---

## 📖 About The Project

Whisper Video ► Text is a powerful command-line tool that bridges the gap between video content and text transcription. Whether you need to transcribe YouTube videos for research, create subtitles for accessibility, or extract text from local video files for documentation, this tool provides state-of-the-art accuracy using OpenAI's Whisper model.

## Demo

[![asciicast](https://asciinema.org/a/demo-whisper-video-to-text.svg)](demo.cast)

*YouTube download and transcription workflow with multiple output formats*

### Why This Project?

- **Local Processing**: No API costs or data privacy concerns - everything runs locally
- **High Accuracy**: Leverages OpenAI Whisper for industry-leading transcription quality
- **Multiple Formats**: Export as plain text, SRT, or VTT subtitles
- **Developer-Friendly**: Built with modern Python practices, fully tested, and production-ready
- **Great for Portfolios**: Showcases real-world Python, CLI development, and automation skills

---

## 🚀 Features

- **🎥 YouTube & Local Video Support:** Download from YouTube or use local MP4 files
- **🎵 Audio Extraction:** Converts video to MP3 using ffmpeg
- **🧠 State-of-the-Art Transcription:** Uses OpenAI Whisper (local inference) for high-accuracy speech-to-text
- **📝 Multiple Output Formats:** Export as plain text, SRT, or VTT subtitles
- **⏰ Timestamps & Metadata:** Optionally include timestamps and language metadata
- **📊 Progress Bars:** Real-time progress for downloads and conversions
- **💻 Robust CLI:** Flexible, user-friendly command-line interface
- **📋 Comprehensive Logging:** Console and optional file logging, with verbosity control
- **🧪 Fully Tested:** 80%+ test coverage with linting and type checks
- **🐳 Docker Ready:** One-command container build

---

## 📋 Table of Contents

- [About The Project](#-about-the-project)
- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [Web Interface](#-web-interface)
- [Docker Compose Deployment](#-docker-compose-deployment)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Docker](#-docker)
- [Roadmap](#-roadmap)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+** - [Download Python](https://python.org/downloads/)
- **ffmpeg** - [Download & Install](https://ffmpeg.org/download.html)
- **uv** (recommended) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

### Verify Installation

```bash
python --version  # Should be 3.9+
ffmpeg -version   # Should show ffmpeg information
uv --version      # Should show uv version
```

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/daryllundy/whisper-video-to-text.git
cd whisper-video-to-text
```

### 2. Set up virtual environment

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

For development (recommended):

```bash
uv pip install -e .  # Editable install with console scripts
```

For production:

```bash
uv pip install .
```

### 4. Verify installation

```bash
whisper_video_to_text --help
```

---

## 🚀 Usage

### Basic Examples

#### Transcribe a local MP4 file

```bash
uv run whisper_video_to_text path/to/video.mp4
```

#### Download from YouTube and transcribe

```bash
uv run whisper_video_to_text "https://youtube.com/watch?v=..." --download
```

#### Export to subtitle formats

```bash
uv run whisper_video_to_text myvideo.mp4 --format srt --format vtt
```

### Advanced Options

```bash
# Use a specific Whisper model
uv run whisper_video_to_text video.mp4 --model large

# Set language for better accuracy
uv run whisper_video_to_text video.mp4 --language en

# Include timestamps in output
uv run whisper_video_to_text video.mp4 --timestamps

# Keep intermediate MP3 file
uv run whisper_video_to_text video.mp4 --keep-audio

# Enable verbose logging
uv run whisper_video_to_text video.mp4 --verbose

# Log to file
uv run whisper_video_to_text video.mp4 --logfile run.log

# Custom output filename
uv run whisper_video_to_text video.mp4 --output my_transcript.txt
```

### Output Files

When `--output` is omitted, files are saved in `~/research` directory with default names based on the current Unix timestamp:

- **Text**: `~/research/transcript-<timestamp>.txt`
- **SRT**: `~/research/transcript-<timestamp>.srt`
- **VTT**: `~/research/transcript-<timestamp>.vtt`

When `--output` is specified, files are saved to that location with the specified name.

---

## 🌐 Web Interface

A modern web UI is included for browser-based transcription.

### Install Web Dependencies

```bash
uv pip install .[web]
```

### Run the Web Server

```bash
uv run python -m whisper_video_to_text.web.main
```

Or using uvicorn directly:

```bash
uvicorn whisper_video_to_text.web.main:app --host 0.0.0.0 --port 8000
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Features

- Upload MP4 or paste YouTube URL
- Select Whisper model, language, and output format
- Real-time progress bar and transcript display
- Download results

---

## 🐳 Docker Compose Deployment

Deploy the web application with docker-compose for simplified container orchestration, persistent storage, and easy configuration management.

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/daryllundy/whisper-video-to-text.git
   cd whisper-video-to-text
   ```

2. **Create environment file (optional)**
   ```bash
   cp .env.example .env
   # Edit .env with your preferences
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Visit the web interface**
   
   Open [http://localhost:8000](http://localhost:8000) in your browser

### Environment Variables

Configure the deployment by creating a `.env` file or setting environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8000` | Web server port |
| `HOST` | `0.0.0.0` | Bind address (0.0.0.0 for all interfaces) |
| `WHISPER_MODEL` | `base` | Whisper model variant (`tiny`, `base`, `small`, `medium`, `large`) |
| `LOG_LEVEL` | `info` | Application log level (`debug`, `info`, `warning`, `error`) |

**Example `.env` file:**
```bash
PORT=8000
WHISPER_MODEL=base
HOST=0.0.0.0
LOG_LEVEL=info
```

### Common Commands

```bash
# Start in foreground (see logs in real-time)
docker-compose up

# Start in background (detached mode)
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down

# Rebuild and start (after code changes)
docker-compose up --build

# Rebuild without cache
docker-compose build --no-cache

# Check service status and health
docker-compose ps

# Remove volumes (⚠️ deletes all transcripts and uploads!)
docker-compose down -v
```

### Development Mode

For development with hot-reload and source code mounting:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This configuration:
- Mounts source code into the container
- Enables automatic reload on code changes
- Preserves your local development environment

### Persistent Storage

Docker volumes are used to persist data across container restarts:

| Volume | Purpose | Location |
|--------|---------|----------|
| `transcripts` | Generated transcript files | `/app/transcripts` |
| `uploads` | Uploaded video files | `/app/uploads` |
| `whisper-cache` | Downloaded Whisper models | `/home/appuser/.cache/whisper` |

Volumes persist even when containers are stopped or removed (unless you use `docker-compose down -v`).

### Troubleshooting

**Port already in use**
```bash
# Change the port in .env file
echo "PORT=9000" >> .env
docker-compose up -d
```

**Permission errors**
- Ensure Docker has proper permissions to access mounted directories
- On Linux, you may need to add your user to the docker group: `sudo usermod -aG docker $USER`

**Model download is slow**
- First run downloads the Whisper model (can take several minutes depending on model size)
- Models are cached in the `whisper-cache` volume for subsequent runs
- Use a smaller model for faster initial setup: `WHISPER_MODEL=tiny`

**Container fails to start**
- Check logs: `docker-compose logs web`
- Verify ffmpeg is installed in the container: `docker-compose exec web ffmpeg -version`
- Ensure all required environment variables are set correctly

**Out of memory errors**
- Larger Whisper models require more RAM
- Use a smaller model (`tiny` or `base`) or increase Docker memory limits
- Add resource limits in docker-compose.yml if needed

**Transcripts not persisting**
- Verify volumes are created: `docker volume ls`
- Check volume mounts: `docker-compose config`
- Ensure you're not using `docker-compose down -v` which removes volumes

---

## 🏗️ Project Structure

```
whisper-video-to-text/
├── whisper_video_to_text/      # Main package
│   ├── __init__.py            # Package initialization
│   ├── cli.py                 # Command-line interface
│   ├── convert.py             # Video to audio conversion
│   ├── download.py            # YouTube download functionality
│   ├── transcribe.py          # Whisper transcription
│   └── web/                   # Optional web UI
│       ├── main.py            # FastAPI app
│       ├── views.py           # Routes, background job
│       ├── progress.py        # In-memory job/progress tracking
│       ├── templates/
│       │   └── index.html     # Minimal UI
│       └── static/
│           └── style.css      # Basic styles
├── tests/                     # Test suite
│   ├── test_convert.py        # Conversion tests
│   ├── test_download.py       # Download tests
│   └── test_transcribe.py     # Transcription tests
├── .github/workflows/         # CI/CD automation
│   ├── ci.yml                 # Main CI workflow
│   └── mirror.yml             # GitLab mirror sync
├── Dockerfile                 # Docker container setup
├── docker-entrypoint.sh       # Docker entrypoint script
├── docker-compose.yml         # Production deployment
├── docker-compose.dev.yml     # Development deployment
├── pyproject.toml            # Project configuration
├── README.md                 # Project documentation
├── LICENSE.txt               # MIT license
├── CONTRIBUTING.md           # Contribution guidelines
└── .gitignore               # Git ignore rules
```

---

## 🧪 Testing

Run the complete test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=whisper_video_to_text

# Run specific test file
pytest tests/test_transcribe.py

# Run with verbose output
pytest -v
```

---

## 🧰 Development

### Pre-commit hooks

This repo is configured with pre-commit to keep code quality high.

```bash
uv venv && source .venv/bin/activate
uv pip install -e .[dev]
pre-commit install
pre-commit run --all-files
```

### Code Quality

The project maintains high code quality standards with automated checks:

- **Linting**: Ruff for fast Python linting
- **Formatting**: Black for consistent code style
- **Type Checking**: mypy for static type analysis
- **Testing**: pytest with 80%+ coverage
- **CI/CD**: GitHub Actions for automated testing and Docker builds

### Makefile shortcuts

```bash
make install     # Install dev deps
make hooks       # Install + run pre-commit on all files
make lint        # Ruff lint
make format      # Ruff --fix + Black
make typecheck   # mypy
make test        # pytest -v
make cov         # pytest with coverage
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Development workflow

---

## 🐳 Docker

### Build the container

```bash
docker build -t whisper-video-to-text .
```

### Run with Docker

The Docker image uses an intelligent entrypoint that supports both CLI and web server modes:

```bash
# Show help
docker run --rm whisper-video-to-text --help

# Transcribe a local file (mount current directory)
docker run --rm -v "$PWD:/workspace" whisper-video-to-text /workspace/video.mp4

# Download and transcribe YouTube video
docker run --rm -v "$PWD:/workspace" whisper-video-to-text "https://youtube.com/watch?v=..." --download

# Run web server (use docker-compose for production)
docker run --rm -p 8000:8000 whisper-video-to-text uvicorn whisper_video_to_text.web.main:app --host 0.0.0.0 --port 8000
```

**Note:** The container runs as a non-root user (`appuser`) for security.

---

## 📋 Roadmap

- [X] Core transcription functionality
- [X] YouTube download support
- [X] Multiple output formats (SRT, VTT, TXT)
- [X] Docker containerization
- [X] Comprehensive test suite
- [ ] Batch processing support
- [X] Web interface (FastAPI, HTMX, real-time progress, upload/YouTube support)
- [ ] GPU acceleration option
- [ ] Additional audio formats support

See [tasks.md](./tasks.md) for detailed progress and planned improvements.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - For the amazing speech recognition model
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - For reliable YouTube downloading
- [FFmpeg](https://ffmpeg.org/) - For audio/video processing
- [FastAPI](https://fastapi.tiangolo.com/) - For the modern web framework
- [pytest](https://pytest.org/) - For the robust testing framework
- [uv](https://github.com/astral-sh/uv) - For blazing fast Python package management
- [Ruff](https://github.com/astral-sh/ruff) - For lightning-fast Python linting

---

## ⭐ Show your support

Give a ⭐️ if this project helped you!

---

<div align="center">

**[⬆ Back to Top](#whisper-video--text)**

</div>
