"""#39: the monitoring dashboard's polling was logged as traffic and skewed its own numbers."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.urls import reverse

from .middleware import UserActivityMiddleware
from .models import UserActivity
from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class PollingIsNotTrafficTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        self.client.force_login(self.root)

    def tearDown(self):
        caches["default"].clear()  # every request counts against the shared rate limits
        super().tearDown()

    def _logged(self, path):
        return UserActivity.objects.filter(path=path).count()

    def test_monitoring_api_polling_is_not_logged(self):
        url = reverse("admin:monitoring_metricsample_api")
        for _ in range(3):
            self.assertEqual(self.client.get(url, {"range": "15m"}).status_code, 200)
        self.assertEqual(self._logged(url), 0)

    def test_announcement_content_is_not_logged(self):
        url = reverse("announcement")
        self.client.get(url)
        self.assertEqual(self._logged(url), 0)

    def test_ordinary_admin_pages_are_still_logged(self):
        url = reverse("admin:base_app_changelist")
        self.client.get(url)
        self.assertEqual(self._logged(url), 1)

    def test_polling_is_not_rate_limited_per_user(self):
        with mock.patch.object(UserActivityMiddleware, "_is_user_rate_limited", return_value=True):
            url = reverse("admin:monitoring_metricsample_api")
            self.assertEqual(self.client.get(url, {"range": "15m"}).status_code, 200)
            self.assertEqual(self.client.get(reverse("admin:base_app_changelist")).status_code, 429)

    def test_projects_add_their_own_polling_endpoints_by_name(self):
        url = reverse("admin:base_app_changelist")
        with override_settings(WN_UNTRACKED_URL_NAMES=["admin:base_app_changelist"]):
            self.client.get(url)
        self.assertEqual(self._logged(url), 0)
