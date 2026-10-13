"""Turn stored samples and request logs into dashboard-ready series."""
import datetime
import math
import re
from collections import defaultdict

from django.utils import timezone

from whiteneuron.base.models import AnonymousActivity, UserActivity

from .collector import conf
from .models import MetricSample

RANGES = {
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "6h": 6 * 3600,
    "24h": 24 * 3600,
    "7d": 7 * 24 * 3600,
}
DEFAULT_RANGE = "1h"
MAX_POINTS = 240                 # points per series sent to the browser
MAX_REQUEST_ROWS = 200_000       # cap on request-log rows read per refresh
APDEX_T_MS = 500                 # "satisfied" threshold for the Apdex score

# averaged per bucket
GAUGE_FIELDS = [
    "cpu_percent", "load_1", "load_5", "load_15", "mem_percent", "mem_used", "swap_percent",
    "disk_percent", "proc_rss", "proc_threads", "process_count", "db_latency_ms", "cache_latency_ms",
]
# cumulative counters, converted to per-second rates
COUNTER_FIELDS = ["disk_read_bytes", "disk_write_bytes", "net_sent_bytes", "net_recv_bytes"]


def parse_range(value):
    key = value if value in RANGES else DEFAULT_RANGE
    return key, RANGES[key]


def hosts():
    since = timezone.now() - datetime.timedelta(days=int(conf("RETENTION_DAYS")))
    return list(
        MetricSample.objects.filter(timestamp__gte=since)
        .order_by().values_list("host", flat=True).distinct()
    )


def _bucket_seconds(seconds):
    return max(int(conf("INTERVAL")), math.ceil(seconds / MAX_POINTS))


def _mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 3) if values else None


def percentile(sorted_values, pct):
    """Nearest-rank percentile of an already sorted list."""
    if not sorted_values:
        return None
    rank = max(0, min(len(sorted_values) - 1, math.ceil(pct / 100 * len(sorted_values)) - 1))
    return sorted_values[rank]


def system_series(host, seconds):
    """Bucketed system metrics for ``host`` over the last ``seconds``."""
    now = timezone.now()
    start = now - datetime.timedelta(seconds=seconds)
    fields = ["timestamp", *GAUGE_FIELDS, *COUNTER_FIELDS]
    rows = list(
        MetricSample.objects.filter(host=host, timestamp__gte=start)
        .order_by("timestamp").values_list(*fields)
    )

    bucket = _bucket_seconds(seconds)
    grouped = defaultdict(lambda: defaultdict(list))
    previous = None
    for row in rows:
        values = dict(zip(fields, row))
        ts = values["timestamp"]
        key = int(ts.timestamp()) // bucket
        for name in GAUGE_FIELDS:
            grouped[key][name].append(values[name])
        if previous is not None:
            dt = (ts - previous["timestamp"]).total_seconds()
            if 0 < dt <= max(bucket, int(conf("INTERVAL"))) * 4:  # skip gaps (collector stopped)
                for name in COUNTER_FIELDS:
                    delta = values[name] - previous[name]
                    # negative delta = counter reset (reboot): no rate for this step
                    grouped[key][name].append(delta / dt if delta >= 0 else None)
        previous = values

    keys = sorted(grouped)
    series = {"t": [k * bucket * 1000 for k in keys], "bucket": bucket}
    for name in GAUGE_FIELDS + COUNTER_FIELDS:
        series[name] = [_mean(grouped[k][name]) for k in keys]
    return series


_ID_SEGMENT = re.compile(r"/(\d+|[0-9a-f]{8}-[0-9a-f-]{27,})(?=/|$)", re.I)


def normalize_path(path):
    """/admin/base/user/12/change/ -> /admin/base/user/:id/change/ (groups endpoints)."""
    return _ID_SEGMENT.sub("/:id", path or "")


