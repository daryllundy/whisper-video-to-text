# Job Controls and Queue Handoff

This document scopes the next web workflow features:

- Stop an in-progress transcription job.
- Pause and resume an in-progress job where feasible.
- Queue multiple dropped files and produce one transcript set per file.

The project is currently a local-first FastAPI app with in-memory job state and a shared synchronous transcription pipeline. That architecture is enough for a stop button and an in-browser multi-file queue. True pause/resume is more constrained because `ffmpeg` and Whisper run as blocking external/CPU-heavy steps.

## Current State

Relevant files:

- `whisper_video_to_text/pipeline.py`
- `whisper_video_to_text/convert.py`
- `whisper_video_to_text/transcribe.py`
- `whisper_video_to_text/web/progress.py`
- `whisper_video_to_text/web/views.py`
- `whisper_video_to_text/web/static/app.js`
- `whisper_video_to_text/web/templates/index.html`
- `whisper_video_to_text/web/static/style.css`
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.dev.yml`

Current behavior:

- A single upload or URL creates one job.
- FastAPI `BackgroundTasks` runs `run_transcription_task`.
- Progress events stream over `/events/{job_id}`.
- Uploaded files are saved to `uploads/{job_id}{suffix}`.
- Output files are written to `transcripts/{job_id}.{txt,srt,vtt}`.
- Job state is in memory only.
- Drag and drop now selects one valid media file and submits through the existing file input.

Important constraint:

- `run_transcription()` is synchronous and has no cancellation token.
- `convert_media_to_whisper_audio()` shells out to `ffmpeg` through `subprocess.run()` or `subprocess.Popen()`.
- `transcribe_audio()` calls Whisper as a blocking Python call.

## Recommended Direction

Build this in two phases.

### Phase 1: Stop and Multi-File Queue

This is the practical next feature set.

Deliver:

1. Client-side queue for multiple dragged files.
2. Sequential upload/transcription of each queued file.
3. Per-file status rows.
4. A stop button for the active job.
5. Backend cancellation that can interrupt `ffmpeg` and prevent later pipeline stages from starting.

This fits the current single-process local app and does not require a database.

### Phase 2: Pause and Resume

Treat pause/resume as a separate design pass.

Useful pause behavior:

- Pause before a queued item starts.
- Pause between pipeline phases.
- Pause the queue after the current file completes.

Risky pause behavior:

- Pausing Whisper mid-transcription and resuming from the same in-memory model state.
- Pausing `ffmpeg` portably across local macOS, Linux containers, and future deployment targets.

Recommendation:

- Implement "pause queue" first.
- Rename true mid-job pause to "defer after current step" unless the process-control behavior is proven reliable.

## Stop Button Design

### Backend API

Add:

```text
POST /api/jobs/{job_id}/cancel
```

Response:

```json
{
  "job_id": "...",
  "status": "cancel_requested"
}
```

Behavior:

- If job does not exist: return `404`.
- If job is already terminal: return current terminal state.
- Otherwise mark the job as cancel requested.
- Active workers should observe cancellation and emit a final `cancelled` progress event.

### Job State

Extend `web/progress.py`:

- Add `cancel_requested: bool`.
- Add helpers:
  - `request_cancel_sync(job_id: str) -> bool`
  - `is_cancel_requested(job_id: str) -> bool`

Keep this in memory for now to match existing job state.

### Pipeline Cancellation

Add a cancellation callback to `TranscriptionRequest` or `run_transcription()`:

```python
CancelCheck = Callable[[], bool]

def run_transcription(
    request: TranscriptionRequest,
    progress: ProgressCallback | None = None,
    should_cancel: CancelCheck | None = None,
) -> TranscriptionResult:
```

Check before each phase:

- Before download.
- Before conversion.
- Before transcription.
- Before rendering/writing output.

Use a custom exception:

```python
class TranscriptionCancelled(Exception):
    pass
