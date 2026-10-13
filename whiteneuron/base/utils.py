from django.utils import timezone
from .models import User, UserActivity, AnonymousActivity
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy
from django.core.cache import caches

# count time run function
def timeit(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        # print(f"{func.__name__} run in {time.time()-start} seconds")
        return result
    return wrapper

from django.core.exceptions import FieldDoesNotExist

_BADGE_CACHE_TIMEOUT = 60

def _make_cache_key(*parts):
    return ":".join(str(p) for p in parts)

def _cacheable_filter_kwargs(filter_kwargs):
    if filter_kwargs is None:
        return "all"
    try:
        return str(sorted(filter_kwargs.items()))
    except TypeError:
        return str(filter_kwargs)

def base_badge_callback(request, model, filter_kwargs=None):
    cache_key = _make_cache_key("badge", model.__name__, _cacheable_filter_kwargs(filter_kwargs))
    cached = caches["default"].get(cache_key)
    if cached is not None:
        return cached

    today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)

    c = getattr(model, 'objects_all', model.objects)
    if hasattr(model, 'updated_at'):
        c = c.filter(updated_at__gte=today)
    elif hasattr(model, 'created_at'):
        c = c.filter(created_at__gte=today)

    if filter_kwargs:
        c = c.filter(**filter_kwargs).count()
    else:
        c = c.count()

    caches["default"].set(cache_key, c, timeout=_BADGE_CACHE_TIMEOUT)
    return c


def user_badge_callback(request):
    return base_badge_callback(request, User)

def useractivity_badge_callback(request):
    cache_key = _make_cache_key("badge", "UserActivity")
    cached = caches["default"].get(cache_key)
    if cached is not None:
        return cached

    c = UserActivity.objects.filter(timestamp__gte=timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    caches["default"].set(cache_key, c, timeout=_BADGE_CACHE_TIMEOUT)
    return c

def anonymousactivity_badge_callback(request):
    cache_key = _make_cache_key("badge", "AnonymousActivity")
    cached = caches["default"].get(cache_key)
    if cached is not None:
        return cached

    c = AnonymousActivity.objects.filter(timestamp__gte=timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    caches["default"].set(cache_key, c, timeout=_BADGE_CACHE_TIMEOUT)
    return c

def visitprofile_badge_callback(request):
    from .models import VisitProfile
    cache_key = _make_cache_key("badge", "VisitProfile")
    cached = caches["default"].get(cache_key)
    if cached is not None:
        return cached

    c = VisitProfile.objects.filter(last_seen__gte=timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    caches["default"].set(cache_key, c, timeout=_BADGE_CACHE_TIMEOUT)
    return c


def group_badge_callback(request):
    return 0

def iter_nav_items(items):
    """Leaf sidebar items: sub-navigation parents (unfold "items") are expanded."""
    for item in items:
        children = item.get('items')
        if isinstance(children, (list, tuple)) and children:
            yield from iter_nav_items(children)
        else:
            yield item


def app_badge_callback(request):
    from django.conf import settings
    try:
        navigation = settings.UNFOLD.get('SIDEBAR', {}).get('navigation', [])
        return sum(
            1 for section in navigation for item in iter_nav_items(section.get('items', []))
            if item.get('title') and item.get('link') and '/base/app/' not in str(item.get('link'))
        )
    except Exception:
        return 0

def user_group_names(user):
    """Group names of ``user``, memoized on the user object (one query per request).

    Sidebar permission callbacks run for every item on every admin page; without
    this each of them issued its own ``groups.filter(...).exists()`` query.
    """
    if not user or not user.is_authenticated:
        return frozenset()
    names = getattr(user, "_wn_group_names", None)
    if names is None:
        names = frozenset(user.groups.values_list("name", flat=True))
        user._wn_group_names = names
    return names


def is_guest_user(user):
    if not user or not user.is_authenticated:
        return True
    if user.username.lower() == "guest":
        return True
    return bool(user_group_names(user) & {"Khách thăm", "Guest", "guest"})


def permission_callback(request):
    return False

def permission_superuser_callback(request):
    return request.user.is_superuser

def permission_admin_callback(request):
    if request.user.is_superuser:
        return True
    return 'Quản trị viên' in user_group_names(request.user)

def permission_non_guest_callback(request):
    return not is_guest_user(request.user)

def permission_viewer_callback(request):
    if not request.user.is_authenticated:
        return False
    return True


import os as _os

def _load_signature():
    sig_path = _os.path.normpath(
        _os.path.join(_os.path.dirname(__file__), '..', 'templates', 'admin', 'signature.html')
    )
    with open(sig_path, 'r', encoding='utf-8') as f:
        return f.read()


TEMPLATE="""
Chào {username},
<br />
Bạn đã được cấp quyền truy cập vào <b>{system_name}</b>. Dưới đây là thông tin
đăng nhập của bạn:
<br />
<b> Tên đăng nhập: {username} </b>
<br />
<b> Mật khẩu tạm thời: {password} </b>
<br />
<b> Lưu ý: </b> Bạn sẽ được yêu cầu thay đổi mật khẩu sau lần đăng nhập đầu tiên
để đảm bảo an toàn cho thông tin cá nhân và tài khoản của bạn.
<br />
<br />
Để đăng nhập, vui lòng truy cập <a href="{url}">đường dẫn trang đăng nhập</a> và
nhập thông tin trên.
<br />
Nếu bạn gặp bất kỳ vấn đề nào trong quá trình đăng nhập, đừng ngần ngại liên hệ
với bộ phận hỗ trợ kỹ thuật của chúng tôi.
<br />
Trân trọng,
<br />
{signature}
"""

from django.conf import settings
from .models import Mail
def send_email_login(username, password, receiver, is_reset=False):
    global TEMPLATE
    SUBJECT = "Đặt lại mật khẩu hệ thống" if is_reset else "Thông tin đăng nhập hệ thống"
    SYSTEM_NAME= settings.NAME
    URL= settings.URL
    subject= SUBJECT
    template= TEMPLATE
    system_name= SYSTEM_NAME
    context= template.format(username= username, password= password, url= URL, system_name= system_name, signature= _load_signature())
    mail= Mail.objects.create(subject= subject, content= context, receiver= receiver)
    # SMTP can take seconds: hand it to a worker when Celery is enabled.
    # Returns True/False when sent inline, None when queued.
    from .queue import enqueue, async_tasks_enabled
    from .tasks import send_mail_task
    result = enqueue(send_mail_task, mail.pk, redact=password)
    return None if async_tasks_enabled() else result

def make_random_password(length=12):
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

from django.utils.safestring import mark_safe
def announcement_callback(request):
    from django.conf import settings
    if not getattr(settings, 'ANNOUNCEMENT_CONTENT_HTML_FILE', None):
        return None
    version = getattr(settings, 'VERSION', '0.1.0')
    return {
        "title": format_lazy(
            _("New announcement for {NAME} - version {VERSION}!"),
            NAME=_(settings.NAME),
            VERSION=version,
        ),
        "version": version,
        "badge": _("NEW"),
    }
