from django.contrib import admin
import ast
import json
import re
from typing import Sequence
from django.contrib.contenttypes.models import ContentType

from whiteneuron.base.admin import base_admin_site
from whiteneuron.base.admin import ModelAdmin
from .models import NotificationConfig, Notification
from .utils import clear_unread_cache
from django.contrib import messages
from django.utils.translation import gettext_lazy as _, ngettext
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from unfold.contrib.filters.admin import AutocompleteSelectFilter
from unfold.decorators import action, display

from whiteneuron.base.html_sanitize import is_safe_href, sanitize_html

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
        "display_flag",
        "display_read",
        "created_at",
    ]
    autocomplete_fields = [ "user", "action_by"]
    search_fields = [
        "user__username",
        "title",
        "content",
        "action_by__username",
    ]
    list_select_related = ["action_by"]
    list_filter = [
        "is_read",
        "action",
        "flag",
        ("action_by", AutocompleteSelectFilter),
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

    actions = ["mark_selected_read", "mark_selected_unread"]
    actions_list = ["mark_all_read"]
    actions_detail = ["view_obj_link", "mark_unread"]

    using_grid_view= False

    @action(description=_("View Linked Object"),
            permissions= ["view_obj_link"],
            url_path="view-obj-link")
    def view_obj_link(self, request, object_id: int):
        obj = get_object_or_404(Notification, pk=object_id, user=request.user)
        if obj.obj_link and url_has_allowed_host_and_scheme(obj.obj_link, allowed_hosts={request.get_host()}):
            return redirect(obj.obj_link)
        self.message_user(request, _("No object link available for this notification."))
        return redirect(reverse('admin:notification_notification_changeform', args=[object_id]))
    
    # Read state. Each changes only the user's own rows (get_queryset) and clears the badge cache.
    @admin.action(description=_("Mark selected notifications as read"))
    def mark_selected_read(self, request, queryset):
        self._set_read(request, queryset, True)

    @admin.action(description=_("Mark selected notifications as unread"))
    def mark_selected_unread(self, request, queryset):
        self._set_read(request, queryset, False)

    def _set_read(self, request, queryset, value):
        updated = queryset.filter(user=request.user).exclude(is_read=value).update(is_read=value)
        clear_unread_cache(request.user.pk)
        message = (ngettext("%(count)d notification marked as read.", "%(count)d notifications marked as read.", updated)
                   if value else
                   ngettext("%(count)d notification marked as unread.", "%(count)d notifications marked as unread.", updated))
        self.message_user(request, message % {"count": updated}, messages.SUCCESS)

    # A dialog, so the change is a POST (a plain list action is a GET link)
    @action(description=_("Mark all as read"), url_path="mark-all-read", icon="done_all",
            dialog={"title": _("Mark all notifications as read?"), "form_submit_text": _("Mark all as read")})
    def mark_all_read(self, request, form):
        self._set_read(request, Notification.objects.filter(user=request.user), True)
        return redirect(reverse("admin:notification_notification_changelist"))

    # Opening a notification marks it read; this puts it back
    @action(description=_("Mark as unread"), url_path="mark-unread", icon="mark_email_unread",
            dialog={"title": _("Mark this notification as unread?"), "form_submit_text": _("Mark as unread")})
    def mark_unread(self, request, form, object_id):
        self._set_read(request, Notification.objects.filter(pk=object_id, user=request.user), False)
        return redirect(reverse("admin:notification_notification_changelist"))

    def has_view_obj_link_permission(self, request, object_id: int):
        if object_id is not None and str(object_id).isdigit():
            return Notification.objects.filter(pk=object_id, user=request.user, obj_link__isnull=False).exclude(obj_link='').exists()
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
        # anyone may delete their own notifications (get_queryset shows no others)
        if not request.user.is_authenticated:
            return False
        return obj is None or obj.user_id == request.user.pk

    def get_actions(self, request):
        actions = super().get_actions(request)
        # a notification is the user's own copy: no trash, restore or duplicate
        for name in ("hard_delete", "restore", "duplicate_objects"):
            actions.pop(name, None)
        return actions

    # Deleting one's own notification is not news for the superusers: no _notify_bulk here
    def delete_model(self, request, obj):
        obj.delete()
        clear_unread_cache(obj.user_id)

    def delete_queryset(self, request, queryset):
        queryset.filter(user=request.user).delete()
        clear_unread_cache(request.user.pk)
    
    # Chỉ hiện thông báo của user đang đăng nhập
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # if request.user.is_superuser:
        #     return qs
        return qs.filter(user=request.user)
    
    # Cập nhật đã đọc khi xem chi tiết
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if object_id and str(object_id).isdigit():
            # mark as read with a single UPDATE (non-numeric ids fall through to the admin's 404 handling)
            if Notification.objects.filter(pk=object_id, user=request.user, is_read=False).update(is_read=True):
                clear_unread_cache(request.user.pk)
        return super().changeform_view(request, object_id=object_id, form_url=form_url, extra_context=extra_context)
    
    def get_list_filter(self, request: HttpRequest) -> Sequence[str]:
        list_filter = super().get_list_filter(request)
        if request.user.is_superuser:
            return list(list_filter) + [('user', AutocompleteSelectFilter)]
        return list_filter
    
    @display(description=_("Content"), header=True)
    def display_content(self, instance: Notification):
        # stored HTML may predate escaping: keep only simple formatting tags
        return mark_safe(sanitize_html(instance.content))

    # A label, not the boolean icon: a red ✗ on every unread row read as "error" (#81)
    @display(description=_("Status"), ordering="is_read", label={"unread": "info", "read": "default"})  # read: neutral grey
    def display_read(self, instance: Notification):
        return ("read", _("Read")) if instance.is_read else ("unread", _("Unread"))

    @display(description=_("Action"), label=True)
    def display_action(self, instance: Notification):
        return instance.action
    
    @display(description=_("Flag"), label={"info": "info", "success": "success", "warning": "warning",
                                            "error": "danger", "danger": "danger"})
    def display_flag(self, instance: Notification):
        return instance.flag, instance.get_flag_display()  # colour by value, translated text
    
    _OBJ_LINK_RE = re.compile(r'/([^/]+)/([^/]+)/(\d+)/change/')

    @classmethod
    def _parse_obj_link(cls, obj_link):
        m = cls._OBJ_LINK_RE.search(obj_link or '')
        return (m.group(1), m.group(2), m.group(3)) if m else None

    @classmethod
    def resolve_components(cls, notifications):
        """Attach (app_label, model_verbose, object_id, obj_str) to each notification.

        Linked objects are fetched with one query per model for the whole page,
        instead of a ContentType + object query for every row.
        """
        wanted = {}
        for n in notifications:
            parsed = cls._parse_obj_link(n.obj_link)
            if parsed:
                wanted.setdefault(parsed[:2], set()).add(int(parsed[2]))
        found = {}
        for (app_label, raw_model), ids in wanted.items():
            try:
                mc = ContentType.objects.get_by_natural_key(app_label, raw_model).model_class()
            except ContentType.DoesNotExist:
                mc = None
            if mc is None:
                found[(app_label, raw_model)] = (raw_model.replace('_', ' ').title(), {})
                continue
            manager = getattr(mc, 'objects_all', mc._default_manager)
            try:
                objs = {o.pk: str(o) for o in manager.filter(pk__in=ids)}
            except Exception:
                objs = {}
            found[(app_label, raw_model)] = (mc._meta.verbose_name.title(), objs)
        for n in notifications:
            parsed = cls._parse_obj_link(n.obj_link)
            if not parsed:
                n._wn_components = (None, None, None, None)
                continue
            app_label, raw_model, object_id = parsed
            model_verbose, objs = found[(app_label, raw_model)]
            n._wn_components = (app_label, model_verbose, object_id, objs.get(int(object_id), f"#{object_id}"))

    def get_components(self, instance: Notification):
        if not hasattr(instance, '_wn_components'):
            self.resolve_components([instance])
        return instance._wn_components

    _changelist_classes = {}

    def get_changelist(self, request, **kwargs):
        base = super().get_changelist(request, **kwargs)
        cls = self._changelist_classes.get(base)
        if cls is None:  # built once per base class, not per request
            class NotificationChangeList(base):
                def get_results(self, request):
                    super().get_results(request)
                    self.model_admin.resolve_components(list(self.result_list))

            cls = self._changelist_classes[base] = NotificationChangeList
        return cls

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
            parts.append(format_html(
                '<span class="ui-badge ui-badge-xs font-mono opacity-70"><strong>{}</strong></span>', model_verbose))

        # [#ID] — clickable link (only same-site paths)
        if object_id:
            if instance.obj_link and instance.obj_link.startswith("/") and is_safe_href(instance.obj_link):
                parts.append(format_html(
                    '<a href="{}" class="ui-badge ui-badge-xs font-mono">#{}</a>', instance.obj_link, object_id))
            else:
                parts.append(format_html('<span class="ui-badge ui-badge-xs font-mono">#{}</span>', object_id))

        # [Object name]
        if obj_str:
            parts.append(format_html('<span class="text-sm font-semibold">{}</span>', obj_str))

        # [Action]
        parts.append(format_html('<span class="ui-badge ui-badge-xs {}">{}</span>', action_cls, action_label))

        # by [Alias] [@username]
        if instance.action_by:
            ab = instance.action_by
            alias = getattr(ab, 'full_name', None) or ''
            username = ab.username
            parts.append(format_html('<span class="text-xs opacity-50">{}</span>', _("by")))
            if alias and alias != username:
                parts.append(format_html(
                    '<span class="ui-badge ui-badge-xs">{}</span><span class="ui-badge ui-badge-xs opacity-60">@{}</span>',
                    alias, username))
            else:
                parts.append(format_html('<span class="ui-badge ui-badge-xs">@{}</span>', username))

        return format_html('<div class="flex flex-wrap items-center gap-1">{}</div>', mark_safe(''.join(parts)))
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
    