from typing import Any, Optional
from unfold.contrib.forms.widgets import WysiwygWidget as UnfoldWysiwygWidget


class WysiwygWidget(UnfoldWysiwygWidget):
    """
    Custom WYSIWYG widget that extends Unfold's WysiwygWidget 
    with HTML Editor functionality.
    """
    template_name = "base/forms/wysiwyg.html"

    class Media:
        css = {
            "all": (
                "unfold/forms/css/trix/trix.css",
                "base/forms/css/html-editor.css",
            )
        }
        js = (
            "base/forms/js/format.html.js",
            "unfold/forms/js/trix/trix.js",
            "base/forms/js/trix.config.js",
        )

    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        super().__init__(attrs)