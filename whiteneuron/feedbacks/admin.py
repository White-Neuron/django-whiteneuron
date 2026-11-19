from django.contrib import admin, messages
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
        return request.user.is_superuser

    # Detail actions show only where they mean something (#103 review): a rejected feedback
    # had "Reject", an open one "Reopen", and the dialog then did nothing
    def _status_is(self, request, object_id, *statuses):
        if not request.user.is_superuser or object_id is None:
            return False
        return FeedbackData.objects.filter(pk=object_id, status__in=statuses).exists()

    def has_handle_open_permission(self, request, object_id=None):
        return self._status_is(request, object_id, FeedbackData.OPEN, FeedbackData.IN_PROGRESS)

    def has_start_permission(self, request, object_id=None):
        return self._status_is(request, object_id, FeedbackData.OPEN)

    def has_reopen_closed_permission(self, request, object_id=None):
        return self._status_is(request, object_id, FeedbackData.RESOLVED, FeedbackData.REJECTED)

    # The other decisions on the detail page too, each with a note for the sender (#47 review):
    # rejecting from the list gave no place to say why
    actions_detail = ["detail_resolve", "detail_in_progress", "detail_reject", "detail_reopen"]

    def _detail_status(self, request, form, object_id, status):
        feedback = self.get_object(request, object_id)
        if feedback is not None and services.set_status(feedback, status, note=form.cleaned_data.get("note") or None):
            self.message_user(request, _("Feedback changed to %(status)s.") % {
                "status": dict(FeedbackData.STATUS_CHOICES)[status]}, messages.SUCCESS)
        return redirect(reverse("admin:feedbacks_feedbackdata_change", args=[object_id]))

    # "Resolve" is one of them too: the hand-drawn button did not shrink with the others and
    # became unreadable at 1440px once History and three more actions shared the row
    @action(description=_("Resolve"), url_path="resolve", icon="check_circle", permissions=["handle_open"],
            dialog={"title": _("Resolve this feedback?"), "form_class": FeedbackNoteForm,
                    "form_submit_text": _("Resolve")})
    def detail_resolve(self, request, form, object_id):
        return self._detail_status(request, form, object_id, FeedbackData.RESOLVED)

    @action(description=_("In progress"), url_path="in-progress", icon="pending", permissions=["start"],
            dialog={"title": _("Mark this feedback as in progress?"), "form_class": FeedbackNoteForm,
                    "form_submit_text": _("In progress")})
    def detail_in_progress(self, request, form, object_id):
        return self._detail_status(request, form, object_id, FeedbackData.IN_PROGRESS)

    @action(description=_("Reject"), url_path="reject", icon="block", permissions=["handle_open"],
            dialog={"title": _("Reject this feedback?"), "form_class": FeedbackNoteForm,
                    "form_submit_text": _("Reject")})
    def detail_reject(self, request, form, object_id):
        return self._detail_status(request, form, object_id, FeedbackData.REJECTED)

    @action(description=_("Reopen"), url_path="reopen", icon="undo", permissions=["reopen_closed"],
            dialog={"title": _("Reopen this feedback?"), "form_class": FeedbackNoteForm,
                    "form_submit_text": _("Reopen")})
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
