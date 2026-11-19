from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from whiteneuron.base.models import BaseModel 

# Feedback
# Đề xuất thay đổi dữ liệu
class FeedbackData(BaseModel):
    user = models.ForeignKey(
        "base.User",
        on_delete=models.CASCADE,
        related_name="feedbacks",
        verbose_name=_("User")
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type")
    )

    object_id = models.CharField(
        max_length=255,
        verbose_name=_("Object ID")
    )

    field= models.CharField(
        max_length=255,
        verbose_name=_("Field"),
        help_text=_("The specific field of the object the feedback is about"),
        blank=True,
        null=True
    )

    content_object = GenericForeignKey('content_type', 'object_id')

    message = models.TextField(
        verbose_name=_("Message"),
    )

    # Workflow (#47). is_resolved stays for compatibility and follows status in save().
    OPEN, IN_PROGRESS, RESOLVED, REJECTED = "open", "in_progress", "resolved", "rejected"
    STATUS_CHOICES = [
        (OPEN, _("Open")),
        (IN_PROGRESS, _("In progress")),
        (RESOLVED, _("Resolved")),
        (REJECTED, _("Rejected")),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=OPEN, db_default=OPEN, db_index=True,
        verbose_name=_("Status"),
    )

    is_resolved = models.BooleanField(
        default=False,
        verbose_name=_("Is Resolved"),
    )

    note= models.TextField(
        verbose_name=_("Note"),
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedbacks")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'{self.user} - {self.content_type}({self.object_id})'

    def save(self, *args, **kwargs):
        self.is_resolved = self.status == self.RESOLVED
        super().save(*args, **kwargs)
        # the sidebar badge counts open feedbacks (feedbacks.utils)
        from django.core.cache import caches

        try:
            caches["default"].delete_many(["badge:feedback:open:all", f"badge:feedback:open:{self.user_id}"])
        except Exception:
            pass

    @property
    def is_closed(self):
        return self.status in (self.RESOLVED, self.REJECTED)
    


    


