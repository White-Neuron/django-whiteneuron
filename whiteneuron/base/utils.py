from django.utils import timezone
from .models import User, UserActivity, App
from django.contrib.auth.models import Group

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

    c = getattr(model, 'objects_all', model.objects).filter(
      updated_at__gte=today,
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

def user_badge_callback(request):
    return base_badge_callback(request, User)

def group_badge_callback(request):
    return 0

def app_badge_callback(request):
    return base_badge_callback(request, App)

def permission_callback(request):
    return False

def permission_superuser_callback(request):
    return request.user.is_superuser

def permission_admin_callback(request):
    if request.user.is_superuser:
        return True
    return request.user.groups.filter(name='Quản trị viên').exists()

def permission_non_guest_callback(request):
    return not request.user.groups.filter(name='Khách thăm').exists()

def prmission_viewer_callback(request):
    return True


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
<div dir="ltr">
  <table
    cellpadding="0"
    cellspacing="0"
    style="
      white-space: nowrap;
      color: rgb(0, 0, 0);
      border-collapse: collapse;
      table-layout: fixed;
      font-family: Arial;
    "
  >
    <tbody>
      <tr>
        <td style="vertical-align: top; padding: 4px 16px 0px 0px">
          <table
            cellpadding="0"
            cellspacing="0"
            width="120px"
            style="
              border-collapse: collapse;
              table-layout: fixed;
              margin: 0px auto;
            "
          >
            <tbody>
              <tr>
                <td style="vertical-align: top">
                  <img
                    src="https://ci3.googleusercontent.com/mail-sig/AIorK4xT4rd9QM6AKtfHJrkL5q-vAckl7ehKZ1PACpIy0Lg-x09Zwo-6VHjO8A4a2phJJbLsi8bX6OxpueMP"
                    alt="logo image"
                    style="
                      display: block;
                      max-width: 100%;
                      height: auto;
                      margin-bottom: 6px;
                      border-radius: 50%;
                    "
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </td>
        <td
          style="
            vertical-align: top;
            border-left-width: 1px;
            border-left-style: solid;
            border-left-color: rgb(0, 0, 0);
            padding: 0px 0px 0px 16px;
          "
        >
          <table
            cellpadding="0"
            cellspacing="0"
            style="border-collapse: collapse; table-layout: fixed"
          >
            <tbody>
              <tr>
                <td style="vertical-align: top; line-height: 24px">
                  <span
                    style="
                      font-size: 18px;
                      margin: 0px;
                      padding: 0px 20px 0px 0px;
                      color: rgb(17, 17, 17);
                      font-weight: bold;
                    "
                    >Tu Anh Nguyen</span
                  >
                </td>
              </tr>
              <tr>
                <td style="vertical-align: top; line-height: 24px">
                  <span
                    style="
                      font-size: 14px;
                      margin: 0px;
                      padding: 0px 0px 0px 0px;
                    "
                    >White Neuron Co., Ltd</span
                  >
                  <span
                    style="
                      font-size: 14px;
                      margin: 0px;
                      padding: 0px 8px 0px 8px;
                      border-left-width: 1px;
                      border-left-style: solid;
                      border-left-color: rgb(0, 0, 0);
                    "
                    > Founder & CTO</span
                  >
                </td>
              </tr>
              <tr>
                <td style="vertical-align: top; line-height: 16px">
                  <a
                    href="tel:+84339802255"
                    rel="nofollow noreferrer"
                    style="text-decoration: none"
                    target="_blank"
                    ><span
                      style="
                        font-size: 12px;
                        margin: 0px;
                        padding: 0px 20px 0px 0px;
                        color: rgb(0, 0, 0);
                      "
                      >+84339802255</span
                    ></a
                  >
                </td>
              </tr>
              <tr>
                <td style="vertical-align: top; line-height: 16px">
                  <a
                    href="mailto:anhnt@whiteneuron.ai"
                    rel="nofollow noreferrer"
                    style="text-decoration: none"
                    target="_blank"
                    ><span
                      style="
                        font-size: 12px;
                        margin: 0px;
                        padding: 0px 20px 0px 0px;
                        color: rgb(0, 0, 0);
                      "
                      >anhnt@whiteneuron.ai</span
                    ></a
                  >
                </td>
              </tr>
              <tr>
                <td style="vertical-align: top; line-height: 16px">
                  <a
                    href="https://whiteneuron.ai/"
                    rel="nofollow noreferrer"
                    style="text-decoration: none"
                    target="_blank"
                    ><span
                      style="
                        font-size: 12px;
                        margin: 0px;
                        padding: 0px 20px 0px 0px;
                        color: rgb(0, 0, 0);
                      "
                      >https://whiteneuron.ai</span
                    ></a
                  >
                </td>
              </tr>
              <tr>
                <td style="vertical-align: top; line-height: 16px">
                  <a
                    href="https://www.google.com/maps/search/?api=1&amp;query=333%2C%2020%20cluster%2C%20Kien%20Hung%20Ward%2C%20Ha%20Dong%20district%2C%20Ha%20Noi%2010000%20Vietnam"
                    rel="nofollow noreferrer"
                    style="text-decoration: none"
                    target="_blank"
                    ><span
                      style="
                        font-size: 12px;
                        margin: 0px;
                        padding: 0px 20px 0px 0px;
                        color: rgb(0, 0, 0);
                      "
                      >333, 20 cluster, Kien Hung, Hanoi, Vietnam</span
                    ></a
                  >
                </td>
              </tr>
              <tr>
                <td style="vertical-align: top; line-height: 24px">
                  <table
                    cellpadding="0"
                    cellspacing="0"
                    style="
                      border-collapse: collapse;
                      table-layout: fixed;
                      margin: 8px 0px 0px;
                    "
                  >
                    <tbody>
                      <tr>
                        <td
                          style="vertical-align: top; padding: 0px 6px 0px 0px"
                        >
                          <a
                            href="https://www.youtube.com/@neuron97"
                            rel="noreferrer"
                            target="_blank"
                            ><img
                              src="https://api.logo.com/api/v2/icons/circle/FFFFFF/111111/youtube.png?u=asdfg"
                              alt="youtube icon"
                              style="display: block; width: 23px; height: 23px"
                          /></a>
                        </td>
                        <td
                          style="vertical-align: top; padding: 0px 6px 0px 0px"
                        >
                          <a
                            href="https://www.facebook.com/tuanh.226"
                            rel="noreferrer"
                            target="_blank"
                            ><img
                              src="https://api.logo.com/api/v2/icons/circle/FFFFFF/111111/facebook.png?u=asdfg"
                              alt="facebook icon"
                              style="display: block; width: 23px; height: 23px"
                          /></a>
                        </td>
                        <td style="vertical-align: top">
                          <a
                            href="https://www.tiktok.com/@anhneuron"
                            rel="noreferrer"
                            target="_blank"
                            ><img
                              src="https://api.logo.com/api/v2/icons/circle/FFFFFF/111111/tiktok.png?u=asdfg"
                              alt="tiktok icon"
                              style="display: block; width: 23px; height: 23px"
                          /></a>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </tbody>
          </table>
        </td>
      </tr>
    </tbody>
  </table>
</div>
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
    context= template.format(username= username, password= password, url= URL, system_name= system_name)
    mail= Mail.objects.create(subject= subject, content= context, receiver= receiver)
    mail.send()
    return mail.is_sent()

def make_random_password():
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))