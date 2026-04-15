from django.conf import settings as django_settings
from django.shortcuts import redirect
from django.urls import reverse
from unfold.sites import UnfoldAdminSite

from .forms import LoginForm


class BaseAdminSite(UnfoldAdminSite):
    login_form = LoginForm

    def logout(self, request, extra_context=None):
        if request.method == "GET":
            return redirect(reverse("%s:login" % self.name))
        return super().logout(request, extra_context=extra_context)

    def toggle_sidebar(self, request):
        return super().toggle_sidebar(request)

    def each_context(self, request):
        context = super().each_context(request)
        announcement = None
        callback_path = getattr(django_settings, 'ANNOUNCEMENT_CALLBACK', None)
        if callback_path:
            from django.utils.module_loading import import_string
            try:
                callback = import_string(callback_path)
                announcement = callback(request)
            except Exception:
                pass
        context['announcement'] = announcement
        return context


base_admin_site = BaseAdminSite()
