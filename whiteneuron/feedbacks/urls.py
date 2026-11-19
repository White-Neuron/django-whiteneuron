from django.urls import path

from .views import FEEDBACK_COOLDOWN_SECONDS, receive_feedback  # noqa: F401 (FEEDBACK_COOLDOWN_SECONDS: re-exported)

urlpatterns = [
    path("feedback/", receive_feedback, name="feedback_endpoint"),
]
