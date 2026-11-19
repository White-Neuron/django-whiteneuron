from django.urls import path, re_path

from whiteneuron.base.api_utils import not_found

from . import api

app_name = "wn_announcement"

urlpatterns = [
    path("", api.announcement, name="detail"),
    path("seen/", api.announcement_seen, name="seen"),
    re_path(r"", not_found),  # JSON 404 for the rest (e.g. a non-numeric id)
]
