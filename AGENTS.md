# Repository Guidelines

## Project Structure & Modules
- `whisper_video_to_text/`: Core package (`cli.py`, `convert.py`, `download.py`, `transcribe.py`, `web/`).
- `tests/`: Pytest suite (`test_*.py`).
- Key files: `pyproject.toml` (scripts, deps), `Dockerfile`, `README.md`.
- CLI entry points: `whisper-video-to-text` and `whisper_video_to_text` (see `[project.scripts]`).

## Build, Test, and Development Commands
- Create env: `uv venv && source .venv/bin/activate`.
- Install (dev): `uv pip install -e .`.
- Run CLI: `uv run whisper_video_to_text path/to/video.mp4`.
- Run web UI: `uv pip install .[web] && uv run whisper_video_to_text/web/main.py`.
- Tests: `pytest` or `pytest --cov=whisper_video_to_text`.
- Docker: `docker build -t whisper-video-to-text .` then `docker run --rm whisper-video-to-text --help`.

## Coding Style & Naming
- Python 3.9+; follow PEP 8 with 4‑space indentation.
- Modules/files: `snake_case.py`; functions/vars: `snake_case`; classes: `CapWords`.
- Keep functions small, log with `logging`, and add docstrings for public interfaces.
- Type hints encouraged; keep imports sorted and minimal.

## Testing Guidelines
- Framework: `pytest` with tests under `tests/` named `test_*.py`.
- Aim for ~80% coverage (see README); add unit tests for new behavior and regressions.
- Prefer mocking external tools (ffmpeg, yt-dlp, Whisper) as in existing tests.
- Run `pytest -v` locally before pushing.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.
- Branch naming: `feature/<slug>` or `fix/<slug>`.
- PRs must include: clear description, linked issue, testing notes (commands run), and any relevant screenshots/CLI output.
- Keep PRs focused and small; update `README.md` if user-facing behavior changes.

## Security & Configuration Tips
- Requires local `ffmpeg`; do not commit large media or generated transcripts—keep them out of Git.
- Transcription runs locally (no API keys required). Be mindful of PII in shared examples.
- For repeatable runs, prefer `uv` workflows shown above.

