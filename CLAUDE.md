# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Convert local media files or YouTube videos to timestamped text using OpenAI Whisper running locally. Ships a CLI (`whisper_video_to_text`) and an optional FastAPI web UI.

Requires `ffmpeg` on the system PATH. Transcription is fully local — no API keys.

## Common Commands

Use `uv` for environment + execution (see `Makefile` for shortcuts):

```bash
# Setup
uv venv && source .venv/bin/activate
uv pip install -e .[dev]      # dev install (also installs ruff/black/mypy/pytest)
uv pip install .[web]         # add FastAPI/uvicorn/jinja2 for the web UI

# Lint / format / typecheck
make lint        # ruff check .
make format      # ruff --fix + black
make typecheck   # mypy whisper_video_to_text

# Tests
make test                                       # pytest -v
pytest tests/test_convert.py -v                 # single file
pytest tests/test_convert.py::test_name -v      # single test
pytest --cov=whisper_video_to_text              # with coverage

# Run app
uv run whisper_video_to_text path/to/video.mp4
uv run python -m whisper_video_to_text.web.main   # web UI on :8000
make web                                          # same thing
```

CI (`.github/workflows/ci.yml`) runs lint → tests (Python 3.9 + 3.12 matrix) → Docker build. Tests must mock ffmpeg / yt-dlp / Whisper — no network or large media in tests.

## Architecture

Three thin modules form the CLI pipeline; both CLI and web call them in the same order.

```
input ─► download.py ─► convert.py ─► transcribe.py ─► output
        (yt-dlp,         (ffmpeg →     (Whisper model,
         optional)        16 kHz mono   txt/srt/vtt
                          PCM WAV)      writers)
```

- **`cli.py`** — `argparse` entry point. `--format` uses `action="append"`, so multiple subtitle formats per run are valid (`--format srt --format vtt`). Default output base is `<stem>-transcript-<unix_ts>` next to the input file.
- **`convert.py`** — `convert_media_to_whisper_audio()` is the canonical converter; everything (CLI + web) calls it. Whisper-ready output is always 16 kHz mono `pcm_s16le` WAV. `SUPPORTED_MEDIA_EXTENSIONS = {.mp3, .wav, .aif, .aiff, .mp4, .mov}` — extend this set when adding formats. `ffmpeg-python` is an optional dep used only to probe duration for the `tqdm` progress bar; absence is handled gracefully. `convert_mp4_to_mp3()` is legacy and not on the live path.
- **`download.py`** — `download_video()` tries `PROGRESSIVE_MP4_FORMAT` first, then falls back to `ADAPTIVE_FORMAT`. This ordering is intentional: progressive single-file MP4 avoids HTTP 403s yt-dlp sometimes gets on adaptive streams. Don't reorder without testing against current YouTube responses.
- **`transcribe.py`** — wraps `whisper.load_model` + `model.transcribe(fp16=False)`. The `save_srt` / `save_vtt` / `save_transcription` writers consume the Whisper `segments` list; `_format_time` is shared with `,` vs `.` ms separator.

### Web layer (`whisper_video_to_text/web/`)

- **`main.py`** — FastAPI app, mounts `/static`, renders `templates/index.html`. `_asset_version()` returns max mtime of CSS/JS for cache-busting.
- **`views.py`** — `POST /api/transcribe` creates a job, then runs `run_transcription_task` via `BackgroundTasks` (thread pool, **not** async). The task replicates the CLI pipeline and writes output files to `transcripts/<job_id>.{txt,srt,vtt}`. `GET /events/{job_id}` streams progress as SSE; `GET /download/{job_id}/{ext}` serves the transcript files; `GET /api/history` lists prior jobs by globbing `transcripts/`.
- **`progress.py`** — in-memory `jobs: dict[str, JobState]` registry. Each `JobState` owns an `asyncio.Queue`. Background threads call `update_progress_sync` / `set_result_sync`, which use `loop.call_soon_threadsafe(queue.put_nowait, ...)` to hand updates to the SSE consumer. **Single-worker only** — for multi-worker deployments this needs Redis or DB backing (noted at the top of the file).

### Package entry points

`pyproject.toml` registers both `whisper-video-to-text` and `whisper_video_to_text` (hyphen + underscore) → `cli:main`. `python -m whisper_video_to_text` also works via `__main__.py`.

## Conventions

- **Python 3.9+** (CI matrix tests 3.9 and 3.12). Don't use 3.10+ syntax (`X | Y` unions in annotations, `match`, etc.) — `from __future__ import annotations` is fine where already used.
- **Line length 100** (black + ruff configured in `pyproject.toml`). Ruff rules: `E, F, I, UP, B`.
- **mypy is strict-ish**: `disallow_untyped_defs`, `disallow_incomplete_defs`, `no_implicit_optional`. Type all new public functions.
- **Logging, not print** — use the `logging` module. CLI configures handlers in `cli.py:main`.
- **Tests must mock external tools** (ffmpeg, yt-dlp, Whisper). See `tests/test_convert.py` and `tests/test_download.py` for the established mocking pattern. Keep tests hermetic — no network, no large files.
- **Conventional Commits** for messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`).
- Don't commit media or generated transcripts. `uploads/` and `transcripts/` are runtime dirs (already in `.gitignore`).

## Docker

`Dockerfile` installs runtime deps directly with `uv pip install --system` (not `uv sync`) — a comment explains: `uv export --frozen` currently fails on Linux x86_64 due to a `triton`/`openai-whisper` resolver conflict. If you bump deps, update both `pyproject.toml` and the explicit install list in the Dockerfile.

`docker-compose.yml` mounts named volumes for `transcripts`, `uploads`, and the Whisper / yt-dlp caches at `/home/appuser/.cache/`.
