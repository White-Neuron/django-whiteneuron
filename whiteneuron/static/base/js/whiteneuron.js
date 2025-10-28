// Copyright (c) 2023-2024 WhiteNeuron

// Set the data-theme attribute on the HTML tag based on the adminTheme setting. It will make daisyui work with Alpine.js
document.addEventListener("DOMContentLoaded", function () {
    const htmlTag = document.documentElement;
    // Tính toán trạng thái dark/light
    const isDark = (adminTheme === 'dark' || (adminTheme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches));
    
    // Set cả class lẫn attribute
    htmlTag.setAttribute("data-theme", isDark ? "dark" : "light");
    htmlTag.classList.toggle("dark", isDark);
});


function toast_(message, type = "info", title = "Notification") {
    const toastContainer = document.getElementById("toast-container");
    if (toastContainer) {
        const toastItem = document.createElement("div");
        toastItem.className = `ui-alert ui-alert-${type}`;
        toastItem.innerHTML = `
            <span>${title}</span>
            <p>${message}</p>
        `;
        toastContainer.appendChild(toastItem);
        
        // Automatically remove the toast after 5 seconds
        setTimeout(() => {
            toastItem.remove();
        }, 5000);
    }
}

// WebSocket connection for notifications
const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
const ws = new WebSocket(wsProtocol + window.location.host + "/ws/notifications/");
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    toast_(data.content, data.type, data.title);
};