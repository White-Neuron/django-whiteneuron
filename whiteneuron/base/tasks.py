from celery import shared_task

from whiteneuron.contrib.wn_import_export import export
from .queue import async_tasks_enabled, enqueue  # noqa: F401  (re-exported)


export_task = export


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_mail_task(mail_id, redact=None):
    """Send a stored Mail; optionally mask a secret (e.g. a password) in the stored copy."""
    from .models import Mail

    mail = Mail.objects_all.filter(pk=mail_id).first()
    if mail is None:
        return False
    mail.send()
    if redact:
        Mail.objects_all.filter(pk=mail_id).update(content=mail.content.replace(redact, "********"))
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
