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

    def get_urls(self):
        return [
            path("about/", self.admin_view(self.about_view), name="about"),
            path("members/", self.admin_view(self.members_view), name="members"),
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

    def members_view(self, request):
        """"Members and roles" (#94 b): give each member one of the roles of WN_ROLES. Open to
        superusers and to managers (base.manage_members); every rule is checked in members.py."""
        from django.contrib import messages
        from django.contrib.auth import get_user_model
        from django.core.exceptions import PermissionDenied

        from . import members
        from .roles import configured_roles, resolve_permissions

        user = request.user
        if not (user.is_superuser or user.has_perm(members.MANAGE_PERMISSION)):
            raise PermissionDenied
        User = get_user_model()
        if request.method == "POST":
            member = User.objects.filter(pk=request.POST.get("member"), is_active=True).first()
            role_key = request.POST.get("role") or None
            if member is None:
                messages.error(request, _("This member cannot be found."))
            else:
                try:
                    if members.assign_role(user, member, role_key):
                        messages.success(request, _("The role of %(member)s has been changed.") % {"member": member})
                except members.RoleChangeRefused as refused:
                    messages.error(request, str(refused))
            return redirect(reverse("%s:members" % self.name))

        roles = configured_roles()
        groups = members.role_groups()
        have = user.get_all_permissions()
        rows = []
        for member in User.objects.filter(is_active=True).prefetch_related("groups").order_by("username"):
            rows.append({
                "member": member,
                "role": members.current_role(member, groups),
                "locked": member.is_superuser or member.is_bot,
            })
        role_rows = []
        for role in roles:
            perms = resolve_permissions(role)
            role_rows.append({
                "role": role,
                "count": len(perms),
                # shown, but the server refuses it anyway: rule 3 of members.py
                "allowed": user.is_superuser or all(f"{p.content_type.app_label}.{p.codename}" in have for p in perms),
            })
        context = {
            **self.each_context(request),
            "title": _("Members and roles"),
            "rows": rows,
            "roles": role_rows,
        }
        return TemplateResponse(request, "admin/members.html", context)

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
