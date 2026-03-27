from django.contrib import admin
import ast
import json
from typing import Sequence

from whiteneuron.base.admin import base_admin_site
from whiteneuron.base.admin import ModelAdmin
from .models import NotificationConfig, Notification
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from unfold.decorators import action, display

@admin.register(NotificationConfig, site=base_admin_site)
class NotificationConfigAdmin(ModelAdmin):
    list_display = ('model', 'event_type', 'send_to_admin', 'send_to_user', 'send_to_group_user')
    search_fields = ('model__model', 'event_type')
    list_filter = ('event_type', 'send_to_admin', 'send_to_user', 'send_to_group_user')
    ordering = ('-id',)

    conditional_fields= {
        'group_users': "send_to_group_user == true",
        'users': "send_to_user == true",
    }

    autocomplete_fields = ('users', 'group_users')

    fieldsets = (
        (None, {
            'fields': ('model', 'event_type')
        }),
        (_('Notification Recipients'), {
            'fields': ('send_to_admin', 'send_to_user', 'users', 'send_to_group_user', 'group_users'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('model')
    
@admin.register(Notification, site=base_admin_site)
class NotificationAdmin(ModelAdmin):
    list_display = [
        # "user",
        "display_title",
        "action_by",
        "display_action",
        "display_flag",
        "is_read",
        "created_at",
    ]
    autocomplete_fields = [ "user", "action_by"]
    search_fields = [
        "user__username",
        "title",
        "content",
        "action_by__username",
    ]
    list_filter = [
        "action_by",
        "is_read",
        "created_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            _("Notification information"),
            {
                "fields": (
                    "user",
                    "action_by",
                    'obj_link',
                    "action",
                    "flag", 
                    "display_title",
                    "display_content",
                    "display_changed_data",
                    "is_read", 
                    "created_at",
                ),
            },
        ),
    )

    actions_submit_line = ["view_obj_link"]

    @action(description=_("View"), permissions= ["view_obj_link"])
    def view_obj_link(self, request, obj):
        return redirect(obj.obj_link)
    
    def has_view_obj_link_permission(self, request, obj=None):
        if obj is not None:
            obj= get_object_or_404(Notification, pk=obj)
            if obj.obj_link:
                return True
        return False
    
    def has_add_permission(self, request):
        # if request.user.is_superuser:
        #     return True
        return False
    
    def has_change_permission(self, request, obj=None):
        # if request.user.is_superuser:
        #     return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        # if request.user.is_superuser:
        #     return True
        return False
    
    # Chỉ hiện thông báo của user đang đăng nhập
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # if request.user.is_superuser:
        #     return qs
        return qs.filter(user=request.user)
    
    # Cập nhật đã đọc khi xem chi tiết
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            obj = get_object_or_404(Notification, pk=object_id)
            if not obj.is_read and obj.user == request.user:
                obj.is_read = True
                obj.save()
        except:
            pass
        return super().changeform_view(request, object_id=object_id, form_url=form_url, extra_context=extra_context)
    
    def get_list_filter(self, request: HttpRequest) -> Sequence[str]:
        list_filter = super().get_list_filter(request)
        if request.user.is_superuser:
            return list(list_filter) + ['user']
        return list_filter
    
    @display(description=_("Content"), header=True)
    def display_content(self, instance: Notification):
        return mark_safe(instance.content)

    @display(description=_("Action"), label=True)
    def display_action(self, instance: Notification):
        return instance.action
    
    @display(description=_("Flag"), label=True)
    def display_flag(self, instance: Notification):
        return instance.flag
    
    def display_title(self, instance: Notification):
        return mark_safe(f"{instance.title}")
    display_title.short_description = _("Title")
    
    def display_changed_data(self, instance: Notification):
        if instance.changed_data:
            changed_data = None
            try:
                changed_data = json.loads(instance.changed_data)
            except json.JSONDecodeError:
                # Backward compatibility for old rows saved with str(list/dict)
                try:
                    changed_data = ast.literal_eval(instance.changed_data)
                except (ValueError, SyntaxError):
                    return instance.changed_data

            if isinstance(changed_data, dict):
                html = "<ul>"
                for field, changes in changed_data.items():
                    old_value = changes.get("old", "") if isinstance(changes, dict) else ""
                    new_value = changes.get("new", "") if isinstance(changes, dict) else ""
                    html += format_html(
                        "<li><strong>{}:</strong> {} → {}</li>",
                        field,
                        old_value,
                        new_value,
                    )
                html += "</ul>"
                return mark_safe(html)

            if isinstance(changed_data, list):
                html = "<ul>"
                for row in changed_data:
                    if not isinstance(row, dict):
                        continue
                    html += format_html(
                        "<li><strong>{}:</strong> {} → {}</li>",
                        row.get("field_name", ""),
                        row.get("old_value", ""),
                        row.get("new_value", ""),
                    )
                html += "</ul>"
                return mark_safe(html)

            return str(changed_data)
        return _("No changes")
    display_changed_data.short_description = _("Changed Data")
    