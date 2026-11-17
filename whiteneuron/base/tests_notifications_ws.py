"""#51: pages opened /ws/notifications/ even under WSGI, where no route serves it."""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core import checks
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from whiteneuron.notification.checks import notifications_websocket_check

from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class NotificationsWebSocketSwitchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def _admin_page(self):
        self.client.force_login(self.root)
        return self.client.get(reverse("admin:index"))

    @override_settings(WN_NOTIFICATIONS_WEBSOCKET=None, ASGI_APPLICATION=None)
    def test_off_under_wsgi_by_default(self):
        self.assertNotContains(self._admin_page(), 'data-wn-ws="1"')

    @override_settings(WN_NOTIFICATIONS_WEBSOCKET=None, ASGI_APPLICATION="project.asgi.application")
    def test_on_by_default_under_asgi(self):
        self.assertContains(self._admin_page(), 'data-wn-ws="1"')

    @override_settings(ASGI_APPLICATION="project.asgi.application")
    def test_setting_overrides_detection(self):
        for value, expected in (("False", False), ("True", True), (False, False), (True, True)):
            with self.settings(WN_NOTIFICATIONS_WEBSOCKET=value):
                self.assertEqual('data-wn-ws="1"' in self._admin_page().content.decode(), expected, value)

    @override_settings(WN_NOTIFICATIONS_WEBSOCKET=True)
    def test_never_for_anonymous_pages(self):
        self.assertNotContains(self.client.get(reverse("admin:login")), 'data-wn-ws="1"')

    def test_script_connects_only_when_asked(self):
        js = (Path(__file__).resolve().parent.parent / "static/base/js/whiteneuron.js").read_text()
        self.assertIn('container.dataset.wnWs !== "1"', js)



REDIS_LAYER = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": ["redis://r"]}}}
MEMORY_LAYER = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


class NotificationsWebSocketCheckTests(SimpleTestCase):
    def _ids(self):
        return [m.id for m in notifications_websocket_check()]

    @override_settings(CHANNEL_LAYERS=REDIS_LAYER, ASGI_APPLICATION=None, WN_NOTIFICATIONS_WEBSOCKET=None)
    def test_warns_when_redis_is_set_up_but_the_websocket_is_off_by_default(self):
        self.assertEqual(self._ids(), ["whiteneuron.W001"])
        self.assertIn("whiteneuron.W001", [m.id for m in checks.run_checks()])

    def test_quiet_otherwise(self):
        cases = [
            dict(CHANNEL_LAYERS=MEMORY_LAYER, ASGI_APPLICATION=None, WN_NOTIFICATIONS_WEBSOCKET=None),
            dict(CHANNEL_LAYERS=REDIS_LAYER, ASGI_APPLICATION="p.asgi.application", WN_NOTIFICATIONS_WEBSOCKET=None),
            dict(CHANNEL_LAYERS=REDIS_LAYER, ASGI_APPLICATION=None, WN_NOTIFICATIONS_WEBSOCKET="False"),
            dict(CHANNEL_LAYERS=REDIS_LAYER, ASGI_APPLICATION=None, WN_NOTIFICATIONS_WEBSOCKET="True"),
        ]
        for case in cases:
            with self.subTest(**case), self.settings(**case):
                self.assertEqual(self._ids(), [])
