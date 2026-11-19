from celery import shared_task

from . import collector, heartbeats


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
    heartbeats.beat("monitoring_collector")


@shared_task(ignore_result=True)
def worker_heartbeat():
    """Prove that celery beat and a worker are both running. Schedule it, e.g. every minute,
    and list it in WN_HEARTBEATS::

        CELERY_BEAT_SCHEDULE = {
            "wn-heartbeat": {"task": "whiteneuron.monitoring.tasks.worker_heartbeat", "schedule": 60.0},
        }
        WN_HEARTBEATS = {"celery": {"label": _("Background tasks"), "max_age": 300,
                                    "consequence": _("E-mails and exports are not sent.")}}
    """
    heartbeats.beat("celery")
