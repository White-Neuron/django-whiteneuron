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
from unfold.contrib.forms.widgets import WysiwygWidget
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

from .models import User, Tag, UserActivity, UserProfile
from .sites import base_admin_site
from django.utils.safestring import mark_safe

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
        if not obj.avatar:
            s= '<span class="material-symbols-outlined" style="font-size: 192px;">person</span>'
        else:
            s= f'<img src="{obj.avatar.url}" height="192" class="rounded-lg"/>'
        string= f"""
<div class="ui-card ui-card-side h-48">
    <figure class="w-48 h-48 flex justify-center">
        {s}
    </figure>
    <div class="ui-card-body">
        <h5>{obj.username}</h5>
        <h4 class="ui-card-title">{obj.full_name}</h4>
        <div class="flex flex-row items-center gap-2">
        {'<span class="ui-badge ui-badge-success">Active</span>' if obj.is_active else '<span class="ui-badge ui-badge-danger">Inactive</span>'}
        {'<span class="ui-badge ui-badge-success">Staff</span>' if obj.is_staff else ''}
        {'<span class="ui-badge ui-badge-warning">Superuser</span>' if obj.is_superuser else ''}
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
        (None, {"fields": (
            "username",  # "username" is not in the original User model
            "email",
            # "password1",
            # "password2",
            )}),
        (_("Personal info"),
         {"fields": (("first_name", "last_name"), "avatar", "biography"),
                     }),
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


