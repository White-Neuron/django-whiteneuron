from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whiteneuron.base"
    verbose_name = _("Base")
