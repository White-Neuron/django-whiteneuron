"""Collect host metrics with psutil and store them as MetricSample rows."""
import datetime
import os
import socket
import time

import psutil
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from .models import MetricSample

DEFAULTS = {
    "INTERVAL": 15,        # seconds between stored samples
    "RETENTION_DAYS": 7,   # samples older than this are deleted
    "DISK_PATH": "/",      # filesystem shown in the disk panels
    "HOST": None,          # defaults to the machine hostname
}


def conf(key):
    return getattr(settings, "WN_MONITORING", {}).get(key, DEFAULTS[key])


def host_name():
    return conf("HOST") or socket.gethostname()


# psutil.cpu_percent(interval=None) compares with the previous call; prime it at import
psutil.cpu_percent(interval=None, percpu=True)
_last_cpu_call = time.monotonic()
_MIN_CPU_WINDOW = 0.5  # seconds: a shorter window reads as ~0% (nothing measured yet)


def _timed_ms(fn):
    start = time.perf_counter()
    try:
        fn()
    except Exception:
        return None
    return round((time.perf_counter() - start) * 1000, 2)


def _db_ping():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def _cache_ping():
    cache.get("wn:monitoring:ping")


def snapshot(cpu_interval=None):
    """Current metrics as a dict of MetricSample field values (nothing is saved)."""
    global _last_cpu_call
    if cpu_interval is None:
        elapsed = time.monotonic() - _last_cpu_call
        if elapsed < _MIN_CPU_WINDOW:
            cpu_interval = _MIN_CPU_WINDOW - elapsed
    # one measurement for all cores; the total is their average
    per_core = psutil.cpu_percent(interval=cpu_interval, percpu=True)
    _last_cpu_call = time.monotonic()
    cpu = round(sum(per_core) / len(per_core), 1) if per_core else 0.0
    try:
        load_1, load_5, load_15 = os.getloadavg()
    except (AttributeError, OSError):  # Windows
        load_1 = load_5 = load_15 = None

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(conf("DISK_PATH"))
    io = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    proc = psutil.Process()
    with proc.oneshot():
        rss = proc.memory_info().rss
        threads = proc.num_threads()

    return {
        "timestamp": timezone.now(),
        "host": host_name(),
        "cpu_percent": cpu,
        "cpu_count": psutil.cpu_count() or 1,
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15,
        "mem_total": mem.total,
        "mem_used": mem.total - mem.available,
        "mem_percent": mem.percent,
        "swap_percent": swap.percent,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "disk_read_bytes": io.read_bytes if io else 0,
        "disk_write_bytes": io.write_bytes if io else 0,
        "net_sent_bytes": net.bytes_sent if net else 0,
        "net_recv_bytes": net.bytes_recv if net else 0,
        "process_count": len(psutil.pids()),
        "proc_rss": rss,
        "proc_threads": threads,
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time(), tz=datetime.timezone.utc),
        "db_latency_ms": _timed_ms(_db_ping),
        "cache_latency_ms": _timed_ms(_cache_ping),
        "extra": {"per_core": per_core},
    }


def record(data=None, force=False):
    """Store a sample, at most once per INTERVAL per host (atomic cache lock).

    Returns the saved MetricSample, or None when another worker already stored one
    in this interval. Old samples are pruned at most once an hour.
    """
    host = (data or {}).get("host") or host_name()
    interval = max(1, int(conf("INTERVAL")))
    if not force and not cache.add(f"wn:monitoring:lock:{host}", 1, timeout=max(1, interval - 1)):
        return None
    sample = MetricSample.objects.create(**(data or snapshot()))
    if cache.add("wn:monitoring:prune", 1, timeout=3600):
        prune()
    return sample


def prune():
    cutoff = timezone.now() - datetime.timedelta(days=int(conf("RETENTION_DAYS")))
    return MetricSample.objects.filter(timestamp__lt=cutoff).delete()[0]
