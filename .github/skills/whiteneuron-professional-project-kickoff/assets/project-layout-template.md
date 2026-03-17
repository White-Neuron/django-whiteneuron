# Project Layout Template

Use this layout as the non-negotiable baseline for new projects.

## Top-level

```text
<project-root>/
  .env.example
  README.md
  pyproject.toml
  uv.lock
  styles.css                # optional (when frontend/admin styling enabled)
  docs/
  scripts/
  docker/
  src/
```

## src layout

```text
src/
  manage.py
  <project_name>/
    __init__.py
    settings.py
    urls.py
    asgi.py
    wsgi.py
  apps/
    __init__.py
    <domain_app>/
      __init__.py
      admin.py
      apps.py
      models.py
      views.py
      migrations/
  templates/
  static/
  media/
  staticfiles/            # runtime output from collectstatic
```

## Profile add-ons

- admin-core:
  - Keep `src/apps/` minimal.
- catalog-api:
  - Add `src/apps/api/` and one domain app.
  - Optional `src/locale/`.
  - Optional `docker/data/` when import sources exist.
- portal-cms:
  - Multiple content apps under `src/apps/`.
  - Keep `src/templates/`, `src/static/`, `src/media/`, `src/staticfiles/`.

## Hard rules

- All business apps must live under `src/apps/`.
- Do not place app code at project root.
- Keep scripts only under `scripts/`.
- Keep container artifacts only under `docker/`.
- Treat `src/staticfiles/` as generated output, not curated source.
