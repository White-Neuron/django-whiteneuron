# Changelog

### v0.3.4.5 (2026-05-10) — latest
**Bugfix: Visit tracking accuracy and dashboard badge improvement**
- **Fixed**: `UserActivityMiddleware` now only tracks visits for non-redirect responses (status codes other than 301, 302), preventing false visit counts from HTTP redirects.
- **Improved**: `visitprofile_badge_callback` now shows today's active visitors count instead of total all-time count, providing more meaningful real-time analytics in the admin sidebar.
- **Removed**: Unused `user_badge_callback` function from `utils.py`.
- **Migration**: New migration `0027` alters `method` fields on `AnonymousActivity` and `UserActivity`; file management models updated with field constraints.
- **Validation**: Build successful (Tailwind + migrations), smoke test passed.
- **Compatibility**: No breaking changes; safe for all v0.3.x users. Minor schema change via migration — no data loss expected.
- **Upgrade Guidance**: Run `python manage.py migrate` after upgrade to apply schema changes.
- **Rollback**: Safe to revert to v0.3.4.4; run `python manage.py migrate` to rollback migrations if needed.

### v0.3.4.4 (2026-05-09)
**Security patch: Upgrade Twisted to 26.4.0rc2 (CVE CVSS 7.5)**
- **Fixed**: Upgraded `twisted` from 25.5.0 to 26.4.0rc2, resolving CVE with CVSS score 7.5 (High) affecting the transitive dependency chain via daphne→twisted.
- **Validation**: Build successful, no migrations required, smoke test passed.
- **Compatibility**: No breaking changes; safe for all v0.3.x users. Note: 26.4.0rc2 is a release candidate — stable 26.x expected soon.
- **Upgrade Guidance**: No manual migration required; upgrade recommended to address security vulnerability.
- **Rollback**: Safe to revert to v0.3.4.3; no schema changes introduced.

### v0.3.4.3 (2026-05-03)
**Improvement: Configurable meta fieldset collapse behavior in ModelAdmin**
- **Improved**: `ModelAdmin.meta_class_in_fieldsets` — added configurable attribute to control whether Meta fieldset is collapsed or always shown; previously hardcoded to `"collapse"`. Now supports `'collapse'` (default) or `'t'` (always show).
- **Validation**: Build, migrations (no changes), and manual validation performed.
- **Compatibility**: No breaking changes; safe for all v0.3.x users.
- **Upgrade Guidance**: No manual migration required; upgrade recommended if you want to customize meta fieldset display behavior.
- **Rollback**: Safe to revert to v0.3.4.2; no schema changes introduced.

### v0.3.4.2 (2026-05-03)
**Bugfix: `duplicate_objects` action now supports models with `title` field in addition to `name`**
- **Fixed**: `ModelAdmin.duplicate_objects()` — previously only copied objects with a `name` field; now also handles objects with a `title` field (e.g. `App.title`). Objects without either field are still duplicated but without renaming.
- **Validation**: Build, migrations (no changes), and manual validation performed.
- **Compatibility**: No breaking changes; safe for all v0.3.x users.
- **Upgrade Guidance**: No manual migration required; upgrade recommended if using `duplicate_objects` on models with `title` field.
- **Rollback**: Safe to revert to v0.3.4.1; no schema changes introduced.

### v0.3.4.1 (2026-05-02) — latest
**Security Enhancement: Improved request payload sanitization and VisitProfile management utility**
- **Improved**: `_sanitize_post()` in `UserActivityMiddleware` now detects and redacts sensitive values via pattern matching (JWT tokens, API keys, session IDs, base64/hex strings), not just field names.
- **Added**: Management command `update_visit_profiles` — updates `first_seen`/`last_seen` for VisitProfile based on timestamps from UserActivity and AnonymousActivity; supports `--dry-run`.
- **Validation**: Build, migrations (no changes), and manual validation performed.
- **Compatibility**: No breaking changes; safe for all v0.3.x users.
- **Upgrade Guidance**: No manual migration required; upgrade recommended for improved security in activity logging.
- **Rollback**: Safe to revert to v0.3.4; no schema changes introduced.

### v0.3.4 (2026-05-01)
**Improvement: Enhanced User Activity tracking and security hardening**
- **Improved**: `UserActivityMiddleware` now captures JSON request payloads (POST/PATCH/PUT/DELETE) with full sensitive-field sanitization, resolving issues where API activity was not being logged.
- **Improved**: Added a 1MB body size limit for JSON requests in middleware to prevent DoS via large payloads.
- **Improved**: `UserActivity` and `AnonymousActivity` now support all standard HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) instead of just GET/POST.
- **Added**: `FEEDBACK_COOLDOWN_SECONDS` setting to allow configurable anti-spam cooldown for the feedback system.
- **Improved**: Admin badge callbacks (`useractivity`, `anonymousactivity`, `visitprofile`) now return `0` instead of an empty string when no activity is found, ensuring consistent UI rendering.
- **Fixed**: Feedback cooldown logic now respects the new `FEEDBACK_COOLDOWN_SECONDS` setting from Django settings.
- **Validation**: Build, migrations (no changes), and manual admin UI/UX validation performed.
- **Compatibility**: No breaking changes; safe for all v0.3.x users.
- **Upgrade Guidance**: No manual migration required; upgrade recommended for improved activity logging accuracy.
- **Rollback**: Safe to revert to v0.3.3.4; no schema changes introduced.

