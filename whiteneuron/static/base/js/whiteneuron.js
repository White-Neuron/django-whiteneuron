// Copyright (c) 2023-2024 WhiteNeuron

// Set the data-theme attribute on the HTML tag based on the adminTheme setting. It will make daisyui work with Alpine.js
document.addEventListener("DOMContentLoaded", function () {
    const htmlTag = document.documentElement;

    const desiredBind = `(adminTheme === 'dark' || (adminTheme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? 'dark' : 'light'`;

    if (!htmlTag.hasAttribute("x-bind:data-theme")) {
        htmlTag.setAttribute("x-bind:data-theme", desiredBind);
    }
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