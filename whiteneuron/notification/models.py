from django.db import models
from whiteneuron.base.models import User, Group
from django.utils.translation import gettext_lazy as _

class NotificationConfig(models.Model):
    """
    Model to store notification configurations.
    """
    model = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        related_name='notification_configs',
        help_text=_("The model this configuration applies to.")
    )
    event_type = models.CharField(
        max_length=100,
        help_text=_("The type of event this configuration applies to (e.g., 'create', 'update', 'delete')."),
        choices=[
            ('all', 'All'),
            ('create', 'Create'),
            ('update', 'Update'),
            ('delete', 'Delete'),
        ]
    )
    
    send_to_admin = models.BooleanField(
        default=True,
        help_text=_("Whether to send notifications to the admin.")
    )
    
    send_to_user = models.BooleanField(
        default=False,
        help_text=_("Whether to send notifications to the user.")
    )

    send_to_group_user = models.BooleanField(
        default=False,
        help_text=_("Whether to send notifications to group users.")
    )

    group_users= models.ManyToManyField(
        Group,
        blank=True,
        related_name='notification_configs',
        help_text=_("Groups of users to send notifications to.")
    )

    users= models.ManyToManyField(
        User,
        blank=True,
        related_name='notification_configs',    
        help_text=_("Specific users to send notifications to.")
    )


from .views import notify_admin
import json
class Notification(models.Model):
    user= models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    obj_link= models.CharField(max_length=255, null=True, blank=True) # link to object
    content = models.TextField()
    changed_data= models.TextField(null=True, blank=True, verbose_name=_("Changed Data"))
    is_read = models.BooleanField(default=False, verbose_name=_("Read"))
    flag = models.CharField(max_length=25, choices=[("info", "info"), 
                                                    ("success", "success"), 
                                                    ("warning", "warning"), 
                                                    ("error", "error"),
                                                    ("danger", "danger")])
    action = models.CharField(max_length=25, null=True, blank=True, choices=[("update", "update"),
                                                                             ("create", "create"),
                                                                             ('restore', 'restore'),
                                                                             ("delete", "delete")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")

    def __str__(self):
        return f"[{self.flag}] {self.title}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()

    def mark_as_unread(self):
        self.is_read = False
        self.save()

    def mark_as_read_all(self):
        self.objects.update(is_read=True)

    def mark_as_unread_all(self):
        self.objects.update(is_read=False)

    # def get_changed_data(self):
        

    def alert(self, request):
        """
        Returns a dictionary suitable for use in a JavaScript alert.
        """
        message = f"{self.title}"
        type= self.flag
        return notify_admin(message, type=type, obj_link=self.obj_link, action=self.action, changed_data=self.changed_data if self.changed_data else "")