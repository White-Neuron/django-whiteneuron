"""Tags for the error pages (400/403/404/429/500, CSRF): the project's name and links, never
the package's own (#46)."""
from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def wn_site_name():
    """``UNFOLD["SITE_TITLE"]``, else ``NAME``, else "Admin"."""
    title = (getattr(settings, "UNFOLD", None) or {}).get("SITE_TITLE")
    return str(title or getattr(settings, "NAME", "") or "Admin")


@register.simple_tag
def wn_home_url():
    """``WN_HOME_URL``, else the admin index, else "/": a link that exists in every project
    (many mount nothing at "/")."""
    url = getattr(settings, "WN_HOME_URL", None)
    if url:
        return url
    from django.urls import NoReverseMatch, reverse

    try:
        return reverse("admin:index")
    except NoReverseMatch:
        return "/"


@register.simple_tag
def wn_support_url():
    """``WN_SUPPORT_URL`` (a page or a mailto: link), or "" for no "Contact support" button."""
    return getattr(settings, "WN_SUPPORT_URL", "") or ""
