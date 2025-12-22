import asyncio
import uuid
from typing import AsyncIterator

# In-memory job state. NOTE: Only works with single-worker deployment.
# For multi-worker, migrate to Redis or database-backed storage.
jobs: dict[str, "JobState"] = {}


class JobState:
    def __init__(self) -> None:
        self.progress: int = 0
        self.status: str = "pending"
        self.message: str = ""
        self.result: dict | None = None
        self.queue: asyncio.Queue = asyncio.Queue()


def create_job() -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState()
    return job_id


def get_job(job_id: str) -> JobState | None:
    """Get a job by ID, or None if not found."""
    return jobs.get(job_id)


async def update_progress(
    job_id: str, progress: int, status: str, message: str = ""
) -> None:
    """Update job progress (async version for use from async context)."""
    job = get_job(job_id)
    if job:
        job.progress = progress
        job.status = status
        job.message = message
        await job.queue.put({"progress": progress, "status": status, "message": message})


def update_progress_sync(
    job_id: str, progress: int, status: str, message: str = ""
) -> None:
    """Update job progress (sync version for use from background threads).
    
    This creates a new event loop to safely put updates on the async queue
    from a synchronous thread context.
    """
    job = get_job(job_id)
    if job:
        job.progress = progress
        job.status = status
        job.message = message
        # Use call_soon_threadsafe or create a loop for thread-safe queue access
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(
                job.queue.put_nowait,
                {"progress": progress, "status": status, "message": message},
            )
        except RuntimeError:
            # No running loop - use put_nowait directly (safe if queue is empty)
            job.queue.put_nowait(
                {"progress": progress, "status": status, "message": message}
            )


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
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(job.queue.put_nowait, update)
        except RuntimeError:
            job.queue.put_nowait(update)


async def progress_stream(job_id: str) -> AsyncIterator[dict]:
    """Stream progress updates for a job."""
    job = get_job(job_id)
    if not job:
        return
    while True:
        update = await job.queue.get()
        yield update
        if update.get("status") == "complete":
            break

