# Unfold Key Features Reference (For Project Bootstrap)

This document summarizes key Unfold capabilities for building complete and optimized Django admin projects with `django-whiteneuron`.

## Source Basis

This reference is built from:

- Installed source in workspace environment:
  - `site-packages/unfold/admin.py`
  - `site-packages/unfold/sites.py`
  - `site-packages/unfold/settings.py`
  - `site-packages/unfold/contrib/*`
- Upstream repo/docs:
  - `https://github.com/unfoldadmin/django-unfold`
  - `https://unfoldadmin.com/docs/`

## 1) Core Architecture Pattern

- Unfold extends Django admin, not replaces it.
- Primary classes:
  - `unfold.admin.ModelAdmin`
  - `unfold.admin.TabularInline` / `StackedInline` and generic inline variants
  - `unfold.sites.UnfoldAdminSite`
- Works with existing `django.contrib.admin` model registrations and workflows.

Bootstrap recommendation:
- Use a custom admin site class (as in `base_admin_site`) and register all project admins against it.

## 2) High-Value ModelAdmin Features

From source (`admin.py`), key capabilities include:

- Action system:
  - action form customization
  - row/list/detail action URLs
- Changelist customization:
  - custom `ChangeList`
  - list layout options (fullwidth, filter sheet/submit, top scrollbar)
- Changeform customization:
  - before/after templates
  - compressed fields mode
  - unsaved form warning
- Dataset support on change form (`change_form_datasets`)
- Custom URL injection per admin class (`custom_urls`)
- Inline pagination/count support via formsets (`per_page`, `show_count`)

Bootstrap recommendation:
- Default project admin base class should expose these options for feature teams to adopt consistently.

## 3) Unfold Admin Site Context Features

From source (`sites.py`), the admin site context supports:

- Site identity and branding:
  - `SITE_HEADER`, `SITE_TITLE`, `SITE_SUBHEADER`, `SITE_ICON`, `SITE_LOGO`, `SITE_FAVICONS`
- UX controls:
  - `SHOW_HISTORY`, `SHOW_VIEW_ON_SITE`, `SHOW_LANGUAGES`, `SHOW_BACK_BUTTON`
- Environment label and title prefix:
  - `ENVIRONMENT`, `ENVIRONMENT_TITLE_PREFIX`
- Navigation framework:
  - account links
  - tabs
  - sidebar navigation
- Global assets:
  - `STYLES`, `SCRIPTS`
- Dashboard callback:
  - `DASHBOARD_CALLBACK`
- Command/search integration:
  - `COMMAND` config (`search_models`, `show_history`, `search_callback`)

Mandatory bootstrap baseline:
- `UNFOLD["SITE_HEADER"] = _(NAME)`
- `UNFOLD["SITE_TITLE"] = _(NAME)`
- `UNFOLD["ENVIRONMENT"] = f"{PROJECT_NAME}.utils.environment_callback"`
- `UNFOLD["STYLES"] = [lambda request: static("css/styles.css")] + UNFOLD["STYLES"]`
- `UNFOLD["SHOW_LANGUAGES"] = True`

## 4) Settings Surface (What To Standardize)

From source (`settings.py`), important configuration groups:

- Site/branding keys
- Form classes (`FORMS.classes`)
- Color system (`COLORS`)
- Sidebar config (`SIDEBAR`)
- Command/search config (`COMMAND`)
- Language and account navigation
- Login config (`LOGIN.image`, `LOGIN.form`, redirect)
- Tabs (`TABS`)
- Extensions (`EXTENSIONS.modeltranslation.flags`)

Bootstrap recommendation:
- Keep a project-level UNFOLD override block grouped and documented.
- Avoid scattered UNFOLD overrides across files.

## 5) Contrib Integrations You Should Plan Early

Installed contrib packages found in source:

- `unfold.contrib.filters`
- `unfold.contrib.forms`
- `unfold.contrib.inlines`
- `unfold.contrib.import_export`
- `unfold.contrib.guardian`
- `unfold.contrib.simple_history`
- `unfold.contrib.constance`
- `unfold.contrib.location_field`

Bootstrap recommendation:
- Enable only what profile needs, but prepare extension points in settings/admin base classes.

## 6) Feature Map For Project Profiles

### admin-core

Enable first:
- Core Unfold admin site + branding baseline
- Sidebar/navigation with permission-safe defaults
- Command/search basic setup

### catalog-api

Add:
- Strong list/filter UX and search for large catalogs
- Import/export workflow integration
- API docs links in navigation

### portal-cms

Add:
- Rich content editor mode
- Multi-section sidebar with badges
- History + language switching
- Async/notification-friendly admin UX

## 7) Safety Rules For Optimal Adoption

- Keep `UNFOLD["STYLES"]` as prepend, not overwrite.
- Ensure callback dotted paths exist (`ENVIRONMENT`, `DASHBOARD_CALLBACK`, badge callbacks).
- Keep navigation entries aligned with installed apps and permissions.
- Validate admin rendering after any UNFOLD config update.

## 8) Validation Checklist (Unfold-specific)

Run in every bootstrap and major settings change:

1. `python manage.py check`
2. Open admin login page and verify styling is loaded.
3. Open admin index and verify sidebar/navigation renders correctly.
4. Verify environment label callback resolves.
5. Verify one project model changelist and changeform render without template errors.
6. If enabled, verify import/export/history/guardian integrations are active.

## 9) Common Pitfalls

- Missing styles path causes unstyled admin.
- Callback path typo breaks index or sidebar rendering.
- Overwriting `UNFOLD["STYLES"]` removes base assets.
- Enabling contrib integrations without corresponding dependencies/apps.
- Registering admin inconsistently between custom admin site and default site.
