from django.contrib.auth.models import AbstractUser, Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.template.defaultfilters import truncatechars

from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
import uuid
import os
from django.utils.safestring import mark_safe
from django.utils.html import escape, format_html, format_html_join

from django.utils import timezone

############################################
# ImageModel
############################################
class ImageModel(models.Model):
    image = models.ImageField(upload_to='images/')

    # Tự động tạo thumbnail
    thumbnail = ImageSpecField(source='image',
                               processors=[ResizeToFill(50, 50)],
                               format='JPEG',
                               options={'quality': 90})

    def __str__(self):
        return self.image.name
    
    def display_image(self):
        return format_html('<img src="{}" alt="{}" />', self.image.url, self.image)
    
    def display_thumbnail(self):
        if self.image:
            return format_html('<img src="{}" alt="{}" />', self.thumbnail.url, self.thumbnail)
        return mark_safe(f'<span class="material-symbols-outlined" style="font-size: 50px;">person</span>')
    
    def clear(self):
        try:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        except Exception:
            pass
        try:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
        except Exception:
            pass

    def listen(self, image_field: models.ImageField):
        # Nếu tạo mới thêm vào
        if not self.pk:
            self.image = image_field
            self.save()
        # Nếu cập nhật thì xóa cũ và thêm mới
        elif self.image != image_field:
            self.clear()
            self.image = image_field
            self.save()
        else:
            pass
############################################
# User
############################################
class Tag(models.Model):
    title = models.CharField(_("title"), max_length=255)
    slug = models.CharField(_("slug"), max_length=255)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name=_("content type")
    )
    object_id = models.PositiveIntegerField(_("object id"))
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return self.title

    class Meta:
        db_table = "tags"
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

class User(AbstractUser):
    uuid = models.UUIDField(_("UUID"), default=uuid.uuid4, unique=True, editable=False)
    # avatar_obj= models.OneToOneField(ImageModel, on_delete=models.CASCADE, null=True, blank=True, default=None, related_name='user_avatar')
    avatar = models.ImageField(_("avatar"), upload_to="avatars/", null=True, blank=True, default=None)
    biography = models.TextField(_("biography"), null=True, blank=True, default=None)
    tags = GenericRelation(Tag)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    # config by user
    show_softdelete = models.BooleanField(_("show soft delete"), default=False, help_text=_("Show soft deleted items in the list view"))
    is_bot= models.BooleanField(_("is bot"), default=False, help_text=_("Designate whether the user is a bot account"))

    class Meta:
        db_table = "users"
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        s= self.username
        if self.is_bot:
            s+= ' (bot)'
        return s

    @property
    def full_name(self):
        s= ''
        if self.first_name and self.last_name:
            s= f"{self.last_name} {self.first_name}"
        if s:
            if self.is_bot:
                s+= ' (bot)'
        return s
    
    # ── Unfold avatar helper (unfold/helpers/avatar.html, unfold >= 0.105) ──
    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar and self.avatar.name else None

    @property
    def avatar_badge_count(self):
        """Unread notifications today, shown as a badge on the sidebar avatar."""
        from whiteneuron.notification.utils import unread_today_count
        count = unread_today_count(self)
        return count if count else None

    @property
    def avatar_badge_variant(self):
        return "danger" if self.avatar_badge_count else None

    @property
    def avatar_badge_url(self):
        if not self.avatar_badge_count:
            return None
        try:
            return reverse("admin:notification_notification_changelist") + "?is_read__exact=0"
        except Exception:
            return None

    def display_avatar(self):
        if self.is_bot:
            return mark_safe(f'<span class="material-symbols-outlined" style="font-size: 32px;">smart_toy</span>')
        if self.avatar:
            # print(instance.avatar.url)
            return format_html('<img src="{}" style="width: 32px; height: 32px; border-radius: 50%;">', self.avatar.url)
        return mark_safe(f'<span class="material-symbols-outlined" style="font-size: 32px;">person</span>')
    
    def display_header(self):
        # Hiển thị avatar bên cạnh username 
        user_url= reverse('admin:base_user_change', args=[self.id])
        return mark_safe(f"""
        <a href="{user_url}" style="text-decoration: none; color: inherit;">
            <div style="display: flex; align-items: center;">
                <div style="border-radius: 50%; overflow: hidden;">
                         {self.display_avatar()}
                </div>
                <div style="margin-left: 10px;">
                    {escape(self.username)}
                </div>
            </div>
        </a>
        """)
    
    def save(self, request=None, *args, **kwargs):
        # if not self.pk:
        #     self.avatar_obj = ImageModel.objects.create()
        # self.avatar_obj.listen(self.avatar)
        
        super().save(*args, **kwargs)

