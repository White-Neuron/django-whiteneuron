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
  (`UNFOLD["COLORS"]`, remapped per theme by `daisy-themes.css`). Every `var()` has CKEditor's
  default as its fallback.
- **Dark mode** follows Unfold's `dark` class on `<html>`, which daisyUI dark themes also set.
  CKEditor's light defaults that are not derived from its base variables (button and input states,
  placeholders, selection, content text, captions) are overridden one by one.
- **Code blocks** are the one exception: CKEditor gives `pre` a fixed `#353535` text color with no
  variable, so a single dark-mode rule recolors it.

## Customizing in a project

Point `CKEDITOR_5_CUSTOM_CSS` at your own static file and override variables there. Start from the
packaged file, or keep it and load yours after it:

```css
:root {
  --ck-color-focus-border: #7c3aed;
  --ck-content-font-family: "Inter", system-ui, sans-serif;
}

.dark {
  --ck-color-base-background: #0b1020;
}
```

CKEditor declares its variables on `:root` and derives most of them from a few base ones
(`--ck-color-base-background`, `-foreground`, `-border`, `-text`). Override them on `<html>` (`:root`,
`.dark`) so the derived variables follow. The full list is in CKEditor's CSS
(`django_ckeditor_5/static/django_ckeditor_5/dist/styles.css`).

If you need Tailwind utilities, compile your stylesheet in your own build and point
`CKEDITOR_5_CUSTOM_CSS` at the output, never at the source.

## Troubleshooting

- **Transparent editor or black text in dark mode**: the stylesheet has invalid values, usually
  Tailwind source served without a build. Check the file in the browser's network tab.
- **Theme does not switch**: the variables follow the `dark` class on `<html>`. Check that Unfold's
  theme switch sets it.
