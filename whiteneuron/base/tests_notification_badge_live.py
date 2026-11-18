"""#68: without the WebSocket the unread badge only changed on a page reload."""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.urls import reverse

from whiteneuron.notification.models import Notification

from .templatetags.wn_notifications import (
    notifications_poll_seconds,
    wn_badge_value,
    wn_unread_badge_class,
)
from .testing import package_test_settings

User = get_user_model()


def toast_container(html):
    return re.search(r'<div[^>]*id="toast-container"[^>]*>', html).group(0)


@package_test_settings(WN_NOTIFICATIONS_WEBSOCKET=False)
class LiveUnreadBadgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.alice)

    def _page(self):
        return self.client.get(reverse("admin:notification_notification_changelist")).content.decode()

    def test_page_knows_where_to_ask_and_how_often(self):
        tag = toast_container(self._page())
        self.assertIn(f'data-wn-unread-url="{reverse("wn_notifications:unread_count")}"', tag)
        self.assertIn('data-wn-unread-poll="60"', tag)
        self.assertNotIn("data-wn-ws", tag)

    @override_settings(WN_NOTIFICATIONS_POLL_SECONDS="0")
    def test_poll_can_be_turned_off(self):
        self.assertIn('data-wn-unread-poll="0"', toast_container(self._page()))

    def test_without_the_api_mounted_the_page_does_not_ask(self):
        with override_settings(ROOT_URLCONF=__name__):
            self.assertIsNone(re.search("data-wn-unread-url", toast_container(self._page())))

    def test_sidebar_badge_is_rendered_even_at_zero_so_the_page_can_fill_it(self):
        html = self._page()
        self.assertRegex(html, r'class="[^"]*wn-unread-badge[^"]*\bhidden\b')
        Notification.objects.create(user=self.alice, title="t", content="", flag="info")
        html = self._page()
        badge = re.search(r'<span class="[^"]*wn-unread-badge[^"]*"[^>]*>\s*([^<]*?)\s*</span>', html, re.S)
        self.assertIsNotNone(badge)
        self.assertEqual(badge.group(1), "+1")
        self.assertNotRegex(badge.group(0), r'\bhidden\b')
        # the avatar badge carries the marker whiteneuron.js looks for
        self.assertIn("?is_read__exact=0#wn-unread", html)

    def test_polled_endpoint_is_not_logged_as_activity(self):
        from .middleware import UNTRACKED_URL_NAMES

        self.assertIn("wn_notifications:unread_count", UNTRACKED_URL_NAMES)

    def test_guest_sees_no_avatar_count(self):
        guest = User.objects.create_user("guest", "g@example.com", "pw", is_staff=True)
        guest.groups.add(Group.objects.get_or_create(name="Guest")[0])
        Notification.objects.create(user=guest, title="t", content="", flag="info")
        self.assertIsNone(guest.avatar_badge_count)


class BadgeHelperTests(TestCase):
    def test_values_match_the_other_sidebar_badges(self):
        self.assertEqual(wn_badge_value("3"), "+3")
        self.assertEqual(wn_badge_value("99+"), "99+")
        for empty in ("", "0", "None", None):
            self.assertEqual(wn_badge_value(empty), "")

    def test_class_keeps_the_items_own_and_hides_at_zero(self):
        self.assertEqual(wn_unread_badge_class({"badge_class": "x"}, "2"), "wn-unread-badge x")
        self.assertEqual(wn_unread_badge_class({}, "0"), "wn-unread-badge hidden")

    def test_poll_seconds_setting(self):
        with override_settings(WN_NOTIFICATIONS_POLL_SECONDS="30"):
            self.assertEqual(notifications_poll_seconds(), 30)
        with override_settings(WN_NOTIFICATIONS_POLL_SECONDS="junk"):
            self.assertEqual(notifications_poll_seconds(), 60)
        with override_settings(WN_NOTIFICATIONS_POLL_SECONDS=-5):
            self.assertEqual(notifications_poll_seconds(), 0)


# A project that has not mounted the JSON API (this module is its URLconf)
def _urlpatterns():
    from django.urls import include, path

    from .sites import base_admin_site
    from .urls import urlpatterns as base_urlpatterns

    return [path("i18n/", include("django.conf.urls.i18n")), path("admin/", base_admin_site.urls), *base_urlpatterns]


urlpatterns = _urlpatterns()
