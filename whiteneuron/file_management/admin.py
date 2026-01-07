from whiteneuron.base.admin import base_admin_site, ModelAdmin
from django.contrib import admin
from unfold.decorators import display
from django.utils.translation import gettext_lazy as _

from .models import ExcelFile, PDFFile

class BaseFileAdmin(ModelAdmin):
    list_display = ("title", "file", "method_view", "status_view", "created_at", "created_by")
    search_fields= ("title", "description")
    filter_horizontal= ()
    list_filter= ("status", "method")
    readonly_fields= ("created_at", "created_by", "updated_at", "updated_by", "status_view", "method_view")
    fieldsets= (
        (_("General Information"), {
            "fields": ("title", "description", 
                       'status_view',
                       'method_view',
                       "file"),
        }),
        (_("Meta"), {
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by')
        }),
    )

@admin.register(ExcelFile, site=base_admin_site)
class ExcelFileAdmin(BaseFileAdmin):
    pass

@admin.register(PDFFile, site=base_admin_site)
class PDFFileAdmin(BaseFileAdmin):
    pass
