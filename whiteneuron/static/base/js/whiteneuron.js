document.addEventListener("DOMContentLoaded", function () {
    const htmlTag = document.documentElement;

    const desiredBind = `(adminTheme === 'dark' || (adminTheme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) ? 'dark' : 'light'`;

    if (!htmlTag.hasAttribute("x-bind:data-theme")) {
        htmlTag.setAttribute("x-bind:data-theme", desiredBind);
    }
});