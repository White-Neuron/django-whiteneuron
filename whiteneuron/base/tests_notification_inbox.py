"""#37: the badge counted only today's unread notifications and went stale for 60s; the inbox had
no "mark all as read" and users could not delete their own notifications."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest import mock

from whiteneuron.notification.models import Notification
from whiteneuron.notification.utils import BADGE_CACHE_KEY, badge_text, unread_count

from .testing import package_test_settings

User = get_user_model()

# what the dialog form posts: unfold shows the dialog again until its hidden field is sent
DIALOG_POST = {"_form_submitted": "True"}


@package_test_settings()
class NotificationInboxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)
        cls.alice.user_permissions.add(Permission.objects.get(codename="view_notification"))
        cls.bob = User.objects.create_user("bob", "b@example.com", "pw", is_staff=True)
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        self.old = Notification.objects.create(user=self.alice, title="old", content="", flag="info")
        Notification.objects.filter(pk=self.old.pk).update(created_at=timezone.now() - timedelta(days=3))
        self.new = Notification.objects.create(user=self.alice, title="new", content="", flag="warning")
        self.bobs = Notification.objects.create(user=self.bob, title="bob's", content="", flag="info")
        self.client.force_login(self.alice)

    def _changelist(self):
        return reverse("admin:notification_notification_changelist")

    # ── the count ──
    def test_badge_counts_every_unread_notification_not_only_today(self):
        self.assertEqual(unread_count(self.alice), 2)
        self.alice.__dict__.pop("_wn_badge_count", None)
        self.assertEqual(self.alice.avatar_badge_count, 2)

    def test_badge_text_caps_at_99(self):
        self.assertIsNone(badge_text(0))
        self.assertEqual(badge_text(99), 99)
        self.assertEqual(badge_text(100), "99+")

    def test_new_notification_clears_the_cached_count(self):
        self.assertEqual(unread_count(self.alice), 2)  # cached now
        Notification.objects.create(user=self.alice, title="x", content="", flag="info")
        self.assertEqual(unread_count(self.alice), 3)

    def test_notify_superusers_clears_their_cached_count(self):
        self.assertEqual(unread_count(self.root), 0)
        with self.captureOnCommitCallbacks(execute=False):
            Notification.notify_superusers(title="t")
        self.assertEqual(unread_count(self.root), 1)

    def test_opening_a_notification_clears_the_cached_count(self):
        self.assertEqual(unread_count(self.alice), 2)
        self.client.get(reverse("admin:notification_notification_change", args=[self.new.pk]))
        self.assertEqual(unread_count(self.alice), 1)

    def test_model_helpers_clear_the_cached_count(self):
        self.assertEqual(unread_count(self.alice), 2)
        self.assertEqual(Notification.mark_as_read_all(self.alice), 2)
        self.assertEqual(unread_count(self.alice), 0)
        Notification.mark_as_unread_all(self.alice)
        self.assertEqual(unread_count(self.alice), 2)

    def test_api_and_badge_count_the_same(self):
        self.assertEqual(self.client.get(reverse("wn_notifications:unread_count")).json()["unread_count"],
                         unread_count(self.alice))

    # ── the admin ──
    def test_changelist_offers_the_actions_and_filters(self):
        response = self.client.get(self._changelist())
        self.assertEqual(response.status_code, 200)
        for text in ("mark_selected_read", "mark_selected_unread", "mark-all-read", "is_read__exact", "flag__exact"):
            self.assertContains(response, text)

    def test_mark_all_read_asks_first_then_changes_only_own(self):
        url = reverse("admin:notification_notification_mark_all_read")
        self.assertEqual(unread_count(self.alice), 2)
        self.assertEqual(self.client.get(url).status_code, 200)  # the dialog: nothing changes on GET
        self.assertEqual(Notification.objects.filter(user=self.alice, is_read=False).count(), 2)
        response = self.client.post(url, DIALOG_POST)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(unread_count(self.alice), 0)
        self.bobs.refresh_from_db()
        self.assertFalse(self.bobs.is_read)

    def test_mark_unread_from_the_detail_page(self):
        self.client.get(reverse("admin:notification_notification_change", args=[self.new.pk]))
        url = reverse("admin:notification_notification_mark_unread", args=[self.new.pk])
        self.assertEqual(self.client.post(url, DIALOG_POST).status_code, 302)
        self.new.refresh_from_db()
        self.assertFalse(self.new.is_read)

    def test_bulk_read_and_unread_ignore_other_users_rows(self):
        selected = [self.old.pk, self.new.pk, self.bobs.pk]
        self.client.post(self._changelist(), {"action": "mark_selected_read", "_selected_action": selected})
        self.assertEqual(unread_count(self.alice), 0)
        self.bobs.refresh_from_db()
        self.assertFalse(self.bobs.is_read)
        self.client.post(self._changelist(), {"action": "mark_selected_unread", "_selected_action": [self.old.pk]})
        self.assertEqual(unread_count(self.alice), 1)

    def test_user_deletes_only_own_notifications_without_telling_superusers(self):
        before = Notification.objects.filter(user=self.root).count()
        response = self.client.post(self._changelist(), {
            "action": "delete_selected", "post": "yes", "_selected_action": [self.new.pk, self.bobs.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.filter(pk=self.new.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=self.bobs.pk).exists())
        self.assertEqual(Notification.objects.filter(user=self.root).count(), before)
        self.assertEqual(unread_count(self.alice), 1)

    def test_cannot_delete_another_users_notification_by_url(self):
        response = self.client.post(reverse("admin:notification_notification_delete", args=[self.bobs.pk]), {"post": "yes"})
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(Notification.objects.filter(pk=self.bobs.pk).exists())

    def test_superuser_has_no_trash_actions_here(self):
        self.client.force_login(self.root)
        response = self.client.get(self._changelist())
        self.assertNotContains(response, 'value="hard_delete"')
        self.assertNotContains(response, 'value="restore"')

    # ── the toast ──
    def test_toast_title_comes_from_the_page_language(self):
        from whiteneuron.notification import views

        layer = mock.Mock()
        with mock.patch.object(views, "get_channel_layer", return_value=layer), \
                mock.patch.object(views, "async_to_sync", side_effect=lambda f: f):
            views.notify_admin("hello", user_ids=[self.alice.pk])
        event = layer.group_send.call_args.args[1]
        self.assertEqual(event["message"]["title"], "")
        self.assertContains(self.client.get(self._changelist()), 'data-wn-toast-title="')


@package_test_settings()
class NotificationStatusLabelTests(TestCase):
    def test_unread_is_a_label_not_a_red_cross(self):
        user = User.objects.create_user("carol", "c@example.com", "pw", is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename="view_notification"))
        Notification.objects.create(user=user, title="t", content="", flag="info")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:notification_notification_changelist"))
        self.assertContains(response, "Unread")
        self.assertNotContains(response, "icon-no.svg")
