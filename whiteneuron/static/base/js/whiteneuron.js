// Copyright (c) 2023-2024 WhiteNeuron

// Set the data-theme attribute on the HTML tag based on the adminTheme setting. It will make daisyui work with Alpine.js

// ======================================================================
// CÁC HÀM THEME ĐƯỢC CHUYỂN RA NGOÀI VÀ GÁN VÀO "WINDOW"
// ======================================================================

/**
 * Tính toán theme (dark/light) dựa trên cài đặt adminTheme.
 * @param {string} adminTheme - Giá trị từ localStorage ('dark', 'light', 'auto').
 * @returns {string} - 'dark' hoặc 'light'.
 */
window.calcGlobalTheme = function(adminTheme) {
    const prefersDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (adminTheme === 'dark' || adminTheme === '"dark"') return 'dark';
    if (adminTheme === 'light' || adminTheme === '"light"') return 'light';
    if (adminTheme === 'auto' || adminTheme === '"auto"') return prefersDark() ? 'dark' : 'light';
    return prefersDark() ? 'dark' : 'light';
}

/**
 * Áp dụng theme (data-theme) cho <html> và tất cả các component UI.
 * @param {string} theme - 'dark' hoặc 'light'.
 */
window.applyGlobalTheme = function(theme) {
    const html = document.documentElement;
    html.setAttribute('data-theme', theme);
    html.classList.toggle('dark', theme === 'dark');
    
    // Tìm tất cả các component "đảo" (dialogs, tables, v.v.) và áp theme
    const elementsToTheme = document.querySelectorAll(
        // Bắt mọi phần tử có token class bắt đầu bằng "ui-" (kể cả không đứng đầu)
        'dialog, .ui-modal, .ui-modal-box, .ui .ui-toast, .ui-table, [class^="ui-"], [class*=" ui-"]'
    );
    
    elementsToTheme.forEach((el) => {
        el.setAttribute('data-theme', theme);
        el.classList.toggle('dark', theme === 'dark');
    });
}

// ======================================================================
// HÀM SYNC GỐC (ĐÃ CẬP NHẬT ĐỂ GỌI CÁC HÀM GLOBAL MỚI)
// ======================================================================

// Theme sync: adminTheme <-> data-theme (for DaisyUI, Alpine.js, etc.)
function syncAdminTheme() {
  const ADMIN_KEY = 'adminTheme';
  const DATA_KEY = 'data-theme';
  const html = document.documentElement;

    // *** Hai hàm calcTheme và applyTheme đã bị XÓA khỏi đây ***

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
    const theme = window.calcGlobalTheme(adminTheme); // <-- ĐÃ SỬA
    persistBoth(adminTheme, theme);
    window.applyGlobalTheme(theme); // <-- ĐÃ SỬA
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
      const theme = window.calcGlobalTheme(adminTheme); // <-- ĐÃ SỬA
      const currentDataTheme = localStorage.getItem(DATA_KEY);
      // Chỉ sync nếu khác nhau để tránh update không cần thiết
      if (currentDataTheme !== theme) {
        // Dùng originalSetItem để tránh trigger lại override
        originalSetItem.call(localStorage, DATA_KEY, theme);
        window.applyGlobalTheme(theme); // <-- ĐÃ SỬA
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
    adminTheme = window.calcGlobalTheme('auto'); // <-- ĐÃ SỬA
    localStorage.setItem(ADMIN_KEY, adminTheme);
  }
  const currentTheme = window.calcGlobalTheme(adminTheme); // <-- ĐÃ SỬA
  persistBoth(adminTheme, currentTheme);
  window.applyGlobalTheme(currentTheme); // <-- ĐÃ SỬA

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
      const theme = window.calcGlobalTheme(adminTheme); // <-- ĐÃ SỬA
      persistBoth(adminTheme, theme);
      window.applyGlobalTheme(theme); // <-- ĐÃ SỬA
    }
    // Nếu data-theme thay đổi, cập nhật lại adminTheme cho khớp
    if (e.key === DATA_KEY) {
      const dataTheme = localStorage.getItem(DATA_KEY);
      let newAdminTheme = 'auto';
      if (dataTheme === 'dark') newAdminTheme = 'dark';
      if (dataTheme === 'light') newAdminTheme = 'light';
      // Chỉ cập nhật nếu lệch
      if (window.calcGlobalTheme(localStorage.getItem(ADMIN_KEY)) !== dataTheme) { // <-- ĐÃ SỬA
        localStorage.setItem(ADMIN_KEY, `"${newAdminTheme}"`);
        window.applyGlobalTheme(dataTheme); // <-- ĐÃ SỬA
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