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


base_admin_site = BaseAdminSite()
