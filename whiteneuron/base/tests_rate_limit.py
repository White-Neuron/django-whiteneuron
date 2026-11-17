"""#38: 60 requests/min per IP and per user blocked ordinary admin work."""
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .middleware import RateLimitMiddleware, UserActivityMiddleware, named_paths, UNTRACKED_URL_NAMES
from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class StaffOverTheIpLimitTests(TestCase):
    """An office behind one NAT IP shares the IP limit: logged-in staff are let through."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.member = User.objects.create_user("member", password="pw", is_staff=False)

    def tearDown(self):
        caches["default"].clear()  # every request counts against the shared rate limits
        super().tearDown()

    def _get(self, client):
        with mock.patch.object(RateLimitMiddleware, "_is_rate_limited", return_value=True):
            return client.get(reverse("admin:index"))

    def test_logged_in_staff_pass(self):
        client = Client()
        client.force_login(self.staff)
        self.assertEqual(self._get(client).status_code, 200)

    def test_anonymous_and_forged_cookies_are_limited(self):
        self.assertEqual(self._get(Client()).status_code, 429)
        forged = Client()
        forged.cookies[settings.SESSION_COOKIE_NAME] = "not-a-session"
        self.assertEqual(self._get(forged).status_code, 429)

    def test_non_staff_users_are_limited(self):
        client = Client()
        client.force_login(self.member)
        self.assertEqual(self._get(client).status_code, 429)

    @override_settings(RATE_LIMIT_EXEMPT_STAFF=False)
    def test_exemption_can_be_turned_off(self):
        client = Client()
        client.force_login(self.staff)
        self.assertEqual(self._get(client).status_code, 429)


class RateLimitDefaultsTests(TestCase):
    def test_settings_and_middlewares_agree(self):
        self.assertEqual(settings.RATE_LIMIT_REQUESTS, 300)
        self.assertEqual(settings.USER_RATE_LIMIT_REQUESTS, 600)
        with override_settings():
            del settings.RATE_LIMIT_REQUESTS
            del settings.USER_RATE_LIMIT_REQUESTS
            self.assertEqual(RateLimitMiddleware(lambda r: None).rate, 300)
            self.assertEqual(UserActivityMiddleware(lambda r: None).user_rate, 600)

    @package_test_settings()
    def test_autocomplete_is_not_logged_or_limited_per_user(self):
        self.assertIn(reverse("admin:autocomplete"), named_paths(UNTRACKED_URL_NAMES))
