from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class FileManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whiteneuron.file_management"
    verbose_name = _("File Management")
