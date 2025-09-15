Trix.config.blockAttributes.heading2 = {
    tagName: "h2",
    breakOnReturn: true,
    group: false,
    terminal: true
}

Trix.config.blockAttributes.heading3 = {
    tagName: "h3",
    breakOnReturn: true,
    group: false,
    terminal: true
}

Trix.config.blockAttributes.heading4 = {
    tagName: "h4",
    breakOnReturn: true,
    group: false,
    terminal: true
}

Trix.config.blockAttributes.p = {
    tagName: "p",
    breakOnReturn: true,
    terminal: true
}

Trix.config.textAttributes.underlined = {
    tagName: "u",
    inheritable: true,
    parser(element) {
        const style = window.getComputedStyle(element);
        return style.textDecoration === "underline";
    },
}

document.addEventListener("trix-before-initialize", () => {
    Trix.config.toolbar.getDefaultHTML = () => document.getElementById("trix-toolbar").innerHTML
})

// HTML Editor functionality
document.addEventListener("DOMContentLoaded", function() {
    // Initialize HTML Editor toggle functionality for all WYSIWYG editors
    function initializeHtmlEditorToggle() {
        document.querySelectorAll('.wysiwyg-container').forEach(container => {
            // Skip if already initialized
            if (container.dataset.htmlEditorInitialized) return;
            
            const trixEditor = container.querySelector('trix-editor');
            const htmlTextarea = container.querySelector('.html-editor-textarea');
            const hiddenInput = container.parentElement.querySelector('input[type="hidden"]');
            
            if (!trixEditor || !htmlTextarea || !hiddenInput) return;
            
            let isHtmlMode = false;
            
            // Find the toggle button in the toolbar
            const toggleButton = document.querySelector('#html-editor-toggle');
            if (!toggleButton) return;
            
            // Clone the button for this specific editor instance
            const editorToggleButton = toggleButton.cloneNode(true);
            editorToggleButton.id = `html-editor-toggle-${trixEditor.getAttribute('input')}`;
            toggleButton.parentElement.replaceChild(editorToggleButton, toggleButton);
            
            function updateButtonState() {
                const icon = editorToggleButton.querySelector('.material-symbols-outlined');
                
                // Get all toolbar buttons except the HTML editor toggle
                const toolbarButtons = document.querySelectorAll('[data-trix-attribute], [data-trix-action]');
                
                if (isHtmlMode) {
                    icon.textContent = 'wysiwyg';
                    editorToggleButton.title = 'Visual Editor';
                    editorToggleButton.classList.add('text-primary-600');
                    
                    // Disable other toolbar buttons in HTML mode
                    toolbarButtons.forEach(button => {
                        button.disabled = true;
                        button.style.opacity = '0.5';
                        button.style.pointerEvents = 'none';
                    });
                } else {
                    icon.textContent = 'html';
                    editorToggleButton.title = 'HTML Editor';
                    editorToggleButton.classList.remove('text-primary-600');
                    
                    // Enable other toolbar buttons in WYSIWYG mode
                    toolbarButtons.forEach(button => {
                        button.disabled = false;
                        button.style.opacity = '';
                        button.style.pointerEvents = '';
                    });
                }
            }
            
            function getHtmlFromTrix() {
                // Get HTML content from Trix editor using multiple fallback methods
                if (trixEditor.editor) {
                    // Try to get the raw HTML from Trix editor's element
                    const trixContent = trixEditor.editor.element.innerHTML || trixEditor.value || hiddenInput.value || '';
                    return formatHtml(trixContent);
                }
                const content = trixEditor.innerHTML || trixEditor.value || hiddenInput.value || '';
                return formatHtml(content);
            }
            
            // function formatHtml(html) {
            //     if (!html) return '';
                
            //     // Add line breaks and indentation for better readability
            //     let formatted = html
            //         // Add line breaks before opening tags
            //         .replace(/(<(?:div|p|h[1-6]|blockquote|ul|ol|li|figure)(?:\s[^>]*)??>)/gi, '\n$1')
            //         // Add line breaks after closing tags
            //         .replace(/(<\/(?:div|p|h[1-6]|blockquote|ul|ol|li|figure)>)/gi, '$1\n')
            //         // Add line breaks around self-closing tags
            //         .replace(/(<(?:br|img|hr)(?:\s[^>]*)?\/?>)/gi, '\n$1\n')
            //         // Clean up multiple line breaks
            //         .replace(/\n\s*\n/g, '\n')
            //         // Trim leading/trailing whitespace
            //         .trim();
                
            //     return formatted;
            // }
            
            function switchToHtmlMode() {
                const htmlContent = getHtmlFromTrix();
                htmlTextarea.value = htmlContent;
                // Also update hidden input to ensure sync
                hiddenInput.value = htmlContent;
                trixEditor.style.display = 'none';
                htmlTextarea.classList.remove('hidden');
                isHtmlMode = true;
                updateButtonState();
            }
            
            function switchToWysiwygMode() {
                let htmlContent = htmlTextarea.value.trim();
                
                // Clean up formatting for Trix consumption
                htmlContent = htmlContent
                    // Remove extra line breaks that might cause display issues
                    .replace(/\n\s*\n/g, '\n')
                    // Remove line breaks around inline elements
                    .replace(/\n(<(?:strong|em|u|a|span)[^>]*>)/gi, '$1')
                    .replace(/(<\/(?:strong|em|u|a|span)>)\n/gi, '$1');
                
                // Update hidden input first
                hiddenInput.value = htmlContent;
                
                // Update Trix editor content using proper method
                try {
                    if (trixEditor.editor) {
                        trixEditor.editor.loadHTML(htmlContent);
                    } else {
                        // Fallback if editor not ready
                        trixEditor.value = htmlContent;
                    }
                } catch (error) {
                    // Try alternative method
                    trixEditor.value = htmlContent;
                }
                
                trixEditor.style.display = 'block';
                htmlTextarea.classList.add('hidden');
                isHtmlMode = false;
                updateButtonState();
            }
            
            // Toggle button click handler
            editorToggleButton.addEventListener('click', function(e) {
                e.preventDefault();
                
                if (isHtmlMode) {
                    switchToWysiwygMode();
                } else {
                    switchToHtmlMode();
                }
            });
            
            // Sync HTML textarea changes back to hidden input and Trix
            htmlTextarea.addEventListener('input', function() {
                if (isHtmlMode) {
                    hiddenInput.value = htmlTextarea.value;
                }
            });
            
            // Sync Trix editor changes to hidden input and HTML textarea
            trixEditor.addEventListener('trix-change', function() {
                if (!isHtmlMode) {
                    const content = trixEditor.value || '';
                    hiddenInput.value = content;
                    // Also update HTML textarea in background so it's ready when switched
                    htmlTextarea.value = content;
                }
            });
            
            // Additional sync on form submission
            const form = trixEditor.closest('form');
            if (form) {
                form.addEventListener('submit', function() {
                    if (isHtmlMode) {
                        hiddenInput.value = htmlTextarea.value;
                    } else {
                        hiddenInput.value = trixEditor.value || '';
                    }
                });
            }
            
            // Wait for Trix editor to be ready before initializing
            trixEditor.addEventListener('trix-initialize', function() {
                // Initialize with current content
                const initialContent = hiddenInput.value || '';
                if (initialContent) {
                    htmlTextarea.value = initialContent;
                    if (trixEditor.editor) {
                        trixEditor.editor.loadHTML(initialContent);
                    }
                }
                updateButtonState();
            });
            
            // If trix is already initialized
            if (trixEditor.editor) {
                const initialContent = hiddenInput.value || '';
                if (initialContent) {
                    htmlTextarea.value = initialContent;
                }
                updateButtonState();
            }
            
            // Mark as initialized
            container.dataset.htmlEditorInitialized = 'true';
        });
    }
    
    // Initialize when page loads
    setTimeout(initializeHtmlEditorToggle, 100);
    
    // Re-initialize when new editors are added dynamically (for inline forms, etc.)
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE && 
                    (node.querySelector && node.querySelector('.wysiwyg-container'))) {
                    setTimeout(initializeHtmlEditorToggle, 200);
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});
