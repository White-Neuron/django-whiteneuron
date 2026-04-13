from django.urls import path

from .views import download_file

urlpatterns = [
    path('download/<str:file_type>/<int:pk>/', download_file, name='file_management_download'),
]
