from celery import shared_task

from . import collector


@shared_task(ignore_result=True)
def collect_metrics():
    """Store one sample of this host. Schedule it with celery beat, e.g. every 15s:

        CELERY_BEAT_SCHEDULE = {
            "wn-monitoring": {"task": "whiteneuron.monitoring.tasks.collect_metrics", "schedule": 15.0},
        }

    Note: it samples the machine running the worker.
    """
    collector.record(collector.snapshot(cpu_interval=1), force=True)
    collector.beat()
