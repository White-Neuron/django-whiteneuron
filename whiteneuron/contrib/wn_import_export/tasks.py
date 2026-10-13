from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.html import format_html

from celery import shared_task
from import_export.formats.base_formats import XLSX

from whiteneuron.file_management.models import ExcelFile
from whiteneuron import base

from .utils import get_resource

@shared_task
def export(fileobj_id,
           app_label,
           model_name,
           ids,
           file_name: str):
    # Khởi tạo resource
    fileobj = ExcelFile.objects.get(id=fileobj_id)
    try:
        model = apps.get_model(app_label=app_label, model_name=model_name)
        resource = get_resource(app_label, model_name)()
        # Only the rows the admin selected / was allowed to see (ids come from the admin queryset)
        manager = getattr(model, 'objects_all', model._default_manager)
        dataset = resource.export(manager.filter(pk__in=ids).order_by('pk'))
        content = XLSX().export_data(dataset)  # bytes
        fileobj.file.save(file_name, ContentFile(content), save=False)
        fileobj.status = 'done'
        fileobj.description = (fileobj.description or '') + format_html('<p>Done at: {}</p>', timezone.now())
        fileobj.save()
    except Exception as e:
        fileobj.status = 'error'
        fileobj.title = '[ERROR] ' + fileobj.title
        fileobj.description = (fileobj.description or '') + format_html('<p>Error: {}</p>', e)
        fileobj.save()
