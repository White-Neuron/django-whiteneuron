# BaseModel And Admin Site Template

Use these snippets as default when creating new app models/admin.

## Model snippet

```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from whiteneuron.base.models import BaseModel


class ExampleEntity(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Example Entity")
        verbose_name_plural = _("Example Entities")

    def __str__(self):
        return self.name
```

## Admin snippet

```python
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from whiteneuron.base.admin import ModelAdmin, base_admin_site

from .models import ExampleEntity


@admin.register(ExampleEntity, site=base_admin_site)
class ExampleEntityAdmin(ModelAdmin):
    list_display = ("name", "created_at", "created_by", "updated_at", "updated_by")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")

    fieldsets = (
        (_("General"), {"fields": ("name", "description")}),
        (_("Meta"), {"fields": ("created_at", "created_by", "updated_at", "updated_by")}),
    )
```

## Validation checklist

- Model inherits `BaseModel`.
- Admin inherits `ModelAdmin`.
- Registration uses `base_admin_site`.
- Meta/audit fields are present in readonly/fieldsets where appropriate.
