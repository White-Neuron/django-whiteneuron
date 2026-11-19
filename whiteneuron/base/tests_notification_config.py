"""#36: the "Notifications config" screen had no effect; every notification went to every
superuser."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from whiteneuron.feedbacks.models import FeedbackData
from whiteneuron.notification.models import Notification, NotificationConfig, recipients_for

from .testing import package_test_settings

User = get_user_model()


class RecipientsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.root2 = User.objects.create_superuser("root2", "r2@example.com", "pw")
        cls.accountants = Group.objects.create(name="Kế toán")
        cls.kt1 = User.objects.create_user("kt1", "k1@example.com", "pw")
        cls.kt2 = User.objects.create_user("kt2", "k2@example.com", "pw")
        cls.kt1.groups.add(cls.accountants)
        cls.kt2.groups.add(cls.accountants)
        cls.watcher = User.objects.create_user("watcher", "w@example.com", "pw")
        cls.ct = ContentType.objects.get_for_model(FeedbackData)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)

    def _config(self, event, admin=False, users=(), groups=()):
        config = NotificationConfig.objects.create(
            model=self.ct, event_type=event, send_to_admin=admin,
            send_to_user=bool(users), send_to_group_user=bool(groups))
        config.users.set(users)
        config.group_users.set(groups)
        return config

    def test_without_config_every_superuser_as_before(self):
        for action in ("create", "update", "delete", "restore", None):
            self.assertEqual(recipients_for(FeedbackData, action), {self.root.pk, self.root2.pk})
        self.assertEqual(recipients_for(None, "update"), {self.root.pk, self.root2.pk})

    def test_update_to_a_group_only(self):
        self._config("update", groups=[self.accountants])
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.kt1.pk, self.kt2.pk})
        self.assertEqual(recipients_for(FeedbackData, "restore"), {self.kt1.pk, self.kt2.pk})
        # other events of the model keep the default
        self.assertEqual(recipients_for(FeedbackData, "create"), {self.root.pk, self.root2.pk})

    def test_admin_users_and_groups_add_up(self):
        self._config("delete", admin=True, users=[self.watcher], groups=[self.accountants])
        self.assertEqual(recipients_for(FeedbackData, "delete"),
                         {self.root.pk, self.root2.pk, self.watcher.pk, self.kt1.pk, self.kt2.pk})

    def test_all_covers_every_event_and_combines_with_a_specific_one(self):
        self._config("all", users=[self.watcher])
        self._config("create", groups=[self.accountants])
        for action in ("update", "delete"):
            self.assertEqual(recipients_for(FeedbackData, action), {self.watcher.pk})
        self.assertEqual(recipients_for(FeedbackData, "create"), {self.watcher.pk, self.kt1.pk, self.kt2.pk})

    def test_inactive_users_are_skipped(self):
        self._config("update", users=[self.watcher])
        self.watcher.is_active = False
        self.watcher.save()
        self.assertEqual(recipients_for(FeedbackData, "update"), set())

    def test_changing_the_config_takes_effect_at_once(self):
        config = self._config("update", users=[self.watcher])
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.watcher.pk})  # cached now
        config.users.add(self.kt1)
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.watcher.pk, self.kt1.pk})
        config.delete()
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.root.pk, self.root2.pk})

    def test_notify_follows_the_config(self):
        self._config("update", groups=[self.accountants])
        with self.captureOnCommitCallbacks(execute=False):
            Notification.notify_superusers(title="t", action="update", model=FeedbackData)
        self.assertEqual(set(Notification.objects.values_list("user_id", flat=True)), {self.kt1.pk, self.kt2.pk})


@package_test_settings()
class HistoryWithoutSuperuserCopiesTests(TestCase):
    def test_history_panel_reads_any_recipient_and_shows_each_event_once(self):
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        group = Group.objects.create(name="Kế toán")
        for name in ("kt1", "kt2"):
            User.objects.create_user(name, f"{name}@example.com", "pw").groups.add(group)
        config = NotificationConfig.objects.create(model=ContentType.objects.get_for_model(User),
                                                   event_type="update", send_to_admin=False, send_to_group_user=True)
        config.group_users.set([group])
        caches["default"].clear()
        url = reverse("admin:base_user_change", args=[root.pk])
        with self.captureOnCommitCallbacks(execute=False):
            Notification.notify_superusers(title="changed once", action="update", obj_link=url, model=User)
        self.assertFalse(Notification.objects.filter(user=root).exists())
        self.client.force_login(root)
        response = self.client.get(url)
        self.assertEqual(len(response.context["history_notifications"]), 1)
