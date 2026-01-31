"""
Task queue wrapper for Video Analyzer.
Uses Redis Queue (RQ) for background tasks.
"""

import os
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")


class TaskQueue:
    """Simple task queue wrapper using RQ."""

    def __init__(self):
        self.client = None
        self.queue = None
        self._connect()

    def _connect(self):
        """Connect to Redis queue."""
        try:
            import redis
            from rq import Queue

            connection = redis.from_url(REDIS_URL)
            connection.ping()
            self.client = connection
            self.queue = Queue(connection=connection)
            logger.info("Task queue connected")
        except Exception as e:
            logger.warning(f"Task queue connection failed: {e}")
            self.client = None
            self.queue = None

    def enqueue(self, func, *args, **kwargs):
        """Enqueue a task for background processing."""
        if not self.queue:
            # Fallback: run synchronously
            logger.warning("Queue not available, running task synchronously")
            return func(*args, **kwargs)

        try:
            job = self.queue.enqueue(func, *args, **kwargs)
            logger.info(f"Task enqueued: {job.id}")
            return job
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            # Fallback: run synchronously
            return func(*args, **kwargs)


# Singleton
_task_queue: Optional[TaskQueue] = None


def get_queue() -> TaskQueue:
    """Get task queue singleton."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
