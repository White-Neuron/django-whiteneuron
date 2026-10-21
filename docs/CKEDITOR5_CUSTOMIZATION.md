# CKEditor 5 in the Unfold admin

django-whiteneuron ships [django-ckeditor-5](https://github.com/hvlads/django-ckeditor-5) configured
for the admin, plus a small stylesheet that themes the editor with Unfold's colors in light and dark
mode.

## Enabling the editor

The default `TextField` widget of `whiteneuron.base.modeladmin.ModelAdmin` is `wysiwyg`. To use
CKEditor in a model admin:

```python
class ArticleAdmin(ModelAdmin):
    text_field_widget = "ckeditor"  # options: 'wysiwyg', 'ckeditor', 'mdeditor', ''
```

Or use `django_ckeditor_5.fields.CKEditor5Field` / `django_ckeditor_5.widgets.CKEditor5Widget` directly.

The package settings (`whiteneuron/base/settings.py`) define `CKEDITOR_5_CONFIGS` (toolbars),
`CKEDITOR_5_FILE_STORAGE`, `CKEDITOR_5_FILE_UPLOAD_PERMISSION` and:

```python
CKEDITOR_5_CUSTOM_CSS = "base/css/ckeditor5.css"
```

django-ckeditor-5 adds that file to the widget's media after CKEditor's own CSS.

## The theme stylesheet

`whiteneuron/static/base/css/ckeditor5.css` is **plain CSS with no build step**. Browsers get the
file exactly as committed, so it must not contain Tailwind syntax (`@apply`, `theme()`,
`@custom-variant`); a regression test checks this.

It only overrides CKEditor's `--ck-*` CSS variables, which is
[CKEditor's documented theming method](https://ckeditor.com/docs/ckeditor5/latest/framework/deep-dive/ui/theme-customization.html).
Layout, sizes and feature styles (colour pickers, highlights, image styles, tables, code blocks,
todo lists) stay CKEditor's own.

- **Colors** come from Unfold: `--color-base-*`, `--color-primary-*` and `--color-font-*`
  (`UNFOLD["COLORS"]`, remapped per theme by `daisy-themes.css`). The `var()` fallbacks only apply
  without them: CKEditor's defaults in light mode, Tailwind grays in dark mode.
- **Content font** is Inter, Unfold's font.
- **Dark mode** follows Unfold's `dark` class on `<html>`, which daisyUI dark themes also set.
  CKEditor's light defaults that are not derived from its base variables (button and input states,
  placeholders, selection, content text, captions, panels) are overridden one by one. A regression
  test lists the ones left as they are (accents, translucent overlays, badges) and fails when a
  django-ckeditor-5 upgrade adds a new one.
- **Fixed colors without a variable** get a dark-mode rule each: code block text (`#353535`), todo
  list checkbox borders (`#333`) and the text of find & replace matches.

## Customizing in a project

django-ckeditor-5 loads a single `CKEDITOR_5_CUSTOM_CSS` file. To keep the packaged theme and adjust
it, point the setting at your own static file and import the packaged one first:

```python
CKEDITOR_5_CUSTOM_CSS = "myproject/css/ckeditor5.css"
```

```css
/* static/myproject/css/ckeditor5.css */
@import url("../../base/css/ckeditor5.css");

:root {
  --ck-color-focus-border: #7c3aed;
}

html.dark {
  --ck-color-base-background: #0b1020;
}
```

Your rules come after the import and use the same selectors, so they win. Django's manifest
storages rewrite the relative `@import` to the hashed file name.

CKEditor declares its variables on `:root` and derives most of them from a few base ones
(`--ck-color-base-background`, `-foreground`, `-border`, `-text`). Override them on `<html>` (`:root`,
`html.dark`) so the derived variables follow. The full list is in CKEditor's CSS
(`django_ckeditor_5/static/django_ckeditor_5/dist/styles.css`).

If you need Tailwind utilities, compile your stylesheet in your own build and point
`CKEDITOR_5_CUSTOM_CSS` at the output, never at the source.

## Troubleshooting

- **Transparent editor or black text in dark mode**: the stylesheet has invalid values, usually
  Tailwind source served without a build. Check the file in the browser's network tab.
- **Theme does not switch**: the variables follow the `dark` class on `<html>`. Check that Unfold's
  theme switch sets it.
