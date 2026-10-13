"""
ASGI config for wndinehub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from dotenv import load_dotenv
from os import environ
load_dotenv()

PROJECT_NAME = environ.get("PROJECT_NAME", "base")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{PROJECT_NAME}.settings")

from django.core.asgi import get_asgi_application

# Initialise Django (apps registry) before importing anything that touches models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
import whiteneuron.notification.routing  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # reject cross-site websocket connections (Origin must match ALLOWED_HOSTS)
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                whiteneuron.notification.routing.websocket_urlpatterns
            )
        )
    ),
})