class UserProfile(User):
    class Meta:
        proxy = True
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return self.username

class VisitProfile(models.Model):
    ip_address = models.GenericIPAddressField(_("IP address"))
    user_agent = models.CharField(_("User agent"), max_length=500)
    first_seen = models.DateTimeField(_("First seen"), auto_now_add=True)
    last_seen = models.DateTimeField(_("Last seen"), auto_now=True)

    class Meta:
        db_table = "visit_profiles"
        verbose_name = _("visit profile")
        verbose_name_plural = _("visit profiles")
        unique_together = [["ip_address", "user_agent"]]
        indexes = [
            models.Index(fields=["ip_address"]),
            models.Index(fields=["first_seen"]),
            models.Index(fields=["last_seen"], name="visit_prof_last_seen_idx"),
        ]

    def __str__(self):
        return f"P{self.id} - {self.ip_address} - {truncatechars(self.user_agent, 20)}"


HTTP_METHOD_CHOICES = [
    ("GET", "GET"),
    ("POST", "POST"),
    ("PUT", "PUT"),
    ("PATCH", "PATCH"),
    ("DELETE", "DELETE"),
    ("HEAD", "HEAD"),
    ("OPTIONS", "OPTIONS"),
]


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile = models.ForeignKey(VisitProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='useractivities')
    path = models.CharField(_("Path"), max_length=255, null=True, blank=True)
    method = models.CharField(_("Method"), max_length=10, choices=HTTP_METHOD_CHOICES, null=True, blank=True)
    data = models.JSONField(_("Data"), null=True, blank=True)
    status_code = models.IntegerField(_("Status code"), null=True, blank=True)
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
    timelapse = models.DurationField(_("Timelapse"), null=True, blank=True) # Thời gian thực hiện hành động

    class Meta:
        db_table = "user_activities"
        verbose_name = _("user activity")
        verbose_name_plural = _("user activities")
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["profile", "timestamp"]),
            # changelist ordering, date_hierarchy, dashboard ranges, cleanup command
            models.Index(fields=["timestamp"], name="user_act_timestamp_idx"),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} - {self.path} at {self.timestamp}"


