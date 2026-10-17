import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views import View

from .utils import ChatbotNotConfigured, chatbot_allowed, get_responder, render_reply

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY = 10  # previous turns sent back to the model


def _error(message, status):
    return JsonResponse({"error": message}, status=status)


class ChatView(View):
    """POST {"message": str, "history": [{"role": "user"|"assistant", "content": str}]}
    -> {"html": str}. CSRF-protected; staff only (see chatbot_allowed)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        if not chatbot_allowed(request.user):
            return _error(_("You do not have permission to use the AI assistant."), 403)
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error(_("Invalid request."), 400)
        message = data.get("message") if isinstance(data, dict) else None
        if not isinstance(message, str) or not message.strip():
            return _error(_("Please enter a message."), 400)
        if len(message) > MAX_MESSAGE_LENGTH:
            return _error(_("The message is too long."), 400)
        if self._rate_limited(request.user):
            return _error(_("Too many messages. Please wait a minute."), 429)

        history = [
            {"role": turn["role"], "content": turn["content"][:MAX_MESSAGE_LENGTH]}
            for turn in (data.get("history") or [])[-MAX_HISTORY:]
            if isinstance(turn, dict)
            and turn.get("role") in ("user", "assistant")
            and isinstance(turn.get("content"), str)
        ]
        try:
            reply = get_responder()(history + [{"role": "user", "content": message.strip()}], request.user)
        except ChatbotNotConfigured as exc:
            logger.warning("AI assistant is not configured: %s", exc)
            return _error(_("The AI assistant is not configured."), 503)
        except Exception:
            logger.exception("AI assistant request failed")
            return _error(_("The AI assistant is unavailable. Please try again later."), 502)
        return JsonResponse({"markdown": reply, "html": render_reply(reply)})

    @staticmethod
    def _rate_limited(user):
        limit = getattr(settings, "CHATBOT_RATE_LIMIT", 20)  # messages per minute per user
        if not limit:
            return False
        key = f"wn:chatbot:rate:{user.pk}"
        cache.add(key, 0, 60)
        try:
            count = cache.incr(key)
        except ValueError:  # expired between add() and incr()
            cache.set(key, 1, 60)
            count = 1
        return count > limit
