"""Tests for the background task queue."""

import asyncio

import pytest

from backend.services.background import BackgroundTask, TaskQueue, TaskStatus


async def dummy_task():
    return "done"


async def slow_task():
    await asyncio.sleep(10)
    return "should not reach"


async def failing_task():
    raise ValueError("intentional failure")


async def progressive_task():
    return 42


def make_queue(max_concurrent=3, default_timeout=5.0):
    return TaskQueue(max_concurrent=max_concurrent, default_timeout=default_timeout)


class TestSubmitTask:
    def test_submit_returns_id(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            result["task_id"] = task_id

        asyncio.run(run())
        assert isinstance(result["task_id"], str)
        assert len(result["task_id"]) > 0

    def test_task_registered(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            result["task_id"] = task_id

        asyncio.run(run())
        task = queue.get_status(result["task_id"])
        assert task is not None
        assert task.id == result["task_id"]
        assert task.name == "dummy_task"

    def test_submit_with_custom_name(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task, name="my_custom_task")
            result["task_id"] = task_id

        asyncio.run(run())
        task = queue.get_status(result["task_id"])
        assert task.name == "my_custom_task"

    def test_task_runs_to_completion(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["task"].status == TaskStatus.COMPLETED
        assert result["task"].result == "done"
        assert result["task"].progress == 100.0


class TestTaskStatusTransitions:
    def test_pending_to_running_to_completed(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            task = queue.get_status(task_id)
            result["initial"] = task.status
            await asyncio.sleep(0.5)
            result["final"] = task.status
            result["started_at"] = task.started_at
            result["completed_at"] = task.completed_at

        asyncio.run(run())
        assert result["initial"] in (TaskStatus.PENDING, TaskStatus.RUNNING)
        assert result["final"] == TaskStatus.COMPLETED
        assert result["started_at"] is not None
        assert result["completed_at"] is not None

    def test_created_at_set(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["task"].created_at is not None

    def test_completed_timestamp_after_running(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            task = queue.get_status(task_id)
            result["started"] = task.started_at
            result["completed"] = task.completed_at

        asyncio.run(run())
        assert result["completed"] >= result["started"]


class TestTaskCancellation:
    def test_cancel_pending_task(self):
        queue = make_queue()
        result = {}

        async def run():
            async def blocking():
                await asyncio.sleep(100)

            task_id = queue.submit(blocking)
            await asyncio.sleep(0.05)

            cancel_result = queue.cancel(task_id)
            result["cancel"] = cancel_result
            await asyncio.sleep(0.1)

            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["cancel"] is True
        assert result["task"].status == TaskStatus.CANCELLED

    def test_cancel_nonexistent_returns_false(self):
        queue = make_queue()

        async def run():
            result = queue.cancel("nonexistent-id")
            assert result is False

        asyncio.run(run())

    def test_cancel_completed_task(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            task = queue.get_status(task_id)
            result["status_before_cancel"] = task.status
            result["cancel"] = queue.cancel(task_id)

        asyncio.run(run())
        assert result["status_before_cancel"] == TaskStatus.COMPLETED
        assert result["cancel"] is False


class TestTaskTimeout:
    def test_timeout_marks_failure(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(slow_task, timeout=0.1)
            await asyncio.sleep(0.5)
            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["task"].status == TaskStatus.FAILED
        assert "timed out" in result["task"].error.lower()

    def test_no_timeout_runs_normally(self):
        queue = make_queue()
        result = {}

        async def run():
            async def quick():
                return "ok"

            task_id = queue.submit(quick)
            await asyncio.sleep(0.3)
            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["task"].status == TaskStatus.COMPLETED


class TestTaskFailure:
    def test_exception_marks_failure(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(failing_task)
            await asyncio.sleep(0.5)
            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["task"].status == TaskStatus.FAILED
        assert "intentional failure" in result["task"].error

    def test_error_field_populated(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(failing_task)
            await asyncio.sleep(0.5)
            result["task"] = queue.get_status(task_id)

        asyncio.run(run())
        assert result["task"].error is not None


class TestConcurrentLimit:
    def test_respects_max_concurrent(self):
        queue = make_queue(max_concurrent=3)
        result = {"started": []}

        async def tracked():
            result["started"].append(True)
            await asyncio.sleep(1.0)
            result["started"].pop()

        async def run():
            for _ in range(5):
                queue.submit(tracked)
            await asyncio.sleep(0.3)
            result["count"] = len(result["started"])

        asyncio.run(run())
        assert result["count"] <= queue.max_concurrent

    def test_queue_stats(self):
        queue = make_queue()
        result = {}

        async def run():
            queue.submit(dummy_task)
            queue.submit(failing_task)
            await asyncio.sleep(0.5)
            result["stats"] = queue.get_queue_stats()

        asyncio.run(run())
        assert result["stats"]["total"] == 2
        assert result["stats"]["max_concurrent"] == 3
        assert "completed" in result["stats"]["by_status"]
        assert "failed" in result["stats"]["by_status"]


class TestListTasksFilter:
    def test_list_all(self):
        queue = make_queue()
        result = {}

        async def run():
            queue.submit(dummy_task)
            queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            result["tasks"] = queue.list_tasks()

        asyncio.run(run())
        assert len(result["tasks"]) == 2

    def test_filter_by_completed(self):
        queue = make_queue()
        result = {}

        async def run():
            queue.submit(dummy_task)
            queue.submit(failing_task)
            await asyncio.sleep(0.5)
            result["completed"] = queue.list_tasks(status=TaskStatus.COMPLETED)

        asyncio.run(run())
        assert len(result["completed"]) >= 1
        for t in result["completed"]:
            assert t.status == TaskStatus.COMPLETED

    def test_filter_by_failed(self):
        queue = make_queue()
        result = {}

        async def run():
            queue.submit(dummy_task)
            queue.submit(failing_task)
            await asyncio.sleep(0.5)
            result["failed"] = queue.list_tasks(status=TaskStatus.FAILED)

        asyncio.run(run())
        assert len(result["failed"]) >= 1
        for t in result["failed"]:
            assert t.status == TaskStatus.FAILED

    def test_limit_and_offset(self):
        queue = make_queue()
        result = {}

        async def run():
            for _ in range(5):
                queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            result["page"] = queue.list_tasks(limit=2, offset=0)

        asyncio.run(run())
        assert len(result["page"]) == 2

    def test_empty_filter(self):
        queue = make_queue()
        result = {}

        async def run():
            queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            result["cancelled"] = queue.list_tasks(status=TaskStatus.CANCELLED)

        asyncio.run(run())
        assert len(result["cancelled"]) == 0


class TestTaskResult:
    def test_get_result_after_completion(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            result["value"] = queue.get_result(task_id)

        asyncio.run(run())
        assert result["value"] == "done"

    def test_get_result_pending_returns_none(self):
        queue = make_queue()
        result = {}

        async def run():
            async def blocker():
                await asyncio.sleep(100)

            task_id = queue.submit(blocker)
            await asyncio.sleep(0.05)
            queue.cancel(task_id)
            await asyncio.sleep(0.1)
            result["value"] = queue.get_result(task_id)

        asyncio.run(run())
        assert result["value"] is None

    def test_get_result_not_found_raises(self):
        queue = make_queue()

        async def run():
            with pytest.raises(KeyError):
                queue.get_result("nonexistent-id")

        asyncio.run(run())

    def test_get_result_failed_raises(self):
        queue = make_queue()

        async def run():
            task_id = queue.submit(failing_task)
            await asyncio.sleep(0.5)
            with pytest.raises(RuntimeError, match="Task failed"):
                queue.get_result(task_id)

        asyncio.run(run())


class TestBackgroundTaskDataclass:
    def test_to_dict(self):
        queue = make_queue()
        result = {}

        async def run():
            task_id = queue.submit(dummy_task)
            await asyncio.sleep(0.5)
            result["dict"] = queue.get_status(task_id).to_dict()

        asyncio.run(run())
        d = result["dict"]
        assert d["name"] == "dummy_task"
        assert d["status"] == "completed"
        assert d["progress"] == 100.0
        assert d["result"] == "done"
        assert d["error"] is None
        assert "created_at" in d

    def test_to_dict_fields(self):
        task = BackgroundTask(id="test-id", name="test")
        d = task.to_dict()
        expected_keys = {
            "id", "name", "status", "progress", "result",
            "error", "created_at", "started_at", "completed_at", "timeout",
        }
        assert set(d.keys()) == expected_keys
