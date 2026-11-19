"""#81: list rows that did not say what happened, red ✗ for normal states, technical words in
the search box, and an empty list that read like a failed search."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from whiteneuron.feedbacks.models import FeedbackData
from whiteneuron.notification.admin import NotificationAdmin
from whiteneuron.notification.models import Notification

from .sites import base_admin_site
from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class ListPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.member = User.objects.create_user("nhanvien1", "n@example.com", "pw", is_staff=True)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.client.force_login(self.root)
        self.client.cookies["django_language"] = "vi"

    def test_notification_row_says_what_happened_to_what(self):
        link = reverse("admin:base_user_change", args=[self.member.pk])
        note = Notification.objects.create(user=self.root, title="x", content="", flag="info",
                                           action="update", obj_link=link, action_by=self.root)
        html = str(NotificationAdmin(Notification, base_admin_site).display_title(note))
        self.assertIn("nhanvien1", html)           # which record
        self.assertIn(f'href="{link}"', html)      # linked
        self.assertIn("root", html)                # by whom
        self.assertIn("font-semibold", html)       # unread: bold
        note.is_read = True
        self.assertNotIn("font-semibold", str(NotificationAdmin(Notification, base_admin_site).display_title(note)))

    def test_notification_without_a_linked_object_shows_its_title(self):
        note = Notification.objects.create(user=self.root, title="Nightly import finished", content="", flag="info")
        html = str(NotificationAdmin(Notification, base_admin_site).display_title(note))
        self.assertIn("Nightly import finished", html)

    def test_pending_feedback_is_a_label_not_a_red_cross(self):
        FeedbackData.objects.create(user=self.root, content_type=ContentType.objects.get_for_model(Group),
                                    object_id="1", message="please check")
        html = self.client.get(reverse("admin:feedbacks_feedbackdata_changelist")).content.decode()
        self.assertIn("Đang chờ", html)
        self.assertNotIn("icon-no.svg", html)

    def test_search_box_has_no_field_paths(self):
        for name in ("admin:notification_notification_changelist", "admin:feedbacks_feedbackdata_changelist",
                     "admin:base_user_changelist"):
            html = self.client.get(reverse(name)).content.decode()
            placeholder = html.split('id="searchbar"')[1].split('placeholder="')[1].split('"')[0]
            self.assertNotIn(" / ", placeholder, name)
            self.assertNotIn("python", placeholder.lower(), name)
            self.assertNotIn("content_type", placeholder, name)

    def test_empty_list_without_filters_is_not_a_failed_search(self):
        url = reverse("admin:file_management_pdffile_changelist")
        html = self.client.get(url).content.decode()
        self.assertIn("Chưa có", html)
        self.assertNotIn("Đặt lại bộ lọc", html)
        html = self.client.get(url, {"q": "nothing-matches"}).content.decode()
        self.assertIn("Đặt lại bộ lọc", html)

    def test_home_title_has_no_trailing_full_stop(self):
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertNotIn("Site quản trị hệ thống.", html)
