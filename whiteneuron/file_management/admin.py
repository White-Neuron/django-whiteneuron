from whiteneuron.base.admin import base_admin_site, ModelAdmin
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminFileFieldWidget

from .models import ExcelFile, PDFFile, compute_file_hash


class FileInputNoDownload(UnfoldAdminFileFieldWidget):
    """Unfold-styled file widget with the download button removed."""
    template_name = "file_management/widgets/clearable_file_input_no_download.html"

class BaseFileAdmin(ModelAdmin):
    file_type = None  # Set in subclasses: 'excel' | 'pdf'
    accepted_file_types = None  # e.g. '.xlsx,.xls' — passed as HTML accept attribute

    list_display = ("title", "method_view", "status_view", "created_at", "created_by")
    search_fields = ("title", "description")
    filter_horizontal = ()
    list_filter = ("status", "method")
    readonly_fields = (
        "created_at", "created_by", "updated_at", "updated_by",
        "status_view", "method_view", "integrity_status", "verified_download",
        "hash_display", "current_hash_display",
    )
    # fieldsets is intentionally omitted — get_fieldsets() handles all cases dynamically.

    def _get_current_hash(self, obj, request=None):
        """Compute the current SHA-256 hash of the file on storage. No caching — always fresh."""
        try:
            return compute_file_hash(obj.file)
        except Exception:
            return None

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == 'file' and field is not None:
            attrs = dict(field.widget.attrs)
            if self.accepted_file_types:
                attrs['accept'] = self.accepted_file_types
            field.widget = FileInputNoDownload(attrs=attrs)
        return field

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if obj and obj.method == 'auto':
            readonly = tuple(readonly) + ('file',)
        return readonly

    def get_fieldsets(self, request, obj=None):
        # For auto-method files: replace editable 'file' with 'verified_download'.
        # For upload-method files: show 'file' widget (for replacing) + verified_download link.
        # For new objects (no pk): only show 'file' upload widget.
        if obj and obj.method == 'auto':
            file_fields = ('verified_download',)
        elif obj and obj.pk:
            file_fields = ('file', 'verified_download')
        else:
            file_fields = ('file',)
        integrity_fields = ('integrity_status', 'hash_display', 'current_hash_display') if (obj and obj.pk) else ()
        return (
            (_('General Information'), {
                'fields': ('title', 'description',
                           'status_view',
                           'method_view',
                           *file_fields,
                           *integrity_fields),
            }),
            (_("Meta"), {
                'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')
            }),
        )

    def integrity_status(self, obj):
        if not obj.pk or not obj.hash:
            return mark_safe('<span style="color: #aaa;">—</span>')
        current = self._get_current_hash(obj)
        if current is None:
            return format_html('<span style="color: #dd4b39;">⚠ {}</span>', _('Cannot read file'))
        if current == obj.hash:
            return mark_safe('<span style="color: #00a65a; font-weight: bold;">✓ OK</span>')
        return format_html('<span style="color: #dd4b39; font-weight: bold;">✗ {}</span>', _('File has been modified'))
    integrity_status.short_description = _('Integrity')

    def hash_display(self, obj):
        if not obj.pk or not obj.hash:
            return mark_safe('<span style="color: #aaa;">—</span>')
        return format_html(
            '<code style="font-family: monospace; font-size: 0.85em; word-break: break-all;">{}</code>',
            obj.hash
        )
    hash_display.short_description = _('Stored hash')

    def current_hash_display(self, obj):
        if not obj.pk or not obj.file or not obj.file.name:
            return mark_safe('<span style="color: #aaa;">—</span>')
        current = self._get_current_hash(obj)
        if current is None:
            return format_html('<span style="color: #dd4b39;">⚠ {}</span>', _('Cannot read file from storage'))
        color = '#dd4b39' if (obj.hash and current != obj.hash) else '#aaa'
        return format_html(
            '<code style="font-family: monospace; font-size: 0.85em; word-break: break-all; color: {};">{}</code>',
            color, current
        )
    current_hash_display.short_description = _('Current hash (live)')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and obj.hash and obj.file and obj.file.name:
            current = self._get_current_hash(obj)
            if current is None:
                messages.error(request, _('Cannot read the file from storage. It may have been deleted externally.'))
            elif current != obj.hash:
                messages.error(
                    request,
                    _('File integrity check failed: the file on storage does not match its stored hash. '
                      'It may have been tampered with or corrupted.')
                )
        return super().change_view(request, object_id, form_url, extra_context)

    def verified_download(self, obj):
        if not obj.pk or not self.file_type:
            return mark_safe('<span style="color: #aaa;">—</span>')
        url = reverse('file_management_download', kwargs={'file_type': self.file_type, 'pk': obj.pk})
        current = self._get_current_hash(obj)
        if current is None:
            return format_html(
                '<span class="ui-badge ui-badge-error gap-1">'
                '<span class="material-symbols-outlined" style="font-size: 14px;">error</span>'
                '{}'
                '</span>',
                _('File missing')
            )
        if obj.hash and current != obj.hash:
            return format_html(
                '<span class="ui-badge ui-badge-error gap-1">'
                '<span class="material-symbols-outlined" style="font-size: 14px;">gpp_bad</span>'
                '{}'
                '</span>',
                _('Tampered — download blocked')
            )
        return format_html(
            '<a href="{}" target="_blank" class="ui-btn ui-btn-primary ui-btn-sm gap-1">'
            '<span class="material-symbols-outlined" style="font-size: 16px;">download</span>'
            '{}'
            '</a>',
            url, _('Download (Verified)')
        )
    verified_download.short_description = _('Verified Download')

    # file nào do ai tạo thì mới thấy, admin xem tất
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by=request.user)


@admin.register(ExcelFile, site=base_admin_site)
class ExcelFileAdmin(BaseFileAdmin):
    file_type = 'excel'
    accepted_file_types = '.xlsx,.xls,.csv'


@admin.register(PDFFile, site=base_admin_site)
class PDFFileAdmin(BaseFileAdmin):
    file_type = 'pdf'
    accepted_file_types = '.pdf'
