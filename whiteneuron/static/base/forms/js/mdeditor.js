(function() {
    'use strict';

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function createModal(targetId) {
        var editorId = targetId.replace('mdeditor-hidden-', '');
        
        // Check if modal already exists in body
        var existingModal = document.getElementById('md-preview-modal-' + editorId);
        if (existingModal) return existingModal;

        var modal = document.createElement('dialog');
        modal.id = 'md-preview-modal-' + editorId;
        modal.className = 'ui-modal';

        // Modal box container
        var modalBox = document.createElement('div');
        modalBox.className = 'ui-modal-box w-full max-w-4xl max-h-[85vh] flex flex-col p-0 overflow-hidden bg-base-100 text-base-content';

        // Header
        var headerDiv = document.createElement('div');
        headerDiv.className = 'flex items-center justify-between px-6 py-4 border-b border-base-200 dark:border-base-700';

        var titleH3 = document.createElement('h3');
        titleH3.className = 'text-lg font-semibold text-base-content';
        titleH3.textContent = 'Markdown Preview';

        // Close button — use modal.close() directly to avoid loading.js interception
        var closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn btn-sm btn-circle btn-ghost dark:hover:bg-base-800';
        closeButton.setAttribute('aria-label', 'Close modal');
        closeButton.textContent = '\u2715';
        closeButton.addEventListener('click', function() { modal.close(); });

        headerDiv.appendChild(titleH3);
        headerDiv.appendChild(closeButton);

        // Content area with prose styling
        var contentDiv = document.createElement('div');
        contentDiv.id = 'md-preview-content-' + editorId;
        contentDiv.className = 'flex-1 overflow-y-auto p-6 prose prose-sm max-w-none text-neutral-800 dark:text-neutral-200 dark:prose-invert';

        // Backdrop — plain div with click handler, no form to intercept
        var backdropDiv = document.createElement('div');
        backdropDiv.className = 'ui-modal-backdrop bg-black/50 dark:bg-black/70';
        backdropDiv.addEventListener('click', function(e) {
            if (e.target === backdropDiv) { modal.close(); }
        });

        modalBox.appendChild(headerDiv);
        modalBox.appendChild(contentDiv);
        modal.appendChild(modalBox);
        modal.appendChild(backdropDiv);

        document.body.appendChild(modal);
        return modal;
    }

    var editorHandlers = {}; // Store handlers for cleanup

    function initMdEditor(container) {
        var targetId = container.dataset.mdeditorTarget;
        if (!targetId || container.dataset.mdeditorInitialized === 'true') return;
        
        // Guard: element must be connected to DOM
        if (!container.isConnected) return;

        var hiddenInput = document.getElementById(targetId);
        var editorId = targetId.replace('mdeditor-hidden-', '');
        var editor = document.getElementById('mdeditor-editor-' + editorId);
        var previewBtn = container.querySelector('.mdeditor-toggle');
        var previewUrl = container.dataset.mdPreviewUrl || '/md-preview/';

        if (!editor || !hiddenInput) return;

        // Cleanup old handlers if re-initializing
        if (editorHandlers[editorId]) {
            var old = editorHandlers[editorId];
            if (old.editor && old.inputHandler) {
                old.editor.removeEventListener('input', old.inputHandler);
            }
            if (old.previewBtn && old.clickHandler) {
                old.previewBtn.removeEventListener('click', old.clickHandler);
            }
            if (old.form && old.submitHandler) {
                old.form.removeEventListener('submit', old.submitHandler);
            }
            // Remove handler reference after cleanup
            delete editorHandlers[editorId];
        }

        // Create modal in body (not nested in container to avoid inert issue)
        var modal = createModal(targetId);
        var previewContent = document.getElementById('md-preview-content-' + editorId);
        var previewLoading = container.querySelector('.preview-loading');
        var previewText = container.querySelector('.preview-text');

        if (!editor || !hiddenInput) return;

        // Sync hidden input synchronously on every keystroke (no debounce)
        function syncValue() {
            hiddenInput.value = editor.value;
        }

        var inputHandler = syncValue;
        editor.addEventListener('input', inputHandler);

        // Find parent form and attach submit handler as backup
        var form = container.closest('form');
        if (form) {
            var submitHandler = function() {
                hiddenInput.value = editor.value;
            };
            form.addEventListener('submit', submitHandler);
        } else {
            console.warn('[mdeditor] Form not found for widget:', editorId);
        }

        // Open preview modal and fetch HTML from server
        if (previewBtn && modal && previewContent) {
            var isFetching = false;

            function resetLoadingState() {
                isFetching = false;
                previewBtn.disabled = false;
                if (previewLoading) previewLoading.classList.add('hidden');
                if (previewText) previewText.textContent = 'Preview';
            }

            var clickHandler = function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                if (isFetching) return;
                
                // Sync value before fetching
                hiddenInput.value = editor.value;
                
                var mdText = editor.value;
                
                // Size limit check (1MB max)
                if (mdText.length > 1048576) {
                    console.error('[mdeditor] Markdown content too large (>1MB)');
                    previewContent.innerHTML = '<p class="text-red-600 dark:text-red-400 text-sm p-4">Markdown content exceeds 1MB limit</p>';
                    modal.showModal();
                    return;
                }
                
                isFetching = true;
                
                // Show loading state on button
                previewBtn.disabled = true;
                if (previewLoading) previewLoading.classList.remove('hidden');
                if (previewText) previewText.textContent = 'Loading...';

                fetch(previewUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ markdown: mdText })
                })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (data.success && previewContent) {
                        previewContent.innerHTML = data.html;
                        modal.showModal();
                    } else {
                        console.error('[mdeditor] Preview error:', data.error);
                        previewContent.innerHTML = '<p class="text-red-600 dark:text-red-400 text-sm p-4">Error rendering preview</p>';
                        modal.showModal();
                    }
                })
                .catch(function(err) {
                    console.error('[mdeditor] Fetch error:', err);
                    if (previewContent) {
                        previewContent.innerHTML = '<p class="text-red-600 dark:text-red-400 text-sm p-4">Network error. Please try again.</p>';
                        modal.showModal();
                    }
                })
                .finally(resetLoadingState);
            };

            previewBtn.addEventListener('click', clickHandler);

            // Reset loading state when modal closes
            modal.addEventListener('close', resetLoadingState);

            // Store handlers for cleanup
            editorHandlers[editorId] = {
                editor: editor,
                inputHandler: inputHandler,
                previewBtn: previewBtn,
                clickHandler: clickHandler,
                form: form || null,
                submitHandler: form ? function() { hiddenInput.value = editor.value; } : null
            };
        }

        container.dataset.mdeditorInitialized = 'true';
    }

    function initAllMdEditors() {
        document.querySelectorAll('.mdeditor-container').forEach(initMdEditor);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllMdEditors);
    } else {
        initAllMdEditors();
    }

    // Debounce MutationObserver to avoid multiple rapid triggers
    var observerDebounceTimer = null;
    var pendingMutation = false;
    
    function triggerObserverCheck() {
        if (pendingMutation) return;
        pendingMutation = true;
        
        clearTimeout(observerDebounceTimer);
        observerDebounceTimer = setTimeout(function() {
            initAllMdEditors();
            pendingMutation = false;
        }, 100);
    }

    // Replace the direct observe with debounced version
    if (document.body) {
        var debouncedObserver = new MutationObserver(function(mutations) {
            triggerObserverCheck();
        });
        debouncedObserver.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            if (document.body) {
                var debouncedObserver = new MutationObserver(function(mutations) {
                    triggerObserverCheck();
                });
                debouncedObserver.observe(document.body, { childList: true, subtree: true });
            }
        });
    }

    // Cleanup modals on page unload to prevent memory leaks
    window.addEventListener('beforeunload', function() {
        var modals = document.querySelectorAll('[id^="md-preview-modal-"]');
        for (var i = 0; i < modals.length; i++) {
            if (modals[i].parentNode) {
                modals[i].parentNode.removeChild(modals[i]);
            }
        }
    });
})();
