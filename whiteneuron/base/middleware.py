from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
import logging


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
        

import ipaddress
def get_client_ip(request):
    def is_public_ipv4(ip):
        try:
            ip_obj = ipaddress.ip_address(ip)
            return (
                isinstance(ip_obj, ipaddress.IPv4Address)
            )
        except ValueError:
            return False

    ip = request.headers.get('X-Client-Ip')
    if ip is None:
        ip = request.headers.get('X-Forwarded-For')
        if ip:
            # Có thể có danh sách IP cách nhau bởi dấu phẩy
            ip_list = [x.strip() for x in ip.split(',')]
            ip = next((x for x in ip_list if is_public_ipv4(x)), None)
    if ip is None:
        remote_addr = request.META.get('REMOTE_ADDR')
        if is_public_ipv4(remote_addr):
            ip = remote_addr

    if not ip:
        ip = 'Public IPv4 not found'
    user_agent = request.headers.get('User-Agent')
    return ip, user_agent

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
        # Chỉ xử lý khi user chưa đăng nhập và path có chứa "login"
        if (
            not request.user.is_authenticated
            and 'login' in request.path.lower()
            and request.method == 'GET'
        ):
            try:
                # Kiểm tra xem guest user có tồn tại không
                guest_user = User.objects.filter(username='guest').first()
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
