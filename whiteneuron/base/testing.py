"""Helpers for the package's own test suite (independent of a project's settings)."""
from django.test import override_settings


def package_test_settings(**extra):
    """URLconf with the admin mounted. (UNFOLD["ENVIRONMENT"] used to be cleared here: it
    pointed at <PROJECT_NAME>.utils; the core's own callback is now the default.)"""
    return override_settings(ROOT_URLCONF="whiteneuron.base.urls_testing", **extra)
