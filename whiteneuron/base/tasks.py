import re

from celery import shared_task

from whiteneuron.contrib.wn_import_export import export
from .queue import async_tasks_enabled, enqueue  # noqa: F401  (re-exported)


export_task = export

# <span data-wn-secret="1">…</span> written by utils.send_email_login
SECRET_MARKER = re.compile(r'(<span data-wn-secret="1">)[^<]*(</span>)')


@shared_task
def send_mail_task(mail_id, redact_secrets=False):
    """Send a stored Mail; with ``redact_secrets`` mask the marked secrets in the stored copy."""
    from .models import Mail

    mail = Mail.objects_all.filter(pk=mail_id).first()
    if mail is None:
        return False
    mail.send()
    if redact_secrets:
        masked = SECRET_MARKER.sub(r"\1********\2", mail.content)
        Mail.objects_all.filter(pk=mail_id).update(content=masked)
    return mail.is_sent()


@shared_task
def gpt_translate_task(app_label, model_name, ids):
    """Translate *_en fields to *_vi for the given objects (one OpenAI call each)."""
    from django.apps import apps
    from whiteneuron.contrib.wn_modeltranslation.utils import translate_object

    model = apps.get_model(app_label, model_name)
    manager = getattr(model, "objects_all", model._default_manager)
    done, failed = [], []
    for obj in manager.filter(pk__in=ids):
        result = translate_object(obj)
        if result["success"]:
            for key, value in result["result"].items():
                if key.endswith("_vi"):
                    setattr(obj, key, value)
            obj.save()
            done.append(str(obj))
        else:
            failed.append((str(obj), str(result["message"])))
    return {"done": done, "failed": failed}
