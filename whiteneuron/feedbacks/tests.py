"""#47: feedback workflow - statuses, one service for single and bulk changes, the badge."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import RequestFactory, TestCase
from django.urls import reverse

from whiteneuron.base.testing import package_test_settings
from whiteneuron.notification.models import Notification

from . import services
from .models import FeedbackData
from .utils import feedback_data_badge_callback

User = get_user_model()


class FeedbackTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.alice = User.objects.create_user("alice", "a@example.com", "pw", is_staff=True)
        cls.bob = User.objects.create_user("bob", "b@example.com", "pw", is_staff=True)
        cls.ct = ContentType.objects.get_for_model(Group)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def _feedback(self, user, message="please check"):
        return FeedbackData.objects.create(user=user, content_type=self.ct, object_id="1", message=message)

    def _sender_notes(self, user):
        return Notification.objects.filter(user=user, title__startswith="Feedback")


class ServiceTests(FeedbackTestCase):
    def test_resolve_saves_notifies_the_sender_and_reopen_works(self):
        fb = self._feedback(self.alice)
        from unittest import mock

        with mock.patch.object(Notification, "alert") as alert, self.captureOnCommitCallbacks(execute=True):
            self.assertTrue(services.resolve(fb, note="fixed"))
        fb.refresh_from_db()
        self.assertEqual((fb.status, fb.is_resolved, fb.note), ("resolved", True, "fixed"))
        self.assertEqual(self._sender_notes(self.alice).count(), 1)
        # the WebSocket toast goes to the sender, after commit
        self.assertIn(mock.call(user_ids=[self.alice.pk]), alert.call_args_list)
        self.assertTrue(services.reopen(fb))
        fb.refresh_from_db()
        self.assertEqual((fb.status, fb.is_resolved), ("open", False))
        self.assertEqual(self._sender_notes(self.alice).count(), 2)

    def test_no_change_no_notification(self):
        fb = self._feedback(self.alice)
        self.assertFalse(services.reopen(fb))
        self.assertFalse(self._sender_notes(self.alice).exists())

    def test_unknown_status_is_refused(self):
        with self.assertRaises(ValueError):
            services.set_status(self._feedback(self.alice), "done")


@package_test_settings()
class AdminWorkflowTests(FeedbackTestCase):
    def test_bulk_resolve_notifies_every_sender_and_records_each(self):
        feedbacks = [self._feedback(self.alice), self._feedback(self.bob), self._feedback(self.alice)]
        history_before = Notification.objects.filter(user=self.root, action="update").count()
        self.client.force_login(self.root)
        self.client.post(reverse("admin:feedbacks_feedbackdata_changelist"),
                         {"action": "mark_as_resolved", "_selected_action": [f.pk for f in feedbacks]})
        self.assertEqual(FeedbackData.objects.filter(status="resolved").count(), 3)
        self.assertEqual(self._sender_notes(self.alice).count(), 2)
        self.assertEqual(self._sender_notes(self.bob).count(), 1)
        # one history ("update") entry per record, from BaseModel.save
        self.assertEqual(Notification.objects.filter(user=self.root, action="update").count() - history_before, 3)

    def test_resolved_feedback_can_be_reopened(self):
        fb = self._feedback(self.alice)
        services.resolve(fb)
        self.client.force_login(self.root)
        self.client.post(reverse("admin:feedbacks_feedbackdata_changelist"),
                         {"action": "reopen", "_selected_action": [fb.pk]})
        fb.refresh_from_db()
        self.assertEqual(fb.status, "open")

    def test_single_resolve_from_the_change_form(self):
        fb = self._feedback(self.alice)
        self.client.force_login(self.root)
        url = reverse("admin:feedbacks_feedbackdata_change", args=[fb.pk]) + "?resolved=1"
        self.assertEqual(self.client.post(url, {"note": "done"}).json(), {"success": True})
        fb.refresh_from_db()
        self.assertEqual(fb.status, "resolved")
        self.assertEqual(self._sender_notes(self.alice).count(), 1)

    def test_only_superusers_change_the_status(self):
        fb = self._feedback(self.alice)
        self.client.force_login(self.alice)
        self.client.post(reverse("admin:feedbacks_feedbackdata_changelist"),
                         {"action": "mark_as_resolved", "_selected_action": [fb.pk]})
        fb.refresh_from_db()
        self.assertEqual(fb.status, "open")


class BadgeTests(FeedbackTestCase):
    def _badge(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return feedback_data_badge_callback(request)

    def test_badge_counts_open_feedbacks(self):
        a1, a2 = self._feedback(self.alice), self._feedback(self.alice)
        self._feedback(self.bob)
        self.assertEqual(self._badge(self.root), 3)
        self.assertEqual(self._badge(self.alice), 2)
        services.resolve(a1)
        self.assertEqual(self._badge(self.root), 2)   # the change clears the cached count
        self.assertEqual(self._badge(self.alice), 1)
        services.set_status(a2, FeedbackData.IN_PROGRESS)
        self.assertEqual(self._badge(self.alice), 0)


class MigrationTests(TestCase):
    def test_existing_resolved_rows_become_resolved(self):
        from importlib import import_module

        migration = import_module("whiteneuron.feedbacks.migrations.0008_status_assignee")
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        ct = ContentType.objects.get_for_model(Group)
        fb = FeedbackData.objects.create(user=root, content_type=ct, object_id="1", message="m")
        FeedbackData.objects.filter(pk=fb.pk).update(is_resolved=True, status="open")
        from django.apps import apps

        migration.status_from_is_resolved(apps, None)
        fb.refresh_from_db()
        self.assertEqual(fb.status, "resolved")
