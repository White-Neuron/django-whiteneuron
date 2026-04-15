import json
import random

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import RedirectView, TemplateView
from unfold.views import UnfoldModelAdminViewMixin


class HomeView(RedirectView):
    pattern_name = "admin:base_app_changelist"


class GuestLoginView(View):
    """POST-only view: đăng nhập guest không cần password, có CSRF protection."""

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['POST'])

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('admin:index')
        try:
            from .models import User
            guest = User.objects.filter(username='guest', is_active=True, is_staff=True).first()
            if guest:
                login(request, guest, backend='django.contrib.auth.backends.ModelBackend')
        except Exception:
            pass
        next_url = request.POST.get('next', '')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('admin:index')
    
from django.http import HttpResponse
def get_announcement_content(request):
    from django.conf import settings
    content_file= getattr(settings, 'ANNOUNCEMENT_CONTENT_HTML_FILE', None)
    if not content_file:
        return None
    content = render_to_string(content_file, request=request)
    return HttpResponse(content)