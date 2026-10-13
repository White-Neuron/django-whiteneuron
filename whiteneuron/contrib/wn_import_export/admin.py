from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse

from import_export.admin import ImportExportModelAdmin as DefaultImportExportModelAdmin
from unfold.contrib.import_export.forms import ImportForm, ExportForm

from whiteneuron.file_management.models import ExcelFile

from .tasks import export
from whiteneuron.base.queue import enqueue


def _export_selected_action(modeladmin, request, queryset):
    """Admin action (Django calls actions as func(modeladmin, request, queryset))."""
    return modeladmin._export_selected_items(request, queryset)


class ImportExportModelAdmin(DefaultImportExportModelAdmin):
    import_form_class = ImportForm
    export_form_class = ExportForm

    def has_import_permission(self, request):
        return request.user.is_superuser

    def has_export_permission(self, request):
        return request.user.username != 'guest'

    def export_action(self, request): # Custom export action to export all items with my custom export function
        return self._export_selected_items(request, queryset=None)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "export_selected_items" not in actions and self.has_export_permission(request):
            actions["export_selected_items"] = (_export_selected_action, "export_selected_items", _("Export selected records"))
        return actions

    def _export_selected_items(self, request, queryset=None):
        if queryset is None:
            title = f"Export all {self.model._meta.verbose_name_plural}"
            queryset = self.get_export_queryset(request)
        else:
            title = f"Export selected {self.model._meta.verbose_name_plural}"
        ids = list(queryset.values_list("pk", flat=True))
        file = ExcelFile(title=title,
                         description=format_html(
                             "<p>User: {}</p><p>Exported at: {}</p><p>Model: {}</p><p>IDs: {}... (Total: {})</p>",
                             request.user, timezone.now(), self.model._meta.verbose_name_plural, ids[:10], len(ids)),
                         status='pending',
                         method='auto',
                         # exports contain table data: private to the requesting user (and superusers)
                         is_public=False,
                         created_by=request.user,
                         updated_by=request.user)
        file.save()
        file.allowed_users.add(request.user)
        applabel = self.model._meta.app_label
        modelname = self.model._meta.model_name
        # Call export task .delay to run in background
        file_name = f"{self.model._meta.verbose_name_plural}.xlsx"
        # worker (after commit, so it sees the ExcelFile row) or inline without Celery
        enqueue(export, file.id, applabel, modelname, ids, file_name=file_name)

        # Thêm thông báo thành công
        messages.success(request, format_html(
            "Export is in progress. You can download the file when it's ready <a class='underline font-semibold text-primary-600' href='{}'>here</a>.",
            reverse('admin:file_management_excelfile_change', args=[file.id])))

        # Redirect về lại trang admin
        return HttpResponseRedirect(
            reverse(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist'))