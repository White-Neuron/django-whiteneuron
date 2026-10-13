"""Run slow work on Celery when available, inline otherwise."""
import logging

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


def async_tasks_enabled():
    """Whether slow work (email, exports, LLM calls) goes to Celery workers.

    Opt-in with ``WN_ASYNC_TASKS = True`` once a Celery worker is running; otherwise
    tasks run inline (a queued task with no worker would never run).
    """
    return getattr(settings, "WN_ASYNC_TASKS", False)


def enqueue(task, *args, **kwargs):
    """Run ``task`` on a worker after the current transaction commits, or inline.

    Returns True when queued, otherwise the task's return value.
    """
    if async_tasks_enabled():
        def publish():
            try:
                task.delay(*args, **kwargs)
            except Exception:
                # broker unreachable: the data is already committed, so don't fail the
                # request — do the work here instead of silently losing it
                logger.exception("Could not queue %s; running it inline", getattr(task, "name", task))
                try:
                    task(*args, **kwargs)
                except Exception:
                    logger.exception("Inline fallback for %s failed", getattr(task, "name", task))

        transaction.on_commit(publish)
        return True
    return task(*args, **kwargs)