### v0.3.3.4 (2026-04-30) — latest
**Patch release: Remove synchronization module, add language switcher template, update Vietnamese i18n**
- **Removed**: `synchronization/` module — cleaned up unused sync models, admin, views, tests, and migrations
- **Added**: Language switcher template for Unfold admin (`language_switch.html`) with multi-language support via `show_languages` context variable
- **Improved**: Vietnamese translations updated — removed stale synchronization references, added new entries for user profile and HTML editor
- **Validation**: Build, migrations (no changes), and manual admin UI/UX validation performed
- **Compatibility**: No breaking changes; safe for all v0.3.3.x users
- **Upgrade Guidance**: No manual migration required; upgrade recommended for all users on v0.3.3.x
- **Rollback**: Safe to revert to v0.3.3.3; no schema changes introduced

### v0.3.3.3 (2026-04-30)
**Patch release: Minor bugfixes and improvements after v0.3.3 series**
- **Fixed**: Minor bugs and regressions reported after v0.3.3.1
- **Improved**: Code quality, admin UX, and file management reliability
- **Validation**: Build, migrations, and manual admin UI/UX validation performed
- **Compatibility**: No breaking changes; safe for all v0.3.3.x users
- **Upgrade Guidance**: No manual migration required; upgrade recommended for all users on v0.3.3.x
- **Rollback**: Safe to revert to v0.3.3.1 or v0.3.3; no schema changes introduced

### v0.3.3 (2026-04-29)
**Feature: Markdown Editor for Admin, File Permissions, and API Preview**
- **Added**: Markdown editor widget for Django Admin (`MarkdownEditorWidget`), with live preview modal and Tailwind-styled HTML rendering using `md2html-tailwind4`.
- **Added**: `/md-preview/` API endpoint for secure, authenticated Markdown-to-HTML preview in admin forms.
- **Added**: JavaScript and template assets for Markdown editing and preview, including modal UX and 1MB content limit.
- **Improved**: File management admin now restricts file visibility—users only see files they created; superusers see all files.
- **Changed**: `BaseFile.delete()` renamed to `hard_delete()` for clarity and safety in file removal logic.
- **Compatibility**: No breaking changes for existing data/models; new widget is opt-in via `text_field_widget = 'mdeditor'`.
- **Validation**: Full build, migrations, and manual admin UI/UX validation performed. Markdown preview tested for XSS safety and large input handling.
- **Upgrade Guidance**: No manual migration required. To enable Markdown editing, set `text_field_widget = 'mdeditor'` in your `ModelAdmin`.
- **Rollback**: Safe to revert to v0.3.2.2; no schema changes introduced

### v0.3.2.2 (2026-04-29)
**Improvement: Superuser-only soft-delete; duplicate action; expanded i18n coverage from django-unfold**
- **Fixed**: `ModelAdmin.get_actions()` — soft-delete (`delete_selected`) is now restricted to superusers only; regular staff no longer see a delete action that could silently soft-delete records they didn't expect to change.
- **Added**: `duplicate_objects` bulk action automatically injected into all `ModelAdmin` subclasses for superusers — creates a copy of selected objects with ` (Copy)` appended to `name`; requires `add` permission.
- **Fixed**: `get_actions()` logic restructured to guard all destructive/restore actions inside the `is_superuser` block, preventing accidental exposure to non-superuser staff.
- **Added**: `scripts/makemessages.sh` — now creates a temporary symlink `_unfold_src → .venv/.../unfold` and runs `makemessages --symlinks` so that translatable strings from the upstream `django-unfold` package are extracted into the project's locale.
- **Improved**: Vietnamese translation (`locale/vi/LC_MESSAGES/django.po`) expanded significantly — now covers unfold core UI strings (filters, actions, submit line, object history, import/export, guardian, simple_history, widgets) in addition to all project-specific strings.

### v0.3.2.1 (2026-04-27)
**Fix: UserActivityMiddleware now captures JSON request payloads in addition to form data**
- **Fixed**: `UserActivityMiddleware._get_request_data()` — previously only captured `request.POST` (form-encoded), missing JSON bodies sent with `Content-Type: application/json`. Now parses `request.body` as JSON when POST is empty, with full sensitive-field sanitization applied.

### v0.3.2 (2026-04-27)
**Feature: VisitProfile-based activity tracking for authenticated + anonymous users, dashboard analytics**
- **Added**: `VisitProfile` model (`whiteneuron/base/models.py`) — deduplicates visits by `(ip_address, user_agent)` combo; tracks `first_seen`, `last_seen`; unique constraint on the pair.
- **Added**: `AnonymousActivity` model — tracks anonymous visitor activity (path, method, status_code, timelapse) linked to `VisitProfile`.
- **Refactored**: `UserActivity` — removed direct `ip_address`/`user_agent` fields; replaced with FK `profile` → `VisitProfile`; data migration backfills existing records.
- **Added**: `UserActivityMiddleware` now creates `VisitProfile` for both authenticated and anonymous requests; handles race conditions via `IntegrityError` retry in `_get_or_create_visit_profile()`.
- **Improved**: `_sanitize_post()` is now recursive — sanitizes nested dicts/lists, not just top-level keys.
- **Added**: Dashboard analytics (`dashboard/views.py`) — new KPI cards for anonymous visits with success rate; 28-day chart expanded from 3 to 6 datasets (user avg/success/error + anonymous avg/success/error).
- **Fixed**: Dashboard `status_code` comparison changed from string `"400"` to int `400`.
- **Added**: Admin — `VisitProfileAdmin`, `AnonymousActivityAdmin`; `BaseActivityInline`/`UserActivityInline` for viewing activities from User detail page; `block_ip` action now handles null profiles gracefully.
- **Added**: Sidebar navigation entries in `settings.py` — "Anonymous activity" and "Visit profiles" links with badge callbacks.
- **Added**: Badge callbacks (`utils.py`) — `anonymousactivity_badge_callback`, `visitprofile_badge_callback`.
- **Added**: Management command `cleanup_old_activities.py` — deletes UserActivity, AnonymousActivity, Notification records older than N days (default 90), plus orphan VisitProfiles; supports `--dry-run`.
- **Updated**: Templates — KPI cards now show `metric_total` + optional `metric_success` subtitle in header/index; account_links.html refactored from modal dialog to dropdown menu items (~60 lines saved); search_form.html per_page select width fixed.
- **Fixed**: `Tag.__str__()` changed from `self.tag` → `self.title`.
- **Fixed**: `BaseModel.notify_superuser()` — uses `values_list('id', flat=True)` + `user_id=` to avoid loading full User queryset into memory.
- **Config**: `.gitignore` — added `.opencode`; `init_admin.py` — sets `_skip_new_user_email = True` to prevent duplicate welcome emails.

