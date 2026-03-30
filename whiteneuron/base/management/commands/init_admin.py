# Khởi tạo admin interface theme cho hệ thống sử dụng BaseCommand

import secrets
import string
from os import environ

from django.core.management.base import BaseCommand
from whiteneuron.base.models import User
from whiteneuron.base.utils import send_email_login


def _generate_password(length: int = 20) -> str:
    """Sinh mật khẩu ngẫu nhiên mạnh: chữ hoa, thường, số, ký tự đặc biệt."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()-_=+'
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Đảm bảo đủ các loại ký tự
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in '!@#$%^&*()-_=+' for c in password)
        ):
            return password


def _apply_password(user: 'User', is_reset: bool = False) -> None:
    """Đặt mật khẩu cho user và gửi email nếu là random."""
    password = environ.get('INIT_ADMIN_PASSWORD') or _generate_password()
    is_random = not environ.get('INIT_ADMIN_PASSWORD')

    # Validate email TRƯỚC khi thay đổi password để tránh mất password mà không gửi được
    recipient = None
    if is_random:
        recipient = user.email or environ.get('INIT_ADMIN_EMAIL', '')
        if not recipient:
            raise ValueError(
                'Không tìm thấy địa chỉ email để gửi mật khẩu. '
                'Vui lòng đặt biến môi trường INIT_ADMIN_EMAIL hoặc đảm bảo tài khoản admin có email.'
            )

    user.set_password(password)
    # User mới (chưa có pk) cần full save; user đã tồn tại chỉ cần update password
    if user.pk:
        user.save(update_fields=['password'])
    else:
        user.save()

    action = 'Reset' if is_reset else 'Tạo'
    print(f'{action} mật khẩu cho admin thành công')

    if is_random:
        print(f'  >> Mật khẩu tạm thời: {password}')
        print(f'  >> Đang gửi email đến {recipient} …')
        send_email_login(username='admin', password=password, receiver=recipient, is_reset=is_reset)
    else:
        print('  >> Mật khẩu lấy từ biến môi trường INIT_ADMIN_PASSWORD')


def init_admin(reset_password: bool = False):
    admin_email = environ.get('INIT_ADMIN_EMAIL', '')
    user = User.objects.filter(username='admin').first()

    if user is None:
        if not admin_email:
            raise ValueError(
                'Không tìm thấy địa chỉ email để tạo tài khoản admin. '
                'Vui lòng đặt biến môi trường INIT_ADMIN_EMAIL.'
            )
        # Tạo mới: _apply_password sẽ set password và save (1 lần ghi DB duy nhất)
        user = User(username='admin', email=admin_email, is_staff=True, is_superuser=True)
        _apply_password(user, is_reset=False)
        print('Tạo người dùng admin thành công')
        return 'created'

    if reset_password:
        _apply_password(user, is_reset=True)
        return 'reset'

    print('Người dùng admin đã tồn tại. Dùng --reset-password để đặt lại mật khẩu.')
    return 'exists'


class Command(BaseCommand):
    help = 'Khởi tạo người dùng mặc định cho hệ thống. Dùng --reset-password để đặt lại mật khẩu nếu đã tồn tại.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-password',
            action='store_true',
            dest='reset_password',
            help='Đặt lại mật khẩu admin nếu tài khoản đã tồn tại',
        )

    def handle(self, *args, **kwargs):
        try:
            result = init_admin(reset_password=kwargs['reset_password'])
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f'Lỗi: {e}'))
            return
        if result == 'created':
            self.stdout.write(self.style.SUCCESS('Khởi tạo người dùng admin thành công'))
        elif result == 'reset':
            self.stdout.write(self.style.SUCCESS('Đặt lại mật khẩu admin thành công'))
        else:
            self.stdout.write(self.style.WARNING('Người dùng admin đã tồn tại. Dùng --reset-password để đặt lại mật khẩu.'))