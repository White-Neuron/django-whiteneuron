"""Assign roles (WN_ROLES) to members, for managers who are not superusers (#94 b).

A manager is a user with ``base.manage_members``. The rules are checked here, on the server,
whatever the page shows:

1. a role never makes anyone a superuser (roles are groups; ``is_superuser`` is never touched);
2. superusers and service accounts (``is_bot``) cannot be changed here;
3. a manager cannot give a role with a permission they do not have themselves;
4. the last manager cannot take away their own ``manage_members``.

Each change replaces the member's role groups (groups made by hand are kept) and is written
to the member's history.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Q
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .roles import configured_roles, resolve_permissions

MANAGE_PERMISSION = "base.manage_members"


class RoleChangeRefused(Exception):
    pass


def role_groups():
    """{role key: Group} for the declared roles whose group exists."""
    roles = {role.group: role for role in configured_roles()}
    return {roles[g.name].key: g for g in Group.objects.filter(name__in=list(roles))}


def current_role(member, groups=None):
    """The key of the member's role, or None."""
    groups = role_groups() if groups is None else groups
    names = set(member.groups.values_list("name", flat=True))
    for key, group in groups.items():
        if group.name in names:
            return key
    return None


def _role_grants(role, codename=MANAGE_PERMISSION):
    app, code = codename.split(".", 1)
    return any(p.content_type.app_label == app and p.codename == code for p in resolve_permissions(role))


def _other_managers_exist(member):
    User = get_user_model()
    perm = Permission.objects.get(content_type__app_label="base", codename="manage_members")
    return User.objects.filter(is_active=True).exclude(pk=member.pk).filter(
        Q(is_superuser=True) | Q(user_permissions=perm) | Q(groups__permissions=perm)
    ).exists()


def check_change(actor, member, role_key):
    """Raise RoleChangeRefused with the reason when ``actor`` may not give ``member`` the role
    ``role_key`` (None = no role)."""
    if not (actor.is_superuser or actor.has_perm(MANAGE_PERMISSION)):
        raise RoleChangeRefused(_("You cannot manage members."))
    if member.is_superuser or getattr(member, "is_bot", False):
        raise RoleChangeRefused(_("Superusers and service accounts cannot be changed here."))
    roles = {r.key: r for r in configured_roles()}
    role = None
    if role_key:
        role = roles.get(role_key)
        if role is None:
            raise RoleChangeRefused(_("Unknown role."))
        if not actor.is_superuser:
            have = actor.get_all_permissions()
            missing = [f"{p.content_type.app_label}.{p.codename}" for p in resolve_permissions(role)
                       if f"{p.content_type.app_label}.{p.codename}" not in have]
            if missing:
                raise RoleChangeRefused(_("You cannot give a role with permissions you do not have yourself."))
    if member.pk == actor.pk and not actor.is_superuser:
        keeps = role is not None and _role_grants(role)
        if not keeps and not _other_managers_exist(member):
            raise RoleChangeRefused(_("You are the last manager: someone else must keep the right to manage members."))
    return role


@transaction.atomic
def assign_role(actor, member, role_key):
    """Give ``member`` the role ``role_key`` (None removes their role), after check_change.
    Returns True when something changed."""
    role = check_change(actor, member, role_key)
    groups = role_groups()
    before = current_role(member, groups)
    if before == (role.key if role else None):
        return False
    member.groups.remove(*groups.values())
    if role is not None:
        group, _created = Group.objects.get_or_create(name=role.group)
        member.groups.add(group)
    _record(actor, member, before, role.key if role else None)
    return True


def _record(actor, member, before, after):
    """Into the member's history (the history panel reads these notifications)."""
    from django.urls import reverse

    from whiteneuron.notification.models import Notification

    names = {r.key: str(r.name or r.key) for r in configured_roles()}
    none = _("no role")
    title = _('Role of "%(member)s" changed from %(before)s to %(after)s by "%(actor)s"') % {
        "member": member, "before": names.get(before, none), "after": names.get(after, none), "actor": actor}
    Notification.notify_superusers(
        title=title, content=format_html("<p>{}</p>", title), action="update", flag="info",
        obj_link=reverse("admin:base_user_change", args=[member.pk]), action_by=actor, model=member,
        changed_data=[{"field_name": "role", "old_value": before or "", "new_value": after or ""}],
    )
