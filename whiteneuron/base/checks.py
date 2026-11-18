from django.conf import settings
from django.core import checks


@checks.register(checks.Tags.urls)
def untracked_url_names_check(app_configs=None, **kwargs):
    """A name in WN_UNTRACKED_URL_NAMES that does not reverse is skipped without a word, so a
    typo keeps a polling endpoint logged. The package's own names may be
    unmounted on purpose; a project's own list should all resolve."""
    from django.urls import NoReverseMatch, reverse

    missing = []
    for name in getattr(settings, "WN_UNTRACKED_URL_NAMES", None) or ():
        try:
            reverse(name)
        except NoReverseMatch:
            missing.append(name)
        except Exception:  # URLconf not importable: Django's own URL checks report it
            return []
    if not missing:
        return []
    return [checks.Warning(
        f"WN_UNTRACKED_URL_NAMES lists URL names that are not in the URLconf: {', '.join(missing)}.",
        hint="Check the spelling and the namespace (e.g. \"app:name\"). The name must be a URL "
             "without arguments: matching is by fixed path, so a pattern like <int:pk> never "
             "applies. Requests to these endpoints are still logged.",
        id="whiteneuron.W002",
    )]
