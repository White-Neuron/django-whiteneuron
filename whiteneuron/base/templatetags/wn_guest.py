from django import template

from ..utils import get_guest_user

register = template.Library()


@register.simple_tag
def guest_login_available():
    """Whether "Log in as guest" can work: GuestLoginView needs an active staff ``guest`` account."""
    return get_guest_user() is not None
