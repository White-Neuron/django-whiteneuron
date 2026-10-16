from django.conf import settings as django_settings
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from unfold.sites import UnfoldAdminSite

from .forms import LoginForm


class BaseAdminSite(UnfoldAdminSite):
    login_form = LoginForm

    def logout(self, request, extra_context=None):
        if request.method == "GET":
            return redirect(reverse("%s:login" % self.name))
        return super().logout(request, extra_context=extra_context)

    def login(self, request, extra_context=None):
        from .models import User

        # Only offer "Log in as guest" when GuestLoginView can actually log someone in
        extra_context = {
            "guest_login_available": User.objects.filter(
                username="guest", is_active=True, is_staff=True
            ).exists(),
            **(extra_context or {}),
        }
        return super().login(request, extra_context=extra_context)

    def get_urls(self):
        return [
            path("about/", self.admin_view(self.about_view), name="about"),
        ] + super().get_urls()

    def about_view(self, request):
        """Application / base package versions, release dates and (superusers) runtime info."""
        from .app_info import get_app_info

        context = {
            **self.each_context(request),
            "title": _("About"),
            **get_app_info(request),
        }
        return TemplateResponse(request, "admin/about.html", context)

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
