"""All of the package's JSON endpoints, for a project to mount under one prefix:

    path("api/v1/", include("whiteneuron.api_urls")),

gives /api/v1/system/…, /api/v1/notifications/… and /api/v1/announcement/… (the version
is the mount prefix, see the README's "Versioning"). Each part can
also be mounted on its own (whiteneuron.base.system_urls,
whiteneuron.notification.api_urls, whiteneuron.notification.announcement_urls).
"""
from django.urls import include, path

urlpatterns = [
    path("system/", include("whiteneuron.base.system_urls")),
    path("notifications/", include("whiteneuron.notification.api_urls")),
    path("announcement/", include("whiteneuron.notification.announcement_urls")),
    # No catch-all here: projects mount their own api/… routes next to this one, and a
    # catch-all would answer them with a 404. Each group above ends with its own (#88 review).
]
