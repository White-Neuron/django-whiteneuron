"""#91: background jobs report a heartbeat; the operator sees which one stopped and what follows."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from whiteneuron.monitoring import beat
from whiteneuron.monitoring.heartbeats import LATE, NEVER, OK, DISABLED, late, statuses
from whiteneuron.monitoring.models import Heartbeat

from .testing import package_test_settings

User = get_user_model()

JOBS = {
    "backup": {"label": "Daily backup", "max_age": 3600, "consequence": "No new backup.", "critical": True},
    "scheduler": {"label": "Scheduler", "max_age": 300, "consequence": "Scheduled work is not running."},
    "night_sync": {"label": "Night sync", "max_age": 60, "enabled": False},
}


def _age(name, seconds):
    Heartbeat.objects.update_or_create(name=name, defaults={"last_beat_at": timezone.now() - timedelta(seconds=seconds)})


@override_settings(WN_HEARTBEATS=JOBS)
class HeartbeatStateTests(TestCase):
    def test_states(self):
        self.assertEqual({j["name"]: j["state"] for j in statuses()},
                         {"backup": NEVER, "scheduler": NEVER, "night_sync": DISABLED})
        _age("backup", 10)
        _age("scheduler", 600)
        _age("night_sync", 10_000)
        states = {j["name"]: j["state"] for j in statuses()}
        self.assertEqual(states, {"backup": OK, "scheduler": LATE, "night_sync": DISABLED})
        self.assertEqual(statuses()[0]["name"], "scheduler")  # late first
        self.assertEqual([j["name"] for j in late(critical_only=True)], [])
        _age("backup", 7200)
        self.assertEqual([j["name"] for j in late(critical_only=True)], ["backup"])

    def test_beat_records_listed_names_only_and_never_raises(self):
        self.assertTrue(beat("backup", info="42 files"))
        self.assertEqual(Heartbeat.objects.get(name="backup").info, "42 files")
        self.assertFalse(beat("not-listed"))
        self.assertFalse(Heartbeat.objects.filter(name="not-listed").exists())
        with mock.patch.object(Heartbeat.objects, "update_or_create", side_effect=RuntimeError("db down")):
            self.assertFalse(beat("backup"))

    def test_core_jobs_report_in(self):
        from whiteneuron.monitoring import tasks

        with override_settings(WN_HEARTBEATS={"celery": {"max_age": 300}, "monitoring_collector": {"max_age": 60}}):
            tasks.worker_heartbeat()
            with mock.patch.object(tasks.collector, "snapshot", return_value={}), \
                    mock.patch.object(tasks.collector, "record"):
                tasks.collect_metrics()
        self.assertEqual(set(Heartbeat.objects.values_list("name", flat=True)), {"celery", "monitoring_collector"})


class NoHeartbeatsConfiguredTests(TestCase):
    def test_nothing_changes_without_settings(self):
        self.assertEqual(statuses(), [])
        self.assertFalse(beat("backup"))
        self.assertFalse(Heartbeat.objects.exists())


@package_test_settings(WN_HEARTBEATS=JOBS)
class HeartbeatPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", "r@example.com", "pw")
        cls.staff = User.objects.create_user("staff", "s@example.com", "pw", is_staff=True)

    def setUp(self):
        caches["default"].clear()
        self.addCleanup(caches["default"].clear)
        _age("backup", 7200)  # critical and late

    def test_monitoring_page_lists_the_jobs(self):
        self.client.force_login(self.root)
        html = self.client.get(reverse("admin:monitoring_metricsample_changelist")).content.decode()
        self.assertIn('id="heartbeat-backup" data-state="late"', html)
        self.assertIn('id="heartbeat-scheduler" data-state="never"', html)
        self.assertIn('id="heartbeat-night_sync" data-state="disabled"', html)
        self.assertIn("No new backup.", html)

    def test_home_warns_only_those_who_may_see_monitoring(self):
        self.client.force_login(self.root)
        self.assertContains(self.client.get(reverse("admin:index")), 'id="wn-late-jobs"')
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(reverse("admin:index")), 'id="wn-late-jobs"')

    def test_ready_lists_late_jobs_for_privileged_callers_without_failing(self):
        self.client.force_login(self.root)
        data = self.client.get(reverse("wn_system:ready")).json()
        self.assertEqual([j["name"] for j in data["late_jobs"]], ["backup"])
        self.client.logout()
        caches["default"].clear()
        self.assertNotIn("late_jobs", self.client.get(reverse("wn_system:ready")).json())
