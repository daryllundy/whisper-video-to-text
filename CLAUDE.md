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

`pipeline.py` is the single orchestrator both CLI and web invoke. The four-stage flow is:

```
input ─► download.py ─► convert.py ─► transcribe.py ─► render_* ─► output
        (yt-dlp,         (ffmpeg →     (Whisper model,   (txt/srt/   (write or
         optional)        16 kHz mono   segments dict)    vtt strs)   stream)
                          PCM WAV)
```

- **`pipeline.py`** — owns `TranscriptionRequest` (input config dataclass), `TranscriptionResult` (output bundle), and `run_transcription(request, progress=..., should_cancel=...)`. Allocates a tempdir, runs download→convert→transcribe→render, optionally writes files when `output_base` is set, and always cleans up the tempdir. The optional `progress` callback is `(pct: int, status: str, msg: str) -> None`; the pipeline reports at `10/30/60/90` for download/convert/transcribe/save phases. The optional `should_cancel` callable is polled before each phase and forwarded into `convert_media_to_whisper_audio()` so `ffmpeg` itself is interruptible; raises `TranscriptionCancelled` (from `errors.py`). **Note Whisper's blocking call:** cancellation requested *during* `transcribe_audio` only takes effect after that call returns (no in-process cancellation of Whisper). **Both `cli.py` and `web/views.py` must go through this** — don't recreate the pipeline inline.
- **`errors.py`** — single-line module holding `TranscriptionCancelled`. Exists as a separate module to break a circular import between `pipeline.py` and `convert.py` (both need to raise the same exception).
- **`cli.py`** — `argparse` entry point. Builds a `TranscriptionRequest` and calls `run_transcription`. `--format` uses `action="append"`, so multiple subtitle formats per run are valid (`--format srt --format vtt`). Default `output_base` is `<stem>-transcript-<unix_ts>` next to the input (or `cwd/transcript-<unix_ts>` for `--download`, since the downloaded name isn't known up front).
- **`convert.py`** — `convert_media_to_whisper_audio(input, output, verbose=False, should_cancel=None)` is the canonical converter and the only media conversion API. Whisper-ready output is always 16 kHz mono `pcm_s16le` WAV. `_run_ffmpeg` always uses `subprocess.Popen` (single code path for progress and non-progress runs) so it can poll `should_cancel` while reading stderr; on cancel it `terminate()`s, waits briefly, `kill()`s if needed, unlinks the partial output WAV, and raises `TranscriptionCancelled`. Supported media is enumerated in `SUPPORTED_AUDIO_EXTENSIONS` (15 entries incl. `.mp3 .m4a .m4b .m4p .wav .aif .aiff .aac .flac .ogg .oga .opus .wma .amr .mka`) and `SUPPORTED_VIDEO_EXTENSIONS` (12 entries incl. `.mp4 .m4v .mov .webm .mkv .avi .wmv .flv .mpeg .mpg .3gp .3g2`), unioned into the `SUPPORTED_MEDIA_EXTENSIONS` frozenset. `SUPPORTED_MEDIA_MIME_TYPES` complements the file-extension set for browser `accept` attributes. Two display helpers must stay aligned with those constants: `supported_media_extensions_display()` (user-facing list, used by CLI epilog and web error messages) and `supported_media_accept_attribute()` (HTML `<input accept="...">`). `ffmpeg-python` is an optional dep used only to probe duration for the `tqdm` progress bar; absence is handled gracefully.
- **`download.py`** — `download_video()` walks `FORMAT_ATTEMPTS` in order: `PROGRESSIVE_MP4_FORMAT` first, then `ADAPTIVE_FORMAT`. This ordering is intentional: progressive single-file MP4 avoids HTTP 403s yt-dlp sometimes gets on adaptive streams. Don't reorder without testing against current YouTube responses.
- **`transcribe.py`** — wraps `whisper.load_model` + `model.transcribe(fp16=False)`. Pure-string renderers (`render_txt`, `render_srt`, `render_vtt`) are the only output formatters and build the pipeline's `rendered: dict[str, str]` map. `_format_time(seconds, ms_sep)` is shared between SRT (`,`) and VTT (`.`) via `_format_srt_time` / `_format_vtt_time`.

### Web layer (`whisper_video_to_text/web/`)

- **`main.py`** — FastAPI app, mounts `/static`, renders `templates/index.html`. `_asset_version()` returns max mtime of CSS/JS for cache-busting. Reads `HOST` / `PORT` / `RELOAD` env vars when run as a script.
- **`views.py`** — `POST /api/transcribe` parses multipart form (file or URL), validates upload suffix against `SUPPORTED_MEDIA_EXTENSIONS`, creates a job, then runs `run_transcription_task` via `BackgroundTasks` (thread pool, **not** async). The task builds a `TranscriptionRequest` with `output_base=transcripts/<job_id>` and a `progress=` lambda that bridges into `update_progress_sync`; it also passes `should_cancel=lambda: is_cancel_requested(job_id)` and catches `TranscriptionCancelled` to emit a terminal `cancelled` SSE event via `set_cancelled_sync`. The successful result dict carries `text`, `language`, `formats`, and `source_name` (original upload filename — used client-side for friendly download names). `POST /api/jobs/{job_id}/cancel` marks the job cancel-requested (404 unknown / current state if terminal). `GET /events/{job_id}` streams progress as SSE; `GET /download/{job_id}/{ext}` serves the transcript files; `GET /api/history` lists prior jobs by globbing `transcripts/`.
- **`progress.py`** — in-memory `jobs: dict[str, JobState]` registry. Each `JobState` owns an `asyncio.Queue` and a `cancel_requested: bool`. Background threads call `update_progress_sync` / `set_result_sync` / `set_cancelled_sync`, which use `loop.call_soon_threadsafe(queue.put_nowait, ...)` to hand updates to the SSE consumer. `TERMINAL_STATUSES = {"complete", "error", "cancelled"}` is what `progress_stream` uses to close the SSE iterator. **Single-worker only** — for multi-worker deployments this needs Redis or DB backing (noted at the top of the file).

### Client-side queue (`web/static/app.js`)

The page is a **client-side sequential queue** — one job in flight at a time. The server is one-job-per-call (no batch endpoint); the queue lives entirely in JS.

- **Queue model:** `queue` array of `{ id, file, status, jobId, formats, sourceName, error }`. Statuses: `waiting`, `starting`, `uploading`/`downloading`/`converting`/`transcribing`/`saving` (active set), `complete`, `cancelled`, `error`.
- **Auto-start drain:** `enqueueFiles()` pushes valid files and calls `processNext()`. `processNext()` early-exits if `queueActive`; otherwise picks the first `waiting` item, POSTs to `/api/transcribe`, opens SSE via `listen(jobId, queueItem)`. On terminal status the SSE handler advances by calling `processNext()` again. There is **no pause/resume** — the user validated that mid-job pause doesn't make sense (Whisper has no checkpoint API), and queue-level pause was removed along with it.
- **Per-row controls** in `renderQueueRow`: `waiting → REMOVE`; active states → `STOP` (calls `stopQueueItem` → `POST /api/jobs/{jobId}/cancel`; disabled until `jobId` lands); `complete → download links` (each with `<a download="...">` set from `friendlyDownloadName(sourceName || file.name, ext)` so users get `meeting-transcript.txt` instead of `transcript-{uuid}.txt`); `cancelled | error → RESTART` (resets the item's status and triggers `processNext`; same `File` blob, new `job_id`).
- **The form submit button** is now only used for the URL one-shot path. When a URL is set with no queued files, `startJob` POSTs directly and listens on its own SSE stream (no queue item). When files are queued, `processNext` was already kicked off by `enqueueFiles`, and form submit is a no-op.

### Package entry points

`pyproject.toml` registers both `whisper-video-to-text` and `whisper_video_to_text` (hyphen + underscore) → `cli:main`. `python -m whisper_video_to_text` also works via `__main__.py`.

## Conventions

- **Python 3.9+** (CI matrix tests 3.9 and 3.12). Don't use 3.10+ syntax (`X | Y` unions in annotations, `match`, etc.) — `from __future__ import annotations` is fine where already used.
- **Line length 100** (black + ruff configured in `pyproject.toml`). Ruff rules: `E, F, I, UP, B`.
- **mypy is strict-ish**: `disallow_untyped_defs`, `disallow_incomplete_defs`, `no_implicit_optional`. Type all new public functions.
- **Logging, not print** — use the `logging` module. CLI configures handlers in `cli.py:main`.
- **Tests must mock external tools** (ffmpeg, yt-dlp, Whisper). The suite covers each module (`test_convert.py`, `test_download.py`, `test_transcribe.py`, `test_pipeline.py`, `test_cli.py`, `test_time_formatting.py`, `test_deeper_refactors.py`, `test_cancellation.py`) plus the web layer (`test_web_upload.py`, `test_web_media_formats.py`) — see them for the established mocking pattern. `test_convert.py` uses a small `_FakePopen` helper because `_run_ffmpeg` always goes through `Popen`. Keep tests hermetic — no network, no large files.
- **Conventional Commits** for messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`).
- Don't commit media or generated transcripts. `uploads/` and `transcripts/` are runtime dirs (already in `.gitignore`).

## Docker

`Dockerfile` derives runtime deps from the lockfile: `uv export --frozen --no-dev --no-emit-project --extra web` → `uv pip install --system -r requirements.txt`. `pyproject.toml` + `uv.lock` are the single source of truth — no hand-maintained install list. (The old `triton`/`openai-whisper==20231117` resolver conflict that forced dual maintenance was resolved by the `20250625` bump.)

`docker-compose.yml` mounts named volumes for `transcripts`, `uploads`, and the Whisper / yt-dlp caches at `/home/appuser/.cache/`. `docker-compose.dev.yml` is an override that bind-mounts `whisper_video_to_text/` and `tests/` into the container and runs uvicorn with `--reload` for live development.

## Feature planning workflow

- **Always use the `codex:codex-rescue` agent to build out feature plans.** When a feature is being planned, delegate the plan build-out to Codex by launching the `codex:codex-rescue` subagent (Agent tool, `subagent_type: "codex:codex-rescue"`) rather than drafting the implementation plan solo.
- **When a plan is complete, commit the change and push to origin.** Commit only the files belonging to the plan (Conventional Commits, as below), then `git push origin`.

## Behavioral guardrails

Distilled from [andrej-karpathy-skills](https://github.com/daryllundy/andrej-karpathy-skills) — only the parts that add signal over Claude Code's built-in defaults.

### Surface confusion, don't silently resolve it
- When a request has multiple plausible interpretations, present them. Don't pick one and run.
- If a simpler approach than what was asked exists, say so before implementing.
- When something is unclear, name what's unclear and ask. "Stuck quietly" is the failure mode.

### Match the codebase, not your preferences
- Match the existing style and patterns even if you'd do it differently in a greenfield project.
- If you spot unrelated dead code or rot, mention it — don't delete it as a drive-by.

### Goal-driven execution with verification
Transform imperative asks into verifiable goals:
- "Add validation" → write tests for invalid inputs, then make them pass.
- "Fix the bug" → write a test that reproduces it, then make it pass.
- "Refactor X" → confirm tests pass before and after.

For multi-step work, sketch the plan as `[step] → verify: [check]` so each step carries a concrete success criterion, then loop on each step until its check passes.
