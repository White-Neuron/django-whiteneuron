"""AI assistant panel: who may use it, the LLM call, and safe rendering of replies."""
import logging
import os
from urllib.parse import urlparse

import markdown
from bs4 import BeautifulSoup
from django.apps import apps
from django.conf import settings
from django.utils.module_loading import import_string

from whiteneuron.base.utils import is_guest_user

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are the assistant of a Django admin site. Answer briefly and in the user's language. "
    "Use Markdown for lists and code."
)


class ChatbotNotConfigured(Exception):
    """No API key / model: the panel is shown but cannot answer."""


def chatbot_allowed(user):
    """Installed app, staff account, not the shared guest (LLM calls cost money)."""
    return (
        apps.is_installed("whiteneuron.chatbot")
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and not is_guest_user(user)
    )


_client = None


def _openai_client():
    global _client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ChatbotNotConfigured("OPENAI_API_KEY is not set")
    if _client is None:
        import openai

        # bounded: a stuck API call must not hold a web worker forever
        _client = openai.Client(api_key=api_key, timeout=60, max_retries=1)
    return _client


def openai_responder(messages, user):
    """Default CHATBOT_RESPONDER: ``messages`` is a list of {"role", "content"}; returns Markdown."""
    model = getattr(settings, "CHATBOT_MODEL", "")
    if not model:
        raise ChatbotNotConfigured("CHATBOT_MODEL is not set")
    system = getattr(settings, "CHATBOT_SYSTEM_PROMPT", "") or DEFAULT_SYSTEM_PROMPT
    response = _openai_client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
    )
    return response.choices[0].message.content or ""


def get_responder():
    """settings.CHATBOT_RESPONDER (dotted path) lets a project plug in its own model or RAG."""
    path = getattr(settings, "CHATBOT_RESPONDER", "") or "whiteneuron.chatbot.utils.openai_responder"
    return import_string(path)


_SAFE_SCHEMES = {"http", "https", "mailto"}


def render_reply(text):
    """Markdown -> HTML that is safe to insert into the admin page.

    The reply comes from an LLM, which a prompt injection can steer: raw HTML is escaped,
    images dropped and links limited to http(s)/mailto."""
    md = markdown.Markdown(extensions=["fenced_code", "tables", "sane_lists"])
    md.preprocessors.deregister("html_block")
    md.inlinePatterns.deregister("html")
    soup = BeautifulSoup(md.convert(text), "html.parser")
    for img in soup.find_all("img"):
        img.replace_with(img.get("alt", ""))
    for link in soup.find_all("a"):
        href = link.get("href", "")
        if urlparse(href).scheme.lower() not in _SAFE_SCHEMES:
            link.unwrap()
            continue
        link.attrs = {"href": href, "target": "_blank", "rel": "noopener noreferrer"}
    return str(soup)
