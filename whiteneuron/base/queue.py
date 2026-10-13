"""Run slow work on Celery when available, inline otherwise."""
from django.conf import settings
from django.db import transaction


def async_tasks_enabled():
    """Whether slow work (email, exports, LLM calls) goes to Celery workers.

    ``WN_ASYNC_TASKS`` defaults to True only when CELERY_BROKER_URL is configured;
    without a broker ``.delay()`` would block or fail, so tasks run inline instead.
    """
    return getattr(settings, "WN_ASYNC_TASKS", False)


def enqueue(task, *args, **kwargs):
    """Run ``task`` on a worker after the current transaction commits, or inline.

    Returns True when queued, otherwise the task's return value.
    """
    if async_tasks_enabled():
        transaction.on_commit(lambda: task.delay(*args, **kwargs))
        return True
    return task(*args, **kwargs)
