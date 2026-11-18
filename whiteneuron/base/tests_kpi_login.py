"""#82: "+57 (0.00%)" when the previous period had nothing; two error boxes for a wrong password."""
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class KpiWithoutPreviousPeriodTests(TestCase):
    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def test_no_percentage_when_the_previous_period_is_empty(self):
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        self.client.force_login(root)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "(no data for the previous period)")
        self.assertNotContains(response, "(0.00%)")


@package_test_settings()
class LoginErrorTests(TestCase):
    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        User.objects.create_user("alice", "a@example.com", "right-pw", is_staff=True)

    def test_wrong_password_shows_one_error_box(self):
        response = self.client.post(reverse("admin:login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter the correct username and password")
        self.assertNotContains(response, "Please correct the error")

    def test_missing_field_still_points_at_it(self):
        response = self.client.post(reverse("admin:login"), {"username": "alice", "password": ""})
        self.assertContains(response, "Please correct the error")


class KpiNoChangeTests(TestCase):
    def test_no_change_is_neutral(self):
        from django.test import RequestFactory
        from unittest import mock

        from whiteneuron.dashboard import views

        from collections import defaultdict

        chart = defaultdict(list)  # no activity on any day
        stats = {"kpi": (5, 5, 5, 0, 0, 0), "chart": chart, "dates": []}
        with mock.patch.object(views, "_dashboard_stats", return_value=stats):
            kpi = views.dashboard_callback(RequestFactory().get("/admin/", {"time": "week"}), {})["kpi"]
        unchanged, empty = str(kpi[0]["footer"]), str(kpi[1]["footer"])
        self.assertIn("text-base-500", unchanged)
        self.assertNotIn("+0", unchanged)
        self.assertIn(">0 (0.00%)<", unchanged.replace("</strong>", "<"))
        self.assertIn("text-base-500", empty)  # 0 now, 0 before
        self.assertNotIn("text-green-600", empty)
