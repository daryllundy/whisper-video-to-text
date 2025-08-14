Contributing Guide
==================

Thanks for your interest in improving Whisper Video → Text! This guide outlines how to set up your environment, contribute code, and submit high‑quality pull requests.

Getting Started
---------------

- Python: 3.9+
- System: ffmpeg installed and in PATH
- Recommended: uv for fast, reproducible workflows

Setup
-----

1) Create a virtual environment and install dev deps

```
uv venv && source .venv/bin/activate
uv pip install -e .[dev]
```

2) Enable pre‑commit hooks (first time only)

```
pre-commit install
# Optionally run on all files once
pre-commit run --all-files
```

Project Conventions
-------------------

- Style: PEP 8, 4‑space indent, type hints encouraged
- Naming: snake_case for files, functions, variables; CapWords for classes
- Logging: use the logging module (no prints in library code)
- Imports: keep minimal and sorted
- Python version: 3.9+

Local Commands
--------------

```
# Lint and format
ruff check .
black .

# Type check
mypy whisper_video_to_text

# Run tests
pytest -v

# Coverage
pytest --cov=whisper_video_to_text
```

Testing Guidelines
------------------

- Framework: pytest (tests in tests/ named test_*.py)
- Aim for ~80% coverage for changed code
- Mock external tools (ffmpeg, yt-dlp, Whisper) in tests
- Keep tests fast and hermetic; avoid network and large files

Commit & PR Guidelines
----------------------

- Conventional Commits for messages: feat:, fix:, docs:, test:, chore:, refactor:
- Branch naming: feature/<slug> or fix/<slug>
- PR checklist:
  - Clear description of the change and rationale
  - Linked issue (if applicable)
  - Testing notes: commands run and outcomes
  - Update README or docs if user-facing behavior changes
- Keep PRs small and focused; prefer follow-ups over mega changes

Security & Repo Hygiene
-----------------------

- Do not commit large media or generated transcripts/subtitles
- ffmpeg is required locally; do not vendor binaries
- All transcription runs locally (no API keys); avoid sharing PII in examples

Web UI
------

```
uv pip install .[web]
uv run whisper_video_to_text/web/main.py
# Visit http://127.0.0.1:8000
```

Release & CI
------------

- CI runs lint (ruff), format check (black), type check (mypy), and tests with coverage
- Keep dependencies pinned in pyproject and prefer uv workflows for reproducibility

Thanks again for contributing! 🙌
