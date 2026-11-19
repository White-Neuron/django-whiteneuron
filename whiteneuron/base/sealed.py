"""Detail actions that apply to the version of the record the user saw (#93 b).

    class OrderAdmin(ModelAdmin):
        actions_detail = ["approve"]

        @action(description=_("Approve"), url_path="approve", dialog={...})
        @sealed(version=lambda obj: obj.updated_at.isoformat())
        def approve(self, request, form, object_id): ...

The change page adds a signed token to the action's URL (for this user, this record, this
action and this version, valid ``WN_ACTION_SEAL_MAX_AGE`` seconds). When the action runs, a
missing, forged or expired token, or a record changed since the page was opened (by someone
else, or in another tab), is refused with a message and a redirect back to the record.

``ModelAdmin.get_action_url_params(request, obj, action_name)`` is the public hook that adds
the token; override it to add parameters of your own.
"""
import functools

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _

SEAL_PARAM = "wn_seal"
SEAL_SALT = "whiteneuron.sealed-action"
DEFAULT_MAX_AGE = 3600


def max_age():
    return int(getattr(settings, "WN_ACTION_SEAL_MAX_AGE", DEFAULT_MAX_AGE))


def seal_version(func):
    """The ``version`` callable of a sealed action (through unfold's @action wrapper), or None."""
    return getattr(func, "_wn_seal_version", None)


def make_seal(request, obj, action_name, version):
    return signing.dumps(
        {"u": request.user.pk, "o": str(obj.pk), "a": action_name, "v": str(version(obj))},
        salt=SEAL_SALT, compress=True,
    )


def check_seal(request, obj, action_name, version):
    """None when the token matches this user, record, action and the record's current version;
    else the message to show."""
    token = request.GET.get(SEAL_PARAM, "")
    try:
        data = signing.loads(token, salt=SEAL_SALT, max_age=max_age())
    except signing.SignatureExpired:
        return _("The page was open too long. Reload it, then decide again.")
    except signing.BadSignature:
        return _("This action needs the page it was opened from. Reload the page, then decide again.")
    if data.get("u") != request.user.pk or data.get("o") != str(obj.pk) or data.get("a") != action_name:
        return _("This action needs the page it was opened from. Reload the page, then decide again.")
    if data.get("v") != str(version(obj)):
        return _("The content has changed since you opened the page. Review it, then decide again.")
    return None


def sealed(version):
    """Refuse a detail action unless the record is still the version shown when the page opened.

    ``version(obj)`` returns something that changes whenever the record does
    (``obj.updated_at.isoformat()``, a hash of the fields that matter, ...)."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(model_admin, request, *args, **kwargs):
            object_id = kwargs.get("object_id")
            obj = model_admin.get_object(request, object_id) if object_id is not None else None
            if obj is not None:
                problem = check_seal(request, obj, func.__name__, version)
                if problem:
                    model_admin.message_user(request, problem, messages.ERROR)
                    opts = model_admin.model._meta
                    return HttpResponseRedirect(
                        reverse(f"{model_admin.admin_site.name}:{opts.app_label}_{opts.model_name}_change",
                                args=[obj.pk]))
            return func(model_admin, request, *args, **kwargs)

        wrapper._wn_seal_version = version
        return wrapper

    return decorator
