from whiteneuron.base.models import BaseModel
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

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

    def status_view(self):
        if self.status == 'pending':
            status_color= '#f39c12'
            status= _('Pending')
        elif self.status == 'done':
            status_color= '#00a65a'
            status= _('Done')
        else:
            status_color= '#dd4b39'
            status= _('Error')
        html= f'<span style="color: {status_color}; font-weight: bold;">{status}</span>'
        return format_html(html)
    status_view.short_description = _('Status')

    def method_view(self):
        if self.method == 'upload':
            method_color= '#00c0ef'
            method= _('Upload')
        else:
            method_color= '#00a65a'
            method= _('Auto')
        html= f'<span style="color: {method_color}; font-weight: bold;">{method}</span>'
        return format_html(html)
    method_view.short_description = _('Method')

    def __str__(self):
        return self.title
    
    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.file.delete()
        super().delete(*args, **kwargs)

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
