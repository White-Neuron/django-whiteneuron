"""URLconf for the package test suite (projects provide their own)."""
from django.urls import include, path

from .sites import base_admin_site
from .urls import urlpatterns as base_urlpatterns

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", base_admin_site.urls),
    path("feedbacks/", include("whiteneuron.feedbacks.urls")),
    path("files/", include("whiteneuron.file_management.urls")),
    *base_urlpatterns,
]
