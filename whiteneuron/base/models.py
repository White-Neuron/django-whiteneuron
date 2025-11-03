from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


from django.db import models
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
import os
from django.utils.safestring import mark_safe

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
        return mark_safe(f'<img src="{self.image.url}" alt="{self.image}" />')
    
    def display_thumbnail(self):
        if self.image:
            return mark_safe(f'<img src="{self.thumbnail.url}" alt="{self.thumbnail}" />')
        return mark_safe(f'<span class="material-symbols-outlined" style="font-size: 50px;">person</span>')
    
    def clear(self):
        try:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        except:
            pass
        try:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
        except:
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
        return self.tag

    class Meta:
        db_table = "tags"
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

from django.contrib.auth.models import Group
class User(AbstractUser):
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
            s= f"{self.last_name}, {self.first_name}"
        if s:
            if self.is_bot:
                s+= ' (bot)'
        else:
            return s
    
    def display_avatar(self):
        if self.is_bot:
            return mark_safe(f'<span class="material-symbols-outlined" style="font-size: 32px;">smart_toy</span>')
        if self.avatar:
            # print(instance.avatar.url)
            return mark_safe(f'<img src="{self.avatar.url}" style="width: 32px; height: 32px; border-radius: 50%;">')
        return mark_safe(f'<span class="material-symbols-outlined" style="font-size: 32px;">person</span>')
    
    def display_header(self):
        # Hiển thị avatar bên cạnh username 
        return mark_safe(f"""
        <a href="/admin/base/user/{self.id}/change/">
            <div style="display: flex; align-items: center;">
                <div style="border-radius: 50%; overflow: hidden;">
                         {self.display_avatar()}
                </div>
                <div style="margin-left: 10px;">
                    {self.username}
                </div>
            </div>
        </a>
        """)
    
    def save(self, request=None, *args, **kwargs):
        # if not self.pk:
        #     self.avatar_obj = ImageModel.objects.create()
        # self.avatar_obj.listen(self.avatar)
        
        # Nếu tạo mới thi mac dinh is_staff = True
        fl= False
        if not self.pk:
            self.is_staff = True
            fl= True
        super().save(*args, **kwargs)
        if fl:
            try:
                group_staff= Group.objects.get(name='Nhân viên')
                self.groups.add(group_staff)
            except:
                print('Group Nhân viên không tồn tại')
                pass

class UserProfile(User):
    class Meta:
        proxy = True
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return self.username

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.TextField(_("User agent"), null=True, blank=True)
    path = models.CharField(_("Path"), max_length=255, null=True, blank=True)
    method = models.CharField(_("Method"), max_length=10, choices=[("GET", "GET"), ("POST", "POST")], null=True, blank=True)
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
        ]

    def __str__(self):
        return f"{self.user.username} - {self.path} at {self.timestamp}"


