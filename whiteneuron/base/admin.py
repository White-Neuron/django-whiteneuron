import types as _types
from typing import Sequence
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.admin import GenericTabularInline
from django.core.validators import EMPTY_VALUES
from django.db import models
from django.db.models import OuterRef, Q, Sum
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import path, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from guardian.admin import GuardedModelAdmin
from import_export.admin import (
    ExportActionModelAdmin,
    ImportExportModelAdmin,
)
from modeltranslation.admin import TabbedTranslationAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateFilter,
    RangeNumericFilter,
    RelatedDropdownFilter,
    SingleNumericFilter,
    TextFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget as UnfoldWysiwygWidget
from whiteneuron.base.widgets import WysiwygWidget
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.contrib.inlines.admin import NonrelatedStackedInline
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm
from django.contrib.auth.forms import UserCreationForm

from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultiple,
    UnfoldAdminColorInputWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSplitDateTimeWidget,
    UnfoldAdminTextInputWidget,
)

from .models import User, Tag, UserActivity, UserProfile, App, IPBlacklist, UABlacklist
from .sites import base_admin_site
from django.utils.safestring import mark_safe

from django.templatetags.static import static

from .modeladmin import ModelAdmin

admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(Group)

class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


@admin.register(PeriodicTask, site=base_admin_site)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule, site=base_admin_site)
class IntervalScheduleAdmin(ModelAdmin):
    pass


@admin.register(CrontabSchedule, site=base_admin_site)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    pass


@admin.register(SolarSchedule, site=base_admin_site)
class SolarScheduleAdmin(ModelAdmin):
    pass


@admin.register(ClockedSchedule, site=base_admin_site)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    pass

class TagGenericTabularInline(TabularInline, GenericTabularInline):
    model = Tag

from .utils import send_email_login, make_random_password
class UserCreationForm(UserCreationForm):
    # password is not required
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        self.fields['email'].required = True

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields

