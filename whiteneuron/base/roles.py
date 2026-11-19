"""Roles declared in code (#94 a): each role is a group with a fixed set of permissions, put
back exactly as declared after every ``migrate`` - no more ticking boxes by hand in each
environment, and no drift between production and staging.

    # settings.py
    from whiteneuron.base.roles import Role

    WN_ROLES = [
        Role(key="editor", name=_("Editor"), summary=_("Writes and edits; cannot approve."),
             permissions=("blog.add_post", "blog.change_post", "blog.view_*")),
        Role(key="reader", name=_("Reader"), permissions=("*.view_*",), exclude=("auth.permission",)),
    ]

Patterns: ``"app_label.codename"``, each side may use ``*`` / ``?`` (``"blog.view_*"``,
``"*.view_*"``, ``"*"`` for everything); a pattern without a dot matches the codename in any
app. ``exclude`` lists models (``"user"`` or ``"base.user"``) whose permissions are left out.

Only the groups of declared roles are touched; groups created by hand are left alone. A role's
group is set to exactly its declaration: permissions ticked by hand on that group are removed
at the next ``migrate`` (also the first time ``WN_ROLES`` names an existing group). A role taken
out of ``WN_ROLES`` keeps its group and permissions as they were; delete the group yourself.
The group is named by ``group_name`` (default: ``key``), so it does not change with the language.
"""
import logging
from dataclasses import dataclass
from fnmatch import fnmatchcase

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Role:
    key: str
    name: str = ""
    summary: str = ""
    permissions: tuple = ()
    exclude: tuple = ()
    group_name: str = ""

    @property
    def group(self):
        return self.group_name or self.key


def configured_roles():
    """``WN_ROLES`` as Role objects (dicts are accepted too)."""
    roles = []
    for item in getattr(settings, "WN_ROLES", None) or ():
        roles.append(item if isinstance(item, Role) else Role(**item))
    return roles


def _matches(pattern, app_label, codename):
    if "." in pattern:
        app_pattern, code_pattern = pattern.split(".", 1)
        return fnmatchcase(app_label, app_pattern) and fnmatchcase(codename, code_pattern)
    return fnmatchcase(codename, pattern)


def _excluded(exclude, app_label, model):
    for item in exclude:
        if "." in item:
            app, name = item.split(".", 1)
            if fnmatchcase(app_label, app) and fnmatchcase(model, name):
                return True
        elif fnmatchcase(model, item):
            return True
    return False


def resolve_permissions(role):
    """The Permission rows a role's patterns select. A pattern that matches nothing (a typo
    such as ``blog.veiw_*``) is logged as a warning."""
    from django.contrib.auth.models import Permission

    perms = list(Permission.objects.select_related("content_type"))
    for pattern in role.permissions:
        if not any(_matches(pattern, p.content_type.app_label, p.codename) for p in perms):
            logger.warning("Role %r: permission pattern %r matches no permission", role.key, pattern)
    return [
        p for p in perms
        if any(_matches(pattern, p.content_type.app_label, p.codename) for pattern in role.permissions)
        and not _excluded(role.exclude, p.content_type.app_label, p.content_type.model)
    ]


def sync_roles(roles=None, stdout=None):
    """Create each role's group if needed and set its permissions to exactly the declared ones.
    Returns {group name: number of permissions}."""
    from django.contrib.auth.models import Group

    result = {}
    for role in configured_roles() if roles is None else roles:
        group, created = Group.objects.get_or_create(name=role.group)
        perms = resolve_permissions(role)
        group.permissions.set(perms)
        result[role.group] = len(perms)
        if stdout is not None:
            stdout.write(f"Role {role.key}: group {role.group!r} {'created' if created else 'updated'}, "
                         f"{len(perms)} permissions")
    return result


def sync_roles_after_migrate(sender, app_config=None, using="default", **kwargs):
    """post_migrate receiver: once per migrate (on the last app, after every app's
    permissions have been created), and only when WN_ROLES is set."""
    from django.apps import apps

    if not getattr(settings, "WN_ROLES", None):
        return
    # Django sends post_migrate only for apps with a models module: the last of those is the
    # last signal of the run (an app without models last, e.g. debug_toolbar, never gets one)
    configs = [c for c in apps.get_app_configs() if c.models_module is not None]
    if not configs or app_config is not configs[-1]:
        return
    sync_roles(stdout=None)
