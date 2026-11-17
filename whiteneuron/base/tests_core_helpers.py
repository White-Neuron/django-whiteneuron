"""#53: helpers every downstream project copied: dialog redirects, environment label, announcement."""
import sys
import types

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .middleware import AdminDialogRedirectMiddleware
from .testing import package_test_settings
from .utils import announcement_callback, environment_callback

User = get_user_model()


def redirecting(request):
    response = HttpResponseRedirect("/admin/base/user/")
    response.set_cookie("messages", "done")
    return response


@package_test_settings()
class AdminDialogRedirectMiddlewareTests(SimpleTestCase):
    def _call(self, method="post", path=None, htmx=True, view=redirecting):
        path = path or reverse("admin:index") + "base/user/1/action/"
        headers = {"HTTP_HX_REQUEST": "true"} if htmx else {}
        request = getattr(RequestFactory(), method)(path, **headers)
        return AdminDialogRedirectMiddleware(view)(request)

    def test_htmx_post_redirect_under_admin_becomes_hx_redirect(self):
        response = self._call()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], "/admin/base/user/")
        self.assertEqual(response.cookies["messages"].value, "done")  # the message still shows

    def test_other_responses_are_untouched(self):
        self.assertEqual(self._call(htmx=False).status_code, 302)
        self.assertEqual(self._call(method="get").status_code, 302)
        self.assertEqual(self._call(path="/api/thing/").status_code, 302)
        self.assertEqual(self._call(view=lambda r: HttpResponse("ok")).status_code, 200)
        self.assertNotIn("HX-Redirect", self._call(view=lambda r: HttpResponse("ok")))

    def test_enabled_by_default(self):
        self.assertIn("whiteneuron.base.middleware.AdminDialogRedirectMiddleware", settings.MIDDLEWARE)


class EnvironmentCallbackTests(SimpleTestCase):
    request = RequestFactory().get("/")

    def setUp(self):
        from . import utils

        cache = mock_dict(utils._project_environment_callbacks, clear=True)  # looked up once per name
        cache.start()
        self.addCleanup(cache.stop)

    @override_settings(PROJECT_NAME="no_such_project", DEBUG=True, WN_ENVIRONMENT_LABEL=None)
    def test_development_with_debug(self):
        self.assertEqual([str(v) for v in environment_callback(self.request)], ["Development", "info"])

    @override_settings(PROJECT_NAME="no_such_project", DEBUG=False, WN_ENVIRONMENT_LABEL=None)
    def test_production_without_debug(self):
        self.assertEqual([str(v) for v in environment_callback(self.request)], ["Production", "warning"])

    @override_settings(PROJECT_NAME="no_such_project", DEBUG=False, WN_ENVIRONMENT_LABEL="Staging")
    def test_label_override(self):
        self.assertEqual(environment_callback(self.request), ["Staging", "warning"])

    def test_a_projects_own_callback_still_wins(self):
        module = types.ModuleType("fakeproj.utils")
        module.environment_callback = lambda request: ["Mine", "success"]
        package = types.ModuleType("fakeproj")
        package.utils = module
        with self.settings(PROJECT_NAME="fakeproj"), \
                mock_modules({"fakeproj": package, "fakeproj.utils": module}):
            self.assertEqual(environment_callback(self.request), ["Mine", "success"])

    def test_a_broken_project_module_is_logged_not_hidden(self):
        # brokenproj/utils.py exists but imports something missing
        def broken_import(name, *args, **kwargs):
            if name == "brokenproj.utils":
                raise ModuleNotFoundError("No module named 'requets'", name="requets")
            return real_import(name, *args, **kwargs)

        import importlib
        real_import = importlib.import_module
        with self.settings(PROJECT_NAME="brokenproj", DEBUG=True, WN_ENVIRONMENT_LABEL=None), \
                mock_patch("importlib.import_module", side_effect=broken_import), \
                self.assertLogs("whiteneuron.base.utils", "WARNING"):
            self.assertEqual(str(environment_callback(self.request)[0]), "Development")

    def test_the_project_lookup_happens_once(self):
        import importlib
        with self.settings(PROJECT_NAME="no_such_project", DEBUG=True), \
                mock_patch("importlib.import_module", wraps=importlib.import_module) as imported:
            environment_callback(self.request)
            environment_callback(self.request)
        self.assertEqual(imported.call_count, 1)

    @override_settings(PROJECT_NAME="no_such_project", DEBUG=False, WN_ENVIRONMENT_LABEL=None)
    def test_label_has_a_translation_context(self):
        from django.utils import translation

        with translation.override("vi"):
            self.assertEqual(str(environment_callback(self.request)[0]), "Chính thức")

    def test_default_is_the_core_callback(self):
        self.assertEqual(settings.UNFOLD["ENVIRONMENT"], "whiteneuron.base.utils.environment_callback")


def mock_modules(modules):
    from unittest import mock

    return mock.patch.dict(sys.modules, modules)


def mock_dict(target, **kwargs):
    from unittest import mock

    return mock.patch.dict(target, **kwargs)


def mock_patch(target, **kwargs):
    from unittest import mock

    return mock.patch(target, **kwargs)


@package_test_settings(PROJECT_NAME="no_such_project", WN_ENVIRONMENT_LABEL=None)  # tests run with DEBUG=False
class EnvironmentLabelRenderTests(TestCase):
    def test_header_shows_the_label_not_one_character(self):
        # without <PROJECT_NAME>/utils.py, Unfold fell back to the dotted path string and
        # the label template showed its first character
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        self.client.force_login(root)
        self.assertContains(self.client.get(reverse("admin:index")), "Production")


class AnnouncementCallbackTests(SimpleTestCase):
    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE="announcement_content.html", NAME="Sense", VERSION="2.54.0")
    def test_short_title_and_version_badge(self):
        data = announcement_callback(RequestFactory().get("/"))
        self.assertEqual((str(data["title"]), data["version"], data["badge"]), ("Sense", "2.54.0", "v2.54.0"))

    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE="announcement_content.html", NAME="Sense", VERSION="v2.54.0")
    def test_badge_does_not_double_the_v(self):
        self.assertEqual(announcement_callback(RequestFactory().get("/"))["badge"], "v2.54.0")

    @override_settings(ANNOUNCEMENT_CONTENT_HTML_FILE=None)
    def test_none_without_content(self):
        self.assertIsNone(announcement_callback(RequestFactory().get("/")))
