from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import MultipleDropdownFilter
class FieldSelectionFilter(MultipleDropdownFilter):
    title = _('field(s) to display')
    parameter_name = 'display_fields'
    def lookups(self, request, model_admin):
        # Built from model metadata (get_fields() instantiated a ModelForm on every
        # changelist render). Many-to-many fields can't be list_display columns.
        excluded = set(model_admin.exclude or ())
        r= [('default', _('Default fields'))]
        for field in model_admin.model._meta.concrete_fields:
            if field.editable and not field.auto_created and field.name not in excluded:
                r.append((field.name, field.verbose_name))
        return r

    def queryset(self, request, queryset):
        return queryset
        