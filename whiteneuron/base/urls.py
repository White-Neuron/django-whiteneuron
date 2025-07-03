from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, re_path
from django.views.static import serve

from .sites import base_admin_site
from .views import HomeView

urlpatterns = []

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
if settings.BROWSER_RELOAD:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    
urlpatterns += [
    # path("", HomeView.as_view(), name="home"),
    # path("i18n/", include("django.conf.urls.i18n")),
]
