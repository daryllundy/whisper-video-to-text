# Whisper Video ► Text

<div align="center">

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg) ![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg) ![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey.svg)

**Convert MP4 video files (local or YouTube) to accurate, timestamped text using OpenAI Whisper. Modern, test-driven, and production-ready.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Table of Contents](#-table-of-contents)

</div>

---

## 📖 About The Project

Whisper Video ► Text is a powerful command-line tool that bridges the gap between video content and text transcription. Whether you need to transcribe YouTube videos for research, create subtitles for accessibility, or extract text from local video files for documentation, this tool provides state-of-the-art accuracy using OpenAI's Whisper model.

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
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Docker](#-docker)
- [Roadmap](#-roadmap)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

---

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** - [Download Python](https://python.org/downloads/)
- **ffmpeg** - [Download &amp; Install](https://ffmpeg.org/download.html)
- **uv** (recommended) - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

### Verify Installation

```bash
python --version  # Should be 3.8+
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

When `--output` is omitted, files are saved with default names based on the current Unix timestamp:

- **Text**: `transcript-<timestamp>.txt`
- **SRT**: `transcript-<timestamp>.srt`
- **VTT**: `transcript-<timestamp>.vtt`

All files are saved in the current directory.

---

## 🌐 Web Interface

A modern web UI is included for browser-based transcription.

### Install Web Dependencies

```bash
uv pip install .[web]
```

### Run the Web Server

```bash
uv run whisper_video_to_text/web/main.py
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Features

- Upload MP4 or paste YouTube URL
- Select Whisper model, language, and output format
- Real-time progress bar and transcript display
- Download results

---

## 🏗️ Project Structure

```
whisper-video-to-text/
├── whisper_video_to_text/      # Main package
│   ├── __init__.py            # Package initialization
│   ├── cli.py                 # Command-line interface
│   ├── convert.py             # Video to audio conversion
│   ├── download.py            # YouTube download functionality
│   └── transcribe.py          # Whisper transcription
├── tests/                     # Test suite
│   ├── test_convert.py        # Conversion tests
│   ├── test_download.py       # Download tests
│   └── test_transcribe.py     # Transcription tests
├── Dockerfile                 # Docker container setup
├── pyproject.toml            # Project configuration
├── README.md                 # Project documentation
├── LICENSE.txt               # MIT license
├── tasks.md                  # Development roadmap
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

## 🐳 Docker

### Build the container

```bash
docker build -t whisper-video-to-text .
```

### Run with Docker

```bash
# Show help
docker run --rm whisper-video-to-text --help

# Transcribe a local file (mount current directory)
docker run --rm -v "$PWD:/app" whisper-video-to-text /app/video.mp4

# Download and transcribe YouTube video
docker run --rm -v "$PWD:/app" whisper-video-to-text "https://youtube.com/watch?v=..." --download
```

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
- [Click](https://click.palletsprojects.com/) - For the beautiful CLI interface
- [pytest](https://pytest.org/) - For the robust testing framework

---

## ⭐ Show your support

Give a ⭐️ if this project helped you!

---

<div align="center">

**[⬆ Back to Top](#whisper-video--text)**

</div>