### v0.3.1.8 (2026-04-24)
**Feature: Add UUID field to User model with admin display support**
- **Added**: `whiteneuron/base/models.py` — new `uuid` field (`UUIDField`, unique, auto-generated via `uuid.uuid4`) on the custom `User` model.
- **Added**: `whiteneuron/base/admin.py` — `uuid` displayed in User changelist list_display; shown as readonly field in User change form under "Personal info" section; excluded from grid view cards.
- **Migration**: `0018_user_uuid` — safely adds uuid to existing users via data migration (nullable → backfill → unique constraint).

### v0.3.1.7 (2026-04-23)
**Fix: post_save signal sends email to new users; fix format_html compat for Django 6; uncomment uv.sources for md2html-tailwind4**
- **Added**: `whiteneuron/base/models.py` — `post_save` signal `_send_email_to_new_user` now fires for every new `User` creation path (API, management commands, shell), not only admin form. Generates a random password, sets it, and calls `send_email_login`. Users with no email address are silently skipped.
- **Added**: `whiteneuron/base/admin.py` — sets `_skip_new_user_email = True` on the instance inside `save_model` so the new signal does not send a duplicate email when the admin form already handles it.
- **Fixed**: `whiteneuron/base/admin.py` — `preview_email` in `MailAdmin` changed from `format_html(obj.content)` to `mark_safe(obj.content)`. Django 6 raises `TypeError` when `format_html` is called without positional/keyword arguments.
- **Fixed**: `pyproject.toml` — uncommented `[tool.uv.sources]` block so `md2html-tailwind4` is resolved from the GitHub git source (`v1.5.0`) rather than PyPI, which only has `<=1.2.0`. `uv.lock` updated accordingly.

### v0.3.1.6 (2026-04-20)
**Dependency: Bump md2html-tailwind4 to v1.5.0; add Tailwind @source directive for md2html_tailwind4**
- **Updated**: `pyproject.toml` — bumped `[tool.uv.sources]` rev for `md2html-tailwind4` from `v1.4.2` to `v1.5.0`.
- **Updated**: `uv.lock` — lock file refreshed; `pymdown-extensions` v10.21.2 added as new transitive dependency of `md2html-tailwind4`.
- **Updated**: `styles.css` — added `@source` directive pointing to the installed `md2html_tailwind4` package so Tailwind CLI scans its Python templates for utility classes.
- **Updated**: `whiteneuron/static/base/css/styles.css` — rebuilt CSS artifact.

### v0.3.1.5 (2026-04-19)
**Dependency: Bump md2html-tailwind4 source to v1.4.2**
- **Updated**: `pyproject.toml` — updated `[tool.uv.sources]` rev for `md2html-tailwind4` from `v1.2.0` to `v1.4.2`.
- **Updated**: `uv.lock` — lock file refreshed.

### v0.3.1.4 (2026-04-17)
**Dependency: Bump md2html-tailwind4 to >=1.1.0**
- **Updated**: `pyproject.toml` — bumped `md2html-tailwind4` minimum version from `>=1.0.0` to `>=1.1.0`; added `[tool.uv.sources]` pointing to GitHub at rev `1.1.0`.
- **Updated**: `uv.lock` — lock file refreshed.

### v0.3.1.3 (2026-04-17)
**Fix: Announcement modal URL uses Django `{% url %}` tag; bump md2html-tailwind4 to >=1.1.0**
- **Fixed**: `templates/base/announcement.html` — replaced hardcoded `/announcement/` path with `{% url 'announcement' %}` in both `data-content-url` attribute and the JavaScript fallback, ensuring correct URL resolution regardless of URL prefix configuration.
- **Updated**: `pyproject.toml` — bumped `md2html-tailwind4` minimum version from `>=1.0.0` to `>=1.1.0`; added `[tool.uv.sources]` pointing to GitHub at rev `1.1.0`.
- **Updated**: `uv.lock` — lock file refreshed.

### v0.3.1.2 (2026-04-16)
**Dependency: Bump django-unfold floor constraint to >=0.89.0**
- **Updated**: `pyproject.toml` — raised `django-unfold` minimum version from `>=0.85.0` to `>=0.89.0` to align with the installed version; incorporates improvements from 0.86.0–0.89.0 (compressed fields by default, removal of unbound template blocks, inline before/after templates, UI component enhancements).
- **Updated**: `uv.lock` — lock file refreshed to reflect the updated constraint.

