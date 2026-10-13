from django import template
from django.conf import settings

from whiteneuron.base.themes import DAISYUI_THEMES

register = template.Library()


@register.simple_tag
def wn_admin_themes():
    """daisyUI themes offered in the admin theme picker.

    ``WN_ADMIN_THEMES`` (list of names) limits the choice; by default every theme
    compiled into base/css/styles.css is offered. "light"/"dark" are handled by
    the Light/Dark/System switch and are not listed.
    """
    names = getattr(settings, "WN_ADMIN_THEMES", None)
    if names is None:  # [] means "no daisyUI themes in the picker"
        names = DAISYUI_THEMES.keys()
    return [
        {"name": name, "label": name.capitalize(), "scheme": DAISYUI_THEMES[name]}
        for name in names
        if name in DAISYUI_THEMES and name not in ("light", "dark")
    ]
