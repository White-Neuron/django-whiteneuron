import logging

from django.db import models, transaction
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
        help_text=_("The model this configuration applies to."),
        verbose_name=_("Model")
    )
    event_type = models.CharField(
        max_length=100,
        help_text=_("The type of event this configuration applies to (e.g., 'create', 'update', 'delete')."),
        choices=[
            ('all', 'All'),
            ('create', 'Create'),
            ('update', 'Update'),
            ('delete', 'Delete'),
        ],
        verbose_name=_("Event Type")
    )
    
    send_to_admin = models.BooleanField(
        default=True,
        help_text=_("Whether to send notifications to the admin."),
        verbose_name=_("Send to Admin")
    )
    
    send_to_user = models.BooleanField(
        default=False,
        help_text=_("Whether to send notifications to the user."),
        verbose_name=_("Send to User")
    )

    send_to_group_user = models.BooleanField(
        default=False,
        help_text=_("Whether to send notifications to group users."),
        verbose_name=_("Send to Group Users")
    )

    group_users= models.ManyToManyField(
        Group,
        blank=True,
        related_name='notification_configs',
        help_text=_("Groups of users to send notifications to."),
        verbose_name=_("Group Users")
    )

    users= models.ManyToManyField(
        User,
        blank=True,
        related_name='notification_configs',    
        help_text=_("Specific users to send notifications to."),
        verbose_name=_("Users")
    )


from .views import notify_admin
import json

logger = logging.getLogger(__name__)
class Notification(models.Model):
    user= models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("User to Notify"))
    title = models.CharField(max_length=255)
    obj_link= models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Object Link")
                               ) # link to object
    content = models.TextField()
    changed_data= models.TextField(null=True, blank=True, verbose_name=_("Changed Data"))
    is_read = models.BooleanField(default=False, verbose_name=_("Read"))
    flag = models.CharField(max_length=25, choices=[("info", _("info")),
                                                    ("success", _("success")),
                                                    ("warning", _("warning")),
                                                    ("error", _("error")),
                                                    ("danger", _("danger"))
                                                    ], verbose_name=_("Notification Type"))
    action = models.CharField(max_length=25, null=True, blank=True, choices=[("update",  _("update")),
                                                                             ("create",  _("create")),
                                                                             ('restore', _('restore')),
                                                                             ("delete",  _("delete"))], verbose_name=_("Action Type"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    action_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  verbose_name=_("Action By"),
                                  related_name='action_by_notifications') # user who performed the action that triggered the notification

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"], name="notif_user_read_created_idx"),
            models.Index(fields=["obj_link", "user", "created_at"], name="notif_objlink_user_idx"),
        ]
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")

    def __str__(self):
        return f"{self.user.username} - {self.id} - {self.action} - {self.flag}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()

    def mark_as_unread(self):
        self.is_read = False
        self.save()

    @classmethod
    def mark_as_read_all(cls, user):
        cls.objects.filter(user=user).update(is_read=True)

    @classmethod
    def mark_as_unread_all(cls, user):
        cls.objects.filter(user=user).update(is_read=False)

    # def get_changed_data(self):
        

    @classmethod
    def notify_superusers(cls, *, title, content="", action=None, flag="info",
                          obj_link=None, changed_data=None, action_by=None):
        """Create one notification per active superuser and broadcast it once.

        ``title`` is plain text (escaped wherever it is rendered); ``content`` must
        already be safe HTML (build it with ``format_html``). Rows are inserted with
        a single ``bulk_create`` and the websocket broadcast runs after the
        transaction commits, so a failing channel layer never breaks the save.
        """
        user_ids = list(User.objects.filter(is_superuser=True, is_active=True).values_list("id", flat=True))
        if not user_ids:
            return []
        if action_by is not None and not getattr(action_by, "pk", None):
            action_by = None  # AnonymousUser
        data = json.dumps(changed_data, default=str, ensure_ascii=False) if changed_data else None
        objs = cls.objects.bulk_create([
            cls(user_id=user_id, title=str(title)[:255], content=str(content), action=action,
                flag=flag, obj_link=obj_link, changed_data=data, action_by=action_by)
            for user_id in user_ids
        ])
        transaction.on_commit(lambda: objs[0].alert(user_ids=user_ids))
        return objs

    def alert(self, user_ids=None):
        """
        Returns a dictionary suitable for use in a JavaScript alert.
        """
        try:
            return notify_admin(self.title, type=self.flag, obj_link=self.obj_link, action=self.action,
                                changed_data=self.changed_data if self.changed_data else "",
                                user_ids=user_ids or [self.user_id])
        except Exception:  # channel layer down: the notification row is still stored
            logger.warning("Notification broadcast failed", exc_info=True)