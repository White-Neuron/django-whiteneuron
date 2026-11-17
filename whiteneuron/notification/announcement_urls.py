from django.urls import path

from . import api

app_name = "wn_announcement"

urlpatterns = [
    path("", api.announcement, name="detail"),
    path("seen/", api.announcement_seen, name="seen"),
]
