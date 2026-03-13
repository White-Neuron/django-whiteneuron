from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
import logging
import ipaddress

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

def get_client_ip(request):
    for h in ("CF-Connecting-IP", "True-Client-IP"):
        ip = request.headers.get(h)
        if ip:
            return ip, request.headers.get("User-Agent")

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        ip_list = [x.strip() for x in xff.split(",")]
        ip = next((x for x in ip_list if is_global_ip(x)), None)
        if ip:
            return ip, request.headers.get("User-Agent")

    ra = request.META.get("REMOTE_ADDR")
    if ra:
        return ra, request.headers.get("User-Agent")

    return None, request.headers.get("User-Agent")


from django.utils import timezone
from .models import UserActivity
class UserActivityMiddleware:

    exclude_paths = [
        ('/media/', 'contains'),
        ('/static/', 'contains'),
        ('/__reload__/', 'contains'),
        ('/base/useractivity/', 'contains'),
        ('/__debug__/', 'contains'),
        ('/jsi18n/', 'contains'),
        ('/.well-known/', 'contains'),
    ]

    def __init__(self, get_response):
        self.get_response = get_response
    
    def process_request(self, request):
        request._request_time = timezone.now()

    def get_response(self, request):
        return self.get_response(request)
    
    def do_not_track(self, request):
        for path, condition in self.exclude_paths:
            if condition == 'startwith' and request.path.startswith(path):
                return True
            if condition == 'contains' and path in request.path:
                return True
            if condition == 'exact' and request.path == path:
                return True
        return False

    def __call__(self, request):
        """
        user = models.ForeignKey(User, on_delete=models.CASCADE)
        ip_address = models.GenericIPAddressField(_("IP address"))
        user_agent = models.TextField(_("User agent"))
        path = models.CharField(_("Path"), max_length=255)
        method = models.CharField(_("Method"), max_length=10, choices=[("GET", "GET"), ("POST", "POST")])
        data = models.JSONField(_("Data"), null=True, blank=True)
        status_code = models.IntegerField(_("Status code"))
        timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
        timelapse = models.DurationField(_("Timelapse")) # Thời gian thực hiện hành động
        """

        response = self.get_response(request)

        if hasattr(request, "_request_time"):
            timelapse = timezone.now() - request._request_time
        else:
            timelapse = None
        if self.do_not_track(request):
            return response
        
        if request.user.is_authenticated:
            ip, user_agent = get_client_ip(request)
            UserActivity.objects.create(
                user=request.user,
                ip_address=ip,
                user_agent=user_agent,
                path=request.path,
                method=request.method,
                data=request.POST.dict(),
                status_code=response.status_code,
                timestamp=timezone.now(),
                timelapse=timelapse,
            )
        return response


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
