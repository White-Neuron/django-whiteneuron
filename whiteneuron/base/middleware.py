from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
import ipaddress
import re
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

class RateLimitMiddleware:
    """
    Global rate limiting dựa trên IP.
    Mặc định: 300 request/phút per IP.
    Cấu hình qua settings:
        RATE_LIMIT_REQUESTS  (int, default 300)
        RATE_LIMIT_WINDOW    (int seconds, default 60)
    """

    EXEMPT_PATHS = (
        '/static/',
        '/media/',
        '/__debug__/',
        '/__reload__/',
        '/.well-known/',
    )

    def __init__(self, get_response):
        self.get_response = get_response
        from django.conf import settings
        self.rate = getattr(settings, 'RATE_LIMIT_REQUESTS', 300)
        self.window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
        # IP Blacklist: parse từ settings (comma-separated IPs và/hoặc CIDR)
        raw_blacklist = getattr(settings, 'IP_BLACKLIST', '')
        self._blacklist_ips: set = set()
        self._blacklist_nets: list = []
        for entry in raw_blacklist.split(','):
            entry = entry.strip()
            if not entry:
                continue
            try:
                net = ipaddress.ip_network(entry, strict=False)
                if net.num_addresses == 1:
                    self._blacklist_ips.add(net.network_address)
                else:
                    self._blacklist_nets.append(net)
            except ValueError:
                pass
        # UA Blacklist: static keywords từ settings (comma-separated)
        raw_ua_blacklist = getattr(settings, 'UA_BLACKLIST', '')
        self._ua_keywords: list = [kw.strip().lower() for kw in raw_ua_blacklist.split(',') if kw.strip()]

    def _is_blacklisted(self, ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        # Static blacklist from .env (loaded at startup, O(1) for IPs, supports CIDRs)
        if addr in self._blacklist_ips:
            return True
        if any(addr in net for net in self._blacklist_nets):
            return True
        # Dynamic blacklist from Redis (managed via Django admin, real-time)
        try:
            if cache.get(f'blacklist:dynamic:{addr}'):
                return True
        except Exception:
            pass
        return False

    def _is_ua_blacklisted(self, ua: str) -> bool:
        if not ua:
            return False
        ua_lower = ua.lower()
        # Static keywords từ settings
        for kw in self._ua_keywords:
            if kw in ua_lower:
                return True
        # Dynamic patterns từ Redis, fallback DB khi cache miss (Redis restart / first boot)
        try:
            from .models import UA_PATTERNS_CACHE_KEY, UABlacklist
            patterns = cache.get(UA_PATTERNS_CACHE_KEY)
            if patterns is None:
                # Cache miss: load từ DB và warm lại cache
                patterns = list(
                    UABlacklist.objects.filter(is_active=True).values_list('pattern', 'is_regex')
                )
                cache.set(UA_PATTERNS_CACHE_KEY, patterns, timeout=None)
            for pattern, is_regex in patterns:
                if is_regex:
                    try:
                        if re.search(pattern, ua, re.IGNORECASE):
                            return True
                    except re.error:
                        pass  # pattern regex không hợp lệ, bỏ qua
                else:
                    if pattern.lower() in ua_lower:
                        return True
        except Exception:
            pass
        return False

    def __call__(self, request):
        if not any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            ip, _ = get_client_ip(request)
            if ip and self._is_blacklisted(ip):
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return JsonResponse(
                        {'detail': 'Your IP has been blocked.'},
                        status=403,
                    )
                html = render_to_string('403.html', {}, request=request)
                return HttpResponse(html, status=403)
            ua = request.headers.get('User-Agent', '')
            if ua and self._is_ua_blacklisted(ua):
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return JsonResponse(
                        {'detail': 'Access denied.'},
                        status=403,
                    )
                html = render_to_string('403.html', {}, request=request)
                return HttpResponse(html, status=403)
            if ip and self._is_rate_limited(ip):
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return JsonResponse(
                        {'detail': 'Too many requests. Please slow down.'},
                        status=429,
                    )
                html = render_to_string('429.html', {'retry_after': self.window}, request=request)
                response = HttpResponse(html, status=429)
                response['Retry-After'] = str(self.window)
                return response
        return self.get_response(request)

    def _is_rate_limited(self, ip: str) -> bool:
        # incr-first pattern: atomic trên Redis.
        # Khi count == 1: key mới tạo bởi Redis (không có TTL) → cần touch để set TTL.
        # Khi ValueError: LocMemCache không tự tạo key → dùng set với timeout.
        # Khi Exception khác (VD: ConnectionError khi Redis không đủ reach): fail-open (không block).
        key = f'rl:global:{ip}'
        try:
            count = cache.incr(key)
            if count == 1:
                cache.touch(key, timeout=self.window)
        except ValueError:
            cache.set(key, 1, timeout=self.window)
            count = 1
        except Exception:
            return False  # fail-open: không block khi cache lỗi
        return count > self.rate


class ReadonlyExceptionHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if (
            exception
            and repr(exception)
            == "OperationalError('attempt to write a readonly database')"
        ):
            messages.warning(
                request,
                _(
                    "Database is operating in readonly mode. Not possible to save any data."
                ),
            )
            return redirect(reverse_lazy("admin:login"))
        

def is_global_ip(ip):
    try:
        obj = ipaddress.ip_address(ip)
        return obj.is_global  
    except ValueError:
        return False

def _parse_ip(raw: str | None) -> str | None:
    """Validate và trả về IP string chuẩn hóa, None nếu không hợp lệ."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None

def get_client_ip(request):
    from django.conf import settings
    # CF-Connecting-IP: chỉ tin tưởng khi deploy sau Cloudflare Proxy (không phải Tunnel).
    # Cloudflare Tunnel (cloudflared) KHÔNG set header này — nếu dùng Tunnel, tắt cờ này.
    # Set BEHIND_CLOUDFLARE=True trong settings để bật.
    if getattr(settings, 'BEHIND_CLOUDFLARE', False):
        for h in ("CF-Connecting-IP", "True-Client-IP"):
            ip = _parse_ip(request.headers.get(h))
            if ip:
                return ip, request.headers.get("User-Agent")

    # X-Forwarded-For: format "client, proxy1, proxy2" — lấy IP client đầu tiên là global.
    # Lưu ý: XFF dễ bị spoof khi không có trusted proxy; chỉ dùng khi BEHIND_CLOUDFLARE=False.
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        for raw in xff.split(","):
            ip = _parse_ip(raw)
            if ip and is_global_ip(ip):
                return ip, request.headers.get("User-Agent")

    ra = request.META.get("REMOTE_ADDR")
    if ra:
        ip = _parse_ip(ra)
        if ip:
            return ip, request.headers.get("User-Agent")

    return None, request.headers.get("User-Agent")


from django.utils import timezone
from .models import UserActivity
class UserActivityMiddleware:
    """
    Ghi log hoạt động user và rate limit per-user cho authenticated requests.
    Cấu hình qua settings:
        USER_RATE_LIMIT_REQUESTS  (int, default 200) — số request per window per user
        USER_RATE_LIMIT_WINDOW    (int seconds, default 60)
    """

    exclude_paths = [
        ('/media/', 'contains'),
        ('/static/', 'contains'),
        ('/__reload__/', 'contains'),
        ('/base/useractivity/', 'contains'),
        ('/__debug__/', 'contains'),
        ('/jsi18n/', 'contains'),
        ('/.well-known/', 'contains'),
        ('/ws/', 'startwith'),  # WebSocket handshake — không log, không rate-limit per-user
    ]

    def __init__(self, get_response):
        self._get_response = get_response
        from django.conf import settings
        self.user_rate = getattr(settings, 'USER_RATE_LIMIT_REQUESTS', 200)
        self.user_window = getattr(settings, 'USER_RATE_LIMIT_WINDOW', 60)

    def do_not_track(self, request):
        for path, condition in self.exclude_paths:
            if condition == 'startwith' and request.path.startswith(path):
                return True
            if condition == 'contains' and path in request.path:
                return True
            if condition == 'exact' and request.path == path:
                return True
        return False

    def _is_user_rate_limited(self, user_id: int) -> bool:
        # incr-first pattern: atomic trên Redis.
        # Khi count == 1: key mới tạo bởi Redis (không có TTL) → cần touch để set TTL.
        # Khi ValueError: LocMemCache không tự tạo key → dùng set với timeout.
        # Khi Exception khác (VD: ConnectionError khi Redis không reach được): fail-open.
        key = f'rl:user:{user_id}'
        try:
            count = cache.incr(key)
            if count == 1:
                cache.touch(key, timeout=self.user_window)
        except ValueError:
            cache.set(key, 1, timeout=self.user_window)
            count = 1
        except Exception:
            return False  # fail-open: không block khi cache lỗi
        return count > self.user_rate

    def __call__(self, request):
        # Ghi nhận thời điểm bắt đầu (fix: đặt ở đây thay vì process_request)
        request._request_time = timezone.now()

        skip = self.do_not_track(request)

        # Per-user rate limit cho authenticated users
        if not skip and request.user.is_authenticated:
            if self._is_user_rate_limited(request.user.id):
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return JsonResponse(
                        {'detail': 'Too many requests. Please slow down.'},
                        status=429,
                    )
                html = render_to_string('429.html', {'retry_after': self.user_window}, request=request)
                response = HttpResponse(html, status=429)
                response['Retry-After'] = str(self.user_window)
                return response

        response = self._get_response(request)

        if skip:
            return response

        timelapse = timezone.now() - request._request_time

        if request.user.is_authenticated:
            ip, user_agent = get_client_ip(request)
            UserActivity.objects.create(
                user=request.user,
                ip_address=ip,
                user_agent=user_agent,
                path=request.path,
                method=request.method,
                data=self._sanitize_post(request.POST.dict()),
                status_code=response.status_code,
                timestamp=timezone.now(),
                timelapse=timelapse,
            )
        return response

    _SENSITIVE_FIELDS = frozenset({
        'password', 'password1', 'password2', 'old_password', 'new_password',
        'token', 'access_token', 'refresh_token', 'secret', 'api_key',
        'credit_card', 'card_number', 'cvv', 'csrfmiddlewaretoken',
    })

    def _sanitize_post(self, data: dict) -> dict:
        return {
            k: '***' if k.lower() in self._SENSITIVE_FIELDS else v
            for k, v in data.items()
        }


from .thread_local import thread_local
from django.contrib.auth import login
from .models import User

class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        thread_local.request = request
        response = self.get_response(request)
        return response


class AutoGuestLoginMiddleware:
    """
    Middleware tự động đăng nhập guest user khi người dùng chưa đăng nhập 
    và truy cập vào bất kỳ path nào có chứa "login".
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Nếu user đã chọn không auto login guest nữa (được set qua cookie) thì bỏ qua
        if request.COOKIES.get("skip_auto_guest") == "1":
            return self.get_response(request)

        # Chỉ xử lý khi user chưa đăng nhập và path có chứa "login"
        if (
            not request.user.is_authenticated
            and 'login' in request.path.lower()
            and request.method == 'GET'
        ):
            try:
                # Kiểm tra xem guest user có tồn tại, đang active và có quyền staff không
                guest_user = User.objects.filter(username='guest', is_active=True, is_staff=True).first()
                if guest_user:
                    # Tự động đăng nhập guest user
                    login(request, guest_user, backend='django.contrib.auth.backends.ModelBackend')
                    # Nếu có tham số next thì redirect luôn tới đó
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                else:
                    pass
            except Exception as e:
                pass

        response = self.get_response(request)
        return response



### Middleware để buộc sử dụng ngôn ngữ mặc định nếu người dùng chưa chọn ngôn ngữ nào cả (không có cookie và không có ngôn ngữ trong URL)
from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import get_language_from_path


class ForceDefaultLanguageMiddleware(MiddlewareMixin):
    """Use LANGUAGE_CODE as default unless user explicitly chose a language."""

    def process_request(self, request):
        cookie_name = getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")
        has_language_cookie = bool(request.COOKIES.get(cookie_name))
        has_language_in_path = bool(get_language_from_path(request.path_info))

        # Keep explicit language choices, but ignore browser Accept-Language by default.
        if not has_language_cookie and not has_language_in_path:
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = translation.get_language()


class DownloadResponseFlagMiddleware:
    """Flag attachment responses so frontend can stop loading for file downloads."""

    REQUEST_TOKEN_COOKIE = "wn_loading_token"
    RESPONSE_DONE_COOKIE = "wn_loading_done"
    TOKEN_PATTERN = re.compile(r"^[a-z0-9]{8,64}$")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        request_token = request.COOKIES.get(self.REQUEST_TOKEN_COOKIE)
        content_disposition = (response.get("Content-Disposition") or "").lower()
        is_attachment = "attachment" in content_disposition

        if request_token and is_attachment and self.TOKEN_PATTERN.match(request_token):
            response.set_cookie(
                self.RESPONSE_DONE_COOKIE,
                request_token,
                max_age=120,
                path="/",
                samesite="Lax",
            )

        return response
