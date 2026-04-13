import posixpath

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseForbidden, Http404
from django.utils.translation import gettext_lazy as _

from .models import ExcelFile, PDFFile, compute_file_hash

_FILE_MODEL_MAP = {
    'excel': ExcelFile,
    'pdf': PDFFile,
}


@login_required
def download_file(request, file_type, pk):
    """Serve a file only after verifying its SHA-256 hash integrity."""
    model_class = _FILE_MODEL_MAP.get(file_type)
    if model_class is None:
        raise Http404

    try:
        instance = model_class.objects.get(pk=pk, is_deleted=False)
    except model_class.DoesNotExist:
        raise Http404

    if not instance.hash:
        # Legacy record: no hash yet. Enroll it now and allow download.
        if not instance.file or not instance.file.name:
            return HttpResponseForbidden(
                str(_('Cannot read file from storage. The file may be missing.'))
            )
        try:
            instance.hash = compute_file_hash(instance.file)
            instance.save(update_fields=['hash'])
        except Exception:
            return HttpResponseForbidden(
                str(_('Cannot read file from storage. The file may be missing.'))
            )
    elif not instance.verify_integrity():
        # Hash exists but does not match – file was tampered with.
        if instance.status != 'error':
            instance.status = 'error'
            instance.save(update_fields=['status'])
        return HttpResponseForbidden(
            str(_('File integrity check failed. This file may have been tampered with and cannot be downloaded.'))
        )

    filename = posixpath.basename(instance.file.name)
    return FileResponse(instance.file.open('rb'), as_attachment=True, filename=filename)
