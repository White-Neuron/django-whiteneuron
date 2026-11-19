"""#95: the loading overlay stayed up after closing a dialog; the floating History button
covered the end of long forms."""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from whiteneuron.notification.models import Notification

from .testing import package_test_settings

User = get_user_model()
LOADING_JS = Path(__file__).resolve().parent.parent / "static" / "base" / "js" / "loading.js"


@package_test_settings()
class HistoryTriggerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.root)
        self.url = reverse("admin:base_user_change", args=[self.root.pk])
        Notification.objects.create(user=self.root, title="changed", content="", flag="info",
                                    action="update", obj_link=self.url)

    def test_history_is_a_page_action_not_a_floating_button(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('id="wn-history-open"', html)
        self.assertIn('id="wn-history-modal"', html)
        self.assertNotIn("fixed bottom-20", html)
        # in the page actions, before the form
        self.assertLess(html.index('id="wn-history-open"'), html.index('id="user_form"'))

    def test_no_history_no_button(self):
        Notification.objects.all().delete()
        self.assertNotIn('id="wn-history-open"', self.client.get(self.url).content.decode())


class LoadingOverlayScriptTests(TestCase):
    """No JS runner in the suite: check the script keeps its guards."""

    def test_dialog_forms_and_scripted_submits_do_not_show_the_overlay(self):
        source = LOADING_JS.read_text()
        self.assertIn("method === 'dialog'", source)
        self.assertIn("formmethod", source)
        self.assertIn("event.defaultPrevented", source.split("addEventListener('submit'")[1].split("});")[0])
        self.assertIn("GIVE_UP_MS", source)
