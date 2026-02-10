from django.conf import settings
from pathlib import Path
import json
import os
from django.core.management.commands.runserver import Command as RunserverCommand

TARGETS_FILE = getattr(settings, "PROM_TARGETS_FILE", "D:/obs/targets.json")
APP_NAME = getattr(settings, "PROM_APP_NAME", "unknown-app")

class Command(RunserverCommand):
    help = "Runserver with Prometheus auto-register"

    def inner_run(self, *args, **options):
        # Create directory if not exists
        target_path = Path(TARGETS_FILE)
        if not target_path.parent.exists():
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[OBS] Could not create directory {target_path.parent}: {e}"))

        self.register_target()
        super().inner_run(*args, **options)

    def register_target(self):
        port = self.port
        host = "host.docker.internal"

        entry = {
            "targets": [f"{host}:{port}"],
            "labels": {
                "app": APP_NAME
            }
        }

        # load existing
        if os.path.exists(TARGETS_FILE):
            with open(TARGETS_FILE, "r") as f:
                data = json.load(f)
        else:
            data = []

        # tránh duplicate
        if entry not in data:
            data.append(entry)

        with open(TARGETS_FILE, "w") as f:
            json.dump(data, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(
                f"[OBS] Registered {APP_NAME} on {host}:{port}"
            )
        )
