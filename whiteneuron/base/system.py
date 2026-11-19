"""System endpoints: version, liveness, readiness and runtime info.

    GET version/  public              application name, version, release date; build id only for
                                      superusers / SYSTEM_API_TOKEN (often a commit hash)
    GET health/   public              liveness: the process answers (no DB / cache access)
    GET ready/    public              readiness: database / cache (/ celery) checks, 503 on failure;
                                      error messages only for superusers / SYSTEM_API_TOKEN
    GET info/     superuser or token  package and runtime versions, uptime, pending migrations, checks

Like the admin About page, nothing here exposes host names, OS, IPs, paths or connection
settings, and package/runtime versions are not public (fingerprinting / CVE lookup).

``ready/`` is public and not rate limited, so public calls reuse this process's last
results for ``READY_CACHE_SECONDS`` and run at most one set of checks at a time; callers
with system access always get fresh results. The memo is per process on purpose:
readiness is a property of each replica, and a result shared through the cache would
let one replica answer for another.

Settings: ``SYSTEM_API_TOKEN`` (optional), ``SYSTEM_API_READY_CHECKS`` (default
``["database", "cache"]``; add ``"celery"`` to ping the broker).
"""
import copy
import logging
import platform
import threading
import time
import uuid

from django.conf import settings
from django.core.cache import caches
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone
from django.views.decorators.cache import never_cache

import whiteneuron

from .api_utils import has_system_access, json_response, require_GET
from .app_info import BUILD_ID_LENGTH, package_version, process_started

logger = logging.getLogger(__name__)

DEFAULT_READY_CHECKS = ("database", "cache")
BROKER_TIMEOUT_SECONDS = 2
READY_CACHE_SECONDS = 2


def application_info():
    build = str(getattr(settings, "BUILD_ID", None) or "")[:BUILD_ID_LENGTH] or None
    return {
        "name": str(settings.NAME) if getattr(settings, "NAME", None) else None,
        "version": getattr(settings, "VERSION", None),
        "release_date": getattr(settings, "RELEASE_DATE", None) or None,
        "build": build,
    }


# ── checks ────────────────────────────────────────────────────────────────

def check_database():
    with connections[DEFAULT_DB_ALIAS].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def check_cache():
    # A key of its own per call: replicas sharing one cache must not overwrite each other.
    cache = caches["default"]
    token = uuid.uuid4().hex
    key = f"wn:system:ready:{token}"
    cache.set(key, token, timeout=10)
    try:
        if cache.get(key) != token:
            raise RuntimeError("cache read-back mismatch")
    finally:
        cache.delete(key)


def check_celery():
    broker_url = getattr(settings, "CELERY_BROKER_URL", None)
    if not broker_url:
        raise RuntimeError("CELERY_BROKER_URL is not set")
    from kombu import Connection

    # One attempt, no retry sleep: a slow or dead broker costs at most the timeout.
    with Connection(broker_url, connect_timeout=BROKER_TIMEOUT_SECONDS) as conn:
        conn.ensure_connection(max_retries=0, timeout=BROKER_TIMEOUT_SECONDS)


CHECKS = {
    "database": check_database,
    "cache": check_cache,
    "celery": check_celery,
}


def run_checks():
    results = {}
    for name in getattr(settings, "SYSTEM_API_READY_CHECKS", None) or DEFAULT_READY_CHECKS:
        check = CHECKS.get(name)
        start = time.perf_counter()
        if check is None:
            result = {"status": "error", "error": "unknown check"}
        else:
            try:
                check()
                result = {"status": "ok"}
            except Exception as exc:  # any failure makes the instance not ready
                logger.warning("Readiness check %s failed", name, exc_info=True)
                # the class only: driver messages carry host names, IPs and ports (they are logged)
                result = {"status": "error", "error": exc.__class__.__name__}
        result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        results[name] = result
    return results


_ready_lock = threading.Lock()
_ready_memo = None  # (time.monotonic(), results)


def cached_checks(max_age=READY_CACHE_SECONDS):
    """``run_checks()``, reused for ``max_age`` seconds within this process.

    The lock lets one request run the checks while concurrent ones wait and reuse its
    results, so a burst of calls does not run a burst of checks.
    """
    global _ready_memo
    with _ready_lock:
        memo = _ready_memo
        if memo is None or time.monotonic() - memo[0] >= max_age:
            memo = _ready_memo = (time.monotonic(), run_checks())
        return copy.deepcopy(memo[1])


def reset_ready_cache():
    global _ready_memo
    with _ready_lock:
        _ready_memo = None


def pending_migrations():
    try:
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        return len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    except Exception:
        logger.warning("Could not compute pending migrations", exc_info=True)
        return None


# ── views ─────────────────────────────────────────────────────────────────

@never_cache
@require_GET
def version_view(request):
    data = application_info()
    if not has_system_access(request):
        data.pop("build")  # a commit hash pins the exact code for anyone looking up issues
    return json_response(data)


@never_cache
@require_GET
def health_view(request):
    return json_response({"status": "ok"})


@never_cache
@require_GET
def ready_view(request):
    privileged = has_system_access(request)
    checks = run_checks() if privileged else cached_checks()
    ok = all(c["status"] == "ok" for c in checks.values())
    if not privileged:
        for c in checks.values():
            c.pop("error", None)
    return json_response({"status": "ok" if ok else "error", "checks": checks}, status=200 if ok else 503)


@never_cache
@require_GET
def info_view(request):
    if not has_system_access(request):
        return json_response({"detail": "Forbidden."}, status=403)
    started = process_started()
    return json_response({
        "application": application_info(),
        "base": {
            "package": "django-whiteneuron",
            "version": whiteneuron.__version__,
            "release_date": whiteneuron.__release_date__,
        },
        "runtime": {
            "python": platform.python_version(),
            "django": package_version("django"),
            "django_unfold": package_version("django-unfold"),
            "database": connections[DEFAULT_DB_ALIAS].display_name,
            "debug": settings.DEBUG,
            "time_zone": settings.TIME_ZONE,
            "server_time": timezone.now().isoformat(),
            "process_started": started.isoformat() if started else None,
            "uptime_seconds": int((timezone.now() - started).total_seconds()) if started else None,
        },
        "pending_migrations": pending_migrations(),
        "checks": run_checks(),
    })
