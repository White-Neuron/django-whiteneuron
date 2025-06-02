from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


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
        

def get_client_ip(request):
    ip = request.headers.get('X-Client-Ip')
    if ip is None:
        ip = request.headers.get('X-Forwarded-For')
        if ip:
            # Extract the first IP address if there's a comma-separated list
            ip = ip.split(',')[0].strip()
    if ip is None:
        try:
            ip = request.META.get('REMOTE_ADDR')
        except:
            ip = 'Not available!'
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

    
