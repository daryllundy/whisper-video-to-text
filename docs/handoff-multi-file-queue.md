# Handoff: Multi-File Queue (Phase 1 step 6-7)

This document hands off the remaining Phase 1 work from
`docs/job-controls-and-queue-handoff.md` to a follow-up session.

## What is already done

Backend cancellation, the `/api/jobs/{job_id}/cancel` endpoint, the stop
button in the UI, and tests for all of the above are merged on
`feat/job-control-and-queue-handoff` (commits `92f67aa` → `ab21b64`).

All 90 tests pass (`uv run pytest`), `make lint`, and `mypy` are clean.

Implemented surface:

- `whisper_video_to_text/errors.py` — `TranscriptionCancelled` exception
  in a standalone module to avoid a circular import between `pipeline.py`
  and `convert.py`.
- `whisper_video_to_text/pipeline.py` — `run_transcription()` accepts a
  `should_cancel: Callable[[], bool] | None` kwarg and checks before
  download / convert / transcribe / render. Raises `TranscriptionCancelled`.
- `whisper_video_to_text/convert.py` — `_run_ffmpeg()` was rewritten to
  always use `subprocess.Popen` (instead of branching on `duration`), polls
  `should_cancel` while reading stderr, and on cancel: `terminate()` →
  brief wait → `kill()` → unlink partial output → raise
  `TranscriptionCancelled`. `convert_media_to_whisper_audio()` accepts and
  forwards `should_cancel`.
- `whisper_video_to_text/web/progress.py` — `JobState.cancel_requested`,
  `request_cancel_sync`, `is_cancel_requested`, `set_cancelled_sync`, and
  a `TERMINAL_STATUSES` set used by `progress_stream` to close on
  `complete | error | cancelled`.
- `whisper_video_to_text/web/views.py` — `POST /api/jobs/{job_id}/cancel`
  endpoint; `run_transcription_task` passes `should_cancel`, catches
  `TranscriptionCancelled`, and also handles "Whisper finished but cancel
  was already requested" by checking `is_cancel_requested(job_id)`
  immediately after `run_transcription()` returns.
- `whisper_video_to_text/web/templates/index.html` — `#stop-btn` inside a
  `.status-card__controls` div.
- `whisper_video_to_text/web/static/app.js` — `activeJobId` tracking,
  `showStopButton` / `hideStopButton`, `handleStopClick` POSTs to the
  cancel endpoint, SSE listener treats `cancelled` as terminal alongside
  `complete` and `error`.
- `tests/test_cancellation.py` — pipeline cancellation, ffmpeg
  termination, cancel endpoint (404 / cancel_requested / terminal), worker
  emits `cancelled` progress.

Behavioral note on Whisper: per the design doc, Whisper itself is one
blocking call. Cancellation requested during it does NOT kill Python; the
worker observes the flag once `model.transcribe()` returns and skips
rendering/output via `set_cancelled_sync`. The UI copy already says
`STOPPING...` while we wait. This was the recommended Phase 1 behavior.

## What is left (this handoff)

Phase 1 step 6 and 7 in `docs/job-controls-and-queue-handoff.md`:

1. **Multiple-file input.** Add `multiple` to `#file` in
   `templates/index.html`. Update drag handling so multi-file drops feed
   the queue instead of rejecting them (`handleDrop` in `app.js`
   currently shows `ONE FILE ONLY`).
2. **In-memory client-side queue model** in `app.js`. The doc spec is:
   ```js
   const queue = [{ id: crypto.randomUUID(), file, status: 'waiting',
                    jobId: null, result: null, error: null }];
   ```
3. **Per-file row rendering**, ideally in a new `<section>` of
   `index.html` next to the existing status card. Each row needs:
   file name, size, status badge, downloads when complete, remove button
   while waiting, and a stop button while active.
4. **Sequential drain loop.** Only one job in flight at a time. When the
   current job's SSE stream reaches a terminal state, advance to the next
   `waiting` item.
5. **Queue controls:** start, pause (prevents next waiting from
   starting), resume, stop active (routes to existing
   `/api/jobs/{id}/cancel`), clear completed.
