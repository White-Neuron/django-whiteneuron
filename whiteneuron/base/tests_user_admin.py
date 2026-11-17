"""#32: deleting a user deleted their records; the user admin deactivates instead."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import caches
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import App
from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class UserDeletionKeepsRecordsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.alice = User.objects.create_user("alice", password="pw")
        cls.bob = User.objects.create_user("bob", password="pw")

    def test_deleting_a_user_keeps_what_they_created_or_edited(self):
        app = App.objects.create(name="kept")
        App.objects_all.filter(pk=app.pk).update(created_by=self.alice, updated_by=self.alice)
        self.alice.delete()
        app = App.objects_all.get(pk=app.pk)
        self.assertEqual((app.created_by_id, app.updated_by_id), (None, None))

    def test_only_superusers_may_delete_users(self):
        from whiteneuron.base.sites import base_admin_site

        user_admin = base_admin_site._registry[User]
        request = RequestFactory().get("/")
        request.user = self.alice
        with mock.patch.object(type(self.alice), "has_perm", return_value=True):  # full model permissions
            self.assertFalse(user_admin.has_delete_permission(request))
        request.user = self.root
        self.assertTrue(user_admin.has_delete_permission(request))


@package_test_settings()
class DeactivateUsersActionTests(TestCase):
    def tearDown(self):
        caches["default"].clear()  # every request counts against the shared per-IP rate limit
        super().tearDown()

    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.admin2 = User.objects.create_superuser("admin2", "a@example.com", "pw")
        cls.alice = User.objects.create_user("alice", password="pw")
        cls.bob = User.objects.create_user("bob", password="pw")
        cls.staff = User.objects.create_user("staff", password="pw", is_staff=True)
        cls.staff.user_permissions.set(Permission.objects.filter(
            content_type__app_label=User._meta.app_label, codename__in=["view_user", "change_user"]))

    def _run(self, actor, action, *users):
        self.client.force_login(actor)
        url = reverse(f"admin:{User._meta.app_label}_{User._meta.model_name}_changelist")
        response = self.client.post(url, {"action": action, "_selected_action": [u.pk for u in users]},
                                    follow=True)
        return [str(m) for m in response.context["messages"]]

    def _active(self, *users):
        return {u.username: User.objects.get(pk=u.pk).is_active for u in users}

    def test_deactivates_the_selection_but_not_yourself(self):
        messages = self._run(self.root, "deactivate_users", self.alice, self.bob, self.root)
        self.assertEqual(self._active(self.alice, self.bob, self.root), {"alice": False, "bob": False, "root": True})
        self.assertIn("2 user(s) deactivated.", messages)
        self.assertIn("You cannot deactivate your own account.", messages)

    def test_staff_cannot_deactivate_a_superuser(self):
        messages = self._run(self.staff, "deactivate_users", self.root, self.alice)
        self.assertEqual(self._active(self.root, self.alice), {"root": True, "alice": False})
        self.assertIn("Only a superuser can deactivate a superuser.", messages)

    def test_a_superuser_may_deactivate_other_superusers_and_stays_active(self):
        # with "not yourself" and "superusers only", an active superuser always remains
        self._run(self.root, "deactivate_users", self.admin2, self.root)
        self.assertEqual(self._active(self.admin2, self.root), {"admin2": False, "root": True})

    def test_nothing_to_do_is_not_reported_as_success(self):
        User.objects.filter(pk=self.alice.pk).update(is_active=False)
        messages = self._run(self.root, "deactivate_users", self.alice)
        self.assertIn("No user was deactivated.", messages)
        self.assertFalse(any("deactivated." in m and m[0].isdigit() for m in messages))

    def test_reactivate(self):
        User.objects.filter(pk__in=[self.alice.pk, self.admin2.pk]).update(is_active=False)
        messages = self._run(self.staff, "activate_users", self.alice, self.admin2)
        self.assertEqual(self._active(self.alice, self.admin2), {"alice": True, "admin2": False})
        self.assertIn("Only a superuser can reactivate a superuser.", messages)
        self._run(self.root, "activate_users", self.admin2)
        self.assertTrue(self._active(self.admin2)["admin2"])
