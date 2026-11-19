"""#46: error pages were English only, branded "White Neuron", always dark, and linked to a
/contact/ page that does not exist."""
import re

from django.template.loader import render_to_string
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from .testing import package_test_settings

PAGES = ("400.html", "403.html", "403_csrf.html", "404.html", "429.html", "500.html")


@package_test_settings(NAME="Acme Portal", UNFOLD={"SITE_TITLE": "Acme Portal"})
class ErrorPageTests(TestCase):
    def _render(self, name, language, **context):
        with translation.override(language):
            return render_to_string(name, context, request=RequestFactory().get("/"))

    def test_every_page_in_both_languages_with_the_project_name(self):
        for name in PAGES:
            for language, lang_attr in (("en", 'lang="en"'), ("vi", 'lang="vi"')):
                html = self._render(name, language)
                self.assertIn(lang_attr, html, name)
                self.assertIn("Acme Portal", html, name)
                self.assertNotIn("White Neuron", html, name)
        self.assertIn("Không tìm thấy trang", self._render("404.html", "vi"))
        self.assertIn("Phiên làm việc đã hết hạn", self._render("403_csrf.html", "vi"))

    def test_no_link_leads_to_a_404(self):
        client = Client()
        for name in PAGES:
            html = self._render(name, "en")
            self.assertNotIn("/contact/", html, name)
            for href in re.findall(r'href="([^"#]+)"', html):
                if href.startswith("/"):
                    self.assertNotEqual(client.get(href).status_code, 404, (name, href))

    def test_home_link_defaults_to_the_admin_and_support_button_is_opt_in(self):
        html = self._render("404.html", "en")
        self.assertIn(f'href="{reverse("admin:index")}"', html)
        self.assertNotIn("Contact support", html)
        with override_settings(WN_SUPPORT_URL="mailto:help@example.com", WN_HOME_URL="/portal/"):
            html = self._render("404.html", "en")
        self.assertIn('href="mailto:help@example.com"', html)
        self.assertIn('href="/portal/"', html)

    def test_follows_the_light_or_dark_theme(self):
        html = self._render("404.html", "en")
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertIn("_x_adminTheme", html)

    def test_429_counts_down_retry_after(self):
        html = self._render("429.html", "en", retry_after=60)
        self.assertIn('<span id="wn-retry-seconds">60</span>', html)
        self.assertRegex(html, r'id="wn-retry"[^>]*disabled')
        self.assertNotIn("disabled", self._render("429.html", "en").split('id="wn-retry"')[1].split(">")[0])

    def test_csrf_failure_uses_the_package_page(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("admin:login"), {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Your session has expired", status_code=403)
        self.assertContains(response, "Acme Portal", status_code=403)

    def test_server_error_page_renders_without_a_request(self):
        # Django renders 500.html with an empty context and no request
        from django.views.defaults import server_error

        response = server_error(RequestFactory().get("/"))
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Something went wrong", response.content)


@package_test_settings(NAME="Acme Portal", UNFOLD={"SITE_TITLE": "Acme Portal"})
class ErrorPageReviewTests(TestCase):
    """Review of #96."""

    def test_a_project_base_html_does_not_reach_the_error_pages(self):
        from django.conf import settings

        templates = [{**settings.TEMPLATES[0], "APP_DIRS": False, "OPTIONS": {
            **settings.TEMPLATES[0]["OPTIONS"],
            "loaders": [
                ("django.template.loaders.locmem.Loader", {"base.html": "PROJECT SITE LAYOUT"}),
                "django.template.loaders.app_directories.Loader",
            ],
        }}]
        with override_settings(TEMPLATES=templates):
            html = render_to_string("404.html", {}, request=RequestFactory().get("/"))
        self.assertNotIn("PROJECT SITE LAYOUT", html)
        self.assertIn("error-section", html)

    def test_retry_buttons_reopen_the_page_with_get(self):
        for name in ("403_csrf.html", "429.html", "500.html"):
            html = render_to_string(name, {"retry_after": 1}, request=RequestFactory().get("/"))
            self.assertNotIn("location.reload()", html, name)
            self.assertIn("location.replace(location.href)", html, name)

    def test_one_primary_action_per_page(self):
        for name in PAGES:
            html = render_to_string(name, {}, request=RequestFactory().get("/"))
            self.assertEqual(html.count("error-btn primary"), 1, name)
