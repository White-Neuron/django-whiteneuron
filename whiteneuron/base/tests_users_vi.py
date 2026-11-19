"""#82: details of the user screens seen in the Vietnamese admin."""
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from .testing import package_test_settings
from .utils import anonymous_user_name

User = get_user_model()


class FullNameOrderTests(TestCase):
    def test_package_default_keeps_the_family_name_first(self):
        user = User(username="u1", first_name="Văn 1", last_name="Nguyễn")
        for viewer in ("vi", "en"):
            with translation.override(viewer):
                self.assertEqual(user.full_name, "Nguyễn Văn 1")

    def test_order_follows_the_site_language_not_the_viewer(self):
        user = User(username="u1", first_name="Văn 1", last_name="Nguyễn")
        with self.settings(LANGUAGE_CODE="vi", WN_NAME_ORDER=None):
            for viewer in ("vi", "en"):
                with translation.override(viewer):
                    self.assertEqual(user.full_name, "Nguyễn Văn 1")
        with self.settings(LANGUAGE_CODE="en", WN_NAME_ORDER=None):
            with translation.override("vi"):
                self.assertEqual(user.get_full_name(), "Văn 1 Nguyễn")

    def test_wn_name_order_overrides_the_language(self):
        user = User(username="u1", first_name="Văn 1", last_name="Nguyễn")
        with self.settings(LANGUAGE_CODE="en", WN_NAME_ORDER="family_first"):
            self.assertEqual(user.get_full_name(), "Nguyễn Văn 1")
        with self.settings(LANGUAGE_CODE="vi", WN_NAME_ORDER="given_first"):
            self.assertEqual(user.get_full_name(), "Văn 1 Nguyễn")

    def test_one_part_alone_is_kept(self):
        self.assertEqual(User(username="u2", first_name="An").full_name, "An")
        self.assertEqual(User(username="u3", last_name="Trần").full_name, "Trần")
        self.assertEqual(User(username="u4").full_name, "")


@package_test_settings()
class UserListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "root@example.com", "pw")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.root)

    def test_guardian_anonymous_user_is_not_listed(self):
        name = anonymous_user_name()
        self.assertTrue(name)
        User.objects.get_or_create(username=name)
        response = self.client.get(reverse("admin:base_user_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(name, [u.username for u in response.context["cl"].result_list])

    def test_card_without_a_name_shows_the_username_once_then_the_email(self):
        from .admin import UserAdmin
        from .sites import base_admin_site

        html = str(UserAdmin(User, base_admin_site).grid_item_header(self.root))
        self.assertEqual(html.count(">root<"), 1)
        self.assertIn("root@example.com", html)

    def test_password_strings_are_translated(self):
        self.client.cookies["django_language"] = "vi"
        response = self.client.get(reverse("admin:base_user_change", args=[self.root.pk]))
        content = response.content.decode()
        self.assertIn('lang="vi"', content)
        self.assertNotIn("Reset password", content)
        self.assertNotIn("Raw passwords are not stored", content)
