from django.urls import path, re_path

from . import system
from .api_utils import not_found

app_name = "wn_system"

urlpatterns = [
    path("version/", system.version_view, name="version"),
    path("health/", system.health_view, name="health"),
    path("ready/", system.ready_view, name="ready"),
    path("info/", system.info_view, name="info"),
    re_path(r"", not_found),
]
