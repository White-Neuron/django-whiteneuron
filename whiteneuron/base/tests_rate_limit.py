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
    def test_autocomplete_is_not_logged(self):
        self.assertIn(reverse("admin:autocomplete"), named_paths(UNTRACKED_URL_NAMES))


@package_test_settings()
class NoUnlimitedPathTests(TestCase):
    """Review of #74: the staff exemption from the IP limit plus the untracked URLs (no per-user
    limit) left endpoints with no limit at all, for guests too."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def _over_both_limits(self, client, url):
        with mock.patch.object(RateLimitMiddleware, "_is_rate_limited", return_value=True), \
                mock.patch.object(UserActivityMiddleware, "_is_user_rate_limited", return_value=True):
            return client.get(url, HTTP_ACCEPT="application/json")

    def test_untracked_urls_still_count_toward_the_user_limit(self):
        client = Client()
        client.force_login(self.staff)
        for name in ("admin:autocomplete", "wn_notifications:unread_count"):
            response = self._over_both_limits(client, reverse(name))
            self.assertEqual(response.status_code, 429, name)
            self.assertEqual(response["Retry-After"], "60")  # JSON answers say how long, too

    def test_probes_stay_free(self):
        response = self._over_both_limits(Client(), reverse("wn_system:health"))
        self.assertEqual(response.status_code, 200)

    def test_guest_is_not_exempt_from_the_ip_limit(self):
        from django.contrib.auth.models import Group

        guest = User.objects.create_user("guest", "g@example.com", "pw", is_staff=True)
        guest.groups.add(Group.objects.get_or_create(name="Guest")[0])
        client = Client()
        client.force_login(guest)
        with mock.patch.object(RateLimitMiddleware, "_is_rate_limited", return_value=True):
            self.assertEqual(client.get(reverse("admin:index")).status_code, 429)

    def test_session_lookup_is_cached_per_cookie(self):
        import django.contrib.auth

        client = Client()
        client.force_login(self.staff)
        real = django.contrib.auth.get_user
        with mock.patch.object(RateLimitMiddleware, "_is_rate_limited", return_value=True), \
                mock.patch("django.contrib.auth.get_user", side_effect=real) as lookup:
            request = mock.Mock(COOKIES=dict((k, v.value) for k, v in client.cookies.items()))
            self.assertTrue(RateLimitMiddleware._is_staff_session(request))
            self.assertTrue(RateLimitMiddleware._is_staff_session(request))
        self.assertEqual(lookup.call_count, 1)
