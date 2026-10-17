import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import redirect_to_login
from django.db import DatabaseError
from django.http import HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import RedirectView, TemplateView
from unfold.views import UnfoldModelAdminViewMixin

from .utils import get_guest_user, log_in_guest, safe_next_url

import logging
logger = logging.getLogger(__name__)


class HomeView(RedirectView):
    pattern_name = "admin:base_app_changelist"


@method_decorator(login_not_required, name='dispatch')
class GuestLoginView(View):
    """POST-only view: đăng nhập guest không cần password, có CSRF protection."""

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['POST'])

    def post(self, request, *args, **kwargs):
        # anyone on the login page may switch to guest; login() flushes a different user's session
        next_url = safe_next_url(request, request.POST.get('next', ''))
        guest = get_guest_user()
        if guest:
            try:
                log_in_guest(request, guest)
            except DatabaseError:  # e.g. database-backed sessions on a read-only database
                logger.exception("Guest login failed")
                guest = None
        if not guest:
            messages.error(request, _("Guest login is not available."))
            if next_url:
                return redirect_to_login(next_url, reverse('admin:login'))
            return redirect('admin:login')
        return HttpResponseRedirect(next_url) if next_url else redirect('admin:index')

def get_announcement_content(request):
    """HTML for the announcement dialog. The template is project-provided
    (ANNOUNCEMENT_CONTENT_HTML_FILE): without it the dialog stays empty instead of a 500."""
    from django.conf import settings
    from django.http import HttpResponse
    from django.template import TemplateDoesNotExist

    content_file = getattr(settings, 'ANNOUNCEMENT_CONTENT_HTML_FILE', None)
    if not content_file:
        return HttpResponse("")
    try:
        content = render_to_string(str(content_file), request=request)
    except TemplateDoesNotExist:
        logger.warning("Announcement template %r not found (ANNOUNCEMENT_CONTENT_HTML_FILE)", content_file)
        return HttpResponse("")
    return HttpResponse(content)


class MarkdownPreviewView(View):
    """Convert markdown to HTML using md2html-tailwind4."""

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
        try:
            data = json.loads(request.body.decode("utf-8"))
            markdown_text = data.get('markdown', '')
            
            from md2html_tailwind4 import Converter
            converter = Converter(font_size='base')
            html_output = converter.convert_md_to_html(markdown_text)
            
            return JsonResponse({
                'success': True,
                'html': html_output
            })
        except Exception as e:
            logger.error('[mdeditor] Preview failed', exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Failed to render preview'
            }, status=500)
