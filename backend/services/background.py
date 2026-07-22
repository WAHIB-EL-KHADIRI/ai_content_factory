"""Background task queue using asyncio with no external dependencies."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger("ai_content_os.background")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: Optional[float] = None
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _cancelled: bool = field(default=False, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "timeout": self.timeout,
        }


class TaskQueue:
    """Async task queue with configurable concurrency and timeout support."""

    def __init__(
        self, max_concurrent: int = 5, default_timeout: Optional[float] = None
    ):
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self._tasks: Dict[str, BackgroundTask] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _ensure_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def submit(
        self,
        coroutine_fn: Callable[..., Coroutine],
        *args: Any,
        timeout: Optional[float] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        task_id = str(uuid.uuid4())
        task_name = name or coroutine_fn.__name__
        effective_timeout = timeout or self.default_timeout

        bg_task = BackgroundTask(
            id=task_id,
            name=task_name,
            timeout=effective_timeout,
        )
        self._tasks[task_id] = bg_task

        loop = asyncio.get_event_loop()
        asyncio_task = loop.create_task(
            self._run_task(bg_task, coroutine_fn, args, kwargs)
        )
        bg_task._task = asyncio_task
        asyncio_task.add_done_callback(lambda _f: None)

        logger.info("Submitted background task '%s' [%s]", task_name, task_id)
        return task_id

    async def _run_task(
        self,
        bg_task: BackgroundTask,
        coroutine_fn: Callable[..., Coroutine],
        args: tuple,
        kwargs: dict,
    ) -> None:
        semaphore = self._ensure_semaphore()
        async with semaphore:
            if bg_task._cancelled:
                bg_task.status = TaskStatus.CANCELLED
                bg_task.completed_at = datetime.now(timezone.utc)
                return

            bg_task.status = TaskStatus.RUNNING
            bg_task.started_at = datetime.now(timezone.utc)
            logger.info("Task '%s' [%s] started", bg_task.name, bg_task.id)

            try:
                if bg_task.timeout:
                    result = await asyncio.wait_for(
                        coroutine_fn(*args, **kwargs),
                        timeout=bg_task.timeout,
                    )
                else:
                    result = await coroutine_fn(*args, **kwargs)

                if bg_task._cancelled:
                    bg_task.status = TaskStatus.CANCELLED
                    bg_task.completed_at = datetime.now(timezone.utc)
                    return

                bg_task.result = result
                bg_task.status = TaskStatus.COMPLETED
                bg_task.progress = 100.0
                bg_task.completed_at = datetime.now(timezone.utc)
                logger.info("Task '%s' [%s] completed", bg_task.name, bg_task.id)

            except asyncio.CancelledError:
                bg_task.status = TaskStatus.CANCELLED
                bg_task.error = "Task was cancelled"
                bg_task.completed_at = datetime.now(timezone.utc)
                logger.info("Task '%s' [%s] cancelled", bg_task.name, bg_task.id)

            except asyncio.TimeoutError:
                bg_task.status = TaskStatus.FAILED
                bg_task.error = f"Task timed out after {bg_task.timeout}s"
                bg_task.completed_at = datetime.now(timezone.utc)
                logger.error("Task '%s' [%s] timed out", bg_task.name, bg_task.id)

            except Exception as exc:
                bg_task.status = TaskStatus.FAILED
                bg_task.error = str(exc)
                bg_task.completed_at = datetime.now(timezone.utc)
                logger.exception("Task '%s' [%s] failed", bg_task.name, bg_task.id)

    def get_status(self, task_id: str) -> Optional[BackgroundTask]:
        return self._tasks.get(task_id)

    def get_result(self, task_id: str) -> Any:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task {task_id} not found")
        if task.status == TaskStatus.COMPLETED:
            return task.result
        if task.status == TaskStatus.FAILED:
            raise RuntimeError(f"Task failed: {task.error}")
        return None

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False

        task._cancelled = True

        if task._task and not task._task.done():
            task._task.cancel()
            logger.info("Task '%s' [%s] cancellation requested", task.name, task_id)
            return True

        if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled"
            task.completed_at = datetime.now(timezone.utc)
            return True

        return False

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BackgroundTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[offset : offset + limit]

    def get_queue_stats(self) -> Dict[str, Any]:
        by_status: Dict[str, int] = {}
        for task in self._tasks.values():
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
        return {
            "total": len(self._tasks),
            "max_concurrent": self.max_concurrent,
            "by_status": by_status,
        }


_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_concurrent=5, default_timeout=300.0)
    return _task_queue
