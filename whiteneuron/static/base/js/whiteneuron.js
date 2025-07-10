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
const ws = new WebSocket("ws://" + window.location.host + "/ws/notifications/");
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    toast_(data.content, data.type, data.title);
};
    // const toast = document.getElementById("toast-container");
    // if (toast) {
    //     const toastItem = document.createElement("div");
    //     if (data.type === "success") {
    //         toastItem.className = "ui-alert ui-alert-success";
    //     } else if (data.type === "error") {
    //         toastItem.className = "ui-alert ui-alert-error";
    //     } else if (data.type === "info") {
    //         toastItem.className = "ui-alert ui-alert-info";
    //     } else if (data.type === "warning") {
    //         toastItem.className = "ui-alert ui-alert-warning";
    //     }
    //     toastItem.innerHTML = `
    //         <span>${data.title}</span>
    //         <p>${data.content}</p>
    //     `;
    //     toast.appendChild(toastItem);
        
    //     // Automatically remove the toast after 5 seconds
    //     setTimeout(() => {
    //         toastItem.remove();
    //     }, 5000);
    // }
// };