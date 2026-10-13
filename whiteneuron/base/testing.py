"""Helpers for the package's own test suite (independent of a project's settings)."""
from django.conf import settings
from django.test import override_settings


def package_test_settings(**extra):
    """URLconf with the admin mounted, and no project-specific Unfold callbacks."""
    unfold = {**getattr(settings, "UNFOLD", {}), "ENVIRONMENT": None}
    return override_settings(ROOT_URLCONF="whiteneuron.base.urls_testing", UNFOLD=unfold, **extra)
