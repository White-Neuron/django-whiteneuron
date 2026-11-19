from django.contrib import admin, messages
from django.http import JsonResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _, ngettext

from django import forms
from django.shortcuts import redirect
from unfold.decorators import action, display
from unfold.forms import BaseDialogForm
from unfold.widgets import UnfoldAdminTextareaWidget

from whiteneuron.base.admin import base_admin_site, ModelAdmin
from . import services
from .models import FeedbackData
from .views import FEEDBACK_COOLDOWN_SECONDS


class FeedbackNoteForm(BaseDialogForm):
    """The dialog of the detail decisions: an optional note, sent to the feedback's author."""
    note = forms.CharField(label=_("Note for the sender"), required=False, max_length=500,
                           widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}))


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
        'display_status',
        'created_at',
    )
    search_help_text = _("Search by message or sender")
    list_filter = ('status', 'created_at', 'user', 'content_type')
    search_fields = ('message', 'user__username', 'content_type__model')

    fieldsets = (
        (_('Feedback Data'), {
            # 'fields': ('user', ('content_type', 'object_id'), ('get_related_object_link', 'field'), 'message')
            'fields': ('user', ('content_type', 'object_id'), 'get_related_object_link', 'message')
        }),
        (_('Status'), {
            'fields': ('status', 'note')
        })
    )

    readonly_fields = ('get_related_object_link',)  # Chỉ hiển thị link, không cho sửa

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        
        # Người liên quan có thể xem feedback        
        return qs.filter(user=request.user) 
    
    # A label, not the boolean icon: a red ✗ on every pending feedback read as "error" (#81)
    @display(description=_("Status"), ordering="status",
             label={"open": "warning", "in_progress": "info", "resolved": "success", "rejected": "default"})
    def display_status(self, obj):
        return obj.status, obj.get_status_display()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        # their help texts only repeated the label ("The message of the feedback") (#81)
        if field is not None and db_field.name in ("message", "is_resolved"):
            field.help_text = ""
        return field

    def get_short_message(self, obj):
        # about a line in the list; the whole message on hover (#47)
        return format_html('<span title="{}">{}</span>', obj.message, Truncator(obj.message).words(30))
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

    # Workflow actions (#47): each record goes through services.set_status, so a bulk change
    # saves, records history and notifies every sender like a single one does
    actions = ['mark_as_resolved', 'mark_in_progress', 'mark_rejected', 'reopen']

    def _bulk_status(self, request, queryset, status):
        changed_items = [fb for fb in queryset.select_related("user") if services.set_status(fb, status, notify=False)]
        services.notify_senders(changed_items)  # one message per sender, not one per feedback
        changed = len(changed_items)
        self.message_user(request, ngettext(
            "%(count)d feedback changed to %(status)s.", "%(count)d feedbacks changed to %(status)s.", changed,
        ) % {"count": changed, "status": dict(FeedbackData.STATUS_CHOICES)[status]}, messages.SUCCESS)

    @admin.action(description=_("Mark selected feedbacks as resolved"), permissions=["resolve"])
    def mark_as_resolved(self, request, queryset):
        self._bulk_status(request, queryset, FeedbackData.RESOLVED)

    @admin.action(description=_("Mark selected feedbacks as in progress"), permissions=["resolve"])
    def mark_in_progress(self, request, queryset):
        self._bulk_status(request, queryset, FeedbackData.IN_PROGRESS)

    @admin.action(description=_("Reject selected feedbacks"), permissions=["resolve"])
    def mark_rejected(self, request, queryset):
        self._bulk_status(request, queryset, FeedbackData.REJECTED)

    @admin.action(description=_("Reopen selected feedbacks"), permissions=["resolve"])
    def reopen(self, request, queryset):
        self._bulk_status(request, queryset, FeedbackData.OPEN)

    def has_resolve_permission(self, request, object_id=None):
        # the same rule as the single "resolve" on the change form
        return request.user.is_superuser

    # The other decisions on the detail page too, each with a note for the sender (#47 review):
    # rejecting from the list gave no place to say why
    actions_detail = ["detail_in_progress", "detail_reject", "detail_reopen"]

    def _detail_status(self, request, form, object_id, status):
        feedback = self.get_object(request, object_id)
        if feedback is not None and services.set_status(feedback, status, note=form.cleaned_data.get("note") or None):
            self.message_user(request, _("Feedback changed to %(status)s.") % {
                "status": dict(FeedbackData.STATUS_CHOICES)[status]}, messages.SUCCESS)
        return redirect(reverse("admin:feedbacks_feedbackdata_change", args=[object_id]))

    @action(description=_("In progress"), url_path="in-progress", icon="pending", permissions=["resolve"],
            dialog={"title": _("Mark this feedback as in progress?"), "form_class": FeedbackNoteForm})
    def detail_in_progress(self, request, form, object_id):
        return self._detail_status(request, form, object_id, FeedbackData.IN_PROGRESS)

    @action(description=_("Reject"), url_path="reject", icon="block", permissions=["resolve"],
            dialog={"title": _("Reject this feedback?"), "form_class": FeedbackNoteForm})
    def detail_reject(self, request, form, object_id):
        return self._detail_status(request, form, object_id, FeedbackData.REJECTED)

    @action(description=_("Reopen"), url_path="reopen", icon="undo", permissions=["resolve"],
            dialog={"title": _("Reopen this feedback?"), "form_class": FeedbackNoteForm})
    def detail_reopen(self, request, form, object_id):
        return self._detail_status(request, form, object_id, FeedbackData.OPEN)

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
            # state change: POST only (CSRF-protected)
            if request.method != 'POST':
                return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)
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
            services.resolve(obj, note=note)  # saves, records history, notifies the sender (+ toast)
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
            # the rule of the Feedback list: others' feedbacks only for superusers (#47)
            if not request.user.is_superuser:
                feedbacks = feedbacks.filter(user=request.user)
            context['feedback_list'] = feedbacks

        return super().render_change_form(request, context, *args, **kwargs)