```

### Interrupting ffmpeg

`convert_media_to_whisper_audio()` currently delegates process execution to `_run_ffmpeg()`.

Update `_run_ffmpeg()` to support cancellation:

```python
def _run_ffmpeg(
    cmd: list[str],
    duration: Optional[float],
    should_cancel: Callable[[], bool] | None = None,
) -> None:
```

Implementation detail:

- Use `subprocess.Popen()` for both progress and non-progress paths so cancellation can terminate the child process.
- Poll the process.
- If cancellation is requested:
  - call `process.terminate()`
  - wait briefly
  - call `process.kill()` if needed
  - remove the incomplete output file if it exists
  - raise `TranscriptionCancelled`

### Interrupting Whisper

Whisper itself is harder to interrupt cleanly because `model.transcribe()` is one blocking call.

Recommended Phase 1 behavior:

- Stop can cancel immediately during upload/download/ffmpeg.
- Stop can mark cancellation during Whisper.
- The worker checks cancellation immediately after Whisper returns and skips rendering/output.
- UI copy should say "Stop requested..." while the active Whisper call winds down.

Future option:

- Move transcription into a separate process and terminate the process for hard cancellation.
- This is more complex because model load time and IPC need handling.

## Pause and Resume Design

### Practical Version: Pause Queue

Add queue-level controls:

- Pause queue.
- Resume queue.
- Stop current item.
- Clear waiting items.

Behavior:

- If an item is waiting, pause prevents it from starting.
- If an item is active, pause takes effect after the current item finishes or is stopped.
- Resume starts the next waiting item.

This is predictable and does not risk corrupting media outputs.

### Mid-Job Pause

Mid-job pause is not recommended for the first implementation.

Reasons:

- `ffmpeg` process pause/resume differs by OS and container runtime.
- Whisper transcription is a blocking function call.
- Persisting enough state to resume from the exact point is not currently available.

If mid-job pause is still required:

- Implement it only for `ffmpeg` first.
- Use process signals on Unix-like platforms.
- Hide or disable it on unsupported platforms.
- Document that Whisper pause is not supported.

## Multi-File Queue Design

### UI Behavior

Allow multiple files in the picker and drag/drop:

```html
<input id="file" name="file" type="file" multiple ... />
```

Queue row fields:

- File name.
- File type.
- Size.
- Status: waiting, uploading, converting, transcribing, saving, complete, error, cancelled.
- Downloads when complete.
- Remove button for waiting items.

Queue controls:

- Start queue.
- Pause queue.
- Resume queue.
- Stop active.
- Clear completed.

### Client-Side Model

In `app.js`, keep an in-memory queue:

```js
const queue = [
  {
    id: crypto.randomUUID(),
    file,
    status: 'waiting',
    jobId: null,
    result: null,
    error: null,
  },
];
```

Only one active upload at a time for Phase 1.

Benefits:

- Simple resource use.
- Avoids running multiple Whisper jobs concurrently on the same machine.
- Predictable progress UI.

### Backend API

Keep the backend one-job-per-file at first.

The client should submit each file individually to:

```text
POST /api/transcribe
```

That avoids adding a bulk upload endpoint immediately.

Future bulk endpoint:

```text
POST /api/transcribe/batch
```

Only add this if the client-side sequential queue becomes too limiting.

### Output Naming

Current output naming is job-based:

```text
transcripts/{job_id}.txt
transcripts/{job_id}.srt
transcripts/{job_id}.vtt
```

For queue UX, preserve original file names in job result metadata:

```json
{
  "text": "...",
  "language": "en",
  "source_name": "meeting.m4a",
  "formats": {
    "txt": "..."
  }
}
```

Download filenames can become:

```text
meeting-transcript-{job_id}.txt
```

Keep the stored server path job-based to avoid filename collision and path traversal issues.

## Suggested Implementation Order

1. Add job cancellation state and `/api/jobs/{job_id}/cancel`.
2. Thread cancellation checks through `run_transcription()`.
3. Make `ffmpeg` execution cancellable.
4. Add `cancelled` status handling in SSE/UI.
5. Add one-file stop button to prove the backend path.
6. Change file input/drop handling to accept multiple files.
7. Add queue rendering and sequential processing.
8. Add pause/resume for waiting queue items.
9. Add tests.
10. Update Docker health checks if the rendered page or runtime checks change.

## Testing Plan

Backend tests:

- Cancelling an unknown job returns `404`.
- Cancelling a queued/running job marks it cancel requested.
- `run_transcription()` stops before conversion when cancellation is already requested.
- `run_transcription()` skips rendering/output after cancellation.
- `_run_ffmpeg()` terminates an active process when cancellation is requested.
- Cancelled jobs emit terminal `cancelled` progress.

Web tests:

- Stop button calls `/api/jobs/{job_id}/cancel`.
- UI returns to an idle state after `cancelled`.
- Multiple dropped valid files populate the queue.
- Invalid files are rejected without removing valid queued files.
- Queue processes files sequentially.
- Pause prevents the next waiting item from starting.
- Resume starts the next waiting item.

Manual/browser tests:

- Drag three valid media files onto the page.
- Start queue and confirm one active job at a time.
- Stop during `ffmpeg` conversion.
- Stop during Whisper transcription and confirm UI shows stop requested until terminal state.
- Pause queue while first item is active; confirm second item does not start.
- Resume queue; confirm second item starts.
- Download transcripts for each completed item.

Docker checks:

- `docker compose config --quiet`
- `docker compose up -d --build web`
- Container health reports `healthy`.
- Rendered page includes queue controls once implemented.
- Container can import the updated cancellation/queue modules.

## Risks and Decisions

Open decisions:

- Should stopping during Whisper hard-kill the worker process, or only prevent output after Whisper returns?
- Should queue state survive page refresh?
- Should queue state survive container restart?
- Should the web app allow concurrent transcriptions, or always enforce sequential processing?
- Should URL jobs join the same queue as files?

Recommended defaults:

- No hard kill for Whisper in Phase 1.
- No persistence across refresh/restart in Phase 1.
- Sequential processing only.
- Keep URL jobs separate until file queue is stable.

## Definition of Done

Phase 1 is done when:

- The page accepts multiple dropped files.
- The user can start a sequential queue.
- Each file produces its own transcript downloads.
- The user can stop the active job.
- The active `ffmpeg` process is terminated when stopped.
- The UI reports cancelled jobs clearly.
- Tests pass locally.
- Dockerfile and Compose files have been reviewed and updated if needed.
- The rebuilt container is healthy.
