import posixpath

from django.http import FileResponse, HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import ExcelFile, PDFFile, HTMLFile, compute_file_hash


_FILE_MODEL_MAP = {
    'excel': ExcelFile,
    'pdf': PDFFile,
    'html': HTMLFile,
}


def _check_access(user, instance):
    """Check access to a file. Returns (allowed: bool, needs_login: bool)."""
    if instance.is_public:
        return True, False
    if user.is_superuser:
        return True, False
    if not user.is_authenticated:
        return False, True
    if user in instance.allowed_users.all():
        return True, False
    if user.groups.filter(id__in=instance.allowed_groups.values_list('pk', flat=True)).exists():
        return True, False
    return False, False


def download_file(request, file_type, pk):
    """Serve a file only after verifying its SHA-256 hash integrity and access permissions."""
    model_class = _FILE_MODEL_MAP.get(file_type)
    if model_class is None:
        raise Http404

    try:
        instance = model_class.objects.get(pk=pk, is_deleted=False)
    except model_class.DoesNotExist:
        raise Http404

    allowed, needs_login = _check_access(request.user, instance)
    if not allowed:
        if needs_login:
            login_url = f"{reverse('admin:login')}?next={request.path}"
            return redirect(login_url)
        return render(request, '403.html', status=403)

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


def preview_file(request, file_type, pk):
    """Preview HTML files inline in the browser after permission check."""
    if file_type != 'html':
        raise Http404

    try:
        instance = HTMLFile.objects.get(pk=pk, is_deleted=False)
    except HTMLFile.DoesNotExist:
        raise Http404

    allowed, needs_login = _check_access(request.user, instance)
    if not allowed:
        if needs_login:
            login_url = f"{reverse('admin:login')}?next={request.path}"
            return redirect(login_url)
        return render(request, '403.html', status=403)

    if not instance.file or not instance.file.name:
        return HttpResponseForbidden(
            str(_('Cannot read file from storage. The file may be missing.'))
        )

    try:
        with instance.file.open('rb') as f:
            content = f.read()
    except (IOError, OSError):
        return HttpResponseForbidden(
            str(_('Cannot read file from storage. The file may be missing.'))
        )

    if not content:
        return HttpResponseForbidden(str(_('File is empty.')))

    return HttpResponse(content, content_type='text/html; charset=utf-8')
