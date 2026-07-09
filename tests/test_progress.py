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
            stream = progress_stream(job_id)
            first_update = asyncio.create_task(stream.__anext__())
            await asyncio.sleep(0)

            update_progress_sync(job_id, 50, "transcribing", "halfway")
            set_result_sync(job_id, {"text": "hi"})

            first = await asyncio.wait_for(first_update, timeout=2)
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
            stream = progress_stream(job_id)
            first_update = asyncio.create_task(stream.__anext__())
            await asyncio.sleep(0)

            update_progress_sync(job_id, 50, "transcribing", "halfway")
            set_cancelled_sync(job_id)

            first = await asyncio.wait_for(first_update, timeout=2)
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


def test_thread_emission_wakes_waiting_consumer_promptly():
    async def scenario():
        job_id = create_job()  # captures the running loop
        try:
            job = get_job(job_id)
            assert job is not None and job.loop is not None

            async def consume():
                return await job.queue.get()

            task = asyncio.create_task(consume())
            await asyncio.sleep(0)  # ensure consumer is parked on the queue

            t = threading.Thread(target=update_progress_sync, args=(job_id, 42, "converting", "hi"))
            t.start()
            update = await asyncio.wait_for(task, timeout=2)
            t.join()
            assert update["progress"] == 42
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_create_job_outside_loop_buffers_update():
    job_id = create_job()
    try:
        job = get_job(job_id)
        assert job is not None
        assert job.loop is None

        update_progress_sync(job_id, 42, "converting", "hi")

        assert job.queue.get_nowait() == {
            "progress": 42,
            "status": "converting",
            "message": "hi",
        }
    finally:
        progress.jobs.pop(job_id, None)


def test_progress_stream_replays_complete_result():
    async def scenario():
        job_id = create_job()
        try:
            live_stream = progress_stream(job_id)
            live_update = asyncio.create_task(live_stream.__anext__())
            await asyncio.sleep(0)

            set_result_sync(job_id, {"text": "hi"})
            assert (await asyncio.wait_for(live_update, timeout=2))["status"] == "complete"
            with pytest.raises(StopAsyncIteration):
                await asyncio.wait_for(live_stream.__anext__(), timeout=2)

            async def collect_replay():
                return [update async for update in progress_stream(job_id)]

            replay = await asyncio.wait_for(collect_replay(), timeout=2)
            assert len(replay) == 1
            assert replay[0]["status"] == "complete"
            assert replay[0]["result"] == {"text": "hi"}
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_progress_stream_replays_error():
    async def scenario():
        job_id = create_job()
        try:
            update_progress_sync(job_id, 100, "error", "boom")

            async def collect_replay():
                return [update async for update in progress_stream(job_id)]

            replay = await asyncio.wait_for(collect_replay(), timeout=2)
            assert len(replay) == 1
            assert replay[0] == {
                "progress": 100,
                "status": "error",
                "message": "boom",
            }
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_terminal_job_is_removed_after_retention_period(monkeypatch):
    monkeypatch.setattr(progress, "JOB_RETENTION_SECONDS", 0.05)

    async def scenario():
        job_id = create_job()
        try:
            set_result_sync(job_id, {"text": "hi"})
            await asyncio.sleep(0.2)
            assert get_job(job_id) is None
        finally:
            progress.jobs.pop(job_id, None)

    asyncio.run(scenario())


def test_terminal_job_without_loop_is_not_scheduled_for_cleanup():
    job_id = create_job()
    try:
        job = get_job(job_id)
        assert job is not None
        assert job.loop is None

        set_result_sync(job_id, {"text": "hi"})

        assert get_job(job_id) is job
    finally:
        progress.jobs.pop(job_id, None)
