"""Heartbeats of background jobs (#91): a scheduler, a worker, a backup command or a bot says
"I just finished a round", and the operator sees which job has stopped and what that means.

In the job, at the end of each round::

    from whiteneuron.monitoring import beat
    beat("backup")              # never raises: a heartbeat must not break the job itself

In the project's settings::

    WN_HEARTBEATS = {
        "backup": {"label": _("Daily backup"), "max_age": 26 * 3600,
                   "consequence": _("No new backup since then."), "critical": True},
        "scheduler": {"label": _("Scheduler"), "max_age": 300,
                      "consequence": _("Scheduled work is not running.")},
        "night_sync": {"label": _("Night sync"), "max_age": 86400, "enabled": False},
    }

Only listed names are recorded or shown: a project without ``WN_HEARTBEATS`` sees no change.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

OK, LATE, NEVER, DISABLED = "ok", "late", "never", "disabled"


def configured():
    """``WN_HEARTBEATS`` with defaults filled in: {name: {label, max_age, consequence, critical, enabled}}."""
    jobs = {}
    for name, spec in (getattr(settings, "WN_HEARTBEATS", None) or {}).items():
        spec = spec or {}
        try:
            max_age = int(spec.get("max_age", 3600))
        except (TypeError, ValueError):
            max_age = 3600
        jobs[str(name)] = {
            "label": spec.get("label") or name,
            "max_age": max(max_age, 1),
            "consequence": spec.get("consequence") or "",
            "critical": bool(spec.get("critical", False)),
            "enabled": spec.get("enabled", True) is not False,
        }
    return jobs


def beat(name, info=""):
    """Record that job ``name`` has just run. Cheap (one upsert), never raises."""
    try:
        if str(name) not in configured():
            return False
        from .collector import host_name
        from .models import Heartbeat

        Heartbeat.objects.update_or_create(
            name=str(name),
            defaults={"last_beat_at": timezone.now(), "host": host_name()[:128], "info": str(info or "")[:255]},
        )
        return True
    except Exception:  # database down, table missing, …: the job itself must go on
        logger.warning("Heartbeat %r could not be recorded", name, exc_info=True)
        return False


def statuses(now=None):
    """One dict per configured job, critical and late ones first:
    {name, label, consequence, critical, max_age, state, last_beat_at, host, info, age_seconds}.

    ``never`` (no beat yet: a fresh install is not an alarm), ``late`` (older than max_age),
    ``disabled`` (``enabled: False``, neutral), else ``ok``.
    """
    jobs = configured()
    if not jobs:
        return []
    from .models import Heartbeat

    now = now or timezone.now()
    try:
        rows = {h.name: h for h in Heartbeat.objects.filter(name__in=list(jobs))}
    except Exception:
        logger.warning("Heartbeats could not be read", exc_info=True)
        rows = {}
    result = []
    for name, job in jobs.items():
        row = rows.get(name)
        age = (now - row.last_beat_at).total_seconds() if row else None
        if not job["enabled"]:
            state = DISABLED
        elif row is None:
            state = NEVER
        elif age > job["max_age"]:
            state = LATE
        else:
            state = OK
        result.append({
            "name": name, **job, "state": state,
            "last_beat_at": row.last_beat_at if row else None,
            "host": row.host if row else "", "info": row.info if row else "",
            "age_seconds": int(age) if age is not None else None,
            "due_at": row.last_beat_at + timedelta(seconds=job["max_age"]) if row else None,
        })
    order = {LATE: 0, NEVER: 1, OK: 2, DISABLED: 3}
    result.sort(key=lambda j: (order[j["state"]], not j["critical"], str(j["label"])))
    return result


def late(critical_only=False):
    """The configured jobs that are late (only ``critical`` ones with ``critical_only``)."""
    return [j for j in statuses() if j["state"] == LATE and (j["critical"] or not critical_only)]
