from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, re_path
from django.views.static import serve

from .sites import base_admin_site
from .views import HomeView, GuestLoginView, get_announcement_content

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
    path("", HomeView.as_view(), name="home"),
    path("base/guest-login/", GuestLoginView.as_view(), name="guest_login"),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path("file-management/", include('whiteneuron.file_management.urls')),
    path("announcement/", get_announcement_content, name="announcement"),
]
