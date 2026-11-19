import logging

from django.db import models, transaction
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
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
    # default, not auto_now_add: notify_superusers stamps every copy of an event with one time
    # before the insert (auto_now_add overwrote it on each copy)
    created_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name=_("Created At"))
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
        updated = cls.objects.filter(user=user, is_read=False).update(is_read=True)
        _clear_unread_cache(user.pk)
        return updated

    @classmethod
    def mark_as_unread_all(cls, user):
        updated = cls.objects.filter(user=user, is_read=True).update(is_read=False)
        _clear_unread_cache(user.pk)
        return updated

    # def get_changed_data(self):
        

    @classmethod
    def notify_superusers(cls, *, title, content="", action=None, flag="info",
                          obj_link=None, changed_data=None, action_by=None, model=None):
        """Create one notification per recipient and broadcast it once.

        Recipients: ``recipients_for(model, action)`` - the "Notifications config" rows of
        that model and event, or every active superuser when there is none (or no ``model``).

        ``title`` is plain text (escaped wherever it is rendered); ``content`` must
        already be safe HTML (build it with ``format_html``). Rows are inserted with
        a single ``bulk_create`` and the websocket broadcast runs after the
        transaction commits, so a failing channel layer never breaks the save.
        """
        user_ids = sorted(recipients_for(model, action))
        if not user_ids:
            return []
        if action_by is not None and not getattr(action_by, "pk", None):
            action_by = None  # AnonymousUser
        data = json.dumps(changed_data, default=str, ensure_ascii=False) if changed_data else None
        # One event, one timestamp for every copy, set before the insert: the history panel groups
        # the copies of an event by time, and copies of a big batch stamped one by one could
        # straddle a second. No extra query, and it holds on every database backend.
        stamp = timezone.now()
        objs = cls.objects.bulk_create([
            cls(user_id=user_id, title=str(title)[:255], content=str(content), action=action,
                flag=flag, obj_link=obj_link, changed_data=data, action_by=action_by, created_at=stamp)
            for user_id in user_ids
        ])
        _clear_unread_cache(*user_ids)  # bulk_create sends no post_save
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

# ── Recipients from "Notifications config" (#36) ───────────────────────────
# A config row's event_type is create / update / delete / all; "restore" counts as update.
_EVENT_FOR_ACTION = {"create": "create", "update": "update", "delete": "delete", "restore": "update"}
_CONFIG_CACHE_VERSION_KEY = "wn:notification_config:version"
_CONFIG_CACHE_TIMEOUT = 300


def _superuser_ids():
    return set(User.objects.filter(is_superuser=True, is_active=True).values_list("id", flat=True))


def _config_version():
    from django.core.cache import caches

    try:
        return caches["default"].get_or_set(_CONFIG_CACHE_VERSION_KEY, 1, None)
    except Exception:
        return None


def recipients_for(model, action):
    """User ids to notify about ``action`` on ``model`` (a class or instance).

    With "Notifications config" rows for that model and event (or "all"): the union of the
    active superusers (send_to_admin), the listed users (send_to_user) and the members of the
    listed groups (send_to_group_user). Without any: every active superuser, as before.
    Superusers always come from the database; the config part is cached until a config changes.
    """
    event = _EVENT_FOR_ACTION.get(action or "")
    if model is None or event is None:
        return _superuser_ids()
    from django.contrib.contenttypes.models import ContentType
    from django.core.cache import caches

    try:
        content_type = ContentType.objects.get_for_model(model, for_concrete_model=True)
    except Exception:
        return _superuser_ids()
    version = _config_version()
    cache_key = f"wn:notification_config:{version}:{content_type.pk}:{event}"
    cached = caches["default"].get(cache_key) if version is not None else None
    if cached is None:
        configs = list(NotificationConfig.objects.filter(model=content_type, event_type__in=[event, "all"])
                       .prefetch_related("users", "group_users"))
        if not configs:
            cached = {"configured": False}
        else:
            to_admin, users = False, set()
            for config in configs:
                to_admin = to_admin or config.send_to_admin
                if config.send_to_user:
                    users.update(u.pk for u in config.users.all())
                if config.send_to_group_user:
                    users.update(User.objects.filter(groups__in=config.group_users.all()).values_list("id", flat=True))
            cached = {"configured": True, "admin": to_admin, "users": sorted(users)}
        if version is not None:
            caches["default"].set(cache_key, cached, _CONFIG_CACHE_TIMEOUT)
    if not cached["configured"]:
        return _superuser_ids()
    ids = set(User.objects.filter(pk__in=cached["users"], is_active=True).values_list("id", flat=True))
    if cached["admin"]:
        ids |= _superuser_ids()
    # Notifications are also the record's change history (until #35): a config that reaches
    # nobody (all boxes off, an empty group) must not erase that trail. Superusers keep it.
    return ids or _superuser_ids()


def _config_changed(**kwargs):
    from django.core.cache import caches

    try:
        caches["default"].incr(_CONFIG_CACHE_VERSION_KEY)
    except Exception:  # not set yet, or a cache without incr: start a new version
        try:
            caches["default"].set(_CONFIG_CACHE_VERSION_KEY, 2, None)
        except Exception:
            pass


from django.db.models.signals import m2m_changed, post_delete  # noqa: E402

post_save.connect(_config_changed, sender=NotificationConfig, dispatch_uid="wn_notification_config_saved")
post_delete.connect(_config_changed, sender=NotificationConfig, dispatch_uid="wn_notification_config_deleted")
m2m_changed.connect(_config_changed, sender=NotificationConfig.users.through, dispatch_uid="wn_notification_config_users")
m2m_changed.connect(_config_changed, sender=NotificationConfig.group_users.through, dispatch_uid="wn_notification_config_groups")


def _clear_unread_cache(*user_ids):
    from .utils import clear_unread_cache

    clear_unread_cache(*user_ids)
    # and again once committed: a page rendered in between would cache the old count
    transaction.on_commit(lambda: clear_unread_cache(*user_ids))


@receiver(post_save, sender=Notification, dispatch_uid="wn_notification_unread_cache")
def _notification_saved(sender, instance, **kwargs):
    # .save() and .create(). Bulk writes and deletes clear it where they happen: a post_delete
    # receiver would make deleting a user load every one of their notifications.
    _clear_unread_cache(instance.user_id)


class AnnouncementReceipt(models.Model):
    """A user has seen the announcement (release notes) of ``version``.

    Lets the announcement API tell clients whether to pop up "what's new" for the
    current version, once per user, across devices.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="announcement_receipts")
    version = models.CharField(max_length=100)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "announcement_receipts"
        constraints = [
            models.UniqueConstraint(fields=["user", "version"], name="announcement_receipt_user_version_uniq"),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.version}"
