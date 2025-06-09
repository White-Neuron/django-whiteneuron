from django.utils import timezone
from .models import Notification

def notification_badge_callback(request):
    c= Notification.objects.filter(
        user=request.user,
        is_read=False,
        created_at__gte= timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)).count()
    if c==0:
        return ''
    return f"+{c}"