############################################
# Base Model
############################################
from .thread_local import thread_local
from whiteneuron.notification.models import Notification
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

    created_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name= _('Date created'))
    created_by = models.ForeignKey(User, null=True, editable=False, verbose_name= _('Created by'),
                                   related_name='%(app_label)s_%(class)s_created', on_delete=models.CASCADE)
    updated_at = models.DateTimeField(default=timezone.now, editable=False, verbose_name= _('Date updated'))
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
        request = getattr(thread_local, 'request', None)
        # save created_by and updated_by when create or update
        # Lấy tham số notification từ kwargs, mặc định là True
        # Trong các trường hợp không muốn gửi thông báo, có thể gọi save với notification= False: ví dụ obj.save(notification= False)
        notification= kwargs.pop('notification', True)
        title= ''
        content_html= ''
        action= ''
        if request is None:
            user= User.objects.filter(is_superuser=True).first()
        else:
            user= request.user
            if user.is_anonymous:
                user= User.objects.filter(is_superuser=True).first()
        changed_data= []
        if not self.pk:  # Nếu là tạo mới
            self.created_by = user
            self.updated_by = user
            self.created_at = timezone.now()
            self.updated_at = timezone.now()
            action= 'create'
            if notification: title= f"{_('New')} {self._meta.verbose_name} \"{self}\" {_('has been created by user')} \"{self.created_by}\"" 
        elif notification:  # Nếu là cập nhật và có yêu cầu gửi thông báo
            fields_changed= []
            if hasattr(self.__class__, 'objects_all'):
                old= self.__class__.objects_all.get(pk= self.pk)
            else:
                old= self.__class__.objects.get(pk= self.pk)
            for attr in self.__dict__:
                if attr in ['_state', 'created_at', 'created_by', 'updated_at', 'updated_by']:
                    continue
                # kiểm tra attr có phải là field không
                if not hasattr(self.__class__, attr):
                    continue
                try:
                    if getattr(self, attr) != getattr(old, attr):
                        fields_changed.append((attr, getattr(old, attr), getattr(self, attr)))
                except Exception as e:
                    print(e)
                    pass
            if fields_changed:
                self.updated_at = timezone.now()
                self.updated_by = user
                action= 'update'
                title= f"{_('Update')} {self._meta.verbose_name} <strong>{self}</strong>({self.id}) {_('has been updated by user')} \"{self.updated_by}\""
                content_html= f"{self._meta.verbose_name} <strong>{self}</strong>({self.id}) has been updated by user \"{self.updated_by}\" with the following changes: <ul>"
                for field in fields_changed:
                    changed_data.append({
                        'field_name': field[0],
                        'old_value': field[1],
                        'new_value': field[2]
                    })
                    content_html+= f"<li>{field[0].verbose_name if hasattr(field[0], 'verbose_name') else field[0]}: {field[1]} -> {field[2]}</li>"
                content_html+= "</ul>"
        
        super(BaseModel, self).save(*args, **kwargs)  # Lưu đối tượng trước khi gửi thông báo
        # Gửi thông báo đến người dùng
        if title and notification:
            if action == 'create':
                content_html= f"""
<p>{_('New')} {self._meta.verbose_name} <strong>{self}({self.id})</strong> {_('has been created by user')} <strong>{self.created_by}</strong></p>
"""
                if self.path():
                    content_html+= f"""<p>{_('You can view it at')} <a href="{self.path()}">{_('this link')}</a>.</p>"""

            obj_link= self.path() if hasattr(self, 'path') else None
            for user in User.objects.filter(is_superuser= True):
                obj= Notification.objects.create(user= user, title= title,
                                                    flag= 'info',
                                                    action= action,
                                                    obj_link= obj_link,
                                                    changed_data= str(changed_data),
                                                    content= content_html)
                obj.alert()

############################################
# Image Model
############################################

from django.utils.html import format_html
from PIL import Image as PILImage
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
from PIL import ExifTags

def handle_orientation(pilimage):
    img= pilimage
    # Xử lý EXIF Orientation nếu có
    try:
        # Lấy metadata EXIF
        exif = img._getexif()
        if exif:
            # Lấy thông tin về Orientation
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif_orientation = exif.get(orientation)

            # Điều chỉnh ảnh theo Orientation
            if exif_orientation == 3:
                img = img.rotate(180, expand=True)
            elif exif_orientation == 6:
                img = img.rotate(270, expand=True)
            elif exif_orientation == 8:
                img = img.rotate(90, expand=True)

    except AttributeError:
        # Nếu ảnh không có EXIF, bỏ qua
        pass
    return img

