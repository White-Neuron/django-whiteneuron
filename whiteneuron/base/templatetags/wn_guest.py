import logging

from django import template

from ..utils import get_guest_user

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag(takes_context=True)
def guest_login_available(context):
    """Whether "Log in as guest" can work here: GuestLoginView redirects authenticated
    users without logging them in, and needs an active staff ``guest`` account."""
    # RequestContext.request survives {% include ... only %} and a missing request context processor
    request = getattr(context, "request", None) or context.get("request")
    if request is None or request.user.is_authenticated:
        return False
    try:
        return get_guest_user() is not None
    except Exception:  # an optional button must never break the login page
        logger.exception("Guest user lookup failed")
        return False
