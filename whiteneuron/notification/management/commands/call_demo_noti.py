# Khởi tạo guest interface theme cho hệ thống sử dụng BaseCommand

from django.core.management.base import BaseCommand
from whiteneuron.notification.views import notify_admin
    
class Command(BaseCommand):
    help = 'Call demo notification to admin'

    def handle(self, *args, **kwargs):
        # Gọi hàm notify_admin để gửi thông báo
        notify_admin("Đây là thông báo demo từ hệ thống.")