def request_stats(seconds):
    """Throughput, errors, latency percentiles and slow endpoints from the activity logs."""
    now = timezone.now()
    start = now - datetime.timedelta(seconds=seconds)
    fields = ("timestamp", "status_code", "timelapse", "method", "path")
    rows = []
    truncated = False
    for model in (UserActivity, AnonymousActivity):
        chunk = list(
            model.objects.filter(timestamp__gte=start).order_by("-timestamp")
            .values_list(*fields)[:MAX_REQUEST_ROWS]
        )
        truncated |= len(chunk) >= MAX_REQUEST_ROWS
        rows.extend(chunk)

    bucket = _bucket_seconds(seconds)
    per_bucket = defaultdict(lambda: {"ok": 0, "4xx": 0, "5xx": 0, "lat": []})
    status_classes = defaultdict(int)
    endpoints = defaultdict(lambda: {"lat": [], "errors": 0})
    latencies = []
    satisfied = tolerating = 0

    for ts, status, elapsed, method, path in rows:
        status = status or 0
        cls = "5xx" if status >= 500 else "4xx" if status >= 400 else "ok"
        b = per_bucket[int(ts.timestamp()) // bucket]
        b[cls] += 1
        status_classes[f"{status // 100}xx" if status else "other"] += 1
        ms = elapsed.total_seconds() * 1000 if elapsed is not None else None
        ep = endpoints[(method or "", normalize_path(path))]
        if status >= 500:
            ep["errors"] += 1
        if ms is not None:
            b["lat"].append(ms)
            latencies.append(ms)
            ep["lat"].append(ms)
            if ms <= APDEX_T_MS:
                satisfied += 1
            elif ms <= 4 * APDEX_T_MS:
                tolerating += 1

    keys = sorted(per_bucket)
    series = {"t": [k * bucket * 1000 for k in keys], "bucket": bucket,
              "ok": [], "4xx": [], "5xx": [], "p50": [], "p95": [], "p99": []}
    for k in keys:
        b = per_bucket[k]
        lat = sorted(b["lat"])
        for name in ("ok", "4xx", "5xx"):
            # requests per minute in this bucket
            series[name].append(round(b[name] * 60 / bucket, 2))
        series["p50"].append(_round(percentile(lat, 50)))
        series["p95"].append(_round(percentile(lat, 95)))
        series["p99"].append(_round(percentile(lat, 99)))

    latencies.sort()
    total = len(rows)
    errors = sum(1 for r in rows if (r[1] or 0) >= 500)
    top = []
    for (method, path), ep in endpoints.items():
        lat = sorted(ep["lat"])
        count = len(lat) or 1
        top.append({
            "method": method,
            "path": path,
            "count": len(lat),
            "avg": _round(sum(lat) / count) if lat else None,
            "p95": _round(percentile(lat, 95)),
            "max": _round(lat[-1]) if lat else None,
            "total": _round(sum(lat)),
            "error_rate": round(ep["errors"] * 100 / count, 2),
        })
    top.sort(key=lambda e: e["total"] or 0, reverse=True)

    return {
        "series": series,
        "summary": {
            "total": total,
            "rpm": round(total * 60 / seconds, 2),
            "error_rate": round(errors * 100 / total, 2) if total else 0,
            "p50": _round(percentile(latencies, 50)),
            "p95": _round(percentile(latencies, 95)),
            "p99": _round(percentile(latencies, 99)),
            "apdex": round((satisfied + tolerating / 2) / len(latencies), 3) if latencies else None,
            "truncated": truncated,
        },
        "status_classes": dict(status_classes),
        "top_endpoints": top[:12],
    }


def _round(value, digits=1):
    return round(value, digits) if value is not None else None


def live(host):
    """Current snapshot plus I/O rates against the latest stored sample of this host."""
    from .collector import snapshot

    data = snapshot()
    last = MetricSample.objects.filter(host=host).order_by("-timestamp").first()
    rates = {}
    if last is not None:
        dt = (data["timestamp"] - last.timestamp).total_seconds()
        if 0 < dt <= 600:
            for name in COUNTER_FIELDS:
                delta = data[name] - getattr(last, name)
                rates[name] = round(delta / dt, 2) if delta >= 0 else None
    data["rates"] = rates
    data["uptime"] = (data["timestamp"] - data["boot_time"]).total_seconds()
    return data
