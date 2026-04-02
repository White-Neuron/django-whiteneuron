import json
import logging
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import timedelta
from whiteneuron.feedbacks.models import FeedbackData

FEEDBACK_COOLDOWN_SECONDS = 60

logger = logging.getLogger(__name__)

@require_POST
def receive_feedback(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": _("User is not authenticated")}, status=403)

    try:
        # Đọc dữ liệu từ request
        body_unicode = request.body.decode("utf-8")

        data = json.loads(body_unicode)
        object_id = data.get("object_id")
        field = data.get("field")
        feedback_message = data.get("feedback_message")
        model_name = data.get("model_name")
        app_label = data.get("app_label")

        # Kiểm tra dữ liệu bắt buộc
        if not object_id or not feedback_message or not model_name or not app_label:
            return JsonResponse({"success": False, "message": _("Missing required fields")}, status=400)

        if len(feedback_message) > 2000:
            return JsonResponse({"success": False, "message": _("Feedback message must not exceed 2000 characters.")}, status=400)

        # Lấy ContentType
        try:
            content_type = ContentType.objects.get(model=model_name, app_label=app_label)
        except ContentType.DoesNotExist:
            return JsonResponse({"success": False, "message": _("Invalid model or app_label")}, status=400)

        # Kiểm tra cooldown chống spam — per user, không phân biệt đối tượng
        cooldown_since = timezone.now() - timedelta(seconds=FEEDBACK_COOLDOWN_SECONDS)
        last_feedback = FeedbackData.objects.filter(
            user=request.user,
            created_at__gte=cooldown_since,
        ).order_by('-created_at').first()
        if last_feedback:
            remaining = FEEDBACK_COOLDOWN_SECONDS - int((timezone.now() - last_feedback.created_at).total_seconds())
            return JsonResponse(
                {"success": False, "message": _("Please wait %(seconds)d seconds before submitting another feedback.") % {"seconds": max(remaining, 1)}},
                status=429,
            )

        # Tạo feedback mới
        feedback = FeedbackData(
            user=request.user,
            content_type=content_type,
            object_id=object_id,
            field=field,
            message=feedback_message,
        )

        feedback.save()

        logger.info("Feedback saved: %s", feedback)
        return JsonResponse({"success": True, "message": _("Feedback saved successfully")})

    except json.JSONDecodeError:
        logger.error("Invalid JSON format in feedback submission")
        return JsonResponse({"success": False, "message": _("Invalid JSON format")}, status=400)
    except Exception as e:
        logger.error("Error saving feedback: %s", e, exc_info=True)
        return JsonResponse({"success": False, "message": _("An unexpected error occurred. Please try again.")}, status=500)

urlpatterns = [
    path("feedback/", receive_feedback, name="feedback_endpoint"),
]
