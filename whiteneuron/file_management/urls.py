from django.urls import path

from .views import download_file, preview_file

urlpatterns = [
    path('download/<str:file_type>/<int:pk>/', download_file, name='file_management_download'),
    path('preview/<str:file_type>/<int:pk>/', preview_file, name='file_management_preview'),
]
