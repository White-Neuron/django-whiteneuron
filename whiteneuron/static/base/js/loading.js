document.addEventListener('DOMContentLoaded', function () {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (!loadingOverlay) {
        return;
    }

    const REQUEST_TOKEN_COOKIE = 'wn_loading_token';
    const RESPONSE_DONE_COOKIE = 'wn_loading_done';
    let downloadPollTimer = null;

    const hideOverlay = function () {
        loadingOverlay.style.display = 'none';
    };

    const showOverlay = function () {
        loadingOverlay.style.display = 'flex';
    };

    const setCookie = function (name, value, maxAgeSeconds) {
        document.cookie = name + '=' + encodeURIComponent(value) + '; path=/; max-age=' + String(maxAgeSeconds) + '; samesite=lax';
    };

    const getCookie = function (name) {
        const cookiePrefix = name + '=';
        const cookies = document.cookie ? document.cookie.split(';') : [];

        for (let i = 0; i < cookies.length; i += 1) {
            const item = cookies[i].trim();
            if (item.startsWith(cookiePrefix)) {
                return decodeURIComponent(item.slice(cookiePrefix.length));
            }
        }

        return null;
    };

    const clearCookie = function (name) {
        document.cookie = name + '=; path=/; max-age=0; samesite=lax';
    };

    const stopDownloadPolling = function () {
        if (downloadPollTimer) {
            window.clearInterval(downloadPollTimer);
            downloadPollTimer = null;
        }
    };

    const startDownloadPolling = function (requestToken) {
        stopDownloadPolling();

        downloadPollTimer = window.setInterval(function () {
            const doneToken = getCookie(RESPONSE_DONE_COOKIE);
            if (doneToken !== requestToken) {
                return;
            }

            stopDownloadPolling();
            hideOverlay();
            clearCookie(RESPONSE_DONE_COOKIE);
            clearCookie(REQUEST_TOKEN_COOKIE);
        }, 300);
    };

    const newRequestToken = function () {
        return (Date.now().toString(36) + Math.random().toString(36).slice(2)).slice(0, 64);
    };

    const beginLoadingHandshake = function () {
        const requestToken = newRequestToken();
        clearCookie(RESPONSE_DONE_COOKIE);
        setCookie(REQUEST_TOKEN_COOKIE, requestToken, 120);
        showOverlay();
        startDownloadPolling(requestToken);
    };

    const isSamePageAnchor = function (anchorUrl) {
        return (
            anchorUrl.origin === window.location.origin &&
            anchorUrl.pathname === window.location.pathname &&
            anchorUrl.search === window.location.search
        );
    };

    hideOverlay();

    // Hiện loading ngay khi bấm link nội bộ điều hướng cùng tab.
    document.addEventListener('click', function (event) {
        const rawTarget = event.target;
        const target = rawTarget instanceof Element ? rawTarget : rawTarget && rawTarget.parentElement;
        if (!target) {
            return;
        }

        const anchor = target.closest('a[href]');
        if (!anchor || !(anchor instanceof HTMLAnchorElement)) {
            return;
        }

        if (event.defaultPrevented || event.button !== 0) {
            return;
        }

        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }

        if (anchor.target && anchor.target !== '_self') {
            return;
        }

        if (anchor.hasAttribute('download')) {
            return;
        }

        const href = anchor.getAttribute('href') || '';
        if (!href || href.startsWith('#') || href.startsWith('javascript:')) {
            return;
        }

        if (href.startsWith('mailto:') || href.startsWith('tel:')) {
            return;
        }

        const anchorUrl = new URL(anchor.href, window.location.href);
        if (isSamePageAnchor(anchorUrl)) {
            return;
        }

        beginLoadingHandshake();
    });

    // Show loading cho submit form; nếu response là file download thì middleware sẽ trả cookie để tự tắt.
    document.addEventListener('submit', function (event) {
        if (event.defaultPrevented) {
            return;
        }

        const form = event.target;
        if (!(form instanceof HTMLFormElement)) {
            return;
        }

        if (form.target && form.target !== '_self') {
            return;
        }

        beginLoadingHandshake();
    });

    // Đảm bảo overlay luôn tắt khi trang vẫn hiện hoặc được khôi phục từ cache.
    window.addEventListener('pageshow', function () {
        stopDownloadPolling();
        clearCookie(REQUEST_TOKEN_COOKIE);
        clearCookie(RESPONSE_DONE_COOKIE);
        hideOverlay();
    });
    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') {
            hideOverlay();
        }
    });

    window.addEventListener('focus', function () {
        if (!downloadPollTimer) {
            hideOverlay();
        }
    });
    window.addEventListener('pagehide', stopDownloadPolling);
});
