"""Small helpers shared by the package's JSON endpoints (system, announcement, notifications)."""
import functools
import hmac

from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def json_response(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def api_login_required(view):
    """401 JSON instead of a redirect to the login page."""

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return json_response({"detail": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def require_methods(*methods):
    """``require_http_methods`` that answers JSON: 405 ``{"detail": ...}`` with ``Allow``.

    Django's own decorator returns an empty body, a third error shape for JSON clients (#76).
    """
    allowed = [m.upper() for m in methods]

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method not in allowed:
                response = json_response(
                    {"detail": f'Method "{request.method}" not allowed.', "allowed": allowed}, status=405)
                response["Allow"] = ", ".join(allowed)
                return response
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


# GET also answers HEAD, as Django's require_GET does not but probes and caches expect
require_GET = require_methods("GET", "HEAD")
require_POST = require_methods("POST")


class _JsonCsrfCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return json_response({"detail": f"CSRF failed: {reason}"}, status=403)


def api_csrf_protect(view):
    """The CSRF check of ``CsrfViewMiddleware``, failing with JSON 403 instead of Django's
    HTML page. The view is marked exempt so the middleware leaves it to this check."""
    check = _JsonCsrfCheck(lambda request: None)

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        rejected = check.process_view(request, None, args, kwargs)
        if rejected is not None:
            return rejected
        return view(request, *args, **kwargs)

    wrapper.csrf_exempt = True
    return wrapper


def not_found(request, *args, **kwargs):
    """JSON 404 for any path under the API that matches no endpoint (e.g. a non-numeric id)."""
    return json_response({"detail": "Not found."}, status=404)


def has_system_access(request):
    """Superuser, or a request carrying ``SYSTEM_API_TOKEN``.

    Not ``is_staff``: every new user (guest included) is staff by default in whiteneuron.
    The token is read from ``X-System-Token`` or ``Authorization: Bearer <token>``.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.is_superuser:
        return True
    expected = getattr(settings, "SYSTEM_API_TOKEN", None)
    if not expected:
        return False
    provided = request.headers.get("X-System-Token", "")
    if not provided:
        auth = request.headers.get("Authorization", "")
        if auth[:7].lower() == "bearer ":
            provided = auth[7:].strip()
    return bool(provided) and hmac.compare_digest(str(provided).encode(), str(expected).encode())


def int_param(request, name, default, minimum=1, maximum=None):
    try:
        value = int(request.GET.get(name, default))
    except (TypeError, ValueError):
        value = default
    value = max(value, minimum)
    return min(value, maximum) if maximum is not None else value


def _page_url(request, page_number):
    """This request's absolute URL with ``page`` set (other query parameters kept)."""
    query = request.GET.copy()
    query["page"] = page_number
    return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")


def paginate(request, queryset, serialize):
    """Page a queryset with ``?page`` / ``?page_size`` (max ``MAX_PAGE_SIZE``).

    ``next`` / ``previous`` are absolute URLs (filters kept), or ``None`` at either end, so
    a client follows them instead of building page URLs itself.
    """
    from django.core.paginator import EmptyPage, Paginator

    page_size = int_param(request, "page_size", DEFAULT_PAGE_SIZE, maximum=MAX_PAGE_SIZE)
    page_number = int_param(request, "page", 1)
    paginator = Paginator(queryset, page_size)
    try:
        results = [serialize(obj) for obj in paginator.page(page_number).object_list]
    except EmptyPage:
        results = []
    num_pages = paginator.num_pages if paginator.count else 0
    has_next = page_number < num_pages
    # past the end: "previous" points at the last page that has results
    previous = min(page_number - 1, num_pages) if page_number > 1 else 0
    return {
        "count": paginator.count,
        "page": page_number,
        "page_size": page_size,
        "num_pages": paginator.num_pages,
        "next": _page_url(request, page_number + 1) if has_next else None,
        "previous": _page_url(request, previous) if previous >= 1 else None,
        "results": results,
    }
