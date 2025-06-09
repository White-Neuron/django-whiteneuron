"""
ASGI config for wndinehub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import whiteneuron.notification.routing

from dotenv import load_dotenv
from os import environ
load_dotenv()


PROJECT_NAME = environ.get("PROJECT_NAME", "base")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{PROJECT_NAME}.settings")
print(f"ASGI application is using settings from: {os.environ['DJANGO_SETTINGS_MODULE']}")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            whiteneuron.notification.routing.websocket_urlpatterns
        )
    ),
})
