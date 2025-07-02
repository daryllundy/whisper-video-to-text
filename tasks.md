# Refactor Roadmap for Whisper Video ► Text (`tasks.md`)
Tick a box (`[x]`) after the task is finished and committed.

| ID | ☑ | Task |
|----|----|------|
| TASK-1 | [x] | Initialize project metadata: create **pyproject.toml** (PEP 621) with pinned deps (`whisper`, `yt-dlp`, `tqdm`, etc.) and Python version. |
| TASK-2 | [x] | Add **README.md** with overview, install instructions using `uv venv` + `uv pip install -r requirements.txt`, and example CLI usage. |
| TASK-3 | [x] | Introduce **logging** module (replace all `print` calls; `--verbose` sets level to `INFO`, otherwise `WARNING`). Add `--logfile` argument to optionally append logs to a file. |
| TASK-4 | [x] | Add **type hints** across mp4_to_text.py & run `mypy --strict`; fix any typing issues. |
| TASK-5 | [x] | Factor script into reusable package structure:<br>``whisper_video_to_text/{__init__.py,cli.py,download.py,convert.py,transcribe.py}``; wire CLI with **Typer**. |
| TASK-6 | [x] | Write **unit tests** with `pytest` mocking subprocess & whisper (coverage ≥ 80%). |
| TASK-7 | [x] | Emit **progress bars** using `tqdm` for download & ffmpeg conversion. |
| TASK-8 | [x] | Support **SRT & VTT export** (`--format srt|vtt|txt`). |
| TASK-9 | [x] | Create **GitHub Actions CI** running lint (`ruff`), type-check (`mypy`), and tests. |
| TASK-10 | [ ] | Build **Dockerfile** with ffmpeg + whisper; document in README. |

_Note:_ If you later drop or add tasks, keep IDs sequential (`TASK-n`) to ease commit messages.
