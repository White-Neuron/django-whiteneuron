from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import MultipleDropdownFilter
class FieldSelectionFilter(MultipleDropdownFilter):
    title = _('field(s) to display')
    parameter_name = 'display_fields'
    def lookups(self, request, model_admin):
        r= [('default', _('Default fields'))]

        for field_name in model_admin.get_fields(request):
            try:
                r.append((field_name, model_admin.model._meta.get_field(field_name).verbose_name))
            except Exception:
                pass
        return r

    def queryset(self, request, queryset):
        return queryset
        