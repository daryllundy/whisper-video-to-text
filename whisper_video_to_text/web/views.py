from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from whisper_video_to_text.web.progress import create_job, update_progress

from fastapi.responses import StreamingResponse
import json
from whisper_video_to_text.web.progress import progress_stream, get_job
import os

# Ensure uploads directory exists at module initialization
os.makedirs('uploads', exist_ok=True)

router = APIRouter()

@router.get("/events/{job_id}")
async def events(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    async def event_generator():
        async for update in progress_stream(job_id):
            yield f"data: {json.dumps(update)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

import os
import shutil
import tempfile
from whisper_video_to_text.download import download_video
from whisper_video_to_text.convert import convert_mp4_to_mp3
from whisper_video_to_text.transcribe import transcribe_audio

def background_stub(job_id, file=None, url=None, model="base", language=None, formats=None, timestamps=False):
    import asyncio
    async def run():
        tempdir = tempfile.mkdtemp(prefix="wvttmp_")
        try:
            mp4_path = None
            # Download or save uploaded file
            if url:
                await update_progress(job_id, 10, "downloading", "Downloading video...")
                mp4_path = download_video(url, output_dir=tempdir)
            elif file:
                await update_progress(job_id, 10, "uploading", "Saving uploaded file...")
                # Save uploaded file to uploads directory
                dest = os.path.join('uploads', file.filename)
                with open(dest, "wb") as f_out:
                    shutil.copyfileobj(file.file, f_out)
                mp4_path = dest
            else:
                await update_progress(job_id, 100, "error", "No file or URL provided")
                return

            await update_progress(job_id, 30, "converting", "Extracting audio...")
            mp3_path = convert_mp4_to_mp3(mp4_path, verbose=False)

            await update_progress(job_id, 60, "transcribing", "Transcribing audio...")
            result = transcribe_audio(str(mp3_path), model_name=model, language=language, verbose=False)

            await update_progress(job_id, 90, "saving", "Saving transcript...")
            # Only return plain text for now; can add SRT/VTT later
            await update_progress(job_id, 100, "complete", "Done")
            from whisper_video_to_text.web.progress import set_result
            await set_result(job_id, result)
        except Exception as e:
            await update_progress(job_id, 100, "error", f"Error: {e}")
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)
    import asyncio
    asyncio.create_task(run())

@router.post("/api/transcribe")
async def transcribe_api(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
    url: str = Form(None),
    model: str = Form("base"),
    language: str = Form(None),
    formats: list[str] = Form(["txt"]),
    timestamps: bool = Form(False),
    request: Request = None
):
    # Create a new job
    job_id = create_job()
    # Start background task with user input
    background_tasks.add_task(
        background_stub,
        job_id,
        file=file,
        url=url,
        model=model,
        language=language,
        formats=formats,
        timestamps=timestamps
    )
    return JSONResponse({"job_id": job_id})
