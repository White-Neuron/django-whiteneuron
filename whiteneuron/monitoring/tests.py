import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from whiteneuron.base.models import UserActivity

from . import collector, stats
from .models import MetricSample


def _sample(ts, **overrides):
    data = dict(
        timestamp=ts, host="h1", cpu_percent=10, cpu_count=4, mem_total=100, mem_used=50, mem_percent=50,
        disk_total=100, disk_used=10, disk_percent=10, disk_read_bytes=0, disk_write_bytes=0,
        net_sent_bytes=0, net_recv_bytes=0,
    )
    data.update(overrides)
    return MetricSample.objects.create(**data)


class HelpersTests(TestCase):
    def test_percentile_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(stats.percentile(values, 50), 50)
        self.assertEqual(stats.percentile(values, 95), 95)
        self.assertEqual(stats.percentile(values, 100), 100)
        self.assertIsNone(stats.percentile([], 95))

    def test_normalize_path_groups_ids(self):
        self.assertEqual(stats.normalize_path("/admin/base/user/12/change/"), "/admin/base/user/:id/change/")
        self.assertEqual(
            stats.normalize_path("/api/x/0f8fad5b-d9cb-469f-a165-70867728950e"), "/api/x/:id"
        )
        self.assertEqual(stats.normalize_path("/api/v2/items/"), "/api/v2/items/")

    def test_parse_range_falls_back(self):
        self.assertEqual(stats.parse_range("nope"), (stats.DEFAULT_RANGE, stats.RANGES[stats.DEFAULT_RANGE]))


@override_settings(WN_MONITORING={"INTERVAL": 10, "RETENTION_DAYS": 1, "DISK_PATH": "/", "HOST": "h1"})
class SeriesTests(TestCase):
    def test_counter_rates_and_reset(self):
        now = timezone.now()
        _sample(now - datetime.timedelta(seconds=30), net_recv_bytes=1000)
        _sample(now - datetime.timedelta(seconds=20), net_recv_bytes=2000)   # +1000 / 10s
        _sample(now - datetime.timedelta(seconds=10), net_recv_bytes=500)    # reboot: reset
        series = stats.system_series("h1", 300)
        rates = [r for r in series["net_recv_bytes"] if r is not None]
        self.assertEqual(rates, [100.0])

    def test_prune_removes_old_samples(self):
        _sample(timezone.now() - datetime.timedelta(days=3))
        _sample(timezone.now())
        self.assertEqual(collector.prune(), 1)
        self.assertEqual(MetricSample.objects.count(), 1)

    def test_snapshot_has_model_fields(self):
        data = collector.snapshot()
        self.assertEqual(data["host"], "h1")
        self.assertTrue(0 <= data["cpu_percent"] <= 100)
        MetricSample.objects.create(**data)  # every key is a model field


class RequestStatsTests(TestCase):
    def test_summary_and_endpoints(self):
        user = get_user_model().objects.create_user("u", password="x")
        for ms, status in [(100, 200), (200, 200), (300, 500), (3000, 200)]:
            UserActivity.objects.create(
                user=user, path="/a/1/", method="GET", status_code=status,
                timelapse=datetime.timedelta(milliseconds=ms),
            )
        result = stats.request_stats(3600)
        summary = result["summary"]
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["error_rate"], 25.0)
        self.assertEqual(summary["p50"], 200.0)
        self.assertEqual(summary["apdex"], 0.75)  # 3 satisfied (<= 500 ms), 1 frustrated (> 2 s)
        self.assertEqual(result["top_endpoints"][0]["path"], "/a/:id/")


class DashboardViewTests(TestCase):
    def setUp(self):
        # cached VisitProfile ids from other tests point at rolled-back rows
        from django.core.cache import cache
        cache.clear()
        User = get_user_model()
        self.admin = User.objects.create_superuser("root", "r@x.io", "pw")
        self.staff = User.objects.create_user("staff", password="pw", is_staff=True)

    def test_dashboard_and_api_for_superuser(self):
        self.client.force_login(self.admin)
        page = self.client.get(reverse("admin:monitoring_metricsample_changelist"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'id="wn-monitoring"')
        api = self.client.get(reverse("admin:monitoring_metricsample_api"), {"range": "15m"})
        self.assertEqual(api.status_code, 200)
        body = api.json()
        self.assertEqual(body["range"], "15m")
        self.assertIn("cpu_percent", body["live"])
        self.assertEqual(MetricSample.objects.count(), 1)  # the dashboard records a sample

    def test_staff_without_permission_is_denied(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("admin:monitoring_metricsample_api")).status_code, 403)
