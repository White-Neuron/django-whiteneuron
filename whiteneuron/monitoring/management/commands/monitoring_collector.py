import signal
import time

from django.core.management.base import BaseCommand

from whiteneuron.monitoring import collector


class Command(BaseCommand):
    help = "Collect server metrics for the monitoring dashboard (run one per host, e.g. as a systemd service)."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=None, help="Seconds between samples (default: WN_MONITORING['INTERVAL']).")
        parser.add_argument("--once", action="store_true", help="Store a single sample and exit.")

    def handle(self, *args, interval=None, once=False, **options):
        interval = interval or int(collector.conf("INTERVAL"))
        running = True

        def stop(*_):
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        self.stdout.write(f"Collecting metrics for {collector.host_name()} every {interval}s")
        while running:
            started = time.monotonic()
            try:
                # cpu_interval=1 measures CPU over one second instead of since the last call
                collector.record(collector.snapshot(cpu_interval=1), force=True, interval=interval)
                collector.beat(interval=interval)
            except Exception as exc:  # keep the collector alive (DB restart, etc.)
                self.stderr.write(f"collect failed: {exc}")
            if once:
                break
            # sleep in short steps so SIGTERM stops the collector promptly
            while running and time.monotonic() - started < interval:
                time.sleep(0.5)
