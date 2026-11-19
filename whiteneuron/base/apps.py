from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "whiteneuron.base"
    verbose_name = _("Base")

    def ready(self):
        from . import checks  # noqa: F401 (registers the system checks)
        from django.db.models.signals import post_migrate

        from .roles import sync_roles_after_migrate

        # WN_ROLES: set each role group back to its declared permissions after every migrate
        post_migrate.connect(sync_roles_after_migrate, dispatch_uid="whiteneuron_sync_roles")
