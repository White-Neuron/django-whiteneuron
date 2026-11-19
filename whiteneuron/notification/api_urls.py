from django.urls import path, re_path

from whiteneuron.base.api_utils import not_found

from . import api

app_name = "wn_notifications"

urlpatterns = [
    path("", api.notification_list, name="list"),
    path("unread-count/", api.notification_unread_count, name="unread_count"),
    path("read-all/", api.notification_read_all, name="read_all"),
    path("<int:pk>/", api.notification_detail, name="detail"),
    path("<int:pk>/read/", api.notification_read, name="read"),
    path("<int:pk>/unread/", api.notification_unread, name="unread"),
    re_path(r"", not_found),  # JSON 404 for the rest (e.g. a non-numeric id)
]
