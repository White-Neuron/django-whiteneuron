from django.db import models
from whiteneuron.base.models import BaseModel 
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class SyncLog(BaseModel):
    """
    Model to log synchronization activities.
    """
    action = models.CharField(max_length=255, choices=[
        ('push', 'Push'),
        ('pull', 'Pull'),
    ], verbose_name=_("Action"), help_text=_("The synchronization action performed"))
    status = models.CharField(max_length=50, choices=[
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('failure', 'Failure'),
    ], verbose_name=_("Status"), help_text=_("The status of the synchronization action"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Timestamp"), help_text=_("The time when the action was performed"))
    details = models.TextField(blank=True, null=True, verbose_name=_("Details"), help_text=_("Additional details about the synchronization action"))

    def __str__(self):
        return f"{self.action} - {self.status} at {self.timestamp}"
    
    class Meta:
        verbose_name = _("Synchronization Log")
        verbose_name_plural = _("Synchronization Logs")
        ordering = ['-timestamp']
