from django.db import models
from django.utils.translation import gettext_lazy as _


class MetricSample(models.Model):
    """One snapshot of a host's resource usage.

    I/O counters are stored as cumulative values (as the OS reports them);
    per-second rates are derived from consecutive samples of the same host.
    """

    timestamp = models.DateTimeField(_("timestamp"), db_index=True)
    host = models.CharField(_("host"), max_length=128)

    # CPU
    cpu_percent = models.FloatField(_("CPU %"))
    cpu_count = models.PositiveSmallIntegerField(_("CPU cores"), default=1)
    load_1 = models.FloatField(_("load 1m"), null=True, blank=True)
    load_5 = models.FloatField(_("load 5m"), null=True, blank=True)
    load_15 = models.FloatField(_("load 15m"), null=True, blank=True)

    # Memory
    mem_total = models.BigIntegerField(_("memory total"))
    mem_used = models.BigIntegerField(_("memory used"))
    mem_percent = models.FloatField(_("memory %"))
    swap_percent = models.FloatField(_("swap %"), default=0)

    # Disk (root filesystem) + cumulative I/O
    disk_total = models.BigIntegerField(_("disk total"))
    disk_used = models.BigIntegerField(_("disk used"))
    disk_percent = models.FloatField(_("disk %"))
    disk_read_bytes = models.BigIntegerField(_("disk read bytes"), default=0)
    disk_write_bytes = models.BigIntegerField(_("disk write bytes"), default=0)

    # Network (cumulative)
    net_sent_bytes = models.BigIntegerField(_("network sent bytes"), default=0)
    net_recv_bytes = models.BigIntegerField(_("network received bytes"), default=0)

    # Processes
    process_count = models.PositiveIntegerField(_("processes"), default=0)
    proc_rss = models.BigIntegerField(_("app memory (RSS)"), default=0)
    proc_threads = models.PositiveIntegerField(_("app threads"), default=0)
    boot_time = models.DateTimeField(_("boot time"), null=True, blank=True)

    # Dependencies
    db_latency_ms = models.FloatField(_("database latency (ms)"), null=True, blank=True)
    cache_latency_ms = models.FloatField(_("cache latency (ms)"), null=True, blank=True)

    extra = models.JSONField(_("extra"), default=dict, blank=True)  # e.g. per-core CPU

    class Meta:
        db_table = "monitoring_metric_samples"
        verbose_name = _("server metric")
        verbose_name_plural = _("server monitoring")
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["host", "timestamp"], name="monitoring_host_ts_idx")]

    def __str__(self):
        return f"{self.host} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"
