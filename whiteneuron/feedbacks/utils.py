from whiteneuron.base.utils import base_badge_callback
from .models import FeedbackData

def feedback_data_badge_callback(request):
    # Lọc feedback theo user hiện tại
    if request.user.is_superuser:
        filter_kwargs = None  # Superuser xem tất cả feedback
    else:
        filter_kwargs = {'user': request.user}
    return base_badge_callback(request, FeedbackData, filter_kwargs)