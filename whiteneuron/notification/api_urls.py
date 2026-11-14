from django.urls import path

from . import api

app_name = "wn_notifications"

urlpatterns = [
    path("", api.notification_list, name="list"),
    path("unread-count/", api.notification_unread_count, name="unread_count"),
    path("read-all/", api.notification_read_all, name="read_all"),
    path("<int:pk>/", api.notification_detail, name="detail"),
    path("<int:pk>/read/", api.notification_read, name="read"),
    path("<int:pk>/unread/", api.notification_unread, name="unread"),
]
