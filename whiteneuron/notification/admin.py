from django.contrib import admin
import ast
import json
import re
from typing import Sequence
from django.contrib.contenttypes.models import ContentType

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
        # "action_by",
        # "display_action",
        # "display_flag",
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

    actions_detail = ["view_obj_link"]

    using_grid_view= False

    @action(description=_("View Linked Object"),
            permissions= ["view_obj_link"],
            url_path="view-obj-link")
    def view_obj_link(self, request, object_id: int):
        obj = get_object_or_404(Notification, pk=object_id)
        if obj.obj_link:
            return redirect(obj.obj_link)
        self.message_user(request, _("No object link available for this notification."))
        return redirect(request.META.get('HTTP_REFERER', 'admin:notification_notification_changeform', args=[object_id]))
    
    def has_view_obj_link_permission(self, request, object_id: int):
        if object_id is not None:
            obj= get_object_or_404(Notification, pk=object_id)
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
    
    def get_components(self, instance: Notification):
        app_label = None
        model_verbose = None
        object_id = None
        obj_str = None
        if instance.obj_link:
            m = re.search(r'/([^/]+)/([^/]+)/(\d+)/change/', instance.obj_link)
            if m:
                app_label = m.group(1)
                raw_model = m.group(2)
                object_id = m.group(3)
                try:
                    ct = ContentType.objects.get(app_label=app_label, model=raw_model)
                    mc = ct.model_class()
                    model_verbose = mc._meta.verbose_name.title()
                    try:
                        manager = getattr(mc, 'objects_all', mc.objects)
                        obj = manager.get(pk=int(object_id))
                        obj_str = str(obj)
                    except Exception:
                        obj_str = f"#{object_id}"
                except Exception:
                    model_verbose = raw_model.replace('_', ' ').title()
                    obj_str = f"#{object_id}"
        return app_label, model_verbose, object_id, obj_str
    
    def display_title(self, instance: Notification):
        # Parse obj_link → extract app_label, model_name, object_id
        app_label, model_verbose, object_id, obj_str = self.get_components(instance)

        _action_cls = {
            'create': 'ui-badge-success',
            'update': 'ui-badge-info',
            'delete': 'ui-badge-error',
            'restore': 'ui-badge-warning',
        }
        action_cls = _action_cls.get(instance.action or '', '')
        action_label = _(instance.action) if instance.action else '—'

        parts = []

        # [Model name]
        if model_verbose:
            parts.append(
                f'<span class="ui-badge ui-badge-xs font-mono opacity-70">'
                f'<strong>{model_verbose}</strong></span>'
            )

        # [#ID] — clickable link
        if object_id:
            if instance.obj_link:
                parts.append(
                    f'<a href="{instance.obj_link}" class="ui-badge ui-badge-xs font-mono">'
                    f'#{object_id}</a>'
                )
            else:
                parts.append(
                    f'<span class="ui-badge ui-badge-xs font-mono">#{object_id}</span>'
                )

        # [Object name]
        if obj_str:
            parts.append(f'<span class="text-sm font-semibold">{obj_str}</span>')

        # [Action]
        parts.append(
            f'<span class="ui-badge ui-badge-xs {action_cls}">{action_label}</span>'
        )

        # by [Alias] [@username]
        if instance.action_by:
            ab = instance.action_by
            alias = getattr(ab, 'full_name', None) or ''
            username = ab.username
            parts.append(f'<span class="text-xs opacity-50">{_("by")}</span>')
            if alias and alias != username:
                parts.append(
                    f'<span class="ui-badge ui-badge-xs">{alias}</span>'
                    f'<span class="ui-badge ui-badge-xs opacity-60">@{username}</span>'
                )
            else:
                parts.append(f'<span class="ui-badge ui-badge-xs">@{username}</span>')

        return mark_safe(
            '<div class="flex flex-wrap items-center gap-1">' + ''.join(parts) + '</div>'
        )
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
    