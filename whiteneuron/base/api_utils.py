"""Small helpers shared by the package's JSON endpoints (system, announcement, notifications)."""
import functools
import hmac

from django.conf import settings
from django.http import JsonResponse

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


def paginate(request, queryset, serialize):
    """Page a queryset with ``?page`` / ``?page_size`` (max ``MAX_PAGE_SIZE``)."""
    from django.core.paginator import EmptyPage, Paginator

    page_size = int_param(request, "page_size", DEFAULT_PAGE_SIZE, maximum=MAX_PAGE_SIZE)
    page_number = int_param(request, "page", 1)
    paginator = Paginator(queryset, page_size)
    try:
        results = [serialize(obj) for obj in paginator.page(page_number).object_list]
    except EmptyPage:
        results = []
    return {
        "count": paginator.count,
        "page": page_number,
        "page_size": page_size,
        "num_pages": paginator.num_pages,
        "results": results,
    }
