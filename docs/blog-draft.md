# Turning a Daily Script Into a Portfolio-Grade Python Tool

I started this project the way a lot of useful tools start: I had a repetitive problem, a few working commands, and just enough annoyance to automate it.

I often needed transcripts from videos, voice notes, downloaded talks, and short clips. I did not want to upload private audio to a hosted service, and I did not want to repeat the same `ffmpeg`, Whisper, and file-renaming steps every time. The first version solved that problem for me. It accepted a media file, extracted audio, ran Whisper locally, and saved text.

That was enough for daily use. It was not enough for a portfolio project.

The gap between "it works on my machine" and "this demonstrates engineering judgment" is not about adding more features. It is about making the boundaries clear, making the tradeoffs explicit, and proving that the boring paths work.

## The Problem

The core workflow is simple:

1. Accept a local media file or a video URL.
2. Normalize the input into audio Whisper can handle reliably.
3. Run local transcription.
4. Save the output in formats that are useful for downstream work.

In practice, each step has edge cases.

Media files arrive as MP3, WAV, MOV, MP4, AIFF, and other variants. YouTube downloads can fail depending on available formats. Whisper works best when input audio is normalized. Plain text is useful for notes, but subtitles need SRT or VTT timestamps. A command-line tool is efficient for repeated use, while a web UI is friendlier for reviewing transcripts and downloading outputs.

The project became useful when it stopped being a single script and became a small pipeline.

## Design Goals

I used four constraints to guide the refactor.

First, transcription should run locally. That keeps private audio private and removes the need for API keys.

Second, the CLI and web UI should share the same core behavior. Two interfaces should not mean two implementations of transcription, formatting, or file handling.

Third, external tools should be isolated. `ffmpeg`, `yt-dlp`, and Whisper are powerful dependencies, but tests should not need network access, GPU availability, or large media files.

Fourth, the project should be honest about its scope. This is a local-first utility, not a multi-tenant transcription platform. The web UI uses in-memory job progress for a single process, and that limitation is documented clearly.

## The Pipeline

The core architecture is:

```text
local file or URL
  -> download/upload handling
  -> ffmpeg audio normalization
  -> Whisper transcription
  -> TXT/SRT/VTT rendering
  -> CLI output files or web downloads
```

The important part is not that each step exists. The important part is that each step has a clear owner.

The download layer handles `yt-dlp` and fallback format selection. The conversion layer handles ffmpeg commands and produces Whisper-ready WAV files. The transcription layer loads the model and returns structured segment data. The render layer (`render_txt`, `render_srt`, `render_vtt`) turns that structure into strings. The CLI and web app orchestrate these pieces through a single `run_transcription(request, progress)` call — neither reimplements any of it.

That separation makes the project easier to test and easier to explain.

## What Made The First Version Feel Messy

The original project grew through practical additions: first a CLI, then YouTube download support, then subtitle formats, then a web interface, then Docker. Each addition made the tool more useful, but it also increased the chance that logic would be duplicated across layers.

The clearest example was subtitle formatting. The CLI had output functions, and the web layer rebuilt similar SRT and VTT strings itself. That is a small smell, but portfolio reviewers notice small smells because they suggest how the project might scale.

Another issue was quality signaling. The README listed `make typecheck`, but type checking did not pass locally and CI did not run mypy. That kind of mismatch is easy to fix, but it matters because it undermines trust.

Several tests checked source file contents — asserting that specific strings appeared in `views.py` — rather than calling behavior and asserting on output. Those tests break on valid refactors, which is the opposite of what tests are for.

The goal of the cleanup was not to make the project bigger. It was to make the claims true.

## What Changed

The refactor touched every layer without adding new features:

- **Shared pipeline.** `pipeline.py` composes download → convert → transcribe → render into a single `run_transcription(request, progress)` function. CLI and web both call it. There is no duplicate sequencing logic.
- **Centralized renderers.** `render_txt`, `render_srt`, and `render_vtt` in `transcribe.py` return strings. `save_srt` and `save_vtt` delegate to them. The web layer imports the same functions — the duplicate `_format_srt_time` and `_format_vtt_time` functions are gone.
- **Type checking passes.** Eight mypy errors fixed across `cli.py`, `convert.py`, and `views.py`. Mypy now runs in CI, so `make typecheck` is truthful.
- **Behavior tests.** Source-inspection tests replaced with tests that call functions and assert on output. A dedicated `test_pipeline.py` covers formats, timestamps, file writing, progress callbacks, and the no-output-base mode.
- **Consistent Docker.** Compose and the app agree on port 8000. Health check URL matches the configured port.

## Testing Strategy

Testing a media transcription tool can get expensive and flaky if every test invokes real external tools. I treated external programs as integration boundaries.

Unit tests mock Whisper model loading, `ffmpeg`, and `yt-dlp`. That keeps the core suite fast and deterministic. Formatter tests use small transcription dictionaries and assert exact TXT, SRT, and VTT output. Pipeline tests verify orchestration without requiring network access or large media files.

For confidence outside unit tests, CI builds the Docker image and validates that the package imports, the CLI help works, and ffmpeg exists in the image. The matrix runs Python 3.9 and 3.12.

That combination gives useful coverage without pretending the test suite proves Whisper's model quality.

## Tradeoffs

The web UI uses in-memory job state. For a local single-user tool, that is acceptable and simple. For a multi-worker deployment, it would need Redis, a database, or another durable job backend — documented at the top of `progress.py` and in the README Limitations section.

The project depends on system ffmpeg. Vendoring ffmpeg would make setup heavier and create platform-specific maintenance work. Requiring ffmpeg in the environment is the right tradeoff for a developer-focused utility.

YouTube download support depends on `yt-dlp` and changing platform behavior. The code handles common format fallback cases, but the README is clear that URL downloads depend on upstream availability.

## What This Project Demonstrates

This project is not interesting because it calls Whisper. Calling a model is the easy part.

The useful engineering work is around the model: normalizing messy media inputs, isolating external tools at testable boundaries, designing a CLI that supports repeated use, exposing the same pipeline through a web UI without duplicating logic, and documenting limitations honestly rather than overclaiming.

That is the difference between a script and a project worth explaining in an interview.

---

**Resume bullet:**

> Built a local-first Python transcription tool that converts local media and YouTube sources into TXT/SRT/VTT using Whisper, with ffmpeg audio normalization, a shared CLI/web pipeline, FastAPI progress streaming, Docker deployment, mypy type checking, and CI-backed tests across Python 3.9 and 3.12.

**Portfolio blurb:**

> Whisper Video to Text is a local-first transcription utility I built after repeatedly needing reliable transcripts from videos, voice notes, and downloaded talks. It packages a practical media pipeline behind both a CLI and a FastAPI web UI, with ffmpeg normalization, Whisper inference, subtitle export, Docker support, and mocked tests for external tools. The refactor added a shared pipeline that both interfaces call, centralized subtitle renderers, passing mypy, and behavior tests — the kind of changes that make the project legible as engineering work rather than a script that grew.