@admin.register(User, site=base_admin_site)
class UserAdmin(BaseUserAdmin, ModelAdmin):

    grid_view= True
    grid_exclude_fields_list_display= ['display_created', 
                                       "first_name",
                                       "last_name", 'is_active', 
                                       'display_staff', 'display_superuser', 'display_header']

    def grid_item_header(self, obj):
        if obj.is_bot:
            avatar_content = '<span class="material-symbols-outlined" style="font-size: 80px; line-height: 1;">smart_toy</span>'
        elif not obj.avatar:
            avatar_content = '<span class="material-symbols-outlined" style="font-size: 80px; line-height: 1;">person</span>'
        else:
            avatar_content = f'''
            <div class="w-full h-full rounded-2xl overflow-hidden bg-base-300/50 dark:bg-base-700/50 ring-1 ring-base-content/10 dark:ring-base-content/20">
                <img src="{obj.avatar.url}" class="w-full h-full object-cover hover:scale-105 transition-transform duration-300"/>
            </div>
            '''
        
        # Status badges với dark mode support
        badges = []
        if obj.is_active:
            badges.append(f'<span class="ui-badge ui-badge-success ui-badge-xs gap-1"><span class="w-1.5 h-1.5 bg-success dark:bg-success-300 rounded-full animate-pulse"></span>{_("Active")}</span>')
        else:
            badges.append(f'<span class="ui-badge ui-badge-error ui-badge-xs gap-1"><span class="w-1.5 h-1.5 bg-error dark:bg-error-300 rounded-full"></span>{_("Inactive")}</span>')
        
        if obj.is_staff:
            badges.append(f'<span class="ui-badge ui-badge-info ui-badge-xs">{_("Staff")}</span>')
        
        if obj.is_superuser:
            badges.append(f'<span class="ui-badge ui-badge-warning ui-badge-xs">{_("Admin")}</span>')
        
        badges_html = ' '.join(badges)
        
        # Tên đầy đủ hoặc fallback
        display_name = obj.full_name or obj.username or _('Unknown User')
        username_display = f'{obj.username}' if obj.username else _('No username')

        role= ""
        if obj.is_superuser:
            role= f'<span class="material-symbols-outlined text-warning" style="font-size:18px" title="{_("Superuser")}">admin_panel_settings</span>'
        elif obj.is_staff:
            role= f'<span class="material-symbols-outlined text-info" style="font-size:18px" title="{_("Staff")}">badge</span>'
        elif obj.is_bot:
            role= f'<span class="material-symbols-outlined text-secondary" style="font-size:18px" title="{_("Bot")}">smart_toy</span>'
        
        # Compact vertical card layout với dark mode support
        string = f"""
<div class="ui-card bg-base-100 dark:bg-base-800 hover:bg-base-200/60 dark:hover:bg-base-700/60 shadow-lg hover:shadow-xl dark:shadow-base-content/10 transition-all duration-300 border border-base-300 dark:border-base-600 hover:border-primary/30 dark:hover:border-primary/50 group w-full">
    <!-- Avatar Section -->
    <figure class="p-3 flex items-center justify-center bg-gradient-to-br from-base-200/50 to-base-300/30 dark:from-base-700/50 dark:to-base-800/30 relative overflow-hidden">
        <!-- Background pattern -->
        <div class="absolute inset-0 bg-gradient-to-br from-transparent via-base-content/[0.02] dark:via-base-content/[0.05] to-transparent"></div>
        <div class="w-20 h-20 relative group-hover:scale-110 transition-transform duration-300 z-10 flex items-center justify-center">
            {avatar_content}
        </div>
        <!-- Glow effect -->
        <div class="absolute inset-0 bg-gradient-to-br from-primary/5 dark:from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
    </figure>

    <div class="ui-card-body py-3 px-4 pb-6 text-center">
        <h5>{display_name}</h5>
        <p class="ui-card-title justify-center text-xs">{username_display}</p>
        <div class="flex flex-wrap items-center justify-center gap-2 mt-3">
        {f'<span class="material-symbols-outlined text-success" style="font-size:18px" title="{_("Active")}">check_circle</span>' if obj.is_active else f'<span class="material-symbols-outlined text-error" style="font-size:18px" title="{_("Inactive")}">cancel</span>'}
        {role}
        </div>

    </div>
</div>
"""
        return mark_safe(string)
    grid_item_header.short_description = "Header"

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    # inlines = [TagGenericTabularInline]
    list_display = [
        "display_header",
        "first_name",
        "last_name",
        "is_active",
        "display_staff",
        "display_superuser",
        "display_created",
    ]

    add_fieldsets = (
        (
            None, 
            {"fields": (
                "username",  # "username" is not in the original User model
                "email",
            # "password1",
            # "password2",
            )}),
        (
            _("Personal info"),
            {
                "fields": (("first_name", "last_name"), "avatar", "biography"), 
                "classes": ["tab"],}
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_bot",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ["tab"],
            },
        ),
    )

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal info"),
            {
                "fields": (("first_name", "last_name"), "email", "avatar", "biography"),
                "classes": ["tab"],
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_bot",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ["tab"],
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login", "date_joined"),
                "classes": ["tab"],
            },
        ),
    )
    filter_horizontal = (
        "groups",
        "user_permissions",
    )
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        models.DateTimeField: {
            "widget": UnfoldAdminSplitDateTimeWidget,
        },
    }
    readonly_fields = ["last_login", "date_joined"]

    @display(description=_("User"))
    def display_header(self, instance: User):
        return instance.display_header()
    
    @display(description=_("Avatar"), image=True)
    def display_avatar(self, instance: User):
        return instance.display_avatar()

    @display(description=_("Staff"), boolean=True)
    def display_staff(self, instance: User):
        return instance.is_staff

    @display(description=_("Superuser"), boolean=True)
    def display_superuser(self, instance: User):
        return instance.is_superuser

    @display(description=_("Created"))
    def display_created(self, instance: User):
        return instance.date_joined
    
    # tự tạo mật khẩu mặc định cho user mới và gửi email thông báo
    def save_model(self, request: HttpRequest, obj, form, change: bool) -> None:
        if not obj.pk:
            # random password
            password = make_random_password()
            # send email
            s= send_email_login(obj.username, password, obj.email)
            if s == False: 
                # messages.error(request, 'Gửi email thông báo mật khẩu thất bại! Hãy đổi mật khẩu để người dùng có thể đăng nhập.')
                messages.error(request, _("Failed to send email notification! Please change the password so that the user can log in."))
            else:
                # messages.success(request, f'Đã gửi email thông báo mật khẩu, vui lòng kiểm tra hộp thư đến {obj.email}!')
                messages.success(request, _("Email notification has been sent, please check your inbox!"))
            super().save_model(request, obj, form, change)
            obj.set_password(password) # để sau super().save_model
            obj.save()

        else:
            super().save_model(request, obj, form, change) 


