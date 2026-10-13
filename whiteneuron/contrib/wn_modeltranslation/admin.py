from modeltranslation.admin import TabbedTranslationAdmin as DefaultTabbedTranslationAdmin

from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from whiteneuron.base.queue import enqueue
from whiteneuron.base.tasks import gpt_translate_task

def _gpt_translate_vi_action(admin_obj, request, queryset):
    if not request.user.is_superuser:
        messages.error(request, _("You must be a superuser to use this action"))
        return
    ids = list(queryset.values_list("pk", flat=True))
    opts = admin_obj.model._meta
    # One OpenAI call per object: run on a Celery worker when available.
    result = enqueue(gpt_translate_task, opts.app_label, opts.model_name, ids)
    if result is True:
        messages.info(request, _("Translating %(count)d record(s) in the background.") % {"count": len(ids)})
        return
    if result["done"]:
        messages.success(request, _("Translated successfully: %s") % ", ".join(result["done"]))
    if result["failed"]:
        messages.error(request, _("Translated failed: %s") % "; ".join(f"{name} ({msg})" for name, msg in result["failed"]))

class TabbedTranslationAdmin(DefaultTabbedTranslationAdmin):
    def get_actions(self, request):
        actions = super().get_actions(request)
        if not "gpt_translate_vi_action" in actions:
            actions["gpt_translate_vi_action"] = (
                _gpt_translate_vi_action,
                "gpt_translate_vi_action",
                _("Translate to Vietnamese"),
            )
        return actions

    