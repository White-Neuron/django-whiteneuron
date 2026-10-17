import hashlib
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
import ipaddress
import time
import json
import re
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
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

        # read env for extra exempt paths (comma-separated)
        from django.conf import settings
        extra_paths = getattr(settings, 'RATE_LIMIT_EXEMPT_PATHS', '')
        for p in extra_paths.split(','):
            p = p.strip()
            if p and p not in self.EXEMPT_PATHS:
                self.EXEMPT_PATHS += (p,)


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
        self._ensure_blacklist_loaded()
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
        # Dynamic patterns (Redis → DB fallback), kept compiled in process memory
        substrings, regexes = self._ua_patterns()
        if any(sub in ua_lower for sub in substrings):
            return True
        return any(rx.search(ua) for rx in regexes)

    _UA_PATTERNS_TTL = 30  # seconds a worker reuses its compiled UA patterns
    _BLACKLIST_CHECK_INTERVAL = 60

    def _ua_patterns(self):
        """(substrings, compiled regexes), refreshed from the cache every 30s.

        Previously the whole pattern list was fetched and unpickled from Redis and
        every regex recompiled on each request.
        """
        now = time.monotonic()
        memo = getattr(self, '_ua_memo', None)
        if memo and now - memo[0] < self._UA_PATTERNS_TTL:
            return memo[1]
        substrings, regexes = [], []
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
                        regexes.append(re.compile(pattern, re.IGNORECASE))
                    except re.error:
                        pass  # pattern regex không hợp lệ, bỏ qua
                else:
                    substrings.append(pattern.lower())
        except Exception:
            pass
        self._ua_memo = (now, (substrings, regexes))
        return substrings, regexes

    def _ensure_blacklist_loaded(self):
        now = time.monotonic()
        if now - getattr(self, '_blacklist_checked_at', -1e9) < self._BLACKLIST_CHECK_INTERVAL:
            return
        self._blacklist_checked_at = now
        from .models import IPBlacklist
        IPBlacklist.ensure_cache_loaded()

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
        count = hit_counter(f'rl:global:{ip}', self.window)
        return count is not None and count > self.rate


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
        

_VP_VERSION_KEY = "wn:vp:version"
_vp_version_memo = (0.0, 1)


def visit_profile_cache_version():
    """Namespace for cached VisitProfile ids; bumped when profiles are deleted.

    Memoized per process for 30s to avoid an extra cache round-trip per request.
    """
    global _vp_version_memo
    now = time.monotonic()
    if now - _vp_version_memo[0] < 30:
        return _vp_version_memo[1]
    try:
        version = cache.get(_VP_VERSION_KEY) or 1
    except Exception:
        version = _vp_version_memo[1]
    _vp_version_memo = (now, version)
    return version


def invalidate_visit_profile_cache():
    """Call after deleting VisitProfiles so cached ids aren't reused."""
    global _vp_version_memo
    try:
        try:
            version = cache.incr(_VP_VERSION_KEY)
        except ValueError:
            version = 2
            cache.set(_VP_VERSION_KEY, version, timeout=None)
    except Exception:
        return
    _vp_version_memo = (time.monotonic(), version)


def hit_counter(key, window):
    """Atomically count a hit in a fixed window; None if the cache is unavailable.

    ``add`` creates the key with its TTL only if missing, then ``incr`` is atomic on
    Redis/Memcached — so the TTL is always set and concurrent requests can't reset it.
    """
    try:
        if cache.add(key, 1, timeout=window):
            return 1
        return cache.incr(key)
    except ValueError:  # expired between add and incr
        try:
            cache.set(key, 1, timeout=window)
        except Exception:
            return None
        return 1
    except Exception:
        return None


def is_global_ip(ip):
    try:
        obj = ipaddress.ip_address(ip)
        return obj.is_global  
    except ValueError:
        return False

def _parse_ip(raw: str | None) -> str | None:
    """Validate và trả về IP string chuẩn hóa, None nếu không hợp lệ.

    Accepts the forms proxies put in X-Forwarded-For: "1.2.3.4", "1.2.3.4:5678",
    "2001:db8::1" and "[2001:db8::1]:5678".
    """
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("["):  # [v6]:port
        raw = raw[1:].split("]", 1)[0]
    elif raw.count(":") == 1:  # v4:port
        raw = raw.split(":", 1)[0]
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

    remote_ip = _parse_ip(request.META.get("REMOTE_ADDR"))

    # X-Forwarded-For: "client, proxy1, proxy2". Every proxy appends the address it
    # received the request from, so only the right-hand part is trustworthy:
    #   - TRUSTED_PROXY_COUNT = N: the N-th entry from the right (exact; recommended)
    #   - 0 (auto): the right-most public address
    #   - IGNORE_X_FORWARDED_FOR = True: never trust the header (app exposed directly)
    xff = request.headers.get("X-Forwarded-For")
    if xff and not getattr(settings, "IGNORE_X_FORWARDED_FOR", False):
        hops = [hop.strip() for hop in xff.split(",") if hop.strip()]  # raw: keep positions
        proxy_count = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0) or 0)
        if proxy_count:
            ip = _parse_ip(hops[-proxy_count]) if len(hops) >= proxy_count else None
        else:
            ip = next((p for p in (_parse_ip(h) for h in reversed(hops)) if p and is_global_ip(p)), None)
        if ip:
            return ip, request.headers.get("User-Agent")

    if remote_ip:
        return remote_ip, request.headers.get("User-Agent")

    return None, request.headers.get("User-Agent")


