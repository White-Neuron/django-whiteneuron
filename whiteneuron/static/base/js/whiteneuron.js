// Copyright (c) 2023-2024 WhiteNeuron

function toast_(message, type = "info", title = "Notification") {
    let toastContainer = document.getElementById("toast-container");

    if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.id = "toast-container";
        // Thêm class của DaisyUI/Unfold để định vị toast
        toastContainer.className = "toast toast-top toast-end z-[9999]"; 
        document.body.appendChild(toastContainer);
    }

    const toastItem = document.createElement("div");
    toastItem.className = `ui-alert ui-alert-${type} shadow-lg`; 
    toastItem.innerHTML = `
        <div class="flex flex-col">
          <span class="font-bold">${title}</span>
          <p>${message}</p>
        </div>
    `;
    toastContainer.appendChild(toastItem);
    
    setTimeout(() => {
        toastItem.remove();
    }, 5000);
}

// Chạy toàn bộ code sau khi DOM đã sẵn sàng
document.addEventListener("DOMContentLoaded", function () {
    const htmlTag = document.documentElement;
    const bodyTag = document.body;

    const desiredBind = `(adminTheme === 'dark' || (adminTheme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? 'dark' : 'light'`;
    if (!htmlTag.hasAttribute("x-bind:data-theme")) {
        htmlTag.setAttribute("x-bind:data-theme", desiredBind);
    }

    function applyThemeToDialog(dialog) {
        const currentTheme = htmlTag.getAttribute('data-theme');
        if (currentTheme) {
            dialog.setAttribute('data-theme', currentTheme);
        }
    }

    const themeObserver = new MutationObserver((mutationsList) => {
        for (const mutation of mutationsList) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                const newTheme = htmlTag.getAttribute('data-theme');
                document.querySelectorAll('dialog.ui-modal, dialog[class*="modal"]').forEach(dialog => {
                    if (newTheme) {
                        dialog.setAttribute('data-theme', newTheme);
                    }
                });
            }
        }
    });

    const dialogObserver = new MutationObserver((mutationsList) => {
        for (const mutation of mutationsList) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        if (node.tagName === 'DIALOG' && (node.classList.contains('ui-modal') || node.classList.contains('modal'))) {
                            applyThemeToDialog(node);
                        }
                        node.querySelectorAll('dialog.ui-modal, dialog[class*="modal"]').forEach(applyThemeToDialog);
                    }
                });
            }
        }
    });

    themeObserver.observe(htmlTag, { 
        attributes: true, 
        attributeFilter: ['data-theme'] 
    });

    dialogObserver.observe(bodyTag, { 
        childList: true, 
        subtree: true 
    });

    document.querySelectorAll('dialog.ui-modal, dialog[class*="modal"]').forEach(applyThemeToDialog);


    try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const ws = new WebSocket(wsProtocol + window.location.host + "/ws/notifications/");

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                toast_(data.content || 'No content', data.type || 'info', data.title || 'Notification');
            } catch (e) {
                console.error("Lỗi parse tin nhắn WebSocket:", e, event.data);
            }
        };

        ws.onerror = function(event) {
            console.error("Lỗi WebSocket:", event);
        };

        ws.onclose = function(event) {
            console.log("WebSocket đã đóng:", event.code);
        };

    } catch (e) {
        console.error("Không thể kết nối WebSocket:", e);
    }

}); 