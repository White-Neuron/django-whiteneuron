"""#94 (b): a manager who is not a superuser assigns roles, within four hard limits."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.urls import reverse

from whiteneuron.notification.models import Notification

from .members import RoleChangeRefused, assign_role, current_role
from .roles import Role, sync_roles
from .testing import package_test_settings

User = get_user_model()

ROLES = [
    Role(key="manager", name="Manager", summary="Manages members",
         permissions=("base.manage_members", "auth.view_group")),
    Role(key="viewer", name="Viewer", permissions=("auth.view_group",)),
    Role(key="admin", name="Admin", permissions=("auth.*",)),
]


@package_test_settings(WN_ROLES=ROLES)
class MembersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_roles(ROLES)
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.boss = User.objects.create_user("boss", "b@example.com", "pw", is_staff=True)
        cls.boss.groups.add(Group.objects.get(name="manager"))
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)
        cls.bot = User.objects.create_user("bot", "bot@example.com", "pw", is_staff=True, is_bot=True)
        cls.hand_made = Group.objects.create(name="Hand made")
        cls.alice.groups.add(cls.hand_made)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def _fresh(self, user):
        return User.objects.get(pk=user.pk)   # no cached permissions

    def test_manager_changes_a_role_and_it_is_recorded(self):
        self.assertTrue(assign_role(self._fresh(self.boss), self.alice, "viewer"))
        self.assertEqual(current_role(self.alice), "viewer")
        self.assertTrue(self.alice.groups.filter(name="Hand made").exists())   # hand-made group kept
        self.assertTrue(assign_role(self._fresh(self.boss), self.alice, "manager"))
        self.assertEqual(current_role(self.alice), "manager")                  # one role at a time
        self.assertTrue(Notification.objects.filter(title__contains="alice", action="update").exists())

    def test_rule_1_never_superuser(self):
        assign_role(self._fresh(self.boss), self.alice, "viewer")
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_superuser)

    def test_rule_2_superusers_and_service_accounts_are_locked(self):
        for member in (self.root, self.bot):
            with self.assertRaises(RoleChangeRefused):
                assign_role(self._fresh(self.boss), member, "viewer")

    def test_rule_3_no_role_with_more_than_the_manager_has(self):
        with self.assertRaises(RoleChangeRefused):
            assign_role(self._fresh(self.boss), self.alice, "admin")
        self.assertIsNone(current_role(self.alice))
        self.assertTrue(assign_role(self.root, self.alice, "admin"))   # a superuser may

    def test_rule_4_the_last_manager_keeps_the_right(self):
        # an active superuser can manage members too: without one, the boss is the last
        User.objects.filter(pk=self.root.pk).update(is_active=False)
        with self.assertRaises(RoleChangeRefused):
            assign_role(self._fresh(self.boss), self.boss, "viewer")
        with self.assertRaises(RoleChangeRefused):
            assign_role(self._fresh(self.boss), self.boss, None)
        self.assertEqual(current_role(self.boss), "manager")

    def test_rule_4_does_not_apply_when_another_manager_exists(self):
        User.objects.filter(pk=self.root.pk).update(is_active=False)
        other = User.objects.create_user("other", "o@example.com", "pw", is_staff=True)
        other.groups.add(Group.objects.get(name="manager"))
        self.assertTrue(assign_role(self._fresh(self.boss), self.boss, "viewer"))

    def test_without_the_permission_nothing_is_possible(self):
        with self.assertRaises(RoleChangeRefused):
            assign_role(self._fresh(self.alice), self.bot, "viewer")

    # ── the page ──
    def test_page_lists_members_and_roles_for_a_manager(self):
        self.client.force_login(self.boss)
        response = self.client.get(reverse("admin:members"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="role-manager"')
        self.assertContains(response, 'id="member-%d"' % self.alice.pk)
        self.assertContains(response, "Manages members")
        self.assertContains(response, 'value="admin" disabled')   # more than the manager has

    def test_page_is_closed_without_the_permission(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("admin:members")).status_code, 403)

    def test_post_changes_the_role_and_refusals_are_reported(self):
        self.client.force_login(self.boss)
        self.client.post(reverse("admin:members"), {"member": self.alice.pk, "role": "viewer"})
        self.assertEqual(current_role(self.alice), "viewer")
        response = self.client.post(reverse("admin:members"), {"member": self.root.pk, "role": "viewer"}, follow=True)
        self.assertContains(response, "cannot be changed here")
        self.assertIsNone(current_role(self.root))

    def test_get_never_changes_anything(self):
        self.client.force_login(self.boss)
        self.client.get(reverse("admin:members"), {"member": self.alice.pk, "role": "viewer"})
        self.assertIsNone(current_role(self.alice))


@package_test_settings(WN_ROLES=ROLES)
class MembersReviewTests(TestCase):
    """Review of #106."""

    @classmethod
    def setUpTestData(cls):
        sync_roles(ROLES)
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.boss = User.objects.create_user("boss", "b@example.com", "pw", is_staff=True)
        cls.boss.groups.add(Group.objects.get(name="manager"))
        cls.director = User.objects.create_user("director", "d@example.com", "pw", is_staff=True)
        cls.director.groups.add(Group.objects.get(name="admin"))
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def _boss(self):
        return User.objects.get(pk=self.boss.pk)

    def test_cannot_demote_or_strip_someone_with_more_permissions(self):
        for target in ("viewer", None):
            with self.assertRaises(RoleChangeRefused):
                assign_role(self._boss(), self.director, target)
        self.assertEqual(current_role(self.director), "admin")

    def test_hand_ticked_permissions_on_a_role_group_count(self):
        viewer = Group.objects.get(name="viewer")
        viewer.permissions.add(Permission.objects.get(content_type__app_label="base", codename="delete_user"))
        with self.assertRaises(RoleChangeRefused):
            assign_role(self._boss(), self.alice, "viewer")
        self.assertIsNone(current_role(self.alice))

    def test_guardian_anonymous_user_is_neither_listed_nor_changeable(self):
        from .utils import anonymous_user_name

        anonymous, _created = User.objects.get_or_create(username=anonymous_user_name())
        with self.assertRaises(RoleChangeRefused):
            assign_role(self.root, anonymous, "viewer")
        self.client.force_login(self.boss)
        self.assertNotContains(self.client.get(reverse("admin:members")), 'id="member-%d"' % anonymous.pk)

    def test_a_member_id_that_is_not_a_number_is_not_a_server_error(self):
        self.client.force_login(self.boss)
        response = self.client.post(reverse("admin:members"), {"member": "abc", "role": "viewer"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This member cannot be found")

    def test_rows_above_the_manager_are_read_only(self):
        self.client.force_login(self.boss)
        html = self.client.get(reverse("admin:members")).content.decode()
        row = html.split('id="member-%d"' % self.director.pk)[1].split("</tr>")[0]
        self.assertNotIn("<select", row)
        self.assertIn("more than you have", row)
