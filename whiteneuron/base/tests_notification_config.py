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
        self._config("update", users=[self.watcher, self.kt1])
        self.watcher.is_active = False
        self.watcher.save()
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.kt1.pk})

    def test_a_config_that_reaches_nobody_keeps_the_superusers(self):
        # notifications are also the change history: never write zero rows (#102 review)
        self._config("update")                                   # every box off
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.root.pk, self.root2.pk})
        caches["default"].clear()
        NotificationConfig.objects.all().delete()
        empty = Group.objects.create(name="Empty")
        self._config("update", groups=[empty])                   # a group without members
        self.assertEqual(recipients_for(FeedbackData, "update"), {self.root.pk, self.root2.pk})

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


@package_test_settings()
class HistoryWithManyRecipientsTests(TestCase):
    def test_fifty_means_fifty_events_whatever_the_number_of_recipients(self):
        root = User.objects.create_superuser("root", "r@example.com", "pw")
        group = Group.objects.create(name="Everyone")
        users = User.objects.bulk_create([User(username=f"u{i}", email=f"u{i}@example.com") for i in range(120)])
        group.user_set.add(*users)
        config = NotificationConfig.objects.create(model=ContentType.objects.get_for_model(User),
                                                   event_type="update", send_to_admin=True, send_to_group_user=True)
        config.group_users.set([group])
        caches["default"].clear()
        url = reverse("admin:base_user_change", args=[root.pk])
        with self.captureOnCommitCallbacks(execute=False):
            for i in range(10):
                Notification.notify_superusers(title=f"change {i}", action="update", obj_link=url, model=User)
        self.assertEqual(Notification.objects.filter(obj_link=url).count(), 10 * 121)
        self.client.force_login(root)
        titles = [n.title for n in self.client.get(url).context["history_notifications"]]
        self.assertEqual(sorted(titles), sorted(f"change {i}" for i in range(10)))


class OneEventOneTimestampTests(TestCase):
    """A flaky failure of the history test (1 in 11 runs): the copies of one event got their
    own timestamps and could straddle a second."""

    def test_every_copy_of_an_event_has_the_same_timestamp(self):
        from unittest import mock
        from datetime import timedelta

        from django.utils import timezone

        users = User.objects.bulk_create([User(username=f"s{i}", email=f"s{i}@example.com", is_superuser=True)
                                          for i in range(5)])
        base = timezone.now().replace(microsecond=999_000)
        ticks = iter(base + timedelta(milliseconds=i) for i in range(100))   # crosses a second
        with mock.patch("django.utils.timezone.now", side_effect=lambda: next(ticks)), \
                self.captureOnCommitCallbacks(execute=False):
            objs = Notification.notify_superusers(title="t", action="update")
        stamps = set(Notification.objects.filter(pk__in=[o.pk for o in objs]).values_list("created_at", flat=True))
        self.assertEqual(len(objs), len(users))
        self.assertEqual(len(stamps), 1)
