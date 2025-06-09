from django.contrib import admin
from typing import Sequence

from whiteneuron.base.admin import base_admin_site
from whiteneuron.base.admin import ModelAdmin
from .models import NotificationConfig, Notification
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpRequest
from django.utils.safestring import mark_safe
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
        "title",
        "display_action",
        "display_flag",
        "is_read",
        "created_at",
    ]
    autocomplete_fields = [ "user" ]
    search_fields = [
        "user__username",
        "title",
        "content",
    ]
    list_filter = [
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
                    "action",
                    "flag", 
                    "title",
                    "display_content",
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
    