class AnonymousActivity(models.Model):
    profile = models.ForeignKey(VisitProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='anonymousactivities')
    path = models.CharField(_("Path"), max_length=255, null=True, blank=True)
    method = models.CharField(_("Method"), max_length=10, choices=HTTP_METHOD_CHOICES, null=True, blank=True)
    data = models.JSONField(_("Data"), null=True, blank=True)
    status_code = models.IntegerField(_("Status code"), null=True, blank=True)
    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True)
    timelapse = models.DurationField(_("Timelapse"), null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        db_table = "anonymous_activities"
        verbose_name = _("anonymous activity")
        verbose_name_plural = _("anonymous activities")
        indexes = [
            models.Index(fields=["profile", "timestamp"]),
            models.Index(fields=["timestamp"], name="anon_act_timestamp_idx"),
        ]

    def __str__(self):
        return f"{self.profile.ip_address if self.profile else 'N/A'} - {self.path} at {self.timestamp}"


############################################
# IP Blacklist (dynamic, managed via admin + Redis)
############################################
class IPBlacklist(models.Model):
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        unique=True,
        db_index=True,
        help_text=_("Single IPv4 or IPv6 address. Use IP_BLACKLIST in .env for CIDR ranges."),
    )
    reason = models.CharField(_("reason"), max_length=500, blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    blocked_until = models.DateTimeField(
        _("blocked until"),
        null=True,
        blank=True,
        help_text=_("Leave empty for permanent block. Temporary blocks expire automatically via Redis TTL."),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ip_blacklists",
        verbose_name=_("created by"),
    )

    class Meta:
        db_table = "ip_blacklists"
        verbose_name = _("IP blacklist")
        verbose_name_plural = _("IP blacklists")
        ordering = ["-created_at"]

    def __str__(self):
        return self.ip_address

    def _cache_key(self):
        return f"blacklist:dynamic:{self.ip_address}"

    def sync_cache(self):
        from django.core.cache import cache
        key = self._cache_key()
        try:
            if self.is_active:
                if self.blocked_until:
                    ttl = int((self.blocked_until - timezone.now()).total_seconds())
                    if ttl > 0:
                        cache.set(key, True, timeout=ttl)
                    else:
                        cache.delete(key)
                else:
                    cache.set(key, True, timeout=None)
            else:
                cache.delete(key)
        except Exception:
            pass

    LOADED_KEY = "blacklist:dynamic:loaded"

    @classmethod
    def ensure_cache_loaded(cls):
        """Re-populate the cache from the DB if it was flushed (Redis restart, new cache).

        A marker key tells whether the dynamic blocks are in the cache; when it is
        missing, the first caller rebuilds every active block.
        """
        from django.core.cache import cache
        try:
            if cache.add(cls.LOADED_KEY, 1, timeout=None):
                for block in cls.objects.filter(is_active=True):
                    block.sync_cache()
        except Exception:
            pass

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_cache()

    def delete(self, *args, **kwargs):
        from django.core.cache import cache
        try:
            cache.delete(self._cache_key())
        except Exception:
            pass
        super().delete(*args, **kwargs)


############################################
# UA Blacklist (dynamic, managed via admin + Redis)
############################################
UA_PATTERNS_CACHE_KEY = 'blacklist:ua_patterns'

class UABlacklist(models.Model):
    pattern = models.CharField(
        _("pattern"),
        max_length=500,
        unique=True,
        help_text=_("Substring or regex to match against the User-Agent header. E.g. 'GPTBot', 'https://openai.com'."),
    )
    is_regex = models.BooleanField(
        _("is regex"),
        default=False,
        help_text=_("If checked, pattern is treated as a Python regex (re.search, case-insensitive); otherwise simple case-insensitive substring match."),
    )
    reason = models.CharField(_("reason"), max_length=500, blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ua_blacklists",
        verbose_name=_("created by"),
    )

    class Meta:
        db_table = "ua_blacklists"
        verbose_name = _("UA blacklist")
        verbose_name_plural = _("UA blacklists")
        ordering = ["-created_at"]

    def __str__(self):
        return self.pattern

    @classmethod
    def rebuild_cache(cls):
        from django.core.cache import cache
        try:
            patterns = list(
                cls.objects.filter(is_active=True).values_list('pattern', 'is_regex')
            )
            cache.set(UA_PATTERNS_CACHE_KEY, patterns, timeout=None)
        except Exception:
            pass

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.__class__.rebuild_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.__class__.rebuild_cache()


############################################
# Base Model
############################################
from django.utils.html import format_html, format_html_join
from .thread_local import thread_local
from whiteneuron.notification.models import Notification


def _current_user():
    """User of the current request; falls back to the first superuser (commands, celery)."""
    request = getattr(thread_local, 'request', None)
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return user
    return User.objects.filter(is_superuser=True).order_by('pk').first()

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, verbose_name= _('Deleted'))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name= _('Deleted at'))

    class Meta:
        abstract = True  # Đây là một lớp trừu tượng, không tạo bảng trong DB

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        super(SoftDeleteModel, self).delete(using=using, keep_parents=keep_parents)

    def restore(self, request=None):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

class BaseManager(models.Manager):
    def get_queryset(self):
        return super(BaseManager, self).get_queryset().filter(is_hidden=False, is_deleted=False)

