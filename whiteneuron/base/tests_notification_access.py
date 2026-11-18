"""Review of #83: a user without view_notification saw an unread count they could never clear."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from whiteneuron.notification.models import Notification

from .testing import package_test_settings

User = get_user_model()


@package_test_settings()
class NotificationInboxAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dave = User.objects.create_user("dave", "d@example.com", "pw", is_staff=True)  # no permissions
        cls.erin = User.objects.create_user("erin", "e@example.com", "pw", is_staff=True)
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        self.mine = Notification.objects.create(user=self.dave, title="mine", content="", flag="info")
        self.theirs = Notification.objects.create(user=self.erin, title="theirs", content="", flag="info")

    def test_signed_in_user_opens_own_inbox_without_the_permission(self):
        self.client.force_login(self.dave)
        response = self.client.get(reverse("admin:notification_notification_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mark-all-read")
        self.assertEqual(self.client.get(
            reverse("admin:notification_notification_change", args=[self.mine.pk])).status_code, 200)
        self.mine.refresh_from_db()
        self.assertTrue(self.mine.is_read)

    def test_another_users_notification_stays_closed(self):
        self.client.force_login(self.dave)
        response = self.client.get(reverse("admin:notification_notification_change", args=[self.theirs.pk]))
        self.assertNotEqual(response.status_code, 200)
        self.theirs.refresh_from_db()
        self.assertFalse(self.theirs.is_read)

    def test_guest_still_needs_the_permission(self):
        guest = User.objects.create_user("guest", "g@example.com", "pw", is_staff=True)
        guest.groups.add(Group.objects.get_or_create(name="Guest")[0])
        self.client.force_login(guest)
        response = self.client.get(reverse("admin:notification_notification_changelist"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_has_no_user_filter_that_finds_nothing(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("admin:notification_notification_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "user__id__exact")