### v0.3.1.1 (2026-04-16)
**Fix: permission_viewer_callback missing unauthenticated guard; add md2html-tailwind4 dependency**
- **Fixed**: `base/utils.py` — `permission_viewer_callback` now checks `request.user.is_authenticated` before returning `True`, preventing unauthenticated (anonymous) users from passing the permission check.
- **Fixed**: `base/settings.py` — UNFOLD navigation Feedbacks menu item permission callback changed from `permission_non_guest_callback` to `permission_viewer_callback` for consistency.
- **Added**: `pyproject.toml` — added `md2html-tailwind4>=1.0.0` as a dependency.

### v0.3.1 (2026-04-15)
**Feature: Announcement system — display important notices in the admin header**
- **Added**: `settings.py` — three new settings: `VERSION` (read from env, default `"0.1.0"`), `ANNOUNCEMENT_CALLBACK` (dotted path to a callback that returns the announcement context), `ANNOUNCEMENT_CONTENT_HTML_FILE` (template name or absolute `Path` pointing to the announcement HTML content file).
- **Added**: `sites.py` — overrode `each_context()` in `BaseAdminSite` to automatically call `ANNOUNCEMENT_CALLBACK` and inject `announcement` into every admin page context; errors in the callback are silently suppressed.
- **Added**: `utils.py` — default `announcement_callback()` returning a `{title, version, badge}` dict using `format_lazy` and `gettext_lazy` for full i18n support.
- **Added**: `views.py` — `get_announcement_content` view; renders `ANNOUNCEMENT_CONTENT_HTML_FILE` via `render_to_string` and returns it as an `HttpResponse`.
- **Added**: `urls.py` — `/announcement/` endpoint wired into `get_announcement_content`.
- **Added**: `templates/base/announcement.html` — DaisyUI-style modal dialog with header, scrollable content area, and footer; content is lazy-loaded via `fetch()` on first open.
- **Added**: `templates/unfold/helpers/userlinks.html` — announcement button in the admin header with `wn-glow-pulse` and `wn-flame-icon` animations; rendered only when `announcement` is present in context.
- **Updated**: `locale/vi` — new Vietnamese translations for announcement-related strings.

### v0.3.0.5 (2026-04-14)
**Security: CSRF 403 on production behind reverse proxy (nginx/Cloudflare)**
- **Fixed**: `base/settings.py` — added `SECURE_PROXY_SSL_HEADER` so Django recognizes HTTPS via `X-Forwarded-Proto` header from reverse proxy, resolving CSRF origin mismatch.

### v0.3.0.4 (2026-04-14)
**Fix: Logout GET request returns 403 CSRF on production**
- **Fixed**: `base/sites.py` — overrode `logout()` in `BaseAdminSite` to redirect GET requests to login page instead of failing with 403 CSRF verification error (Django 4.1+ requires POST for logout).

### v0.3.0.3 (2026-04-14)
**Dependency: Upgrade pillow ≥12.2.0, cryptography ≥46.0.7**
- **Updated**: `pillow` minimum version bumped from `12.1.1` to `12.2.0` — latest upstream patch.
- **Updated**: `cryptography` minimum version bumped from `46.0.5` to `46.0.7` — security and bug-fix release.

### v0.3.0.2 (2026-04-13)
**Hotfix: Loading overlay no longer auto-hides after timeout**
- **Fixed**: `loading.js` — removed the auto-hide logic that dismissed the overlay after 45 seconds. The overlay now only hides when the server sends back the `wn_loading_done` cookie, or via `pageshow`/`visibilitychange`/`focus` events.

### v0.3.0.1 (2026-04-13)
**Hotfix: Email signature extracted to standalone file; exclude signature_ceo.html from build**
- **Fixed**: `TEMPLATE` in `base/utils.py` — replaced hardcoded inline HTML signature with a `{signature}` placeholder; content is now read from `templates/admin/signature.html` at the time `send_email_login` is called.
- **Added**: `_load_signature()` helper — reads `signature.html` relative to `utils.py`.
- **Added**: `templates/admin/signature.html` — standalone HTML email signature (CTO).
- **Added**: `templates/admin/signature_ceo.html` — CEO email signature (local-only, excluded from package build).
- **Config**: `pyproject.toml` — added `[tool.setuptools.exclude-package-data]` to exclude `signature_ceo.html` from wheel/sdist.

### v0.3.0 (2026-04-13)
**Feature: File integrity protection — SHA-256 hash verification for ExcelFile & PDFFile**
- **Added**: `compute_file_hash()` function — computes SHA-256 of a `FieldFile` via direct `storage.open()` to avoid Django internal state issues (works for both in-memory uploads and committed storage files).
- **Added**: `BaseFile.save()` override — automatically computes and stores SHA-256 hash on every new upload; resets `status='done'` when file is replaced after an error; backfills hash for existing files with no hash.
- **Added**: `BaseFile.verify_integrity()` — compares live storage hash against stored hash; returns `False` if missing or mismatched.
- **Added**: `download_file` view — `@login_required` endpoint for `/file-management/download/<type>/<pk>/`; enrolls legacy records on first download, blocks tampered files with `403 Forbidden`, marks them `status='error'`.
- **Added**: `file_management/urls.py` — wired into `base/urls.py`.
- **Added**: `FileInputNoDownload` widget — extends `UnfoldAdminFileFieldWidget` with a custom template that removes the direct download button; adds `accepted_file_types` support per admin subclass (`.xlsx,.xls,.csv` for Excel; `.pdf` for PDF).
- **Added**: `BaseFileAdmin` enhancements — `integrity_status`, `hash_display`, `current_hash_display` readonly fields; `verified_download` smart button (primary button when OK, error badge when tampered/missing); `change_view` shows Django error message banner on integrity failure; `get_fieldsets` context-aware layout (auto/upload/new).
- **Fixed**: `status_view` / `method_view` XSS — replaced f-string + `format_html` pattern with proper `format_html(template, *args)` escaping.
- **Fixed**: `file.delete(save=False)` in `BaseFile.delete()` — prevents extra `save()` call after file deletion.
- **Improved**: `accepted_file_types` class attribute on admin subclasses — browser-level file type filtering in upload dialog.

