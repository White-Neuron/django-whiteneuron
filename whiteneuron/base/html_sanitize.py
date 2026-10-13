"""Tiny allowlist HTML sanitizer for stored, server-generated snippets.

Used for notification bodies created before values were escaped: it keeps simple
formatting tags and drops everything else (scripts, event handlers, styles...).
"""
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {"p", "ul", "ol", "li", "strong", "b", "em", "i", "br", "code", "span", "a"}
VOID_TAGS = {"br"}
SAFE_URL_PREFIXES = ("/", "http://", "https://", "mailto:")


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
            if href.strip().lower().startswith(SAFE_URL_PREFIXES) and not href.strip().startswith("//"):
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
