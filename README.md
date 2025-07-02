# Whisper Video ► Text

[![CI](https://github.com/yourusername/whisper-video-to-text/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/whisper-video-to-text/actions)

**Convert MP4 video files (local or YouTube) to accurate, timestamped text using OpenAI Whisper. Modern, test-driven, and production-ready.**

---

## 🚀 Features

- **YouTube & Local Video Support:** Download from YouTube or use local MP4 files.
- **Audio Extraction:** Converts video to MP3 using ffmpeg.
- **State-of-the-Art Transcription:** Uses OpenAI Whisper (local inference) for high-accuracy speech-to-text.
- **Multiple Output Formats:** Export as plain text, SRT, or VTT subtitles.
- **Timestamps & Metadata:** Optionally include timestamps and language metadata.
- **Progress Bars:** Real-time progress for downloads and conversions.
- **Robust CLI:** Flexible, user-friendly command-line interface.
- **Logging:** Console and optional file logging, with verbosity control.
- **Fully Tested:** 80%+ test coverage, CI/CD with linting and type checks.
- **Docker & CI Ready:** One-command container build and GitHub Actions workflow.

---

## 🛠️ Quickstart

### 1. Clone and set up environment

```bash
git clone https://github.com/yourusername/whisper-video-to-text.git
cd whisper-video-to-text
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or install via PEP 621 metadata:

```bash
uv pip install .
```

### 2. Install system dependencies

- **ffmpeg**: [Download & install](https://ffmpeg.org/download.html)

### 3. Usage Examples

#### Local MP4 file

```bash
python -m whisper_video_to_text path/to/video.mp4
```

#### Download from YouTube and transcribe

```bash
python -m whisper_video_to_text "https://youtube.com/watch?v=..." --download
```

#### Export to SRT and VTT

```bash
python -m whisper_video_to_text myvideo.mp4 --format srt --format vtt
```

#### Advanced options

- Use a specific Whisper model: `--model large`
- Set language: `--language en`
- Include timestamps: `--timestamps`
- Keep intermediate MP3: `--keep-audio`
- Show verbose output: `--verbose`
- Log to file: `--logfile run.log`

---

## 🧑‍💻 Why This Project?

- **Modern Python:** Type hints, modular structure, and best practices throughout.
- **Production-Ready:** Dockerfile, CI/CD, and robust error handling.
- **Test-Driven:** Pytest-based unit tests with mocking for reliability.
- **Extensible:** Easy to add new formats, models, or integrations.
- **Great for Demos & Interviews:** Showcases real-world Python, CLI, and automation skills.

---

## 🏗️ Project Structure

```
whisper-video-to-text/
├── whisper_video_to_text/
│   ├── __init__.py
│   ├── cli.py
│   ├── convert.py
│   ├── download.py
│   └── transcribe.py
├── tests/
│   ├── test_convert.py
│   ├── test_download.py
│   └── test_transcribe.py
├── .github/workflows/ci.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── tasks.md
└── .gitignore
```

---

## 🧪 Testing

Run all tests with:

```bash
pytest
```

---

## 🐳 Docker

Build and run in a container:

```bash
docker build -t whisper-video-to-text .
docker run --rm -v "$PWD:/app" whisper-video-to-text --help
```

---

## 📋 Roadmap

See [tasks.md](./tasks.md) for completed and planned improvements.

---

## 📄 License

MIT License

---

## 👤 Author

**Your Name**
[Your GitHub](https://github.com/yourusername)
[Your LinkedIn](https://linkedin.com/in/yourprofile)
