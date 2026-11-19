"""#80: the home page and the user change form scrolled sideways at 390px. Measured in a
browser for the PR; these tests keep the markup and CSS that fix it."""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from .testing import package_test_settings

User = get_user_model()
BTN_CSS = Path(__file__).resolve().parent.parent / "static" / "base" / "css" / "btn-styles.css"


@package_test_settings()
class MobileOverflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.root)

    def test_home_tabs_scroll_in_their_strip_and_kpis_stack(self):
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertEqual(html.count("wn-nav-scroll max-w-full overflow-x-auto"), 2)
        # the KPI row is a column below lg (the flex component adds flex-row unless col=1)
        self.assertIn("flex  flex-col gap-8 mb-8 lg:flex-row", html)
        self.assertNotIn('class="absolute right-0 top-0"', html.split("gap-8 mb-8 lg:flex-row")[1].split("monitoring")[0])

    def test_css_keeps_forms_inside_the_screen(self):
        css = BTN_CSS.read_text()
        self.assertIn("fieldset.module {\n    min-width: 0;", css)
        self.assertIn("#id_password.readonly", css)
        self.assertIn(".wn-nav-scroll > a", css)
