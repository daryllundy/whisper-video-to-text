# Whisper Video ► Text

Convert MP4 video files (local or YouTube) to text using OpenAI Whisper, with automatic audio extraction and transcription.

---

## Features

- Download videos from YouTube or use local MP4 files
- Extract audio (MP3) using ffmpeg
- Transcribe audio to text with OpenAI Whisper (local inference)
- Optional timestamps in output
- Supports multiple Whisper models (`tiny`, `base`, `small`, `medium`, `large`)
- Simple CLI interface

---

## Quickstart

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

### 3. Usage

#### Local MP4 file

```bash
python mp4_to_text.py path/to/video.mp4
```

#### Download from YouTube and transcribe

```bash
python mp4_to_text.py "https://youtube.com/watch?v=..." --download
```

#### Advanced options

- Use a specific Whisper model: `--model large`
- Set language: `--language en`
- Include timestamps: `--timestamps`
- Keep intermediate MP3: `--keep-audio`
- Show verbose output: `--verbose`

#### Example

```bash
python mp4_to_text.py myvideo.mp4 --model small --timestamps --verbose
```

---

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/download.html) (system)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [openai-whisper](https://github.com/openai/whisper)
- [tqdm](https://github.com/tqdm/tqdm)

All Python dependencies are pinned in `pyproject.toml`.

---

## Roadmap

See [tasks.md](./tasks.md) for planned improvements and refactoring steps.

---

## License

MIT License
