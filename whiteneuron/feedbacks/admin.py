from django.contrib import admin, messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from whiteneuron.base.admin import base_admin_site, ModelAdmin
from .models import FeedbackData
from .urls import FEEDBACK_COOLDOWN_SECONDS

from whiteneuron.notification.models import Notification

@admin.register(FeedbackData, site=base_admin_site)
class FeedbackDataAdmin(ModelAdmin):
    using_grid_view = False
    date_hierarchy = 'created_at'
    change_form_template = 'admin/feedbacks/feedback_change_form.html'
    list_display = (
        'id',
        'user',
        'content_type',
        'get_related_object_link',  # Hiển thị link đến object gốc
        'get_short_message',
        'is_resolved',
        'created_at',
    )
    list_filter = ('is_resolved', 'created_at', 'user', 'content_type')
    search_fields = ('message', 'user__username', 'content_type__model')

    fieldsets = (
        (_('Feedback Data'), {
            # 'fields': ('user', ('content_type', 'object_id'), ('get_related_object_link', 'field'), 'message')
            'fields': ('user', ('content_type', 'object_id'), 'get_related_object_link', 'message')
        }),
        (_('Status'), {
            'fields': ('is_resolved', 'note')
        })
    )

    readonly_fields = ('get_related_object_link',)  # Chỉ hiển thị link, không cho sửa

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Người liên quan có thể xem feedback        
        return qs.filter(user=request.user) 
    
    def get_short_message(self, obj):
        return Truncator(obj.message).words(200)
    get_short_message.short_description = _('Message')

    def get_related_object_link(self, obj):
        """Hiển thị link đến object gốc"""
        if obj.content_object:
            admin_url = reverse(
                f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                args=[obj.object_id]
            )
            return format_html('<a href="{}" target="_blank">{}</a>', admin_url, obj.content_object)
        return "-"
    get_related_object_link.short_description = _("Related Object")  # Tiêu đề trong Admin

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
                return JsonResponse({"success": False, "message": str(_("Only superuser can mark feedback as resolved"))}, status=403)
            
            # note
            note= request.POST.get('note', '')
            if len(note) > 500:
                return JsonResponse({"success": False, "message": str(_("Note must not exceed 500 characters."))}, status=400)

            obj = self.get_object(request, object_id)
            if obj is None:
                return JsonResponse({"success": False, "message": str(_("Feedback not found."))}, status=404)
            obj.is_resolved = True
            obj.note = note
            obj.save()

            # Thông báo đến user gửi feedback rằng feedback đã được xử lý
            noti= Notification(
                user= obj.user,
                title= _("Feedback resolved"),
                content= format_html(
                    '<p>{}</p><p>{}: {}</p><p>{}: {}</p>',
                    _("Your feedback has been resolved."),
                    _("Object"), self.get_related_object_link(obj),
                    _("Note"), note,
                ),
                action='update',
                flag= 'success',
            )
            noti.save()

            return JsonResponse({"success": True})

        return super().changeform_view(request, object_id, form_url, extra_context)

# FeedBack base admin
# Cho phép các model khác kế thừa để gọi
class FeedbackBaseAdmin(ModelAdmin):
    change_form_outer_after_template = "admin/feedbacks/change_form_feedback_list.html"

    def render_change_form(self, request, context, *args, **kwargs):
        context['show_feedback'] = True
        context['feedback_cooldown_ms'] = FEEDBACK_COOLDOWN_SECONDS * 1000

        original = context.get('original')
        if original is not None:
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(original)
            feedbacks = FeedbackData.objects.filter(
                content_type=ct,
                object_id=str(original.pk),
            ).select_related('user')
            context['feedback_list'] = feedbacks

        return super().render_change_form(request, context, *args, **kwargs)
