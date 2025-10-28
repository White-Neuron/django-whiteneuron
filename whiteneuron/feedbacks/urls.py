import json
import logging
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from whiteneuron.feedbacks.models import FeedbackData

User = get_user_model()
logger = logging.getLogger(__name__)

@csrf_exempt  # Chỉ dùng nếu API không cần CSRF bảo vệ
def receive_feedback(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method"}, status=400)

    try:
        # Đọc dữ liệu từ request
        body_unicode = request.body.decode("utf-8")
        logger.info(f"Received request body: {body_unicode}")  # Log dữ liệu nhận được

        data = json.loads(body_unicode)
        object_id = data.get("object_id")
        field = data.get("field")
        feedback_message = data.get("feedback_message")
        model_name = data.get("model_name")
        app_label = data.get("app_label")

        # Kiểm tra dữ liệu bắt buộc
        if not object_id or not feedback_message or not model_name or not app_label:
            return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)

        # Kiểm tra user
        if not request.user.is_authenticated:
            return JsonResponse({"success": False, "message": "User is not authenticated"}, status=403)

        user_id = request.user.id

        # Lấy ContentType
        try:
            content_type = ContentType.objects.get(model=model_name, app_label=app_label)
        except ContentType.DoesNotExist:
            return JsonResponse({"success": False, "message": "Invalid model or app_label"}, status=400)

        # Tạo feedback mới
        feedback = FeedbackData(
            user=User.objects.get(id=user_id),
            content_type=content_type,
            object_id=object_id,
            field=field,
            message=feedback_message,
        )

        feedback.save()  # Lưu feedback có request để lưu thông tin người thực hiện

        logger.info(f"Feedback saved: {feedback}")
        return JsonResponse({"success": True, "message": "Feedback saved successfully"})

    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        return JsonResponse({"success": False, "message": "Invalid JSON format"}, status=400)
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)

urlpatterns = [
    path("feedback/", receive_feedback, name="feedback_endpoint"),
]