### v0.2.48.4 (2026-04-11)
**Security: Upgrade cbor2 5.9.0 and ujson 5.12.0**
- **Security**: `cbor2` upgraded from `v5.8.0` to `v5.9.0` — patch release with bug fixes and improved CBOR encoding/decoding.
- **Security**: `ujson` upgraded from `v5.11.0` to `v5.12.0` — security patch and improved JSON serialization performance.

### v0.2.48.3 (2026-04-10)
**Improve: Notification list — DaisyUI badge display, search field verbose names**
- **Improved**: `NotificationAdmin.display_title` rewritten — renders `[Model][#ID][Object name][Action] by [Alias][@username]` using `ui-badge ui-badge-xs` badges with correct color mapping (`ui-badge-success/info/error/warning`).
- **Fixed**: `obj_link` parsing regex updated to handle paths without `/admin/` prefix — e.g. `/techniques/technique/58316/change/`.
- **Fixed**: `get_verbose_name_field` now traverses `__`-separated lookup paths (e.g. `user__username`) to resolve proper verbose names for all search fields in `search_help_text`.

### v0.2.48.2 (2026-04-10)
**Security: Upgrade django 5.2.13 and add pyOpenSSL 26.0.0**
- **Security**: `django` lower bound raised from `>=5.2.12` to `>=5.2.13` — latest Django security patch.
- **Security**: `pyopenssl==26.0.0` added as an explicit dependency — ensures the latest version of pyOpenSSL is used, patching potential vulnerabilities in TLS/SSL handling.

### v0.2.48.1 (2026-04-06)
**Fix: Duplicate history entries in change history panel**
- **Fixed**: History panel showed duplicate entries when multiple superusers exist — each save event creates one `Notification` per superuser. Fix: query is now filtered by `request.user` (if superuser) or the first superuser, guaranteeing exactly one row per event with no dedup overhead.

### v0.2.48 (2026-04-06)
**Feature: Change history panel — modal UI, M2M diff, permission gate**
- **Added**: Change history panel shown on every change-form — floating "History" button (bottom-right, `fixed position`) opens a scrollable modal listing the 50 most recent `Notification` records for the object.
- **Added**: Each history entry displays: action badge (Create/Update/Delete/Restore), actor avatar + username, timestamp, and an **old → new diff** for every changed field using `changed_data` from the `Notification` model.
- **Added**: `has_view_history_permission()` on `ModelAdmin` — panel is shown only to superusers or users with `change` permission; read-only staff cannot see history.
- **Added**: `show_history = True` class attribute on `ModelAdmin` — subclasses can opt out per model by setting `show_history = False`.
- **Fixed**: DaisyUI v5 `ui-` prefix applied correctly to `ui-modal`, `ui-modal-box`, `ui-modal-backdrop`, `ui-btn` — resolves invisible/broken modal.
- **Fixed**: Trigger `<button type="button">` — prevents accidental form submission when clicking the History button.
- **Fixed**: Close button and backdrop use `dialog.close()` via JS — avoids nested `<form method="dialog">` inside the admin form (HTML spec violation that caused the button to escape DOM).
- **Fixed**: UNFOLD's built-in "Lịch sử" button hidden via `{% block object-tools-items %}{% endblock %}` — eliminates duplicate history link in the toolbar.
- **Improved**: `import ast` and `reverse` moved to module-level imports in `modeladmin.py`.
- **Improved**: All panel strings wrapped in `{% trans %}` for full i18n support.
- **Improved**: `change_list.html` — pagination state (`p=...`) now preserved in `sessionStorage` alongside filters; navigating back from a change form restores the correct page instead of jumping to page 1.

### v0.2.47 (2026-04-05)
**Feature: M2M change tracking, zero-DB App dashboard, dual-view UI**
- **Added**: `m2m_changed` signal handler for all concrete `BaseModel` subclasses — `.add()`, `.remove()`, `.set()`, `.clear()` on any ManyToMany field now correctly updates `updated_at`/`updated_by` and sends a notification to superusers with the same `changed_data` format as `save()`.
- **Added**: App dashboard — two toggle-able view modes: **grid** (2-level category → app cards) and **list** (flat grouped), persisted via `localStorage`.
- **Removed**: `init_app_db()` DB-write mechanism — App dashboard now reads directly from `settings.UNFOLD['SIDEBAR']` via a new `_parse_sidebar_apps()` helper; zero DB writes on page load.
- **Fixed**: `app_badge_callback()` counted from stale DB; now counts from `settings.UNFOLD['SIDEBAR']` — badge is always in sync with config.
- **Fixed**: `has_permission()` in `AppAdmin` now handles callable UNFOLD permissions (lambdas) in addition to dotted-string imports.
- **Improved**: Pagination and filter bars hidden on App dashboard via `{% block pagination %}` and `{% block filters %}` override.

