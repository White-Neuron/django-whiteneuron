import datetime

from django.contrib import admin
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from whiteneuron.base.sites import base_admin_site

from . import collector, stats
from .models import MetricSample

REFRESH_CHOICES = ["off", "5s", "10s", "30s", "1m", "5m"]

# labels used by dashboard.js
JS_STRINGS = {
    "cpu": _("CPU"), "load1": _("1m"), "load5": _("5m"), "load15": _("15m"), "cores": _("cores"),
    "memUsed": _("Used"), "swap": _("Swap %"), "read": _("Read"), "write": _("Write"),
    "recv": _("Received"), "sent": _("Sent"), "disk": _("Disk used"),
    "ok": _("2xx/3xx"), "c4xx": _("4xx"), "c5xx": _("5xx"),
    "p50": _("p50"), "p95": _("p95"), "p99": _("p99"),
    "db": _("Database"), "cache": _("Cache"), "rss": _("Memory (RSS)"), "threads": _("Threads"),
    "of": _("of"), "perMin": _("req/min"), "requests": _("requests"), "noData": _("No data"),
    "staleCollector": _("No collector is running for this host: history is only recorded while a dashboard is open. Run \"manage.py monitoring_collector\" (or schedule the Celery task) to keep collecting."),
    "remoteHost": _("Live values come from the latest stored sample of this host."),
    "fetchError": _("Could not load metrics"),
    "updated": _("Updated"), "truncated": _("Request statistics are based on the most recent requests only (row limit reached)."),
    "days": _("d"), "hours": _("h"), "minutes": _("m"),
    "satisfied": _("Excellent"), "good": _("Good"), "fair": _("Fair"), "poor": _("Poor"),
}
_STATS_TTL = 5  # seconds: several open dashboards share one computation

# model fields of a snapshot (live() adds a few presentation-only keys)
_SAMPLE_FIELDS = {f.name for f in MetricSample._meta.concrete_fields} - {"id"}


@admin.register(MetricSample, site=base_admin_site)
class MetricSampleAdmin(ModelAdmin):
    """Grafana-style server dashboard instead of a plain changelist."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_urls(self):
        info = self.opts.app_label, self.opts.model_name
        return [
            path("api/", self.admin_site.admin_view(self.api_view), name="%s_%s_api" % info),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            raise PermissionDenied
        range_key, _seconds = stats.parse_range(request.GET.get("range"))
        refresh = request.GET.get("refresh", "10s")
        context = {
            **self.admin_site.each_context(request),
            "opts": self.opts,
            "title": _("Server monitoring"),
            "api_url": reverse("admin:%s_%s_api" % (self.opts.app_label, self.opts.model_name)),
            "range": range_key,
            "ranges": list(stats.RANGES),
            "refresh": refresh if refresh in REFRESH_CHOICES else "10s",
            "refresh_choices": REFRESH_CHOICES,
            "host": request.GET.get("host") or collector.host_name(),
            "interval": int(collector.conf("INTERVAL")),
            "i18n_strings": {k: str(v) for k, v in JS_STRINGS.items()},
            **(extra_context or {}),
        }
        return TemplateResponse(request, "admin/monitoring/dashboard.html", context)

    def api_view(self, request):
        if not self.has_view_permission(request):
            return JsonResponse({"detail": "forbidden"}, status=403)

        range_key, seconds = stats.parse_range(request.GET.get("range"))
        local_host = collector.host_name()
        host = request.GET.get("host") or local_host

        if host == local_host:
            live = stats.live(host)
            # keep history even without a collector process: store at most one sample per interval
            collector.record({k: v for k, v in live.items() if k in _SAMPLE_FIELDS})
        else:
            last = MetricSample.objects.filter(host=host).order_by("-timestamp").first()
            live = _sample_as_live(last) if last else None

        ttl = _stats_ttl(seconds)
        system = _cached(f"wn:mon:sys:{host}:{range_key}", lambda: stats.system_series(host, seconds), ttl)
        requests = _cached(f"wn:mon:req:{range_key}", lambda: stats.request_stats(seconds), ttl)

        latest = MetricSample.objects.filter(host=host).order_by("-timestamp").values_list("timestamp", flat=True).first()
        interval = int(collector.conf("INTERVAL"))
        return JsonResponse({
            "host": host,
            "local_host": local_host,
            "hosts": sorted(set(stats.hosts()) | {local_host}),
            "range": range_key,
            "seconds": seconds,
            "interval": interval,
            "server_time": timezone.now().isoformat(),
            "collector": {
                "last_sample": latest.isoformat() if latest else None,
                # the dashboard stores samples itself, so sample age can't tell whether a
                # collector runs: use its heartbeat (local host) or sample age (remote hosts)
                "stale": (not collector.collector_running(host)) if host == local_host
                else (latest is None or (timezone.now() - latest).total_seconds() > interval * 3),
            },
            "live": _jsonable(live),
            "system": system,
            "requests": requests,
        })


def _stats_ttl(seconds):
    """Share results between dashboards for a fraction of a chart bucket (5s..5min)."""
    return int(max(_STATS_TTL, min(300, seconds / stats.MAX_POINTS / 2)))


def _cached(key, compute, timeout=_STATS_TTL):
    try:
        value = cache.get(key)
    except Exception:  # cache down: compute every time rather than fail
        return compute()
    if value is None:
        value = compute()
        try:
            cache.set(key, value, timeout=timeout)
        except Exception:
            pass
    return value


def _sample_as_live(sample):
    data = {name: getattr(sample, name) for name in _SAMPLE_FIELDS}
    data["rates"] = {}
    data["uptime"] = (sample.timestamp - sample.boot_time).total_seconds() if sample.boot_time else None
    return data


def _jsonable(data):
    if data is None:
        return None
    out = {}
    for key, value in data.items():
        if isinstance(value, datetime.datetime):
            value = value.isoformat()
        out[key] = value
    out["per_core"] = (data.get("extra") or {}).get("per_core", [])
    out.pop("extra", None)
    return out
