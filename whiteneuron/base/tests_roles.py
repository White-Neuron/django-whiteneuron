"""#94 (a): roles declared in code, put back after every migrate."""
from io import StringIO

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase, override_settings

from .roles import Role, resolve_permissions, sync_roles, sync_roles_after_migrate


def codes(perms):
    return {f"{p.content_type.app_label}.{p.codename}" for p in perms}


class PatternTests(TestCase):
    def test_exact_and_wildcards(self):
        self.assertEqual(codes(resolve_permissions(Role(key="r", permissions=("auth.add_group",)))), {"auth.add_group"})
        auth_views = codes(resolve_permissions(Role(key="r", permissions=("auth.view_*",))))
        self.assertEqual(auth_views, {"auth.view_group", "auth.view_permission"})
        every_view = codes(resolve_permissions(Role(key="r", permissions=("view_*",))))
        self.assertIn("auth.view_group", every_view)
        self.assertTrue(all(c.split(".")[1].startswith("view_") for c in every_view))

    def test_exclude_by_model_or_app_model(self):
        perms = codes(resolve_permissions(Role(key="r", permissions=("auth.view_*",), exclude=("permission",))))
        self.assertEqual(perms, {"auth.view_group"})
        perms = codes(resolve_permissions(Role(key="r", permissions=("*.view_*",), exclude=("auth.group",))))
        self.assertNotIn("auth.view_group", perms)
        self.assertIn("auth.view_permission", perms)


class SyncTests(TestCase):
    def test_sync_sets_exactly_the_declared_permissions_and_leaves_other_groups(self):
        manual = Group.objects.create(name="Hand made")
        manual.permissions.add(Permission.objects.get(codename="delete_group"))
        editor = Group.objects.create(name="editor")
        editor.permissions.add(Permission.objects.get(codename="delete_group"))   # drifted by hand
        sync_roles([Role(key="editor", permissions=("auth.view_group", "auth.change_group"))])
        self.assertEqual(codes(editor.permissions.all()), {"auth.view_group", "auth.change_group"})
        self.assertEqual(codes(manual.permissions.all()), {"auth.delete_group"})

    def test_group_name_does_not_follow_the_language(self):
        sync_roles([Role(key="reader", name="Người đọc", permissions=("auth.view_group",))])
        self.assertTrue(Group.objects.filter(name="reader").exists())

    @override_settings(WN_ROLES=[Role(key="auditor", permissions=("auth.view_*",))])
    def test_after_migrate_on_the_last_app_only(self):
        configs = list(apps.get_app_configs())
        sync_roles_after_migrate(sender=configs[0], app_config=configs[0])
        self.assertFalse(Group.objects.filter(name="auditor").exists())
        sync_roles_after_migrate(sender=configs[-1], app_config=configs[-1])
        self.assertEqual(codes(Group.objects.get(name="auditor").permissions.all()),
                         {"auth.view_group", "auth.view_permission"})

    def test_without_wn_roles_migrate_changes_nothing(self):
        configs = list(apps.get_app_configs())
        before = Group.objects.count()
        sync_roles_after_migrate(sender=configs[-1], app_config=configs[-1])
        self.assertEqual(Group.objects.count(), before)


class InitGroupuserTests(TestCase):
    def test_same_groups_and_rules_as_before(self):
        call_command("init_groupuser", stdout=StringIO())
        for name in ("Quản trị viên", "Quản lý", "Nhân viên", "Khách hàng", "Khách thăm"):
            self.assertTrue(Group.objects.filter(name=name).exists(), name)
        admin = codes(Group.objects.get(name="Quản trị viên").permissions.all())
        self.assertIn("auth.delete_group", admin)
        manager = codes(Group.objects.get(name="Quản lý").permissions.all())
        self.assertIn("auth.change_group", manager)
        self.assertFalse(any("delete" in c for c in manager))
        guest = codes(Group.objects.get(name="Khách thăm").permissions.all())
        self.assertTrue(guest and all("view" in c for c in guest))
        self.assertFalse({"base.view_user", "auth.view_group", "file_management.view_pdffile"} & guest)
        staff = codes(Group.objects.get(name="Nhân viên").permissions.all())
        self.assertIn("file_management.view_pdffile", staff)

    def test_running_it_again_undoes_drift(self):
        call_command("init_groupuser", stdout=StringIO())
        guest = Group.objects.get(name="Khách thăm")
        guest.permissions.add(Permission.objects.get(codename="delete_group"))
        call_command("init_groupuser", stdout=StringIO())
        self.assertNotIn("auth.delete_group", codes(guest.permissions.all()))
