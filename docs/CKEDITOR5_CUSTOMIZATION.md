# CKEditor5 Unfold Theme Integration

This implementation provides a comprehensive customization of CKEditor5 to seamlessly integrate with the Unfold admin theme, utilizing Tailwind CSS 3 and DaisyUI 4 with the `ui-` prefix.

## Features

### 🎨 **Visual Design**
- **Modern UI**: Clean, minimalist design matching Unfold's aesthetic
- **Dark Mode Support**: Automatic theme detection and switching
- **Responsive Design**: Mobile-first approach with adaptive toolbars
- **DaisyUI Integration**: Uses `ui-` prefixed components for consistency

### 🛠 **Enhanced Functionality**
- **Auto-save**: Automatic content preservation with localStorage
- **Accessibility**: WCAG 2.1 compliant with proper ARIA labels
- **Word Count**: Real-time statistics display
- **Responsive Toolbar**: Simplified mobile interface
- **Theme Synchronization**: Automatic dark/light mode switching

### 🎯 **User Experience**
- **Smooth Animations**: Subtle transitions and hover effects
- **Focus Management**: Enhanced keyboard navigation
- **Error States**: Visual feedback for form validation
- **Loading States**: Progressive enhancement indicators

## File Structure

```
whiteneuron/static/base/
├── css/
│   └── ckeditor5.css          # Main styling with Tailwind classes
└── js/
    └── ckeditor5-unfold.js    # Enhanced functionality and configuration
```

## Implementation Details

### CSS Architecture (`ckeditor5.css`)

The CSS file uses Tailwind's `@apply` directive to leverage the existing design system:

- **Container Styling**: Matches Django form field appearance
- **Toolbar Design**: Uses DaisyUI button components with `ui-` prefix
- **Content Area**: Styled with typography utilities
- **Dark Mode**: Automatic color scheme adaptation
- **Responsive Breakpoints**: Mobile-optimized layouts

### JavaScript Enhancements (`ckeditor5-unfold.js`)

The JavaScript file provides advanced functionality:

- **Theme Management**: Detects and responds to theme changes
- **Configuration**: Comprehensive CKEditor setup optimized for content editing
- **Auto-save**: Background content preservation
- **Accessibility**: Enhanced keyboard and screen reader support
- **Mobile Optimization**: Responsive toolbar configuration

## Configuration Options

### Default Toolbar Configuration

```javascript
toolbar: {
    items: [
        'heading', '|',
        'bold', 'italic', 'link', '|',
        'bulletedList', 'numberedList', 'blockQuote', '|',
        'uploadImage', 'insertTable', '|',
        'code', 'codeBlock', '|',
        'subscript', 'superscript', 'highlight', '|',
        'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', '|',
        'mediaEmbed', 'removeFormat', '|',
        'sourceEditing'
    ]
}
```

### Color Palette Integration

The color picker integrates with your theme's primary colors:

```javascript
fontColor: {
    colors: [
        // Standard colors
        { color: 'hsl(0, 0%, 0%)', label: 'Black' },
        // ... other colors
        // Theme integration
        { color: 'rgb(var(--color-sky-500))', label: 'Primary' },
        { color: 'rgb(var(--color-sky-600))', label: 'Primary Dark' },
        { color: 'rgb(var(--color-sky-400))', label: 'Primary Light' }
    ]
}
```

## Usage

### Basic Implementation

```html
<!-- Include the CSS and JS files -->
<link rel="stylesheet" href="{% static 'base/css/ckeditor5.css' %}">
<script src="{% static 'base/js/ckeditor5-unfold.js' %}"></script>

<!-- Your CKEditor textarea -->
<div class="ck-editor-container">
    <textarea class="django_ckeditor_5" name="content"></textarea>
</div>
```

### Django Template Integration

```html
{% load static %}

<div class="field-box">
    <label for="id_content">Content:</label>
    <div class="ck-editor-container">
        {{ form.content }}
    </div>
</div>

<!-- Include styles and scripts -->
<link rel="stylesheet" href="{% static 'base/css/ckeditor5.css' %}">
<script src="{% static 'base/js/ckeditor5-unfold.js' %}"></script>
```

### Custom Configuration

```javascript
// Initialize with custom configuration
window.initUnfoldCKEditor(document.querySelector('#my-editor'), {
    toolbar: ['bold', 'italic', 'link'],
    placeholder: 'Custom placeholder text...',
    // Other custom options
});
```

## Customization

### Adding New Toolbar Items

```javascript
// Extend the default configuration
window.UnfoldCKEditorConfig.toolbar.items.push('specialCharacters');
```

### Custom Color Themes

```javascript
// Add custom colors to the palette
window.UnfoldCKEditorConfig.fontColor.colors.push({
    color: '#your-color',
    label: 'Custom Color'
});
```

### Styling Overrides

```css
/* Add custom styles in your CSS file */
.ck.ck-editor.my-custom-editor {
    @apply border-2 border-blue-500;
}

.ck.ck-editor.my-custom-editor .ck-toolbar {
    @apply bg-blue-50 dark:bg-blue-900;
}
```

## Browser Support

- **Modern Browsers**: Chrome 63+, Firefox 60+, Safari 12+, Edge 79+
- **Mobile Support**: iOS Safari 12+, Chrome Mobile 63+
- **Accessibility**: WCAG 2.1 AA compliant
- **RTL Support**: Full right-to-left text direction support

## Performance Considerations

- **Lazy Loading**: CKEditor initializes only when needed
- **Asset Optimization**: Minified CSS and JavaScript
- **Memory Management**: Proper cleanup on navigation
- **Auto-save Throttling**: Configurable save intervals

## Accessibility Features

- **Keyboard Navigation**: Full keyboard support for all features
- **Screen Reader Support**: Comprehensive ARIA labels and descriptions
- **High Contrast Mode**: Enhanced visibility in high contrast environments
- **Focus Management**: Proper focus indicators and tab order

## Error Handling

The implementation includes robust error handling:

- **Initialization Errors**: Graceful fallback to plain textarea
- **Network Issues**: Local storage backup for content
- **Browser Compatibility**: Feature detection and polyfills

## Development Notes

### CSS Processing

The CSS file uses Tailwind's `@apply` directive and requires processing through your build pipeline:

```bash
# Process through Tailwind
npx tailwindcss -i ./static/base/css/ckeditor5.css -o ./dist/ckeditor5.css
```

### JavaScript Dependencies

The JavaScript file depends on:
- CKEditor5 Classic Editor build
- Modern browser APIs (MutationObserver, localStorage)
- CSS custom properties support

### Testing Considerations

Test the implementation across:
- Different screen sizes (mobile, tablet, desktop)
- Theme switching (light/dark modes)
- Form validation states
- Content restoration from auto-save

## Troubleshooting

### Common Issues

1. **Styles not applying**: Ensure Tailwind CSS is processing the `@apply` directives
2. **Theme not switching**: Check that `data-theme` attribute changes are detected
3. **Auto-save not working**: Verify localStorage availability and permissions
4. **Mobile toolbar issues**: Check responsive breakpoints and toolbar configuration

### Debug Mode

Enable debug logging by setting:

```javascript
window.CKEditorDebug = true;
```

This will log initialization steps and theme changes to the console.

## License

This implementation follows the same license as your Django project and includes integration code compatible with CKEditor5's GPL license.