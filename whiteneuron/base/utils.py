from django.utils import timezone
from .models import User, UserActivity, AnonymousActivity
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy

# count time run function
def timeit(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        # print(f"{func.__name__} run in {time.time()-start} seconds")
        return result
    return wrapper

from django.utils import timezone
from django.core.exceptions import FieldDoesNotExist

def base_badge_callback(request, model, filter_kwargs=None):
    today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)

    # try:
    #     model._meta.get_field("is_deleted")
    #     model._meta.get_field("deleted_at")
    #     has_soft_delete = True
    # except FieldDoesNotExist:
    #     has_soft_delete = False

    # if has_soft_delete:
    #     number_update = model.objects.filter(
    #         is_deleted=False,
    #         updated_at__gte=today,
    #     ).count()
        
    #     number_delete= getattr(model, 'objects_all', model.objects).filter(is_deleted=True,deleted_at__gte= timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    #     print("model:",model.__name__,"number_delete:",number_delete)

    #     c = number_update - number_delete
    # else:
    #     c = model.objects.filter(
    #         updated_at__gte=today,
    #     ).count()

    c = getattr(model, 'objects_all', model.objects)
    if hasattr(model, 'updated_at'):
        c = c.filter(
          updated_at__gte=today,
        )
    elif hasattr(model, 'created_at'):
        c = c.filter(
          created_at__gte=today,
        )
        
    if filter_kwargs:
        c = c.filter(**filter_kwargs).count()
    else:        
        c = c.count()
    return c


def user_badge_callback(request):
    return base_badge_callback(request, User)

def useractivity_badge_callback(request):
    c= UserActivity.objects.filter(timestamp__gte= timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    if c==0:
        return ''
    return f"{c}"

def anonymousactivity_badge_callback(request):
    c= AnonymousActivity.objects.filter(timestamp__gte= timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    if c==0:
        return ''
    return f"{c}"

def visitprofile_badge_callback(request):
    from .models import VisitProfile
    c = VisitProfile.objects.count()
    if c == 0:
        return ''
    return f"{c}"

def user_badge_callback(request):
    return base_badge_callback(request, User)

def group_badge_callback(request):
    return 0

def app_badge_callback(request):
    from django.conf import settings
    try:
        navigation = settings.UNFOLD.get('SIDEBAR', {}).get('navigation', [])
        return sum(
            1 for section in navigation for item in section.get('items', [])
            if item.get('title') and item.get('link') and '/base/app/' not in str(item.get('link'))
        )
    except Exception:
        return 0

def is_guest_user(user):
    if not user or not user.is_authenticated:
        return True
    if user.username.lower() == "guest":
        return True
    return user.groups.filter(name__in=["Khách thăm", "Guest", "guest"]).exists()


def permission_callback(request):
    return False

def permission_superuser_callback(request):
    return request.user.is_superuser

def permission_admin_callback(request):
    if request.user.is_superuser:
        return True
    return request.user.groups.filter(name='Quản trị viên').exists()

def permission_non_guest_callback(request):
    return not is_guest_user(request.user)

def permission_viewer_callback(request):
    if not request.user.is_authenticated:
        return False
    return True


import os as _os

def _load_signature():
    sig_path = _os.path.normpath(
        _os.path.join(_os.path.dirname(__file__), '..', 'templates', 'admin', 'signature.html')
    )
    with open(sig_path, 'r', encoding='utf-8') as f:
        return f.read()


TEMPLATE="""
Chào {username},
<br />
Bạn đã được cấp quyền truy cập vào <b>{system_name}</b>. Dưới đây là thông tin
đăng nhập của bạn:
<br />
<b> Tên đăng nhập: {username} </b>
<br />
<b> Mật khẩu tạm thời: {password} </b>
<br />
<b> Lưu ý: </b> Bạn sẽ được yêu cầu thay đổi mật khẩu sau lần đăng nhập đầu tiên
để đảm bảo an toàn cho thông tin cá nhân và tài khoản của bạn.
<br />
<br />
Để đăng nhập, vui lòng truy cập <a href="{url}">đường dẫn trang đăng nhập</a> và
nhập thông tin trên.
<br />
Nếu bạn gặp bất kỳ vấn đề nào trong quá trình đăng nhập, đừng ngần ngại liên hệ
với bộ phận hỗ trợ kỹ thuật của chúng tôi.
<br />
Trân trọng,
<br />
{signature}
"""

from django.conf import settings
from .models import Mail
def send_email_login(username, password, receiver, is_reset=False):
    global TEMPLATE
    SUBJECT = "Đặt lại mật khẩu hệ thống" if is_reset else "Thông tin đăng nhập hệ thống"
    SYSTEM_NAME= settings.NAME
    URL= settings.URL
    subject= SUBJECT
    template= TEMPLATE
    system_name= SYSTEM_NAME
    context= template.format(username= username, password= password, url= URL, system_name= system_name, signature= _load_signature())
    mail= Mail.objects.create(subject= subject, content= context, receiver= receiver)
    mail.send()
    return mail.is_sent()

def make_random_password():
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

from django.utils.safestring import mark_safe
def announcement_callback(request):
    from django.conf import settings
    if not getattr(settings, 'ANNOUNCEMENT_CONTENT_HTML_FILE', None):
        return None
    version = getattr(settings, 'VERSION', '0.1.0')
    return {
        "title": format_lazy(
            _("New announcement for {NAME} - version {VERSION}!"),
            NAME=_(settings.NAME),
            VERSION=version,
        ),
        "version": version,
        "badge": _("NEW"),
    }
