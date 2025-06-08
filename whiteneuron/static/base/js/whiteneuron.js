// Copyright (c) 2023-2024 WhiteNeuron

// Set the data-theme attribute on the HTML tag based on the adminTheme setting. It will make daisyui work with Alpine.js
document.addEventListener("DOMContentLoaded", function () {
    const htmlTag = document.documentElement;

    const desiredBind = `(adminTheme === 'dark' || (adminTheme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? 'dark' : 'light'`;

    if (!htmlTag.hasAttribute("x-bind:data-theme")) {
        htmlTag.setAttribute("x-bind:data-theme", desiredBind);
    }
});