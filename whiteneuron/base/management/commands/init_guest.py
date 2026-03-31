# Khởi tạo guest interface theme cho hệ thống sử dụng BaseCommand

from django.core.management.base import BaseCommand
from whiteneuron.base.models import User, Group

def init_guest():
    if User.objects.filter(username='guest').count() == 0:
        user = User(username='guest', is_staff=True)
        user.set_unusable_password()
        user.save()
    else:
        user = User.objects.get(username='guest')

    # group guest
    gr= Group.objects.get(name='Khách thăm')
    user.groups.add(gr)
    user.save()

    print('Tạo người dùng guest thành công')
    return True
    
class Command(BaseCommand):
    help = 'Khởi tạo người dùng mặc định cho hệ thống'

    def handle(self, *args, **kwargs):
        fl= init_guest()
        if fl:
            self.stdout.write(self.style.SUCCESS('Khởi tạo người dùng khách thăm thành công'))
        else:
            self.stdout.write(self.style.ERROR('Khởi tạo người dùng khách thăm thất bại'))