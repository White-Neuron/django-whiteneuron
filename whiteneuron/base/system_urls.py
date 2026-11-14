from django.urls import path

from . import system

app_name = "wn_system"

urlpatterns = [
    path("version/", system.version_view, name="version"),
    path("health/", system.health_view, name="health"),
    path("ready/", system.ready_view, name="ready"),
    path("info/", system.info_view, name="info"),
]
