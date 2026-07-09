"""Characterization tests for the web progress registry and SSE stream."""

import asyncio
import threading
import uuid

import pytest

from whisper_video_to_text.web import progress
from whisper_video_to_text.web.progress import (
    create_job,
    get_job,
    is_cancel_requested,
    progress_stream,
    request_cancel_sync,
    set_cancelled_sync,
    set_result_sync,
    update_progress_sync,
)


def test_create_job_registers_pending_job():
    job_id = create_job()
    try:
        assert str(uuid.UUID(job_id)) == job_id

        job = get_job(job_id)
        assert job is not None
        assert job.status == "pending"
        assert job.progress == 0
        assert job.cancel_requested is False
    finally:
        progress.jobs.pop(job_id, None)


def test_get_job_returns_none_for_unknown_job():
    assert get_job("nope") is None


def test_request_cancel_sync_marks_active_job():
    job_id = create_job()
    try:
        assert request_cancel_sync(job_id) is True
        assert is_cancel_requested(job_id) is True
    finally:
        progress.jobs.pop(job_id, None)


def test_request_cancel_sync_returns_false_for_unknown_job():
    assert request_cancel_sync("nope") is False


def test_request_cancel_sync_returns_false_for_terminal_job():
    job_id = create_job()
    try:
        job = get_job(job_id)
        assert job is not None
        job.status = "complete"

        assert request_cancel_sync(job_id) is False
        assert job.cancel_requested is False
    finally:
        progress.jobs.pop(job_id, None)


def test_progress_stream_ends_after_complete_result():
    async def scenario():
        job_id = create_job()
        try:
            update_progress_sync(job_id, 50, "transcribing", "halfway")
            set_result_sync(job_id, {"text": "hi"})

            stream = progress_stream(job_id)
            first = await asyncio.wait_for(stream.__anext__(), timeout=2)
            second = await asyncio.wait_for(stream.__anext__(), timeout=2)

            assert first == {
                "progress": 50,
                "status": "transcribing",
                "message": "halfway",
            }
            assert second["status"] == "complete"
            assert second["result"] == {"text": "hi"}

            with pytest.raises(StopAsyncIteration):
                await asyncio.wait_for(stream.__anext__(), timeout=2)
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_progress_stream_ends_after_cancelled_status():
    async def scenario():
        job_id = create_job()
        try:
            update_progress_sync(job_id, 50, "transcribing", "halfway")
            set_cancelled_sync(job_id)

            stream = progress_stream(job_id)
            first = await asyncio.wait_for(stream.__anext__(), timeout=2)
            second = await asyncio.wait_for(stream.__anext__(), timeout=2)

            assert first == {
                "progress": 50,
                "status": "transcribing",
                "message": "halfway",
            }
            assert second["status"] == "cancelled"
            assert second["message"] == "Cancelled by user"

            with pytest.raises(StopAsyncIteration):
                await asyncio.wait_for(stream.__anext__(), timeout=2)
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_set_result_sync_updates_job_state():
    async def scenario():
        job_id = create_job()
        try:
            result = {"text": "hi"}
            set_result_sync(job_id, result)

            job = get_job(job_id)
            assert job is not None
            assert job.status == "complete"
            assert job.result == result
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_update_from_worker_thread_reaches_async_consumer():
    async def scenario():
        job_id = create_job()
        try:

            def worker():
                update_progress_sync(job_id, 60, "transcribing", "from thread")

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

            job = get_job(job_id)
            assert job is not None
            update = await asyncio.wait_for(job.queue.get(), timeout=2)

            assert update["status"] == "transcribing"
            assert update["progress"] == 60
            assert update["message"] == "from thread"
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())