### v0.2.46 (2026-04-04)
**Fix: Email template — logo URL, company name, and contact details**
- **Fixed**: Logo URL updated from `api.logo.com` to stable Google-hosted URL.
- **Fixed**: Company name updated to `White Neuron Co., Ltd` (official name).
- **Fixed**: Title updated to `Founder & CTO`.
- **Fixed**: Website URL in signature changed to full `https://whiteneuron.ai`.

### v0.2.45 (2026-04-03)
**Security: 11 CVE fixes across django, pillow, cryptography, pyasn1**
- **Security**: `django` lower bound raised from `>=5.1.6` to `>=5.2.12` — patches 7 CVEs including SQL Injection (CVE-2026-1207), DoS ×5, race condition in file-system storage (CVE-2026-25674), and URLField vulnerability (CVE-2026-25673).
- **Security**: `pillow` lower bound raised from `>=11.0.0` to `>=12.1.1` — patches heap buffer overflow (CVE-2026-25990).
- **Security**: `cryptography>=46.0.5` added as an explicit dependency — patches Improper Input Validation (CVE-2026-26007); previously uncontrolled transitive dependency.
- **Security**: `pyasn1>=0.6.2` added as an explicit dependency — patches CVE-2026-23490; `==0.6.1` was the sole affected version.
- **Validation**: `safety` scan confirms 0 known vulnerabilities after upgrade (down from 11).

### v0.2.44 (2026-04-02)
**Fixes & Improvements: Feedback System — Error handling, input limits, i18n lazy evaluation**
- **Fixed**: `changeform_view` now returns `JsonResponse({"success": True})` after a successful resolve instead of falling through to `super()` with a POST request — prevents a spurious HTTP 403 caused by `has_change_permission = False`.
- **Fixed**: `note` is read from `request.POST` instead of `request.GET` — prevents HTTP 414 (URI Too Long) when the note is lengthy.
- **Fixed**: JS `fetch` upgraded to POST + `FormData` with CSRF token; error handling now maps status codes (403/404/500/network) to specific user-facing messages.
- **Added**: Two-sided character limits — `maxlength` attribute + live counter on client; server-side validation: `note ≤ 500`, `feedback_message ≤ 2000`.
- **Added**: `get_short_message()` in `FeedbackDataAdmin.list_display` — truncates to 200 words via Django's `Truncator`.
- **Fixed**: `search_help_text` moved from `__init__` to a `@property` using `format_lazy` — now re-evaluates per request and responds correctly to language switches instead of being frozen at server startup.
- **Improved**: `base_badge_callback()` accepts an optional `filter_kwargs` parameter; `feedback_data_badge_callback()` now scopes the badge count to the current user for non-superusers.

### v0.2.43 (2026-04-01)
**Feature: Feedback System — DaisyUI modals, anti-spam cooldown, i18n, security hardening**
- **Added**: DaisyUI `<dialog>` modals replace native `prompt()`/`alert()` in both `feedback_change_form.html` (Mark as Resolved flow) and `submit_line.html` (Feedback submission) — smooth animations, no browser dialogs.
- **Added**: Server-side anti-spam cooldown — 60s per user globally; HTTP 429 with dynamically calculated remaining seconds (`remaining = 60 - elapsed`).
- **Security**: Replaced `@csrf_exempt` with `@require_POST` in feedback endpoint — CSRF protection fully enforced via `X-CSRFToken` header.
- **Security**: Auth check moved before body parse; removed redundant `User.objects.get()` in favor of `request.user`.
- **Fixed**: `FeedbackDataAdmin.changeform_view()` — null guard added after `get_object()` to prevent `AttributeError` when object does not exist.
- **Fixed**: OK button in result modal now wrapped in `<form method="dialog">` — dialog closes correctly, `close` event fires `location.reload()`.
- **Fixed**: Buttons missing `type="button"` were inadvertently submitting the admin form — fixed across all modals.
- **Fixed**: Modals moved to `document.body` via JS — eliminates content flash at page bottom during closing animation.
- **Fixed**: Import cleanup in `feedbacks/admin.py` — removed unused `display` import, moved `FEEDBACK_COOLDOWN_SECONDS` import to top.
- **Added**: Full i18n (`{% trans %}`, `{% blocktrans %}`, `gettext_lazy`) across feedback templates and `modeladmin.py` (12 strings); Vietnamese translations updated in `locale/vi`.
- **Added**: `feedback_cooldown_ms` passed from server via `FeedbackBaseAdmin.render_change_form()` — no more hardcoded 60000ms in template.

