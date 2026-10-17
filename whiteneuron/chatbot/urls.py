from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("api/chat/", views.ChatView.as_view(), name="chat"),
]