from django.urls import reverse
class BaseModel(SoftDeleteModel):
    id= models.AutoField(primary_key=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name= _('Date created'), db_index=True)
    created_by = models.ForeignKey(User, null=True, editable=False, verbose_name= _('Created by'),
                                   related_name='%(app_label)s_%(class)s_created', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name= _('Date updated'), db_index=True)
    updated_by = models.ForeignKey(User, null=True, editable=False, verbose_name= _('Updated by'),
                                   related_name='%(app_label)s_%(class)s_updated', on_delete=models.CASCADE)
    is_hidden = models.BooleanField(default=False, verbose_name= _('Hidden'))
    
    objects = BaseManager()
    objects_all = models.Manager()

    class Meta:
        abstract=True

    def path(self):
        # return f'/admin/{self._meta.app_label}/{self._meta.model_name}/{self.id}/'
        try:
            return reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
        except:
            return ''

    def delete(self, request=None, *args, **kwargs):
        super(BaseModel, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Trong các trường hợp không muốn gửi thông báo, gọi save(notification=False)
        notification = kwargs.pop('notification', True)
        user = _current_user()
        action = ''
        fields_changed = []
        if not self.pk:  # Nếu là tạo mới
            now = timezone.now()
            self.created_by = user
            self.updated_by = user
            self.created_at = now
            self.updated_at = now
            action = 'create'
        else:  # Nếu là cập nhật
            manager = self.__class__.objects_all if hasattr(self.__class__, 'objects_all') else self.__class__.objects
            old = manager.filter(pk=self.pk).first()
            if old is None:
                action = 'create'
            else:
                for attr in self.__dict__:
                    if attr in ('_state', 'created_at', 'created_by', 'updated_at', 'updated_by'):
                        continue
                    # chỉ so sánh các field của model
                    if not hasattr(self.__class__, attr):
                        continue
                    try:
                        if getattr(self, attr) != getattr(old, attr):
                            fields_changed.append((attr, getattr(old, attr), getattr(self, attr)))
                    except Exception:
                        pass
                if fields_changed:
                    self.updated_at = timezone.now()
                    self.updated_by = user
                    action = 'update'

        super(BaseModel, self).save(*args, **kwargs)  # Lưu đối tượng trước khi gửi thông báo

        if not notification or not action:
            return
        verbose_name = self._meta.verbose_name
        obj_link = self.path()
        if action == 'create':
            title = f'{_("New")} {verbose_name} "{self}" {_("has been created by user")} "{self.created_by}"'
            content_html = format_html(
                '<p>{} {} <strong>{} ({})</strong> {} <strong>{}</strong></p>',
                _('New'), verbose_name, self, self.pk, _('has been created by user'), self.created_by,
            )
            if obj_link:
                content_html += format_html('<p>{} <a href="{}">{}</a>.</p>', _('You can view it at'), obj_link, _('this link'))
            changed_data = []
        else:
            title = f'{_("Update")} {verbose_name} "{self}" ({self.pk}) {_("has been updated by user")} "{self.updated_by}"'
            changed_data = [
                {'field_name': name, 'old_value': old_value, 'new_value': new_value}
                for name, old_value, new_value in fields_changed
            ]
            content_html = format_html(
                '{} <strong>{}</strong> ({}) has been updated by user "{}" with the following changes: <ul>{}</ul>',
                verbose_name, self, self.pk, self.updated_by,
                format_html_join('', '<li>{}: {} -> {}</li>', fields_changed),
            )
        Notification.notify_superusers(
            title=title, content=content_html, action=action, flag='info',
            obj_link=obj_link or None, changed_data=changed_data,
            action_by=self.updated_by if action == 'update' else self.created_by,
        )

# ── M2M tracking ────────────────────────────────────────────────────────────
# Changes to ManyToMany fields (.add / .remove / .set / .clear) never call
# save(), so updated_at / updated_by would silently stay stale.
# We fix this by connecting to m2m_changed for every concrete BaseModel
# subclass.  A direct queryset update is used to avoid re-triggering save(),
# then a notification is sent to all superusers (same behaviour as save()).
from django.db.models.signals import class_prepared, m2m_changed as _m2m_changed, post_save


def _base_model_m2m_changed(sender, instance, action, pk_set, model, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if not isinstance(instance, BaseModel) or instance.pk is None:
        return

    user = _current_user()

    now = timezone.now()
    # Guard: if no user found, still update timestamps but skip notification
    if user is None:
        instance.__class__.objects_all.filter(pk=instance.pk).update(updated_at=now)
        instance.updated_at = now
        return
    # Use queryset.update() to avoid re-triggering save() / infinite loop
    instance.__class__.objects_all.filter(pk=instance.pk).update(updated_at=now, updated_by=user)
    instance.updated_at = now
    instance.updated_by = user

    # ── Resolve the M2M field name & verbose_name ──
    field_name = None
    field_verbose = None
    for f in instance.__class__._meta.local_many_to_many:
        if f.remote_field.through == sender:
            field_name = f.name
            field_verbose = str(f.verbose_name)
            break
    if field_name is None:
        field_name = sender.__name__
        field_verbose = field_name

    # ── Build change description (same format as save()) ──
    pk_list = list(pk_set or [])

    def _labels_from_qs(qs):
        """Return list of '__str__ (pk)' for a queryset."""
        return [f"{o} ({o.pk})" for o in qs]

    def _resolve_labels(pks):
        """Return list of '__str__ (pk)' for pk list, fallback to pk on error."""
        try:
            objs = {o.pk: o for o in model.objects.filter(pk__in=pks)}
            return [f"{objs[pk]} ({pk})" if pk in objs else str(pk) for pk in pks]
        except Exception:
            return [str(pk) for pk in pks]

    # current state (post-signal, so add already happened / remove already happened)
    try:
        current_qs = getattr(instance, field_name).all()
        current_labels = _labels_from_qs(current_qs)
    except Exception:
        current_labels = []

    if action == 'post_add':
        added_labels = _resolve_labels(pk_list)
        added_set = set(pk_list)
        old_value = [lbl for lbl in current_labels if not any(f"({pk})" in lbl for pk in added_set)]
        new_value = current_labels
        desc = f"{_('added')}: {added_labels}"
    elif action == 'post_remove':
        removed_labels = _resolve_labels(pk_list)
        old_value = current_labels + removed_labels
        new_value = current_labels
        desc = f"{_('removed')}: {removed_labels}"
    else:  # post_clear
        old_value = '(all)'
        new_value = []
        desc = str(_('cleared'))

    changed_data = [{'field_name': field_name, 'old_value': old_value, 'new_value': new_value}]

    title = (
        f'{_("Update")} {instance._meta.verbose_name} "{instance}" ({instance.pk}) '
        f'{_("has been updated by user")} "{user}"'
    )
    content_html = format_html(
        '{} <strong>{}</strong> ({}) has been updated by user "{}" with the following changes: '
        '<ul><li>{}: {}</li></ul>',
        instance._meta.verbose_name, instance, instance.pk, user, field_verbose, desc,
    )
    try:
        Notification.notify_superusers(
            title=title, content=content_html, action='update', flag='info',
            obj_link=instance.path() or None, changed_data=changed_data, action_by=user,
        )
    except Exception:
        pass


def _connect_m2m_for_base_model(sender, **kwargs):
    if sender._meta.abstract or not issubclass(sender, BaseModel):
        return
    for field in sender._meta.local_many_to_many:
        _m2m_changed.connect(_base_model_m2m_changed, sender=field.remote_field.through)


class_prepared.connect(_connect_m2m_for_base_model)
# ─────────────────────────────────────────────────────────────────────────────

############################################
# Image Model
############################################

from django.utils.html import format_html
from PIL import Image as PILImage
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import ImageOps

def handle_orientation(pilimage):
    """Apply the EXIF Orientation tag (all 8 cases); always returns a new image."""
    try:
        return ImageOps.exif_transpose(pilimage)
    except Exception:
        return pilimage.copy()

def save_pilimage_to_imagefield(pilimage, field, quality=85, max_size= None, new_name= None, save=True):
    """Resize (keeping aspect ratio, never upscaling) and store a PIL image in ``field``.

    The encoder follows the file extension (JPEG for .jpg/.jpeg, PNG otherwise) —
    previously PNG data was written to files named *.jpg.
    """
    img= handle_orientation(pilimage)
    if max_size is not None:
        img.thumbnail(max_size, PILImage.LANCZOS)

    filename = new_name or field.name.split('/')[-1]
    is_jpeg = filename.lower().endswith(('.jpg', '.jpeg'))
    if is_jpeg and img.mode != 'RGB':
        img = img.convert('RGB')

    buffer = BytesIO()
    if is_jpeg:
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
    else:
        img.save(buffer, format='PNG', optimize=True)
    field.save(filename, ContentFile(buffer.getvalue()), save=save)


MAX_SIZE= (1280, 1280)
THUMBNAIL_SIZE= (256, 256)
import os
class Image(BaseModel):
    image = models.ImageField(upload_to='images', verbose_name= _('Image'))
    thumbnail = models.ImageField(upload_to='images', verbose_name= _('Thumbnail'),
                                  blank=True, null=True)
    preview = models.ImageField(upload_to='images', verbose_name= _('Preview'),
                                blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name= _('Description'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('System image')
        verbose_name_plural = _('System images')

    def __str__(self):
        return self.image.name
    
    # kiểm tra bị mất ảnh
    def lost_data(self):
        return os.path.isfile(self.image.path) == False
    
    def getImage(self):
        if hasattr(self, 'img'):
            return self.img
        with self.image.open('rb') as fh, PILImage.open(fh) as raw:
            img = handle_orientation(raw)
        self.img= img
        return img
    
    def width(self):
        return self.getImage().width
    
    def height(self):
        return self.getImage().height
    
    def _derivative_url(self, field_name, max_size, suffix):
        """URL of a resized copy (thumbnail/preview), generated once if missing.

        Changelists call this for every row: when the file is already recorded it only
        builds the URL — no file is opened. A missing derivative is created and stored
        with a queryset update (no BaseModel.save → no extra SELECT / notifications).
        """
        field = getattr(self, field_name)
        if field and field.name:
            return field.url
        if not self.image or not self.image.name:
            return None
        base = os.path.splitext(os.path.basename(self.image.name))[0]
        try:
            with self.image.open('rb') as fh, PILImage.open(fh) as img:
                img.load()
                save_pilimage_to_imagefield(img, field, max_size=max_size,
                                            new_name=f"{base}_{suffix}.jpg", save=False)
        except Exception:
            return None
        if self.pk:
            type(self).objects_all.filter(pk=self.pk).update(**{field_name: field.name})
        return field.url

    def getImgThumbnailUrl(self):
        return self._derivative_url('thumbnail', THUMBNAIL_SIZE, 'thumbnail')

    def getImgPreviewUrl(self):
        return self._derivative_url('preview', MAX_SIZE, 'preview')

    def imgThumbnail(self):
        r= self.getImgThumbnailUrl()
        if r is None or self.image is None:
            mes= _('Image not found')
            return format_html('<p>{}</p>', mes)
        return format_html('<img src="{}" width="100" height="100" style="width: 100px; height: 100px; object-fit: cover;"/>', r)
    imgThumbnail.short_description = _('Thumbnail')

    def imgPreview(self):
        r= self.getImgPreviewUrl()
        img_url= self.image.url
        if r is None or self.image is None:
            mes= _('Image not found')
            return format_html('<p>{}</p>', mes)
        mes= _('View original image size')
        return format_html('<a href="{}" target="_blank"><img src="{}" width="512"/><br><small>{}</small></a>', img_url, r, mes)
    imgPreview.short_description = _('Preview')

    def url(self):
        return self.getImgPreviewUrl()
    
    def innerHTML(self):
        if self.image is None:
            return ''
        url= self.getImgPreviewUrl()
        html= f"""
<div class="cd-banner-area pb-20">
    <div class="container">
        <div class="row">
            <div class="col-12">
                <div class="cd-banner-img">
                    <img src="{url}" alt="">
                </div>
            </div>
        </div>
    </div>
</div>
""" 
        return html
    
    def hard_delete(self, *args, **kwargs):
        if self.image:
            try:
                self.image.delete(save= False) # Xóa file ảnh khi xóa object
            except Exception as e:
                print(f'Error when delete image: {e}')
        if self.thumbnail:
            try:
                self.thumbnail.delete(save= False) # Xóa file thumbnail khi xóa object
            except Exception as e:
                print(f'Error when delete thumbnail: {e}')
        if self.preview:
            try:
                self.preview.delete(save= False)
            except Exception as e:
                print(f'Error when delete preview: {e}')
        super(Image, self).hard_delete(*args, **kwargs)


    def save(self, *args, **kwargs):

        # Nếu preview thay đổi thì cập nhật thumbnail
        try:
            old= Image.objects.get(id= self.id) if self.id else None
        except:
            old= None
        if old and not old.image is None and not self.image is None and old.image != self.image:
            old.image.delete(save= False) # Xóa file ảnh cũ
            old.thumbnail.delete(save= False)
            old.preview.delete(save= False)

            self.thumbnail= None
            self.preview= None

        super(Image, self).save(*args, **kwargs)
        # Build derivatives at upload time instead of during the next changelist GET
        self.getImgThumbnailUrl()
        self.getImgPreviewUrl()

    def set_image_from_pilimage(self, pilimage, fname= None):
        save_pilimage_to_imagefield(pilimage, self.image, max_size=MAX_SIZE, new_name= fname, save=False)
        self.save()

############################################
# Mail
############################################

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import BadHeaderError
import smtplib
import ssl

class Mail(BaseModel):
    subject = models.CharField(max_length=255, verbose_name= _('Subject'))
    content = models.TextField(verbose_name= _('Content'))
    receiver = models.EmailField(verbose_name= _('Receiver'))
    status = models.CharField(max_length=25, choices= [('pending', _('Pending')),
                                                       ('sent', _('Sent')),
                                                       ('failed', _('Failed'))], 
                                                       default='pending', verbose_name= _('Status'))
    note = models.TextField(blank=True, null=True, verbose_name= _('Note'))

    class Meta:
        db_table = 'mail'
        verbose_name = _('Email notification')
        verbose_name_plural = _('Email notifications')

    def __str__(self):
        return self.subject
    
    def save(self, *args, **kwargs):
        super(Mail, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super(Mail, self).delete(*args, **kwargs)

    def send(self):
        if not self.receiver:
            self.status = 'failed'
            self.note = 'No receiver'
            self.save()
            return
        try:
            # send_mail uses the configured EMAIL_BACKEND / SMTP settings (with TLS verification)
            send_mail(
                self.subject,
                self.content,
                settings.EMAIL_ALIAS_USER,
                [self.receiver],
                html_message= self.content,
                fail_silently=False,
            )
            print("Email sent successfully")
            self.status = 'sent'
            self.note = "Email sent successfully"
        except BadHeaderError:
            print("Invalid header found.")
            self.note = "Invalid header found."
            self.status = 'failed'
        except smtplib.SMTPException as e:
            print(f"SMTP error occurred: {e}")
            self.note = f"SMTP error occurred: {e}"
            self.status = 'failed'
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.note = f"An unexpected error occurred: {e}"
            self.status = 'failed'
        self.save()

    def is_sent(self):
        return self.status == 'sent'
    

# Apps
class App(BaseModel):
    name = models.CharField(max_length=255, verbose_name= _('App name'))
    is_active = models.BooleanField(default=True, verbose_name= _('Active'))
    icon= models.CharField(max_length=255, blank=True, null=True, verbose_name= _('Icon'), help_text= _('Icon name (Material Symbols Outlined) or URL'))
    url = models.URLField(blank=True, null=True, verbose_name= _('URL'))
    category = models.CharField(max_length=255, blank=True, null=True, verbose_name= _('Category'))
    permission= models.CharField(max_length=255, blank=True, null=True, verbose_name= _('Permission'), help_text= _('Permission required to access this app'))
    thumbnail_url= models.URLField(blank=True, null=True, verbose_name= _('Thumbnail URL'))

    class Meta:
        verbose_name = _('App')
        verbose_name_plural = _('Apps')
        ordering = ['id']

    def __str__(self):
        if self.name:
            return str(_(self.name))  # __str__ must return str, not a lazy proxy
        return f'App {self.id}'


# ── Gửi email thông tin đăng nhập khi tạo user mới ─────────────────────────
# Hoạt động với MỌI nguồn tạo user (admin form, API, management command, shell...).
# Nếu admin form đã tự xử lý (save_model), nó sẽ đặt flag _skip_new_user_email=True
# trên instance để tránh gửi email 2 lần.
def _send_email_to_new_user(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(instance, '_skip_new_user_email', False):
        return
    if not instance.email:
        return
    # Only users created without a password (e.g. invited by e-mail) get a generated
    # one: never overwrite a password set by create_user()/createsuperuser/fixtures.
    if instance.has_usable_password():
        return
    from .utils import send_email_login, make_random_password
    password = make_random_password()
    instance.set_password(password)
    instance.save(update_fields=['password'])
    transaction.on_commit(lambda: send_email_login(instance.username, password, instance.email))


post_save.connect(
    _send_email_to_new_user,
    sender=User,
    dispatch_uid='base.models._send_email_to_new_user',
)