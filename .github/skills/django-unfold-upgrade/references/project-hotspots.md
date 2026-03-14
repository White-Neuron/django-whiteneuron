# Project Hotspots For django-unfold Upgrades

Use this map to focus compatibility review where local customizations are deepest.

## Dependency and Core Settings
- `pyproject.toml`:
  - dependency floor for `django-unfold>=0.72.0`
- `whiteneuron/base/settings.py`:
  - `INSTALLED_APPS` includes multiple `unfold.contrib.*`
  - large `UNFOLD` configuration with callbacks, sidebar, styles, scripts, colors
  - crispy integration via `unfold_crispy`

## Python-Level Integrations
- `whiteneuron/base/admin.py`:
  - imports and uses `unfold.admin`, `unfold.decorators`, `unfold.widgets`, contrib forms/inlines/filters
- `whiteneuron/base/modeladmin.py`:
  - shared custom admin base built on Unfold classes/widgets/paginator
- `whiteneuron/base/views.py`:
  - `UnfoldModelAdminViewMixin`
- `whiteneuron/base/filters.py`:
  - `MultipleDropdownFilter`
- `whiteneuron/base/forms.py`:
  - custom auth form based on `unfold.forms.AuthenticationForm`
- `whiteneuron/base/sites.py`:
  - `UnfoldAdminSite`
- `whiteneuron/contrib/wn_import_export/admin.py`:
  - Unfold import/export forms
- Feature app admins using Unfold decorators:
  - `whiteneuron/notification/admin.py`
  - `whiteneuron/file_management/admin.py`
  - `whiteneuron/feedbacks/admin.py`

## Template and Templatetag Overrides (High Risk)
- Admin templates overriding default admin/Unfold behavior:
  - `whiteneuron/templates/admin/base.html`
  - `whiteneuron/templates/admin/login.html`
  - `whiteneuron/templates/admin/index.html`
  - `whiteneuron/templates/admin/header.html`
  - `whiteneuron/templates/admin/change_list.html`
  - `whiteneuron/templates/admin/grid_view_results.html`
- Direct Unfold helper overrides:
  - `whiteneuron/templates/unfold/helpers/field_password.html`
  - `whiteneuron/templates/unfold/helpers/navigation_user.html`
  - `whiteneuron/templates/unfold/helpers/pagination.html`
- Templatetag overrides:
  - `whiteneuron/base/templatetags/unfold_list_custom.py`
  - `whiteneuron/base/templatetags/wn_filters.py`

## Known Fragility Patterns
- Direct references to internal template helper paths may break across upstream releases.
- Any overridden helper template can drift from upstream context variables and block rendering.
- Custom callback-driven sidebar and badges depend on expected Unfold data contracts.
- Admin decorators and mixins can change signatures or behavior between releases.

## Recommended Focus Order
1. Import and startup validation (`manage.py check`, import traces)
2. Template render validation for login/index/changelist/changeform
3. Admin actions, filters, pagination, and sidebar callback behavior
4. Styling/widget regressions in customized forms and CKEditor integrations