def save_pilimage_to_imagefield(pilimage, field, quality=100, max_size= None, new_name= None):
    img= pilimage

    img= handle_orientation(img)

    if max_size is not None:
        # max size cho mỗi chiều, giữ nguyên tỷ lệ
        h= img.height
        w= img.width
        if h > w:
            max_h= max_size[1] if h > max_size[1] else h
            max_w= int(max_h / h * w)
        else:
            max_w= max_size[0] if w > max_size[0] else w
            max_h= int(max_w / w * h)
        max_size= (max_w, max_h)
        img= img.resize(max_size, PILImage.LANCZOS)
    if img.mode != 'RGB':
        img= img.convert('RGB')

    if new_name is None:
        filename= field.name.split('/')[-1]
    else:
        filename= new_name

    tempfile= img
    tempfile_io= BytesIO()
    tempfile.save(tempfile_io, format='PNG', quality=quality)
    image_file= InMemoryUploadedFile(tempfile_io, None, filename, 'image/png', tempfile_io.tell(), None)
    field.save(filename, image_file)


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
        img= handle_orientation(PILImage.open(self.image))
        self.img= img
        return img
    
    def width(self):
        return self.getImage().width
    
    def height(self):
        return self.getImage().height
    
    def getImgThumbnailUrl(self):
        fl= True
        try:
            self.thumbnail.url
        except:
            # Nếu không có ảnh thumbnail thì lấy ảnh preview giảm kích thước để làm thumbnail
            fl= False
        try:
            img= PILImage.open(self.thumbnail)
        except:
            fl= False
        if not fl:
            try:
                img= PILImage.open(self.image)
            except:
                return None
            save_pilimage_to_imagefield(img, self.thumbnail, max_size=THUMBNAIL_SIZE, new_name= self.image.name.split('/')[-1][:-4] + '_thumbnail.jpg')
        return self.thumbnail.url
    
    def getImgPreviewUrl(self):
        fl= True
        try:
            self.preview.url
        except:
            fl= False
        try:
            img= PILImage.open(self.preview)
        except:
            fl= False

        if not fl:
            # Nếu không có ảnh preview thì giảm kích thước ảnh gốc để làm preview
            try:
                img= PILImage.open(self.image)
            except:
                return None
            save_pilimage_to_imagefield(img, self.preview, max_size=MAX_SIZE, new_name= self.image.name.split('/')[-1][:-4] + '_preview.jpg')
        return self.preview.url

    def imgThumbnail(self):
        r= self.getImgThumbnailUrl()
        if r is None or self.image is None:
            mes= _('Image not found')
            return format_html(f'<p>{mes}</p>')
        return format_html('<img src="{}" width="100" height="100" style="width: 100px; height: 100px; object-fit: cover;"/>', r)
    imgThumbnail.short_description = _('Thumbnail')

    def imgPreview(self):
        r= self.getImgPreviewUrl()
        img_url= self.image.url
        if r is None or self.image is None:
            mes= _('Image not found')
            return format_html(f'<p>{mes}</p>')
        mes= _('View original image size')
        return format_html(f"""<a href="{img_url}" target="_blank"><img src="{r}" width="512"/>
                            <br><small>{mes}</small>
                           </a>""")
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

    def set_image_from_pilimage(self, pilimage, fname= None):
        save_pilimage_to_imagefield(pilimage, self.image, max_size=MAX_SIZE, new_name= fname)
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
            context = ssl._create_unverified_context()
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
                send_mail(
                    self.subject,
                    self.content,
                    settings.EMAIL_HOST_USER,
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

# Init data cho bảng App with Model Manager and Settings
# UNFOLD = {
#.    ..........
#     "SIDEBAR": {
#         "show_search": True,
#         "show_all_applications": False,
#         "navigation": [
#             {
#                 "title": _("Navigation"),
#                 "items": [
#                     {
#                         "title": _("Dashboard"),
#                         "icon": "dashboard",
#                         "link": reverse_lazy("admin:index"),
#                     },
#                     {
#                         "title": _("Notifications"),
#                         "icon": "notifications",
#                         "link": reverse_lazy("admin:notification_notification_changelist"),
#                         "badge": "whiteneuron.notification.utils.notification_badge_callback",
#                     },
#                     {
#                         "title": _("Feedbacks"),
#                         "icon": "feedback",
#                         "link": reverse_lazy("admin:feedbacks_feedbackdata_changelist"),
#                         "badge": "whiteneuron.feedbacks.utils.feedback_data_badge_callback",
#                     },
#                 ],
#             },
#             {
#                 "title": _("File Management"),
#                 "collapsible": True,
#                 "items": [
#                     {
#                         "title": _("Excel Files"),
#                         "icon": "table",
#                         "link": reverse_lazy("admin:file_management_excelfile_changelist"),
#                         "badge": "whiteneuron.file_management.utils.excelfile_badge_callback",
#                         "permission": "whiteneuron.base.utils.permission_non_guest_callback",
#                     },
#                     {
#                         "title": _("PDF Files"),
#                         "icon": "picture_as_pdf",
#                         "link": reverse_lazy("admin:file_management_pdffile_changelist"),
#                         "badge": "whiteneuron.file_management.utils.pdffile_badge_callback",
#                         "permission": "whiteneuron.base.utils.permission_non_guest_callback",
#                     },
#                 ],
#             },
#             {
#                 "title": _("Users & Groups"),
#                 "collapsible": True,
#                 "items": [
#                     {
#                         "title": _("Users"),
#                         "icon": "person",
#                         "link": reverse_lazy("admin:base_user_changelist"),
#                         "badge": "whiteneuron.base.utils.user_badge_callback",
#                         "permission": "whiteneuron.base.utils.permission_admin_callback",
#                     },
#                     {
#                         "title": _("User activity"),
#                         "icon": "history",
#                         "link": reverse_lazy("admin:base_useractivity_changelist"),
#                         "badge": "whiteneuron.base.utils.useractivity_badge_callback",
#                         "permission": "whiteneuron.base.utils.permission_admin_callback",
#                     },
#                     {
#                         "title": _("Groups"),
#                         "icon": "group",
#                         "link": reverse_lazy("admin:auth_group_changelist"),
#                         "badge": "whiteneuron.base.utils.group_badge_callback",
#                         "permission": "whiteneuron.base.utils.permission_admin_callback",
#                     },
#                 ],
#             },
#             {
#                 "title": _("System"),
#                 "collapsible": True,
#                 "items": [
#                     {
#                         "title": _("Images"),
#                         "icon": "image",
#                         "link": reverse_lazy("admin:base_image_changelist"),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                     {
#                         "title": _("Emails"),
#                         "icon": "email",
#                         "link": reverse_lazy("admin:base_mail_changelist"),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                     {
#                         "title": _("Notifications config"),
#                         "icon": "notifications",
#                         "link": reverse_lazy("admin:notification_notificationconfig_changelist"),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     }
#                 ],
#             },
#             {
#                 "title": _("Celery Tasks"),
#                 "collapsible": True,
#                 "items": [
#                     {
#                         "title": _("Clocked"),
#                         "icon": "hourglass_bottom",
#                         "link": reverse_lazy(
#                             "admin:django_celery_beat_clockedschedule_changelist"
#                         ),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                     {
#                         "title": _("Crontabs"),
#                         "icon": "update",
#                         "link": reverse_lazy(
#                             "admin:django_celery_beat_crontabschedule_changelist"
#                         ),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                     {
#                         "title": _("Intervals"),
#                         "icon": "arrow_range",
#                         "link": reverse_lazy(
#                             "admin:django_celery_beat_intervalschedule_changelist"
#                         ),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                     {
#                         "title": _("Periodic tasks"),
#                         "icon": "task",
#                         "link": reverse_lazy(
#                             "admin:django_celery_beat_periodictask_changelist"
#                         ),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                     {
#                         "title": _("Solar events"),
#                         "icon": "event",
#                         "link": reverse_lazy(
#                             "admin:django_celery_beat_solarschedule_changelist"
#                         ),
#                         "permission": "whiteneuron.base.utils.permission_superuser_callback",
#                     },
#                 ],
#             },
#         ],
#     },
# }

class App(BaseModel):
    name = models.CharField(max_length=255, verbose_name= _('App name'))
    is_active = models.BooleanField(default=True, verbose_name= _('Active'))
    icon= models.CharField(max_length=255, blank=True, null=True, verbose_name= _('Icon'), help_text= _('Icon name (Material Symbols Outlined) or URL'))
    url = models.URLField(blank=True, null=True, verbose_name= _('URL'))
    category = models.CharField(max_length=255, blank=True, null=True, verbose_name= _('Category'))
    permission= models.CharField(max_length=255, blank=True, null=True, verbose_name= _('Permission'), help_text= _('Permission required to access this app'))
    class Meta:
        verbose_name = _('App')
        verbose_name_plural = _('Apps')
        ordering = ['id']

    def __str__(self):
        if self.name:
            return self.name
        return f'App {self.id}'