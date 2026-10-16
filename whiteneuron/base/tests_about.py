"""Admin "About" page: application / base versions and release dates."""
import pathlib
import re

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

import whiteneuron
from whiteneuron.base.testing import package_test_settings

User = get_user_model()
ROOT = pathlib.Path(whiteneuron.__file__).resolve().parent.parent


@package_test_settings(VERSION="2.3.4", RELEASE_DATE="2026-10-01", BUILD_ID="abc1234")
class AboutPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("about_root", "root@example.com", "pw")
        cls.staff = User.objects.create_user("about_staff", "staff@example.com", "pw", is_staff=True)
        cls.user = User.objects.create_user("about_user", "user@example.com", "pw")

    def test_requires_staff(self):
        url = reverse("admin:about")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_staff_sees_versions_but_not_runtime(self):
        self.client.force_login(self.staff)
        with translation.override("en"):
            page = self.client.get(reverse("admin:about"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "2.3.4")
        self.assertContains(page, "abc1234")
        self.assertContains(page, whiteneuron.__version__)
        self.assertEqual(page.context["app_release_date"], "Oct. 1, 2026")
        self.assertIsNone(page.context["runtime"])
        self.assertIsNone(page.context["packages"])
        self.assertNotContains(page, "Dependencies")

    def test_superuser_sees_runtime_and_dependencies(self):
        self.client.force_login(self.root)
        page = self.client.get(reverse("admin:about"))
        self.assertEqual(page.status_code, 200)
        labels = [str(label) for label, _value in page.context["runtime"]]
        self.assertIn("Database", labels)
        self.assertIn("django", dict(page.context["packages"]))

    @override_settings(RELEASE_DATE="", VERSION=None, APP_INFO_CALLBACK="whiteneuron.base.tests_about.broken_callback")
    def test_missing_values_and_broken_callback_do_not_break_the_page(self):
        self.client.force_login(self.staff)
        with self.assertLogs("whiteneuron.base.app_info", "WARNING"):
            page = self.client.get(reverse("admin:about"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["app_version"], "-")

    @override_settings(APP_INFO_CALLBACK="whiteneuron.base.tests_about.extra_rows")
    def test_callback_adds_rows(self):
        self.client.force_login(self.staff)
        page = self.client.get(reverse("admin:about"))
        self.assertIn(("Tenant", "acme"), page.context["application"])


def broken_callback(request):
    raise RuntimeError("boom")


def extra_rows(request):
    return [("Tenant", "acme")]


class PackageVersionTests(TestCase):
    def test_version_matches_pyproject_and_changelog(self):
        pyproject = ROOT / "pyproject.toml"
        if not pyproject.exists():  # installed from a wheel
            self.skipTest("source checkout only")
        self.assertIn(f'version = "{whiteneuron.__version__}"', pyproject.read_text())
        heading = re.search(
            rf"^### v{re.escape(whiteneuron.__version__)} \(([\d-]+)\)", (ROOT / "CHANGELOG.md").read_text(), re.M
        )
        self.assertIsNotNone(heading, "CHANGELOG.md has no heading for this version")
        self.assertEqual(heading.group(1), whiteneuron.__release_date__)
