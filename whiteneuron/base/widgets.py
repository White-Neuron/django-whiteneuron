from typing import Any, Optional
from django.forms import Widget as BaseWidget
from unfold.contrib.forms.widgets import WysiwygWidget

from django_ckeditor_5.widgets import CKEditor5Widget


class MarkdownEditorWidget(BaseWidget):
    template_name = "base/forms/mdeditor.html"

    class Media:
        js = (
            "base/forms/js/mdeditor.js",
        )

    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        super().__init__(attrs)
