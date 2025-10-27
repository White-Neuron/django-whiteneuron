// Copyright (c) 2023-2024 WhiteNeuron

/**
 * Hiển thị thông báo toast.
 * Tự động tạo container nếu chưa tồn tại.
 */
function toast_(message, type = "info", title = "Notification") {
    let toastContainer = document.getElementById("toast-container");

    // Tối ưu: Nếu container chưa tồn tại, hãy tạo nó.
    if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.id = "toast-container";
        // Thêm class của DaisyUI/Unfold để định vị toast
        toastContainer.className = "toast toast-top toast-end z-[9999]"; 
        document.body.appendChild(toastContainer);
    }

    const toastItem = document.createElement("div");
    // Sử dụng đúng class alert của bạn
    toastItem.className = `ui-alert ui-alert-${type} shadow-lg`; 
    toastItem.innerHTML = `
        <div class="flex flex-col">
          <span class="font-bold">${title}</span>
          <p>${message}</p>
        </div>
    `;
    toastContainer.appendChild(toastItem);
    
    // Tự động xóa toast sau 5 giây
    setTimeout(() => {
        toastItem.remove();
    }, 5000);
}

// Chỉ chạy 1 lần sau khi toàn bộ DOM đã sẵn sàng
document.addEventListener("DOMContentLoaded", function () {
    const htmlTag = document.documentElement;
    const bodyTag = document.body;

    // --- LOGIC MỚI: Tự động xử lý theme cho <dialog> ---
    // Logic này là đúng và được giữ lại.
    // Nó "lắng nghe" theme gốc của Unfold thay đổi.

    function applyThemeToDialog(dialog) {
        // Lấy theme (vd: "dark_unfold") mà Unfold đã set
        const currentTheme = htmlTag.getAttribute('data-theme');
        if (currentTheme) {
            dialog.setAttribute('data-theme', currentTheme);
        }
    }

    // Observer 1: Theo dõi <html> nếu `data-theme` thay đổi
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

    // Observer 2: Theo dõi <body> nếu có <dialog> mới được thêm vào
    const dialogObserver = new MutationObserver((mutationsList) => {
        for (const mutation of mutationsList) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // Chỉ kiểm tra element
                        if (node.tagName === 'DIALOG' && (node.classList.contains('ui-modal') || node.classList.contains('modal'))) {
                            applyThemeToDialog(node);
                        }
                        node.querySelectorAll('dialog.ui-modal, dialog[class*="modal"]').forEach(applyThemeToDialog);
                    }
                });
            }
        }
    });

    // Kích hoạt cả hai observers
    themeObserver.observe(htmlTag, { 
        attributes: true, 
        attributeFilter: ['data-theme'] 
    });

    dialogObserver.observe(bodyTag, { 
        childList: true, 
        subtree: true 
    });

    // Chạy 1 lần lúc tải trang cho các dialog có sẵn (nếu có)
    document.querySelectorAll('dialog.ui-modal, dialog[class*="modal"]').forEach(applyThemeToDialog);


    // --- LOGIC CŨ: Kết nối WebSocket (đã được tối ưu) ---
    // Được đưa vào đây để đảm bảo chạy sau khi DOM ready
    try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const ws = new WebSocket(wsProtocol + window.location.host + "/ws/notifications/");

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                // Gọi hàm toast_ (giờ đã an toàn vì container được tự tạo)
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