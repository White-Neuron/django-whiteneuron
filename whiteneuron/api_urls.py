"""All of the package's JSON endpoints, for a project to mount under one prefix:

    path("api/", include("whiteneuron.api_urls")),

gives /api/system/…, /api/notifications/… and /api/announcement/…. Each part can
also be mounted on its own (whiteneuron.base.system_urls,
whiteneuron.notification.api_urls, whiteneuron.notification.announcement_urls).
"""
from django.urls import include, path, re_path

from whiteneuron.base.api_utils import not_found

urlpatterns = [
    path("system/", include("whiteneuron.base.system_urls")),
    path("notifications/", include("whiteneuron.notification.api_urls")),
    path("announcement/", include("whiteneuron.notification.announcement_urls")),
    re_path(r"", not_found),  # any other path under the API: JSON 404, not the HTML page
]
