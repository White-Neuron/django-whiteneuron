"""Tiny allowlist HTML sanitizer for stored, server-generated snippets.

Used for notification bodies created before values were escaped: it keeps simple
formatting tags and drops everything else (scripts, event handlers, styles...).
"""
import re
from html import escape
from html.parser import HTMLParser

from django.utils.http import url_has_allowed_host_and_scheme

ALLOWED_TAGS = {"p", "ul", "ol", "li", "strong", "b", "em", "i", "br", "code", "span", "a"}
VOID_TAGS = {"br"}
SAFE_URL_PREFIXES = ("/", "http://", "https://", "mailto:")


def is_safe_href(href):
    """http(s)/mailto URLs, or a path on this site.

    Browsers drop tab/CR/LF anywhere in a URL and read "\\" as "/", so "/\t/evil.com"
    or "/\\evil.com" are protocol-relative links to another host: same-site paths are
    checked with Django's url_has_allowed_host_and_scheme after that normalization.
    """
    cleaned = re.sub(r"[\t\n\r]", "", href or "").strip()
    if cleaned.lower().startswith(SAFE_URL_PREFIXES[1:]):
        return True
    return cleaned.startswith("/") and url_has_allowed_host_and_scheme(cleaned, allowed_hosts=set())


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip_depth = 0  # inside <script>/<style>

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip_depth += 1
            return
        if tag not in ALLOWED_TAGS:
            return
        attr = ""
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if is_safe_href(href):
                attr = f' href="{escape(href, quote=True)}"'
        self.out.append(f"<{tag}{attr}>")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(escape(data, quote=False))


def sanitize_html(value: str) -> str:
    parser = _Sanitizer()
    parser.feed(value or "")
    parser.close()
    return "".join(parser.out)
