"""JSON API: /api/system/, /api/notifications/, /api/announcement/ (whiteneuron.api_urls)."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from whiteneuron.notification.models import AnnouncementReceipt, Notification
from whiteneuron.notification.utils import BADGE_CACHE_KEY

from . import system
from .middleware import RateLimitMiddleware, UserActivityMiddleware
from .testing import package_test_settings

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


class CleanCacheTestCase(TestCase):
    """Each request counts against the per-IP rate limit in the shared cache: start and leave it empty."""

    def setUp(self):
        super().setUp()
        caches["default"].clear()

    def tearDown(self):
        caches["default"].clear()
        super().tearDown()


def failing(message):
    return mock.Mock(side_effect=RuntimeError(message))


@package_test_settings(CACHES=LOCMEM, SYSTEM_API_TOKEN="s3cret", SYSTEM_API_READY_CHECKS=["database", "cache"],
                       VERSION="2.5.0", RELEASE_DATE="2026-11-01", BUILD_ID="0123456789abcdef")
class SystemApiTests(CleanCacheTestCase):
    def setUp(self):
        super().setUp()
        system.reset_ready_cache()

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.root = User.objects.create_superuser("root", "root@example.com", "x")
        cls.staff = User.objects.create_user("staff", password="x")  # whiteneuron users are staff by default

    def test_version_is_public_and_minimal(self):
        r = self.client.get(reverse("wn_system:version"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["version"], "2.5.0")
        self.assertEqual(r.json()["release_date"], "2026-11-01")
        self.assertEqual(r.json()["build"], "0123456789ab")
        self.assertEqual(set(r.json()), {"name", "version", "release_date", "build"})  # no runtime versions

    def test_health(self):
        r = self.client.get(reverse("wn_system:health"))
        self.assertEqual((r.status_code, r.json()), (200, {"status": "ok"}))
        self.assertIn("no-cache", r["Cache-Control"])
        self.assertEqual(self.client.post(reverse("wn_system:health")).status_code, 405)

    def test_ready_ok(self):
        r = self.client.get(reverse("wn_system:ready"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()["checks"]), {"database", "cache"})

    def test_ready_failure_is_503_and_hides_the_error_from_the_public(self):
        with mock.patch.dict("whiteneuron.base.system.CHECKS", {"cache": failing("redis down")}):
            r = self.client.get(reverse("wn_system:ready"))
            self.assertEqual(r.status_code, 503)
            self.assertNotIn("error", r.json()["checks"]["cache"])
            r = self.client.get(reverse("wn_system:ready"), HTTP_X_SYSTEM_TOKEN="s3cret")
            self.assertIn("redis down", r.json()["checks"]["cache"]["error"])

    def test_public_ready_reuses_recent_results_privileged_gets_fresh_ones(self):
        check = mock.Mock()
        with mock.patch.dict("whiteneuron.base.system.CHECKS", {"database": check, "cache": check}):
            for _ in range(3):
                self.assertEqual(self.client.get(reverse("wn_system:ready")).status_code, 200)
            self.assertEqual(check.call_count, 2)  # one run of both checks for the three public calls
            check.side_effect = RuntimeError("down")
            self.assertEqual(self.client.get(reverse("wn_system:ready"), HTTP_X_SYSTEM_TOKEN="s3cret").status_code, 503)
            self.assertEqual(self.client.get(reverse("wn_system:ready")).status_code, 200)  # still the memo
            system.reset_ready_cache()
            self.assertEqual(self.client.get(reverse("wn_system:ready")).status_code, 503)

    def test_cache_check_uses_a_key_per_call_and_removes_it(self):
        cache = caches["default"]
        with mock.patch.object(cache, "set", wraps=cache.set) as set_:
            system.check_cache()
            system.check_cache()
        keys = [c.args[0] for c in set_.call_args_list]
        self.assertEqual(len(set(keys)), 2)
        self.assertTrue(all(k.startswith("wn:system:ready:") for k in keys))
        self.assertTrue(all(cache.get(k) is None for k in keys))

    @override_settings(CELERY_BROKER_URL="memory://")
    def test_celery_check_makes_one_attempt_without_retry_sleep(self):
        with mock.patch("kombu.Connection") as connection:
            system.check_celery()
        conn = connection.return_value.__enter__.return_value
        conn.ensure_connection.assert_called_once_with(max_retries=0, timeout=system.BROKER_TIMEOUT_SECONDS)

    def test_info_needs_superuser_or_token(self):
        url = reverse("wn_system:info")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(url, HTTP_X_SYSTEM_TOKEN="wrong").status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(url, HTTP_AUTHORIZATION="Bearer s3cret").status_code, 200)
        self.client.force_login(self.root)
        data = self.client.get(url).json()
        self.assertEqual(data["pending_migrations"], 0)
        self.assertIn("python", data["runtime"])
        self.assertEqual(data["base"]["package"], "django-whiteneuron")

    @override_settings(SYSTEM_API_TOKEN=None)
    def test_no_token_configured_never_matches(self):
        self.assertEqual(self.client.get(reverse("wn_system:info"), HTTP_AUTHORIZATION="Bearer ").status_code, 403)


@package_test_settings(CACHES=LOCMEM)
class ProbeMiddlewareTests(CleanCacheTestCase):
    """Exemptions follow the URL names, wherever the project mounts them."""

    def test_probes_skip_rate_limit_and_activity_log(self):
        from django.test import RequestFactory

        factory = RequestFactory()
        ok = mock.Mock(return_value="passed")
        rl = RateLimitMiddleware(ok)
        with mock.patch.object(RateLimitMiddleware, "_is_rate_limited", return_value=True):
            self.assertEqual(rl(factory.get(reverse("wn_system:health"))), "passed")
            self.assertEqual(rl(factory.get(reverse("wn_system:ready"))), "passed")
            self.assertNotEqual(rl(factory.get(reverse("wn_system:version"))), "passed")
        with mock.patch.object(RateLimitMiddleware, "_is_blacklisted", return_value=True):
            self.assertEqual(rl(factory.get(reverse("wn_system:ready"))).status_code, 403)  # still blocked

        ua = UserActivityMiddleware(ok)
        self.assertTrue(ua.do_not_track(factory.get(reverse("wn_system:health"))))
        self.assertTrue(ua.do_not_track(factory.get(reverse("wn_notifications:unread_count"))))
        self.assertFalse(ua.do_not_track(factory.get(reverse("wn_notifications:list"))))


@package_test_settings(CACHES=LOCMEM)
class NotificationApiTests(CleanCacheTestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user("alice", password="x")
        cls.bob = User.objects.create_user("bob", password="x")
        Notification.objects.all().delete()  # signals may notify on user creation
        mk = Notification.objects.create
        cls.n1 = mk(user=cls.alice, title="A1", content="c1", flag="info", changed_data='{"x": 1}', action_by=cls.bob)
        cls.n2 = mk(user=cls.alice, title="A2", content="c2", flag="error")
        cls.n3 = mk(user=cls.alice, title="A3", content="c3", flag="info", is_read=True)
        cls.other = mk(user=cls.bob, title="B1", content="b", flag="info")

    def setUp(self):
        super().setUp()
        self.client.force_login(self.alice)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("wn_notifications:list")).status_code, 401)
        self.assertEqual(self.client.get(reverse("wn_notifications:unread_count")).status_code, 401)

    def test_list_own_newest_first(self):
        data = self.client.get(reverse("wn_notifications:list")).json()
        self.assertEqual([i["title"] for i in data["results"]], ["A3", "A2", "A1"])
        self.assertEqual((data["count"], data["unread_count"]), (3, 2))
        self.assertNotIn("changed_data", data["results"][0])

    def test_filters_and_pages(self):
        url = reverse("wn_notifications:list")
        self.assertEqual(self.client.get(url, {"unread": "1"}).json()["count"], 2)
        self.assertEqual([i["title"] for i in self.client.get(url, {"flag": "error"}).json()["results"]], ["A2"])
        self.assertEqual(self.client.get(url, {"flag": "<script>"}).status_code, 400)
        data = self.client.get(url, {"page_size": 2, "page": 2}).json()
        self.assertEqual((data["num_pages"], len(data["results"])), (2, 1))
        self.assertEqual(self.client.get(url, {"page": 99}).json()["results"], [])
        self.assertEqual(self.client.get(url, {"page_size": 10_000}).json()["page_size"], 100)

    def test_detail_and_unread_count(self):
        data = self.client.get(reverse("wn_notifications:detail", args=[self.n1.pk])).json()
        self.assertEqual((data["changed_data"], data["action_by"]), ('{"x": 1}', "bob"))
        self.assertEqual(self.client.get(reverse("wn_notifications:unread_count")).json(), {"unread_count": 2})

    def test_other_users_notifications_are_404(self):
        self.assertEqual(self.client.get(reverse("wn_notifications:detail", args=[self.other.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("wn_notifications:read", args=[self.other.pk])).status_code, 404)
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_read)

    def test_read_unread_and_badge_cache(self):
        caches["default"].set(BADGE_CACHE_KEY.format(self.alice.pk), 7)
        r = self.client.post(reverse("wn_notifications:read", args=[self.n1.pk]))
        self.assertEqual(r.json(), {"id": self.n1.pk, "is_read": True, "unread_count": 1})
        self.assertIsNone(caches["default"].get(BADGE_CACHE_KEY.format(self.alice.pk)))
        self.assertEqual(self.client.post(reverse("wn_notifications:unread", args=[self.n1.pk])).json()["unread_count"], 2)
        self.assertEqual(self.client.get(reverse("wn_notifications:read", args=[self.n1.pk])).status_code, 405)

    def test_read_all_only_touches_own(self):
        self.assertEqual(self.client.post(reverse("wn_notifications:read_all")).json(), {"updated": 2, "unread_count": 0})
        self.other.refresh_from_db()
        self.assertFalse(self.other.is_read)

    def test_post_needs_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        self.assertEqual(client.post(reverse("wn_notifications:read_all")).status_code, 403)


def announcement_cb(request):
    return {"title": "Sense", "version": "2.54.0", "badge": "v2.54.0"}


@package_test_settings(CACHES=LOCMEM, ANNOUNCEMENT_CALLBACK=f"{__name__}.announcement_cb",
                       ANNOUNCEMENT_CONTENT_HTML_FILE=None)
class AnnouncementApiTests(CleanCacheTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("carol", password="x")

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("wn_announcement:detail")).status_code, 401)

    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE="does/not/exist.html")
    def test_announcement_then_seen_once_per_version(self):
        data = self.client.get(reverse("wn_announcement:detail")).json()["announcement"]
        self.assertEqual(data, {"title": "Sense", "version": "2.54.0", "badge": "v2.54.0", "html": "", "is_seen": False})
        self.assertEqual(self.client.post(reverse("wn_announcement:seen")).json(), {"version": "2.54.0", "is_seen": True})
        self.client.post(reverse("wn_announcement:seen"))
        self.assertEqual(AnnouncementReceipt.objects.filter(user=self.user).count(), 1)
        self.assertTrue(self.client.get(reverse("wn_announcement:detail")).json()["announcement"]["is_seen"])

    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE=None)
    def test_new_version_is_unseen_again(self):
        AnnouncementReceipt.objects.create(user=self.user, version="2.53.0")
        self.assertFalse(self.client.get(reverse("wn_announcement:detail")).json()["announcement"]["is_seen"])

    def test_long_version_is_seen_after_seen(self):
        with mock.patch(f"{__name__}.announcement_cb", return_value={"title": "Sense", "version": "9" * 150}):
            self.client.post(reverse("wn_announcement:seen"))
            data = self.client.get(reverse("wn_announcement:detail")).json()["announcement"]
        self.assertEqual(len(data["version"]), 100)
        self.assertTrue(data["is_seen"])

    @override_settings(ANNOUNCEMENT_CALLBACK=None)
    def test_no_announcement(self):
        self.assertEqual(self.client.get(reverse("wn_announcement:detail")).json(), {"announcement": None})
        self.assertEqual(self.client.post(reverse("wn_announcement:seen")).status_code, 404)

    @override_settings(ANNOUNCEMENT_CALLBACK="no.such.callback")
    def test_broken_callback_is_no_announcement(self):
        self.assertEqual(self.client.get(reverse("wn_announcement:detail")).json(), {"announcement": None})