### v0.2.42 (2026-03-31)
**Improve: persist filter/search state in admin changelist + fix Django duplicate filter bug**
- **Added**: Filter/search state is now persisted via `sessionStorage` across navigation — selecting a filter, navigating to a detail page, then returning restores the exact filter state automatically.
- **Fixed**: Django bug — `add_preserved_filters()` uses `dict(parse_qsl())` which drops duplicate filter params (e.g. `?chapter__id__exact=29&chapter__id__exact=31` → only `=31` kept after save). Fixed server-side in `ModelAdmin._fix_preserved_filters()` — rebuilds the redirect URL with `parse_qsl()` (preserves all values) when duplicates are detected.
- **Fixed**: `_changelist_filters` URL param (Django's format for preserved filters when navigating from change form) — decoded to individual params before saving to storage, then the URL is redirected to clean form (no ugly `_changelist_filters=...` in browser bar).
- **Fixed**: README image broken on PyPI — changed from relative `docs/images/main.png` to absolute GitHub raw URL.
- **Improved**: Single redirect point in changelist JS — eliminated multiple chained `window.location.replace()` calls; at most one redirect per page load.

### v0.2.41 (2026-03-31)
**Fix: App dashboard menu not syncing after SIDEBAR changes**
- **Fixed**: `init_app_db()` used `cache.set(..., timeout=None)` (permanent cache) — after deploy/SIDEBAR changes, the App DB was never re-synced, causing dashboard menu to show stale data.
- **Fixed**: Cache TTL changed to 300s (5 minutes) — SIDEBAR changes now propagate automatically within 5 minutes without manual cache clearing.

### v0.2.40 (2026-03-31)
**Improve: App Dashboard — two-level category/app grid, UI polish, i18n fixes**
- **Added**: Two-level App dashboard grid — category cards (level 1) expand to app cards (level 2) via Alpine.js client-side navigation, no page reload.
- **Added**: `app_change_list.html` model-specific template — category mosaic (2×2 icon grid), app card grid, back button, smooth transitions.
- **Improved**: Category mosaic — handles 1 app (single large icon), 2–3 apps (placeholder fill), 4 apps (full 2×2), 5+ apps (3 icons + "+N" counter on 4th cell).
- **Improved**: App card icon — removed incorrect `static()` wrapper on `thumbnail_url` (already a full URL).
- **Improved**: Search bar hidden on App dashboard (not usable in two-level layout).
- **Fixed**: `change_list_view` queryset evaluated once via `list(qs)` to avoid double `get_queryset()` / double `init_app_db()` call.
- **Fixed**: Translation `"Active"` → `"Hoạt động"` (was incorrectly `"Hành động"` = Action).
- **Fixed**: Removed incorrect `{% trans %}` on DB values (`category`, `app.name`) — Django `{% trans %}` only resolves catalog entries, DB values are already stored in the target language.

### v0.2.39 (2026-03-31)
**Fix: `get_client_ip()` — validate IP headers, fix block-all bug with Cloudflare Tunnel**
- **Fixed**: `CF-Connecting-IP` and `True-Client-IP` headers were not validated before use — raw strings could flow directly into Redis cache keys, causing incorrect rate limiting or unintended blocks.
- **Fixed**: `REMOTE_ADDR` was also used without validation — now normalized through `_parse_ip()` before use.
- **Fixed**: Block-all-users bug — when using Cloudflare **Tunnel** (`cloudflared`), `CF-Connecting-IP` is not set; code fell through to XFF which contained the Cloudflare Edge IP as the first entry → all users shared one IP bucket → blocking one user blocked everyone.
- **Added**: `_parse_ip()` helper — normalizes and validates IP strings via `ipaddress.ip_address()`, returns `None` for invalid input; applied to all header sources (CF, XFF, REMOTE_ADDR).
- **Improved**: XFF parsing refactored — uses an explicit loop with `_parse_ip()` per entry instead of a list comprehension calling `is_global_ip()` on raw strings.
- **Fixed**: `env.example` — corrected `BEHIND_CLOUDFLARE` default to `False` and added clear comment distinguishing Cloudflare Proxy vs Cloudflare Tunnel.

### v0.2.38 (2026-03-31)
**Security: UA Blacklist — block bots/crawlers by User-Agent**
- **Added**: `UABlacklist` model (`base/ua_blacklists`) — manage blocked IPs in real-time via Django Admin, supports permanent and temporary blocks (`blocked_until` with Redis TTL auto-expiry).
- **Added**: `UABlacklistAdmin` — UI with Activate/Deactivate actions, `is_regex` toggle, shown in System sidebar under `block` icon, superuser only.
- **Added**: `RateLimitMiddleware._is_ua_blacklisted()` — two-layer check: static keywords from `UA_BLACKLIST` env (loaded at startup) + dynamic patterns from Redis cache (managed via admin, real-time).
- **Added**: `UA_BLACKLIST` setting in `env.example` — comma-separated substring keywords loaded at startup (no Redis required), e.g. `GPTBot,ClaudeBot,https://openai.com`.
- **Added**: Dynamic patterns support `is_regex=True` — executes `re.search(pattern, ua, re.IGNORECASE)`, invalid regex patterns are safely skipped per-entry.
- **Fixed**: Cache miss fallback — when Redis restarts or on first boot, patterns are loaded from DB and cache is warmed automatically (prevents bots from slipping through during cold start).
- **Added**: Migration `base/016_uablacklist.py`.

### v0.2.37 (2026-03-31)
**Security: guest login — remove hardcoded password, passwordless login view**
- **Security**: Removed hardcoded password `'whiteneuron-guest-2024@'` from `init_guest.py` — guest user now created with `set_unusable_password()`, cannot be authenticated via password at all.
- **Security**: Removed JavaScript-based guest login button that exposed the password in plain HTML source — replaced with a server-side `GuestLoginView` (POST-only, CSRF-protected).
- **Added**: `GuestLoginView` at `base/guest-login/` — bypasses password authentication entirely, calls `login()` directly, validates `next` redirect with `url_has_allowed_host_and_scheme()`.
- **Improved**: `init_guest` command now sets `is_staff=True` explicitly on user creation.
- **CI**: Added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to GitHub Actions workflow — prevents deprecation warnings for Node.js 20 before June 2026 deadline.

### v0.2.36 (2026-03-30)
**Security: init_admin — remove hardcoded password, random generation, auto email delivery**
- **Security**: Removed hardcoded password `'wnadmin2024&'` from `init_admin.py` — replaced with `secrets.choice()` (CSPRNG) generating a 20-character password (uppercase, lowercase, digits, special chars).
- **Added**: `INIT_ADMIN_PASSWORD` env var support — uses fixed password from `.env` if set, otherwise generates randomly.
- **Added**: `INIT_ADMIN_EMAIL` env var (required) — email recipient for the temporary password; no longer hardcoded.
- **Added**: Automatically sends password via `send_email_login()` using the standard project email template (company signature, login link) when password is random.
- **Added**: `--reset-password` flag for `init_admin` command — resets password for an existing admin without affecting normal CI/CD runs.
- **Fixed**: Double DB write when creating a new user — now a single `save()` call.
- **Fixed**: Email validation happens before writing password to DB — prevents password being changed without email delivery.
- **Improved**: `send_email_login()` accepts `is_reset` param — email subject adapts to context (new account vs reset).
- **Removed**: Unused `templates/admin/base/email_password.html`.

### v0.2.35 (2026-03-29)
**Dynamic IP Blacklist: Redis + Model + Admin**
- **Added**: `IPBlacklist` model (`base/ip_blacklists`) — manage blocked IPs in real-time via Django Admin, supports permanent and temporary blocks (`blocked_until` with Redis TTL auto-expiry).
- **Added**: `IPBlacklistAdmin` — IP blacklist management UI with Activate/Deactivate actions, shown in System sidebar under `block` icon, superuser only.
- **Added**: **"Block IP address"** action in `UserActivityAdmin` — select activity records → block IP immediately in Redis, no Daphne restart required.
- **Improved**: `RateLimitMiddleware._is_blacklisted()` also checks `cache.get('blacklist:dynamic:<ip>')` after static env blacklist — hybrid two-layer static + dynamic blocking.
- **Added**: Migration `base/015_ipblacklist.py`.

### v0.2.34 (2026-03-29)
**IP Blacklist: permanent IP/CIDR blocking via `.env`**
- **Added**: `RateLimitMiddleware._is_blacklisted()` — checks IP/CIDR blacklist before rate limiting, returns 403 immediately for blocked IPs.
- **Added**: Parse `IP_BLACKLIST` from settings (comma-separated IPs and/or CIDRs), supports IPv4 and IPv6 — single IPs use `set` lookup O(1), CIDR ranges use `ip_network` match.
- **Added**: `IP_BLACKLIST` setting in `settings.py` and corresponding variable in `env.example`.

### v0.2.33 (2026-03-29)
**Rate Limiting fix for Docker + Daphne**
- **Fixed**: `_is_rate_limited()` and `_is_user_rate_limited()` now catch `except Exception: return False` — handles `ConnectionError` when Redis is unreachable in Docker (previously unhandled exception caused requests to crash or bypass rate limiting).
- **Fixed**: Default `RATE_LIMIT_REQUESTS` lowered from 300 → 60 req/60 s, `USER_RATE_LIMIT_REQUESTS` from 200 → 60 — appropriate for an admin panel.
- **Fixed**: `User.display_header()` uses `reverse('admin:base_user_change')` instead of hardcoded `/admin/base/user/` — prevents broken links when changing admin prefix.
- **Fixed**: Default `BEHIND_CLOUDFLARE=True` since deployments always use Cloudflare Tunnel.

### v0.2.32 (2026-03-29)
**Security hardening & Gunicorn production readiness**
- **Security**: `get_client_ip()` only trusts `CF-Connecting-IP` / `True-Client-IP` when `BEHIND_CLOUDFLARE=True` — prevents rate limit bypass via spoofed headers.
- **Fixed**: `UserActivityMiddleware.__call__()` caches `do_not_track()` result in `skip` — avoids double invocation per request.
- **Removed**: Unused `import logging` from middleware.py.

### v0.2.31 (2026-03-29)
**Rate Limiting, Security Hardening & Error Pages**
- **Added**: `RateLimitMiddleware` — global IP-based rate limiting (60 req/60 s default) placed immediately after `SecurityMiddleware`, works for both API and browser requests.
- **Improved**: `UserActivityMiddleware` adds per-user rate limiting (60 req/60 s default).
- **Added**: `/ws/` added to `UserActivityMiddleware` `exclude_paths` — WebSocket handshakes are not logged and are not counted toward rate limits.
- **Security**: Sanitizes `POST` data before writing to `UserActivity` — masks sensitive fields (password, token, api_key, etc.).
- **Security**: Switched to `cache.incr()` first pattern (atomic on Redis) to prevent race conditions.
- **Added**: Full error templates: `400.html`, `403.html`, `404.html`, `429.html`, `500.html`.
- **Added**: Minimal `base.html` skeleton for error pages — no dependency on external static files.
- **Added**: Startup warning when running production without Redis (rate limiting inaccurate on multi-worker).

### v0.2.30 (2026-03-29)
- **Improved**: `AppAdmin.get_queryset()` returns only active apps the user actually has access to.
- **Improved**: `superuser` retains visibility over all active apps.

### v0.2.29 (2026-03-28)
- **Fixed**: `NotificationAdmin` no longer returns 403 when clicking `View Linked Object`.
- **Improved**: View linked object action routed via a dedicated detail action, better compatibility with Unfold.
- **Improved**: Safe handling when notification has no `obj_link`.

### v0.2.28 (2026-03-28)
- **Improved**: Grid view of user/app uses more intuitive icons for role and status.
- **Improved**: Standardized `verbose_name` for multiple fields in `Notification` and `NotificationConfig`.
- **Added**: Migration `notification/012` to sync field-level metadata.

### v0.2.27 and earlier
See [releases](https://github.com/White-Neuron/django-whiteneuron/releases) for full history.
