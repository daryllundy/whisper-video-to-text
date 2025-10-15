import asyncio
import uuid

# In-memory job state and progress tracking
jobs = {}


class JobState:
    def __init__(self):
        self.progress = 0
        self.status = "pending"
        self.message = ""
        self.result = None
        self.queue = asyncio.Queue()


def create_job():
    job_id = str(uuid.uuid4())
    jobs[job_id] = JobState()
    return job_id


def get_job(job_id):
    return jobs.get(job_id)


async def update_progress(job_id, progress, status, message=""):
    job = get_job(job_id)
    if job:
        job.progress = progress
        job.status = status
        job.message = message
        await job.queue.put({"progress": progress, "status": status, "message": message})


async def set_result(job_id, result):
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


async def progress_stream(job_id):
    job = get_job(job_id)
    if not job:
        return
    while True:
        update = await job.queue.get()
        yield update
        if update.get("status") == "complete":
            break
