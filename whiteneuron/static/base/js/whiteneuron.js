// Copyright (c) 2023-2024 WhiteNeuron

/*
 * Admin themes.
 *
 * Unfold toggles the "dark" class on <html> from its persisted `adminTheme`
 * (light / dark / auto). On top of that the user may pick a daisyUI theme,
 * stored in localStorage["wnTheme"]; its color scheme drives unfold's mode.
 * The CSS (daisy-themes.css) maps the active daisyUI theme onto unfold colors.
 *
 * This file is loaded synchronously in <head> (UNFOLD["SCRIPTS"]), so
 * data-theme is set before the first paint — no flash of the wrong theme.
 */
(function () {
    "use strict";

    var STORAGE_KEY = "wnTheme";
    var UNFOLD_KEY = "adminTheme"; // Alpine.$persist(...).as("adminTheme") in unfold app.js
    var html = document.documentElement;

    function read(key) {
        try {
            return localStorage.getItem(key);
        } catch (e) {
            return null;
        }
    }

    function write(key, value) {
        try {
            if (value === null) {
                localStorage.removeItem(key);
            } else {
                localStorage.setItem(key, value);
            }
        } catch (e) {
            // storage unavailable (private mode): theme just isn't remembered
        }
    }

    function customTheme() {
        return read(STORAGE_KEY) || "";
    }

    function isDarkMode() {
        if (html.classList.contains("dark")) {
            return true;
        }
        if (html.classList.contains("light")) {
            return false;
        }
        // Before Alpine has run (or in "auto"), fall back to unfold's stored mode.
        var mode = "auto";
        try {
            mode = JSON.parse(read(UNFOLD_KEY)) || "auto";
        } catch (e) {}
        return mode === "dark" || (mode === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    }

    function apply() {
        var theme = customTheme() || (isDarkMode() ? "dark" : "light");
        if (html.getAttribute("data-theme") !== theme) {
            html.setAttribute("data-theme", theme);
        }
    }

    // Charts resolve their CSS-variable colors once at render: redraw them by reloading
    function refreshCharts() {
        if (document.querySelector("canvas.chart")) {
            window.location.reload();
        }
    }

    function setUnfoldMode(mode) {
        var data = window.Alpine && window.Alpine.$data ? window.Alpine.$data(html) : null;
        if (data && "adminTheme" in data) {
            data.adminTheme = mode; // persisted by Alpine.$persist
        } else {
            write(UNFOLD_KEY, JSON.stringify(mode));
        }
    }

    window.WNTheme = {
        get: customTheme,
        // Use a daisyUI theme; `scheme` ("light" | "dark") drives unfold's mode.
        set: function (name, scheme) {
            write(STORAGE_KEY, name);
            setUnfoldMode(scheme === "dark" ? "dark" : "light");
            apply();
            refreshCharts();
        },
        // Back to plain unfold light / dark / auto.
        mode: function (mode) {
            var changed = customTheme() !== "";
            write(STORAGE_KEY, null);
            setUnfoldMode(mode);
            apply();
            if (changed) {
                refreshCharts();
            }
        },
    };

    // Alpine component used by unfold/helpers/theme_switch.html
    window.wnThemePicker = function () {
        return {
            wnTheme: customTheme(),
            showThemes: false,
            setMode: function (mode) {
                window.WNTheme.mode(mode);
                this.wnTheme = "";
            },
            setTheme: function (name, scheme) {
                window.WNTheme.set(name, scheme);
                this.wnTheme = name;
            },
        };
    };

    apply();
    // Keep data-theme in sync whenever unfold toggles the "dark" class.
    new MutationObserver(apply).observe(html, { attributes: true, attributeFilter: ["class"] });

    // Another tab changed the theme.
    window.addEventListener("storage", function (event) {
        if (event.key === STORAGE_KEY) {
            apply();
        }
    });
})();

var TOAST_CLASSES = {
    info: "ui-alert-info",
    danger: "ui-alert-error",
    success: "ui-alert-success",
    warning: "ui-alert-warning",
    error: "ui-alert-error",
};

function toast_(message, type = "info", title = "Notification") {
    const toastContainer = document.getElementById("toast-container");
    if (!toastContainer) {
        return;
    }

    const toastItem = document.createElement("div");
    toastItem.setAttribute("role", type === "error" ? "alert" : "status");
    toastItem.className = "ui-alert shadow-lg cursor-pointer max-w-sm " + (TOAST_CLASSES[type] || TOAST_CLASSES.info);
    toastItem.title = "Click to dismiss";

    const body = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "font-semibold";
    heading.textContent = title || "";
    const text = document.createElement("div");
    text.className = "text-sm";
    text.textContent = message || ""; // never innerHTML: content comes from the server/websocket
    body.append(heading, text);
    toastItem.appendChild(body);

    const remove = () => toastItem.remove();
    toastItem.addEventListener("click", remove);
    toastContainer.appendChild(toastItem);

    // Keep the toast while hovered, otherwise remove after 5 seconds.
    let timer = setTimeout(remove, 5000);
    toastItem.addEventListener("mouseenter", () => clearTimeout(timer));
    toastItem.addEventListener("mouseleave", () => {
        timer = setTimeout(remove, 2000);
    });
}

// WebSocket notifications — only on authenticated admin pages (they render #toast-container).
document.addEventListener("DOMContentLoaded", function () {
    if (!document.getElementById("toast-container") || !("WebSocket" in window)) {
        return;
    }

    const url = (window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host + "/ws/notifications/";
    let ws = null;
    let retries = 0;
    let closedByPage = false;

    const connect = function () {
        ws = new WebSocket(url);
        ws.onopen = function () {
            retries = 0;
        };
        ws.onmessage = function (event) {
            try {
                const data = JSON.parse(event.data);
                toast_(data.content, data.type, data.title);
            } catch (e) {
                // ignore malformed messages
            }
        };
        ws.onclose = function (event) {
            // 4xxx = rejected by the server (e.g. not authenticated): don't hammer it.
            if (closedByPage || (event.code >= 4000 && event.code < 5000) || retries >= 8) {
                return;
            }
            const delay = Math.min(30000, 1000 * 2 ** retries) + Math.random() * 1000;
            retries += 1;
            setTimeout(connect, delay);
        };
    };

    connect();

    // Close cleanly so the page stays eligible for the back/forward cache.
    window.addEventListener("pagehide", function () {
        closedByPage = true;
        if (ws) {
            ws.close();
        }
    });
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            closedByPage = false;
            retries = 0;
            connect();
        }
    });
});
