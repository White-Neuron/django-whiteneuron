"""#33: the channel layer's Redis URL (CACHE_REDIS_LOCATION or CHANNEL_REDIS_URL)."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

URLS = {
    "auth and db": "redis://:secret@redis:6380/2",
    "no port": "redis://redis",
    "tls": "rediss://:secret@managed.example:6380/0",
    "user and password": "redis://default:secret@redis:6379/1",
}


def channel_layers(**env):
    """CHANNEL_LAYERS of the core settings imported with ``env`` (a fresh process: settings
    read the environment at import)."""
    base = {k: v for k, v in os.environ.items()
            if k not in ("USE_CACHE", "CACHENAME", "CACHE_REDIS_LOCATION", "CHANNEL_REDIS_URL")}
    base.update(PYTHONPATH=str(Path(__file__).resolve().parents[2]), DEBUG="True", **env)
    with tempfile.TemporaryDirectory() as scripts:
        script = Path(scripts, "manage.py")
        script.write_text("import json, whiteneuron.base.settings as s\nprint(json.dumps(s.CHANNEL_LAYERS))\n")
        out = subprocess.run([sys.executable, str(script)], cwd=scripts, env=base,
                             capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


class ChannelLayerUrlTests(SimpleTestCase):
    def test_cache_url_is_passed_whole_and_keeps_password_db_and_tls(self):
        from channels_redis.core import RedisChannelLayer
        from channels_redis.utils import create_pool

        for label, url in URLS.items():
            with self.subTest(label):
                layers = channel_layers(USE_CACHE="True", CACHENAME="redis", CACHE_REDIS_LOCATION=url)
                config = layers["default"]
                self.assertEqual(config["BACKEND"], "channels_redis.core.RedisChannelLayer")
                self.assertEqual(config["CONFIG"]["hosts"], [url])
                # what channels_redis connects with (no connection is opened)
                host = RedisChannelLayer(**config["CONFIG"]).hosts[0]
                kwargs = create_pool(host).connection_kwargs
                if "secret" in url:
                    self.assertEqual(kwargs["password"], "secret")
                if url.endswith("/2"):
                    self.assertEqual(kwargs["db"], 2)
                if url.startswith("rediss://"):
                    self.assertEqual(create_pool(host).connection_class.__name__, "SSLConnection")

    def test_channel_redis_url_overrides_the_cache(self):
        layers = channel_layers(USE_CACHE="True", CACHENAME="redis", CACHE_REDIS_LOCATION="redis://cache:6379/0",
                                CHANNEL_REDIS_URL="redis://channels:6379/3")
        self.assertEqual(layers["default"]["CONFIG"]["hosts"], ["redis://channels:6379/3"])

    def test_channel_redis_url_without_a_redis_cache(self):
        # WebSockets over Redis while the cache stays local
        layers = channel_layers(USE_CACHE="False", CHANNEL_REDIS_URL="redis://channels:6379/3")
        self.assertEqual(layers["default"]["BACKEND"], "channels_redis.core.RedisChannelLayer")
        self.assertEqual(layers["default"]["CONFIG"]["hosts"], ["redis://channels:6379/3"])

    def test_in_memory_without_redis(self):
        layers = channel_layers(USE_CACHE="False")
        self.assertEqual(layers["default"]["BACKEND"], "channels.layers.InMemoryChannelLayer")
