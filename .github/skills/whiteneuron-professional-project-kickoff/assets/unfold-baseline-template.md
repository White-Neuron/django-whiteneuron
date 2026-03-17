# UNFOLD Baseline Template

Use this block as mandatory baseline in project settings overrides.

```python
from django.templatetags.static import static

UNFOLD["SITE_HEADER"] = _(NAME)
UNFOLD["SITE_TITLE"] = _(NAME)
UNFOLD["ENVIRONMENT"] = f"{PROJECT_NAME}.utils.environment_callback"
UNFOLD["STYLES"] = [lambda request: static("css/styles.css")] + UNFOLD["STYLES"]
UNFOLD["SHOW_LANGUAGES"] = True
```

## Recommended additions

```python
UNFOLD["DASHBOARD_CALLBACK"] = "whiteneuron.dashboard.views.dashboard_callback"
UNFOLD["SITE_SUBHEADER"] = _("Admin panel")
UNFOLD["SHOW_HISTORY"] = True
```

## Safety checks

- Ensure `PROJECT_NAME.utils.environment_callback` exists.
- Ensure `src/static/css/styles.css` exists when `UNFOLD["STYLES"]` prepends that path.
- Keep `UNFOLD["STYLES"]` prepend, not overwrite, to preserve base library styles.
- Keep callback paths as importable dotted paths.