6. **Tests:**
   - Backend: nothing new required; the endpoint and pipeline already
     handle one-job-at-a-time. The doc explicitly says "Keep the backend
     one-job-per-file at first" — do not add a batch endpoint.
   - Web/JS: `tests/test_web_media_formats.py` is the place to assert
     that `<input ... multiple>` and queue control elements render. The
     suite reads `app.js` text for binding assertions — add similar
     assertions for the queue functions you introduce.
7. **Filename UX (optional but in the doc):** preserve original filename
   in the SSE `result` payload so download buttons can show
   `meeting-transcript-{job_id}.txt`. The doc suggests adding
   `source_name` to the result; that means a tiny update to
   `run_transcription_task` (carry `file.filename` into the result dict)
   and to the SSE/UI consumer.

## Constraints and gotchas to know going in

- **Auto-commit hook is on.** Each `TaskUpdate` to `completed` triggers
  an auto-commit named `auto-commit: task N completed`. Keep tasks
  granular so commits stay coherent, and don't be alarmed by the noisy
  log — it's expected on this branch.
- **`progress_stream` already closes on `cancelled`.** No SSE-side
  changes needed for the queue. New rows just listen on their own
  `/events/{job_id}` and react to terminal statuses.
- **`activeJobId` is a single global in `app.js`.** When you move to a
  queue, either repurpose it for "currently-active job" (still
  single-track) or replace with a queue-driven `currentItem` reference.
  The stop button can stay tied to the active row.
- **`handleDrop` currently rejects multi-file drops** with
  `ONE FILE ONLY` — that branch needs to go.
- **Keep `/api/transcribe` one-file-per-call.** Per the doc, do not add
  `/api/transcribe/batch` in Phase 1. The client just POSTs each file
  serially.
- **Don't add concurrent processing.** Same Whisper model load,
  single-CPU concern. Sequential only.
- **CSS lives in `whisper_video_to_text/web/static/style.css`.** I did
  not need to touch it for the stop button (reuses `btn-compact`); the
  queue list will likely need new rules.
- **URL jobs stay separate.** The doc says "Keep URL jobs separate
  until file queue is stable." Treat the YouTube URL input as a
  single-shot path, not a queue source.

## Suggested order

1. Add `multiple` to `<input id="file">` and rip the `ONE FILE ONLY`
   branch out of `handleDrop`.
2. Build a tiny queue module in `app.js` (`enqueue`, `dequeue`, `next`,
   `renderQueue`) before rewiring `startJob`.
3. Refactor `startJob` to push files into the queue and kick off the
   drain loop. The drain loop calls a new `processNext()` that posts
   one file to `/api/transcribe`, opens SSE, and on terminal status
   advances.
4. Add queue control buttons + handlers.
5. Add tests (`test_web_media_formats.py` for HTML/JS surface, and a
   new `tests/test_web_queue.py` if you want JS behavior assertions
   beyond string matching).
6. Browser smoke test per the doc's "Manual/browser tests" section.

## Definition of done (unchanged from the source doc)

- Page accepts multiple dropped files.
- User can start a sequential queue; each file produces its own
  downloads.
- Stop active job works (already wired — confirm it still works after
  the refactor).
- UI reports `cancelled` clearly per row.
- `uv run pytest`, `make lint`, `mypy` all clean.
- Docker container rebuilds and reports `healthy`; rendered page
  includes queue controls.

## Files touched so far on this branch

```
whisper_video_to_text/errors.py                  (new)
whisper_video_to_text/pipeline.py
whisper_video_to_text/convert.py
whisper_video_to_text/web/progress.py
whisper_video_to_text/web/views.py
whisper_video_to_text/web/templates/index.html
whisper_video_to_text/web/static/app.js
tests/test_cancellation.py                       (new)
tests/test_convert.py                            (rewritten to mock Popen)
tests/test_web_media_formats.py                  (fake_convert sig update)
tests/test_web_upload.py                         (fake_run sig update)
```
