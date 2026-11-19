"""#77: settle versioning (api/v1/) and give paginated lists next / previous links."""
import re

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.urls import reverse

from whiteneuron.notification.models import Notification

from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class PaginationLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)
        for i in range(5):
            Notification.objects.create(user=cls.alice, title=f"n{i}", content="", flag="info")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.alice)
        self.url = reverse("wn_notifications:list")

    def _page(self, **params):
        return self.client.get(self.url, {"page_size": 2, **params}).json()

    def test_links_walk_the_pages_and_keep_filters(self):
        first = self._page(unread=1)
        self.assertIsNone(first["previous"])
        self.assertTrue(first["next"].startswith("http://testserver" + self.url))
        self.assertIn("unread=1", first["next"])
        self.assertIn("page_size=2", first["next"])
        second = self.client.get(first["next"]).json()
        self.assertEqual(second["page"], 2)
        self.assertIn("page=1", second["previous"])
        last = self.client.get(second["next"]).json()
        self.assertEqual(len(last["results"]), 1)
        self.assertIsNone(last["next"])

    def test_past_the_end_points_back_to_the_last_page(self):
        data = self._page(page=9)
        self.assertEqual(data["results"], [])
        self.assertIsNone(data["next"])
        self.assertIn("page=3", data["previous"])

    def test_empty_list_has_no_links(self):
        Notification.objects.all().delete()
        data = self._page()
        self.assertEqual((data["count"], data["next"], data["previous"]), (0, None, None))


@override_settings(ROOT_URLCONF=__name__)
class MountedUnderV1Tests(TestCase):
    """The recommended mount: every endpoint, name and exemption works under api/v1/."""

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def test_endpoints_resolve_under_v1(self):
        self.assertEqual(reverse("wn_system:health"), "/api/v1/system/health/")
        self.assertEqual(self.client.get("/api/v1/system/health/").json(), {"status": "ok"})
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("wn_notifications:unread_count")).json(), {"unread_count": 0})

    def test_probes_are_exempt_from_the_https_redirect_under_both_prefixes(self):
        from django.conf import settings as live

        # the production value (DEBUG=False), read from the source: tests run with DEBUG=True
        from pathlib import Path

        source = Path(live.BASE_DIR, "base", "settings.py").read_text()
        pattern = re.search(r'SECURE_REDIRECT_EXEMPT = \[r"(.+?)"\]', source).group(1)
        for path in ("api/v1/system/health/", "api/system/ready/"):
            self.assertRegex(path, pattern)
        self.assertNotRegex("api/v1/system/info/", pattern)


def _urlpatterns():
    from django.urls import include, path

    from .sites import base_admin_site

    return [path("admin/", base_admin_site.urls), path("api/v1/", include("whiteneuron.api_urls"))]


urlpatterns = _urlpatterns()
