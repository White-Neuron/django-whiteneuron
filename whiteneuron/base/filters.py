from django.contrib.admin.utils import flatten_fieldsets
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import MultipleDropdownFilter

# Never offered as list columns: the change form masks them (e.g. the password hash
# widget), a changelist cell would print the raw value.
SENSITIVE_FIELDS = frozenset({"password"})


def _change_form_fields(request, model_admin):
    """Field names on the *change* form of ``model_admin``.

    ``get_fieldsets(request, None)`` would be the add form (e.g. UserAdmin's
    add_fieldsets), so an unsaved instance stands in for "an object". If the admin's
    layout code can't handle it, fall back to the default list columns only.
    """
    try:
        return flatten_fieldsets(model_admin.get_fieldsets(request, model_admin.model()))
    except Exception:
        return [f for f in model_admin.list_display if isinstance(f, str)]


class FieldSelectionFilter(MultipleDropdownFilter):
    title = _('field(s) to display')
    parameter_name = 'display_fields'

    def lookups(self, request, model_admin):
        """Columns the user may pick: only fields the admin itself exposes.

        Taken from the change form layout (flattened ``get_fieldsets()``), so
        ``fields``, ``fieldsets`` and ``exclude`` all apply — ``get_fields()``
        alone ignores ``fieldsets``. Memoized per request because the changelist
        calls it several times. ``ModelAdmin.field_selection_exclude`` hides more.
        """
        cache = request.__dict__.setdefault('_wn_field_choices', {}) if request is not None else {}
        key = model_admin  # the object itself (an id() could be reused after GC)
        if key not in cache:
            excluded = SENSITIVE_FIELDS | set(getattr(model_admin, 'field_selection_exclude', ()) or ())
            choices = [('default', _('Default fields'))]
            for name in _change_form_fields(request, model_admin):
                if not isinstance(name, str) or name in excluded:
                    continue
                try:
                    field = model_admin.model._meta.get_field(name)
                except FieldDoesNotExist:
                    continue  # admin-only/readonly callables aren't model columns
                if field.many_to_many or not field.concrete:
                    continue  # can't be list_display columns
                choices.append((name, field.verbose_name))
            cache[key] = choices
        return cache[key]

    def queryset(self, request, queryset):
        return queryset
