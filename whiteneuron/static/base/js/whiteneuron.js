// Copyright (c) 2023-2024 WhiteNeuron

// Set the data-theme attribute on the HTML tag based on the adminTheme setting. It will make daisyui work with Alpine.js

// Theme sync: adminTheme <-> data-theme (for DaisyUI, Alpine.js, etc.)
function syncAdminTheme() {
    const ADMIN_KEY = 'adminTheme';
    const DATA_KEY = 'data-theme';
    const html = document.documentElement;

    // Get system dark mode
    const prefersDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

    // Calculate theme from adminTheme
    function calcTheme(adminTheme) {
        if (adminTheme === 'dark' || adminTheme === '"dark"') return 'dark';
        if (adminTheme === 'light' || adminTheme === '"light"') return 'light';
        if (adminTheme === 'auto' || adminTheme === '"auto"') return prefersDark() ? 'dark' : 'light';
        return prefersDark() ? 'dark' : 'light';
    }

    // Apply theme to HTML, dialogs, toast, and all ui-* elements
    function applyTheme(theme) {
        html.setAttribute('data-theme', theme);
        html.classList.toggle('dark', theme === 'dark');
        // Dialogs, modals, toast
        document.querySelectorAll('dialog, .ui-modal, .ui-toast').forEach((el) => {
            el.setAttribute('data-theme', theme);
            el.classList.toggle('dark', theme === 'dark');
        });
        // All elements with class starting with ui-
        document.querySelectorAll('[class^="ui-"]').forEach((el) => {
            el.setAttribute('data-theme', theme);
            el.classList.toggle('dark', theme === 'dark');
        });
    }

    // Persist theme to localStorage
    function persistBoth(adminTheme, theme) {
        let cleanAdminTheme = 'auto';
        if (adminTheme) {
            cleanAdminTheme = adminTheme.replace(/"/g, '');
        }
        localStorage.setItem(ADMIN_KEY, `"${cleanAdminTheme}"`);
        localStorage.setItem(DATA_KEY, theme);
    }

    // Set theme (manual toggle)
    function setTheme(adminTheme) {
        const theme = calcTheme(adminTheme);
        persistBoth(adminTheme, theme);
        applyTheme(theme);
        const toggle = document.querySelector('.theme-controller');
        if (toggle) toggle.checked = theme === 'dark';
    }

    // Flag để tránh vòng lặp vô hạn
    let isSyncing = false;
    
    // Lưu reference đến original setItem trước khi override
    const originalSetItem = Storage.prototype.setItem;

    // Sync theme from current adminTheme value
    function syncFromAdminTheme() {
        if (isSyncing) return; // Tránh recursive call
        isSyncing = true;
        
        const adminTheme = localStorage.getItem(ADMIN_KEY);
        if (adminTheme) {
            const theme = calcTheme(adminTheme);
            const currentDataTheme = localStorage.getItem(DATA_KEY);
            // Chỉ sync nếu khác nhau để tránh update không cần thiết
            if (currentDataTheme !== theme) {
                // Dùng originalSetItem để tránh trigger lại override
                originalSetItem.call(localStorage, DATA_KEY, theme);
                applyTheme(theme);
                const toggle = document.querySelector('.theme-controller');
                if (toggle) toggle.checked = theme === 'dark';
            }
        }
        
        isSyncing = false;
    }

    // --- Override localStorage.setItem to detect adminTheme changes in same tab ---
    Storage.prototype.setItem = function(key, value) {
        const oldValue = this.getItem(key);
        originalSetItem.call(this, key, value);
        // Nếu adminTheme thay đổi và giá trị thực sự khác, tự động sync data-theme
        if (key === ADMIN_KEY && oldValue !== value && !isSyncing) {
            syncFromAdminTheme();
        }
    };

    // --- Init on page load ---
    let adminTheme = localStorage.getItem(ADMIN_KEY);
    if (!adminTheme) {
        adminTheme = prefersDark() ? 'dark' : 'light';
        localStorage.setItem(ADMIN_KEY, adminTheme);
    }
    const currentTheme = calcTheme(adminTheme);
    persistBoth(adminTheme, currentTheme);
    applyTheme(currentTheme);

    // --- Listen for theme toggle (if exists) ---
    document.addEventListener('DOMContentLoaded', () => {
        const toggle = document.querySelector('.theme-controller');
        if (toggle) {
            toggle.checked = currentTheme === 'dark';
            toggle.addEventListener('change', () => setTheme(toggle.checked ? 'dark' : 'light'));
        }
    });

    // --- Listen for changes between tabs ---
    window.addEventListener('storage', (e) => {
        // Nếu adminTheme thay đổi, cập nhật lại data-theme cho khớp
        if (e.key === ADMIN_KEY) {
            const adminTheme = localStorage.getItem(ADMIN_KEY);
            const theme = calcTheme(adminTheme);
            persistBoth(adminTheme, theme);
            applyTheme(theme);
        }
        // Nếu data-theme thay đổi, cập nhật lại adminTheme cho khớp
        if (e.key === DATA_KEY) {
            const dataTheme = localStorage.getItem(DATA_KEY);
            let newAdminTheme = 'auto';
            if (dataTheme === 'dark') newAdminTheme = 'dark';
            if (dataTheme === 'light') newAdminTheme = 'light';
            // Chỉ cập nhật nếu lệch
            if (calcTheme(localStorage.getItem(ADMIN_KEY)) !== dataTheme) {
                localStorage.setItem(ADMIN_KEY, `"${newAdminTheme}"`);
                applyTheme(dataTheme);
            }
        }
    });
}

// Run theme sync on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncAdminTheme);
} else {
    // DOM already ready, run immediately
    syncAdminTheme();
}

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