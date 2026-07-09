from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Optional

# In-memory job state. NOTE: Only works with single-worker deployment.
# For multi-worker, migrate to Redis or database-backed storage.
jobs: dict[str, JobState] = {}


TERMINAL_STATUSES = frozenset({"complete", "error", "cancelled"})


class JobState:
    def __init__(self) -> None:
        self.progress: int = 0
        self.status: str = "pending"
        self.message: str = ""
        self.result: Optional[dict] = None  # noqa: UP045
        self.queue: asyncio.Queue = asyncio.Queue()
        self.cancel_requested: bool = False
        self.loop: asyncio.AbstractEventLoop | None = None


def create_job() -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())
    state = JobState()
    try:
        state.loop = asyncio.get_running_loop()
    except RuntimeError:
        state.loop = None  # created outside an event loop (tests, CLI)
    jobs[job_id] = state
    return job_id


def get_job(job_id: str) -> Optional[JobState]:  # noqa: UP045
    """Get a job by ID, or None if not found."""
    return jobs.get(job_id)


def _emit_threadsafe(job: JobState, update: dict) -> None:
    """Hand an update to the SSE consumer, crossing threads safely.

    Uses the loop captured at job creation when available; falls back to a
    direct put only when no loop was ever captured (unit tests without a
    server).
    """
    if job.loop is not None and not job.loop.is_closed():
        job.loop.call_soon_threadsafe(job.queue.put_nowait, update)
    else:
        job.queue.put_nowait(update)


def request_cancel_sync(job_id: str) -> bool:
    """Mark a job as cancel-requested. Returns False if job is unknown or terminal."""
    job = get_job(job_id)
    if not job or job.status in TERMINAL_STATUSES:
        return False
    job.cancel_requested = True
    return True


def is_cancel_requested(job_id: str) -> bool:
    """Return True if cancellation has been requested for this job."""
    job = get_job(job_id)
    return bool(job and job.cancel_requested)


def set_cancelled_sync(job_id: str, message: str = "Cancelled by user") -> None:
    """Mark a job as cancelled and emit a terminal SSE update."""
    job = get_job(job_id)
    if not job:
        return
    job.status = "cancelled"
    job.message = message
    update = {"progress": job.progress, "status": "cancelled", "message": message}
    _emit_threadsafe(job, update)


async def update_progress(job_id: str, progress: int, status: str, message: str = "") -> None:
    """Update job progress (async version for use from async context)."""
    job = get_job(job_id)
    if job:
        job.progress = progress
        job.status = status
        job.message = message
        await job.queue.put({"progress": progress, "status": status, "message": message})


def update_progress_sync(job_id: str, progress: int, status: str, message: str = "") -> None:
    """Update job progress (sync version for use from background threads).

    This creates a new event loop to safely put updates on the async queue
    from a synchronous thread context.
    """
    job = get_job(job_id)
    if job:
        job.progress = progress
        job.status = status
        job.message = message
        _emit_threadsafe(job, {"progress": progress, "status": status, "message": message})


async def set_result(job_id: str, result: dict) -> None:
    """Set the final result for a job (async version)."""
    job = get_job(job_id)
    if job:
        job.result = result
        job.status = "complete"
        await job.queue.put(
            {
                "progress": 100,
                "status": "complete",
                "message": "Transcription complete",
                "result": result,
            }
        )


def set_result_sync(job_id: str, result: dict) -> None:
    """Set the final result for a job (sync version for background threads)."""
    job = get_job(job_id)
    if job:
        job.result = result
        job.status = "complete"
        update = {
            "progress": 100,
            "status": "complete",
            "message": "Transcription complete",
            "result": result,
        }
        _emit_threadsafe(job, update)


async def progress_stream(job_id: str) -> AsyncIterator[dict]:
    """Stream progress updates for a job."""
    job = get_job(job_id)
    if not job:
        return
    while True:
        update = await job.queue.get()
        yield update
        if update.get("status") in TERMINAL_STATUSES:
            break
