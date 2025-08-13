.PHONY: install lint format typecheck test cov hooks web

install:
	uv pip install -e .[dev]

hooks:
	pre-commit install
	pre-commit run --all-files || true

lint:
	ruff check .

format:
	ruff check --fix .
	black .

typecheck:
	mypy whisper_video_to_text

test:
	pytest -v

cov:
	pytest --cov=whisper_video_to_text

web:
	uv run whisper_video_to_text/web/main.py