@admin.register(UserActivity, site=base_admin_site)
class UserActivityAdmin(ModelAdmin):
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(_("IP address"))
    user_agent = models.TextField(_("User agent"))
    path = models.CharField(_("Path"), max_length=255)
    method = models.CharField(_("Method"), max_length=10, choices=[("GET", "GET"), ("POST", "POST")])
    data = models.JSONField(_("Data"), null=True, blank=True)
    status_code = models.IntegerField(_("Status code"))
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
    timelapse = models.DurationField(_("Timelapse")) # Thời gian thực hiện hành động
    """

    compressed_fields = True
    using_grid_view = False

    list_display = [
        "user",
        "ip_address",
        "path",
        "method",
        "status_code",
        "timestamp",
    ]
    search_fields = [
        "user__username",
        "ip_address",
        "path",
    ]
    list_filter = [
        "status_code",
        "method",
        "timestamp",
    ]
    date_hierarchy = "timestamp"

    fieldsets = (
        (
            _("Client information"),
            {
                "fields": (
                    ("user", "ip_address",),
                    "user_agent",
                ),
            },
        ),
        (
            _("Request information"),
            {
                "fields": (
                    "path",
                    "method",
                    "data",
                    "status_code",
                ),
            },
        ),
    )
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

    @action(description=_("Block IP address"))
    def block_ip(self, request, queryset):
        blocked = []
        skipped = []
        for activity in queryset:
            if not activity.ip_address:
                continue
            obj, created = IPBlacklist.objects.get_or_create(
                ip_address=activity.ip_address,
                defaults={
                    'reason': f'Blocked from UserActivity by {request.user}',
                    'created_by': request.user,
                    'is_active': True,
                },
            )
            if not created and not obj.is_active:
                obj.is_active = True
                obj.reason = f'Re-blocked from UserActivity by {request.user}'
                obj.save()
            blocked.append(activity.ip_address)
        if blocked:
            messages.success(request, _(f"Blocked {len(blocked)} IP(s): {', '.join(set(blocked))}"))
        if skipped:
            messages.warning(request, _(f"{len(skipped)} activity records had no IP address."))

    actions = ['block_ip']


@admin.register(IPBlacklist, site=base_admin_site)
class IPBlacklistAdmin(ModelAdmin):
    compressed_fields = True
    list_display = ['ip_address', 'is_active_display', 'reason', 'blocked_until', 'created_at', 'created_by']
    search_fields = ['ip_address', 'reason']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'created_by']
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('Target'), {
            'fields': ('ip_address', 'reason'),
        }),
        (_('Block settings'), {
            'fields': ('is_active', 'blocked_until'),
        }),
        (_('Meta'), {
            'fields': ('created_at', 'created_by'),
        }),
    )

    @display(label=True, boolean=True, description=_("Active"))
    def is_active_display(self, obj):
        return obj.is_active

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @action(description=_("Activate selected IPs"))
    def activate(self, request, queryset):
        for obj in queryset:
            obj.is_active = True
            obj.save()
        messages.success(request, _("Selected IPs have been activated."))

    @action(description=_("Deactivate selected IPs"))
    def deactivate(self, request, queryset):
        for obj in queryset:
            obj.is_active = False
            obj.save()
        messages.success(request, _("Selected IPs have been deactivated."))

    actions = ['activate', 'deactivate']


@admin.register(UABlacklist, site=base_admin_site)
class UABlacklistAdmin(ModelAdmin):
    compressed_fields = True
    list_display = ['pattern', 'is_regex', 'is_active_display', 'reason', 'created_at', 'created_by']
    search_fields = ['pattern', 'reason']
    list_filter = ['is_active', 'is_regex']
    readonly_fields = ['created_at', 'created_by']
    date_hierarchy = 'created_at'

    fieldsets = (
        (_('Target'), {
            'fields': ('pattern', 'is_regex', 'reason'),
        }),
        (_('Block settings'), {
            'fields': ('is_active',),
        }),
        (_('Meta'), {
            'fields': ('created_at', 'created_by'),
        }),
    )

    @display(label=True, boolean=True, description=_("Active"))
    def is_active_display(self, obj):
        return obj.is_active

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @action(description=_("Activate selected patterns"))
    def activate(self, request, queryset):
        for obj in queryset:
            obj.is_active = True
            obj.save()
        messages.success(request, _("Selected UA patterns have been activated."))

    @action(description=_("Deactivate selected patterns"))
    def deactivate(self, request, queryset):
        for obj in queryset:
            obj.is_active = False
            obj.save()
        messages.success(request, _("Selected UA patterns have been deactivated."))

    actions = ['activate', 'deactivate']


@admin.register(Group, site=base_admin_site)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(request, extra_context=extra_context)
    

# User Profile

@admin.register(UserProfile, site=base_admin_site)
class UserProfileAdmin(ModelAdmin):
    change_form_template= 'admin/base/userprofile_change_form.html'
    readonly_fields = ['email']
    fieldsets = (
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email', 'avatar', 'biography')
        }),
    )
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        if obj is not None and obj == request.user:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context= None):
        # redirect to change_view of current user
        extra_context = {}
        extra_context['show_save_as_new']= False
        extra_context['show_save_and_add_another']= False
        extra_context['show_save_and_continue']= False
        return super().changeform_view(request, object_id=str(request.user.pk), extra_context=extra_context, form_url='')
    
    def get_fieldsets(self, request: HttpRequest, obj: None) -> list[tuple[str, dict]]:
        fieldsets = super().get_fieldsets(request, obj)
        if obj == request.user and request.user.is_superuser:
            # Thêm ,
            # (_('Configuration'), {
            #     'fields': ('show_softdelete',)
            # })
            fieldsets = list(fieldsets)  # Convert to list to modify
            print(fieldsets)
            fieldsets.insert(1, (_('Configuration'),
                {
                    'fields': ('show_softdelete',)
                }
            ))
        return fieldsets

from .models import Image
@admin.register(Image, site=base_admin_site)
class ImageAdmin(ModelAdmin):
    change_form_template = 'admin/base/image_change_form.html'
    list_display = ['image', 'imgThumbnail', 'description']
    search_fields = ['image', 'description']
    readonly_fields = ['imgThumbnail']
    fieldsets = (
        (_('Image info'), {
            'fields': ('image', 'description')
        }),
    )

    def copy_code(self, obj):
        # Trả về thông tin cần sao chép
        return obj.innerHTML()
    
    # Thêm nút sao chép vào trang chỉnh sửa
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            obj = self.get_object(request, object_id)
            extra_context['copy_code'] = self.copy_code(obj)
        return super(ImageAdmin, self).changeform_view(request, object_id, form_url, extra_context)

from .models import Mail
from django.utils.html import format_html

@admin.register(Mail, site=base_admin_site)
class MailAdmin(ModelAdmin):
    list_display = ['subject', 'receiver', 'status', 'created_at']
    search_fields = ['subject', 'receiver', 'status']
    readonly_fields = ['content', 'status', 'created_at', 'updated_at', 'preview_email']
    list_filter = ['status']
    fieldsets = (
        (_('Mail info'), {
            'fields': ('subject', 'preview_email', 'receiver', 'status', 'note')
        }),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def has_delete_permission(self, request: HttpRequest, obj= None) -> bool:
        return False
    
    def has_change_permission(self, request: HttpRequest, obj= None) -> bool:
        return False
    
    def preview_email(self, obj):
        return format_html(obj.content)
    preview_email.short_description = _('Content')


from django.conf import settings

def _parse_sidebar_apps():
    """Parse UNFOLD SIDEBAR settings into app-like objects. No DB access."""
    apps = []
    try:
        navigation = settings.UNFOLD.get('SIDEBAR', {}).get('navigation', [])
        for section in navigation:
            category = section.get('title')
            for item in section.get('items', []):
                name = item.get('title')
                link = item.get('link')
                if not (name and link) or '/base/app/' in str(link):
                    continue
                apps.append(_types.SimpleNamespace(
                    pk=None,
                    name=name,
                    url=link,
                    icon=item.get('icon'),
                    category=category,
                    permission=item.get('permission'),
                    thumbnail_url=item.get('thumbnail'),
                    is_active=True,
                ))
    except Exception:
        pass
    return apps

# App Model Admin
from django.utils.module_loading import import_string
from whiteneuron.dashboard.views import dashboard_callback
@admin.register(App, site=base_admin_site)
class AppAdmin(ModelAdmin):

    list_before_template= 'admin/header.html'
    change_list_template= 'admin/base/app_change_list.html'

    default_toggle_sidebar= False

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj = ...):
        return False   
    
    def has_delete_permission(self, request, obj = ...):
        return False

    def has_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        permission = obj.permission if obj else None
        if permission:
            perm_func = permission if callable(permission) else import_string(permission)
            return perm_func(request)
        return True

    def get_queryset(self, request):
        return super().get_queryset(request).none()

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update(dashboard_callback(request, extra_context))
        extra_context['title'] = _('Dashboard')

        apps = _parse_sidebar_apps()
        if not request.user.is_superuser:
            apps = [app for app in apps if self.has_permission(request, app)]

        app_by_category = {}
        for app in apps:
            cat = app.category or ''
            app_by_category.setdefault(cat, []).append(app)
        extra_context['app_by_category'] = app_by_category

        return super().changelist_view(request, extra_context)