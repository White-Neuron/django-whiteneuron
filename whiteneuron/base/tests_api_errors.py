"""#76: JSON API errors came in three shapes (empty 405, HTML CSRF 403, HTML 404)."""
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import Client, TestCase
from django.urls import reverse

from whiteneuron.notification.models import Notification

from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class JsonApiErrorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)
        cls.note = Notification.objects.create(user=cls.alice, title="t", content="", flag="info")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.alice)

    def assertJsonError(self, response, status):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("detail", response.json())

    def test_wrong_method_is_json_405_with_allow(self):
        response = self.client.get(reverse("wn_notifications:read", args=[self.note.pk]))
        self.assertJsonError(response, 405)
        self.assertEqual(response["Allow"], "POST")
        response = self.client.post(reverse("wn_system:health"))
        self.assertJsonError(response, 405)
        self.assertEqual(response["Allow"], "GET, HEAD")

    def test_head_is_allowed_where_get_is(self):
        self.assertEqual(self.client.head(reverse("wn_system:health")).status_code, 200)

    def test_csrf_failure_is_json_403(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        response = client.post(reverse("wn_notifications:read", args=[self.note.pk]))
        self.assertJsonError(response, 403)
        self.assertIn("CSRF", response.json()["detail"])
        self.note.refresh_from_db()
        self.assertFalse(self.note.is_read)

    def test_valid_csrf_token_still_works(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        client.get(reverse("admin:index"))  # sets the CSRF cookie
        token = client.cookies["csrftoken"].value
        response = client.post(reverse("wn_notifications:read", args=[self.note.pk]), HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_unknown_paths_are_json_404(self):
        for path in ("/api/notifications/abc/", "/api/notifications/1/nope/", "/api/system/nope/",
                     "/api/announcement/x/"):
            self.assertJsonError(self.client.get(path), 404)

    def test_project_routes_after_the_api_include_are_reached(self):
        # a project's own api/… URL declared after include("whiteneuron.api_urls")
        with self.settings(ROOT_URLCONF=__name__):
            response = self.client.get("/api/project-endpoint/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"project")

    def test_anonymous_post_is_401_not_a_csrf_403(self):
        client = Client(enforce_csrf_checks=True)
        self.assertJsonError(client.post(reverse("wn_notifications:read", args=[self.note.pk])), 401)

    def test_paths_outside_the_api_keep_the_html_404(self):
        response = self.client.get("/admin/nothing-here-at-all/")
        self.assertNotEqual(response.get("Content-Type"), "application/json")


def _urlpatterns():
    from django.http import HttpResponse
    from django.urls import include, path

    from .sites import base_admin_site

    return [
        path("admin/", base_admin_site.urls),
        path("api/", include("whiteneuron.api_urls")),
        path("api/project-endpoint/", lambda request: HttpResponse("project")),
    ]


urlpatterns = _urlpatterns()
