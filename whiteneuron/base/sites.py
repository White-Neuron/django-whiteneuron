from unfold.sites import UnfoldAdminSite

from .forms import LoginForm


class BaseAdminSite(UnfoldAdminSite):
    login_form = LoginForm

    def toggle_sidebar(self, request):
        return super().toggle_sidebar(request)


base_admin_site = BaseAdminSite()
