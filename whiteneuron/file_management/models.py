import hashlib

from whiteneuron.base.models import BaseModel
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


def compute_file_hash(file_field):
    """Compute SHA-256 hash of a Django FieldFile (uncommitted upload or committed storage file)."""
    sha256 = hashlib.sha256()
    if not file_field._committed:
        # Newly uploaded file in memory/temp – read directly from the upload object
        f = file_field.file
        try:
            f.seek(0)
        except (AttributeError, OSError):
            pass
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
        try:
            f.seek(0)  # Reset so Django can still write it to storage
        except (AttributeError, OSError):
            pass
    else:
        # File is on storage – open directly through the storage backend to avoid
        # FieldFile internal state issues (e.g. when triggered from FieldFile.save()).
        with file_field.storage.open(file_field.name, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
    return sha256.hexdigest()

class BaseFile(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    status = models.CharField(max_length=25, choices=(('pending', _('Pending')),
                                                      ('done', _('Done')),
                                                      ('error', _('Error'))),
                                                      default='done', verbose_name=_('Status'))
    method= models.CharField(max_length=25, choices=(('upload', _('Upload')),
                                                     ('auto', _('Auto'))),
                                                     default='upload', verbose_name=_('Method'))
    hash = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Hash'))

    def status_view(self):
        if self.status == 'pending':
            status_color = '#f39c12'
            status = _('Pending')
        elif self.status == 'done':
            status_color = '#00a65a'
            status = _('Done')
        else:
            status_color = '#dd4b39'
            status = _('Error')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            status_color, status
        )
    status_view.short_description = _('Status')

    def method_view(self):
        if self.method == 'upload':
            method_color = '#00c0ef'
            method = _('Upload')
        else:
            method_color = '#00a65a'
            method = _('Auto')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            method_color, method
        )
    method_view.short_description = _('Method')

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        # Skip hash logic when only specific fields are being updated (e.g. status)
        if update_fields is None and self.file and self.file.name:
            if not self.file._committed:
                # New upload in memory – hash before writing to storage
                self.hash = compute_file_hash(self.file)
                # A new file replaces any previous error state
                if self.status == 'error':
                    self.status = 'done'
            elif not self.hash:
                # File already in storage but no hash yet (auto/programmatic creation)
                self.hash = compute_file_hash(self.file)
        super().save(*args, **kwargs)

    def verify_integrity(self):
        """Verify the file on storage matches its stored hash. Returns True if OK."""
        if not self.hash or not self.file or not self.file.name:
            return False
        try:
            return compute_file_hash(self.file) == self.hash
        except Exception:
            return False

    def __str__(self):
        return self.title

    class Meta:
        abstract = True

    def hard_delete(self, *args, **kwargs):
        self.file.delete(save=False)
        super().hard_delete(*args, **kwargs)

class ExcelFile(BaseFile):
    file = models.FileField(upload_to='excels')


    class Meta:
        verbose_name = _('Excel File')
        verbose_name_plural = _('Excel Files')

class PDFFile(BaseFile):
    file = models.FileField(upload_to='pdfs')

    class Meta:
        verbose_name = _('PDF File')
        verbose_name_plural = _('PDF Files')