from django.db import IntegrityError, connection
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from .models import UserActivity, AnonymousActivity, VisitProfile
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
        ('/ws/', 'startswith'),  # WebSocket handshake — không log, không rate-limit per-user
        ('/health/', 'startswith'),  # Health check endpoint — không log, không rate-limit per-user
    ]

    def __init__(self, get_response):

        # read env for extra exclude paths (comma-separated, format: "path,condition;path,condition;...")
        from django.conf import settings
        extra = getattr(settings, 'USER_ACTIVITY_EXCLUDE_PATHS', '')
        for item in extra.split(';'):
            item = item.strip()
            if not item:
                continue
            try:
                path, condition = item.split(',')
                condition = condition.strip().lower()
                if condition not in ('startswith', 'contains', 'exact'):
                    continue
                self.exclude_paths.append((path.strip(), condition))
            except ValueError:
                continue


        self._get_response = get_response
        from django.conf import settings
        self.user_rate = getattr(settings, 'USER_RATE_LIMIT_REQUESTS', 200)
        self.user_window = getattr(settings, 'USER_RATE_LIMIT_WINDOW', 60)
        self._MAX_BODY_SIZE = 1024 * 1024  # 1MB

    def do_not_track(self, request):
        for path, condition in self.exclude_paths:
            if condition == 'startswith' and request.path.startswith(path):
                return True
            if condition == 'contains' and path in request.path:
                return True
            if condition == 'exact' and request.path == path:
                return True
        return False

    def _is_user_rate_limited(self, user_id: int) -> bool:
        count = hit_counter(f'rl:user:{user_id}', self.user_window)
        if count is None:
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

        # Đọc body sớm cho JSON requests (trước khi DRF consume)
        if (request.method in ('POST', 'PATCH', 'PUT', 'DELETE')
                and 'application/json' in request.META.get('CONTENT_TYPE', '')
                and self._content_length(request) <= self._MAX_BODY_SIZE):
            try:
                raw_body = request.body
                if len(raw_body) <= self._MAX_BODY_SIZE:
                    request._raw_body = raw_body.decode('utf-8')
            except Exception:
                pass

        response = self._get_response(request)

        # Parse cached body thành dict cho logging (sau khi DRF đã consume request stream)
        if hasattr(request, '_raw_body'):
            try:
                body_data = json.loads(request._raw_body)
                if isinstance(body_data, dict):
                    request._visit_data = self._sanitize_post(body_data)
            except (json.JSONDecodeError, ValueError):
                pass

        if skip:
            return response

        timelapse = timezone.now() - request._request_time

        ip, user_agent = get_client_ip(request)

        if not ip:
            return response

        # Lấy data đã parse từ body (nếu có), fallback về _get_request_data
        log_data = getattr(request, '_visit_data', None)
        if log_data is None:
            log_data = self._get_request_data(request)

        if request.user.is_authenticated:
            model, extra = UserActivity, {'user': request.user}
        elif getattr(response, 'status_code', None) not in (301, 302):
            model, extra = AnonymousActivity, {}
        else:
            return response
        fields = dict(
            extra,
            path=request.path[:255],
            method=request.method,
            data=log_data,
            status_code=response.status_code,
            timestamp=timezone.now(),
            timelapse=timelapse,
        )
        try:
            model.objects.create(profile_id=self._visit_profile_id(ip, user_agent), **fields)
        except IntegrityError:
            # cached profile was deleted meanwhile: forget it and log without profile
            self._forget_visit_profile(ip, user_agent)
            model.objects.create(profile_id=None, **fields)
        return response

    _PROFILE_CACHE_TTL = 3600
    _LAST_SEEN_INTERVAL = 300  # refresh VisitProfile.last_seen at most every 5 minutes

    @staticmethod
    def _visit_profile_key(ip_address, user_agent):
        ua = user_agent[:500] if user_agent else ''
        version = visit_profile_cache_version()
        return f"wn:vp:{version}:" + hashlib.sha1(f"{ip_address}|{ua}".encode()).hexdigest()

    def _forget_visit_profile(self, ip_address, user_agent):
        try:
            cache.delete(self._visit_profile_key(ip_address, user_agent))
        except Exception:
            pass

    def _visit_profile_id(self, ip_address: str, user_agent: str):
        """VisitProfile id for (IP, UA), cached so that logging costs a single INSERT.

        Without the cache every tracked request did SELECT profile + UPDATE last_seen
        + INSERT activity; now the profile lookup and the last_seen write are rare.
        """
        # Inside a transaction (tests, ATOMIC wrappers) a cached id could point at a
        # row rolled back since; the FK is only checked at commit, too late to recover.
        if connection.in_atomic_block:
            return self._get_or_create_visit_profile(ip_address, user_agent)[0].pk
        key = self._visit_profile_key(ip_address, user_agent)
        try:
            profile_id = cache.get(key)
        except Exception:
            profile_id = None
        if profile_id is None:
            profile, created = self._get_or_create_visit_profile(ip_address, user_agent)
            profile_id = profile.pk
            try:
                cache.set(key, profile_id, timeout=self._PROFILE_CACHE_TTL)
                if created:
                    cache.add(f"{key}:seen", 1, timeout=self._LAST_SEEN_INTERVAL)
            except Exception:
                pass
            if created:
                return profile_id
        try:
            # cache.add is atomic: only the first request in each interval writes
            touch = cache.add(f"{key}:seen", 1, timeout=self._LAST_SEEN_INTERVAL)
        except Exception:
            touch = True
        if touch:
            VisitProfile.objects.filter(pk=profile_id).update(last_seen=timezone.now())
        return profile_id

    def _get_or_create_visit_profile(self, ip_address: str, user_agent: str):
        """Get or create a VisitProfile based on IP + UA. Returns (profile, created)."""
        ua = user_agent[:500] if user_agent else ''
        try:
            return VisitProfile.objects.get(ip_address=ip_address, user_agent=ua), False
        except VisitProfile.DoesNotExist:
            try:
                return VisitProfile.objects.create(ip_address=ip_address, user_agent=ua), True
            except IntegrityError:
                # Race condition: profile được tạo bởi request khác giữa 2 bước trên
                profile, _ = VisitProfile.objects.get_or_create(
                    ip_address=ip_address, user_agent=ua
                )
                return profile, False

    @staticmethod
    def _content_length(request):
        try:
            return int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            return 0

    def _get_request_data(self, request):
        if request.method == 'POST' and request.POST:
            return self._sanitize_post(request.POST.dict())
        # JSON body đã được cache trong __call__, chỉ fallback khi cần
        try:
            raw = getattr(request, '_raw_body', None)
            if raw is None and 0 < self._content_length(request) <= self._MAX_BODY_SIZE:
                raw = request.body.decode('utf-8')
            if raw:
                body = json.loads(raw)
                if isinstance(body, dict):
                    return self._sanitize_post(body)
        except Exception:
            pass
        return {}

    _SENSITIVE_FIELDS = frozenset({
        'password', 'password1', 'password2', 'old_password', 'new_password',
        'token', 'access_token', 'refresh_token', 'secret', 'api_key',
        'credit_card', 'card_number', 'cvv', 'csrfmiddlewaretoken',
    })

    _SENSITIVE_VALUE_PATTERNS = frozenset({
        'authorization', 'bearer', 'apikey', 'api-key', 'x-api-key',
        'x-apikey', 'x-access-token', 'jwt', 'sessionid', 'session_id',
        'sid', 'auth', 'credential', 'credentials', 'passwd', 'passphrase',
    })

    def _is_sensitive_value(self, value) -> bool:
        if not isinstance(value, str):
            return False
        low = value.lower()
        for pattern in self._SENSITIVE_VALUE_PATTERNS:
            if pattern in low:
                return True
        # JWT token: three base64url segments separated by dots (min ~50 chars)
        parts = value.split('.')
        if len(parts) == 3 and all(
            len(p) >= 10 and all(
                c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in p
            ) for p in parts
        ):
            return True
        # Long base64 string (no dots, min 40 chars)
        if len(value) >= 40 and all(
            c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/' for c in value
        ):
            return True
        # Long hex string (min 32 chars)
        if len(value) >= 32 and all(c in '0123456789abcdef' for c in low):
            return True
        return False

    def _sanitize_post(self, data) -> dict:
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if k.lower() in self._SENSITIVE_FIELDS:
                    result[k] = '***'
                elif isinstance(v, (dict, list)):
                    result[k] = self._sanitize_post(v)
                elif self._is_sensitive_value(v):
                    result[k] = '***'
                else:
                    result[k] = v
            return result
        if isinstance(data, list):
            return [self._sanitize_post(item) for item in data]
        return data


from .thread_local import thread_local
from .utils import get_guest_user, log_in_guest
import logging
logger = logging.getLogger(__name__)

class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        thread_local.request = request
        try:
            return self.get_response(request)
        finally:
            # don't leak this request/user into later work on the same thread
            thread_local.request = None


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
                guest_user = get_guest_user()
                if guest_user:
                    # Tự động đăng nhập guest user
                    log_in_guest(request, guest_user)
                    # Nếu có tham số next thì redirect luôn tới đó (URL, không phải tên route)
                    next_url = request.GET.get('next')
                    if next_url and url_has_allowed_host_and_scheme(
                        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
                    ):
                        return HttpResponseRedirect(next_url)
            except Exception:
                logger.exception("Auto guest login failed")

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
