from django.contrib import admin, messages
from django.utils.translation import gettext as _
from unfold.decorators import display

from whiteneuron.base.admin import base_admin_site, ModelAdmin
from .models import FeedbackData

from django.urls import reverse

from whiteneuron.notification.models import Notification

@admin.register(FeedbackData, site=base_admin_site)
class FeedbackDataAdmin(ModelAdmin):
    date_hierarchy = 'created_at'
    change_form_template = 'admin/feedbacks/feedback_change_form.html'
    list_display = (
        'id',
        'user',
        'content_type',
        'get_related_object_link',  # Hiển thị link đến object gốc
        'message',
        'is_resolved',
        'created_at',
    )
    list_filter = ('is_resolved', 'created_at', 'user', 'content_type')
    search_fields = ('message', 'user__username', 'content_type__model')

    fieldsets = (
        ('Feedback Data', {
            'fields': ('user', ('content_type', 'object_id'), ('get_related_object_link', 'field'), 'message')
        }),
        ('Status', {
            'fields': ('is_resolved', 'note')
        })
    )

    readonly_fields = ('get_related_object_link',)  # Chỉ hiển thị link, không cho sửa

    def get_related_object_link(self, obj):
        """Hiển thị link đến object gốc"""
        if obj.content_object:
            admin_url = reverse(
                f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change', 
                args=[obj.object_id]
            )
            return format_html(f'<a href="{admin_url}" target="_blank">{obj.content_object}</a>')
        return "-"
    get_related_object_link.short_description = "Related Object"  # Tiêu đề trong Admin

    # Định nghĩa action để đánh dấu đã xử lý
    actions = ['mark_as_resolved']

    @admin.action(description=_("Mark selected feedbacks as resolved"))
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(
            request,
            _("%d feedback(s) marked as resolved.") % updated,
            messages.SUCCESS
        )

    # Vô hiệu thêm mới
    def has_add_permission(self, request):
        return False

    # Vô hiệu xoá
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj = ...):
        return False

    # Cho phép xem (change view) nhưng tất cả các trường đều ở chế độ readonly
    def get_readonly_fields(self, request, obj=None):
        fields= super().get_readonly_fields(request, obj)
        fields += ('get_related_object_link',)
        return fields
    
    def changeform_view(self, request, object_id = None, form_url = "", extra_context = None):

        #?resolved=1 

        if request.GET.get('resolved') == '1' and object_id:
            # chỉ cho phép superuser thực hiện
            if not request.user.is_superuser:
                self.message_user(request, _("Only superuser can mark feedback as resolved"), messages.ERROR)
                return super().changeform_view(request, object_id, form_url, extra_context)
            
            # note
            note= request.GET.get('note', '')

            obj = self.get_object(request, object_id)
            obj.is_resolved = True
            obj.note = note
            obj.save()

            # Thông báo đến user gửi feedback rằng feedback đã được xử lý
            noti= Notification(
                user= obj.user,
                title= _("Feedback resolved"),
                content= f"""
                    <p>Your feedback has been resolved.</p>
                    <p>Object: {self.get_related_object_link(obj)}</p>
                    <p>Note: {note}</p>
                """,
                action='update',
                flag= 'success',
            )
            noti.save()

            # reload và thông báo
            self.message_user(request, _("Feedback marked as resolved"), messages.SUCCESS)

        return super().changeform_view(request, object_id, form_url, extra_context)

# FeedBack base admin
# Cho phép các model khác kế thừa để gọi
from django.utils.html import format_html
class FeedbackBaseAdmin(ModelAdmin):
    def render_change_form(self, request, context, *args, **kwargs):
        # Thêm show_feedback = True vào context để hiển thị feedbacks
        context['show_feedback'] = True
        return super().render_change_form(request, context, *args, **kwargs)


        
    