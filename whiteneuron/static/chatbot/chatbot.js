/* AI assistant panel (whiteneuron.chatbot). Replies arrive as server-sanitized HTML;
   everything the user typed is inserted as text.

   The conversation is kept per browser tab (sessionStorage) so it survives moving between
   admin pages; the key includes the user id so a different login in the same tab starts fresh. */
(function () {
    const panel = document.getElementById("wn-chatbot-panel");
    const toggle = document.getElementById("wn-chatbot-toggle");
    if (!panel || !toggle) return;

    const backdrop = document.querySelector(".wn-chatbot-backdrop");
    // The markup sits in the header, whose stacking context would keep the panel under
    // page elements such as the changelist footer: move it to <body>.
    document.body.append(backdrop, panel);
    const messages = panel.querySelector(".wn-chatbot-messages");
    const greeting = panel.querySelector("template[data-chatbot-greeting]");
    const form = panel.querySelector("form");
    const input = form.querySelector("textarea");
    const submit = form.querySelector("button[type=submit]");
    const text = panel.dataset;
    const storageKey = "wn-chatbot:" + text.user;
    const touch = window.matchMedia("(pointer: coarse)").matches;
    const TIMEOUT_MS = 90000;

    // entries: {kind: "user"|"bot"|"error", text?, html?, markdown?, retry?}
    let state = load() || { open: false, entries: [] };
    let pending = null;  // {controller, row}; a reply that arrives after a reset is dropped

    function load() {
        try { return JSON.parse(sessionStorage.getItem(storageKey)); } catch (e) { return null; }
    }
    function save() {
        try { sessionStorage.setItem(storageKey, JSON.stringify(state)); } catch (e) { /* private mode, quota */ }
    }
    function history() {  // [{role, content}] sent back so the model keeps the context
        return state.entries
            .filter((e) => e.kind === "user" || (e.kind === "bot" && e.markdown !== undefined))
            .map((e) => ({ role: e.kind === "user" ? "user" : "assistant", content: e.kind === "user" ? e.text : e.markdown }))
            .slice(-10);
    }

    /* ---------- rendering ---------- */
    function icon(name) {
        const span = document.createElement("span");
        span.className = "material-symbols-outlined";
        span.setAttribute("aria-hidden", "true");
        span.textContent = name;
        return span;
    }
    function smallButton(iconName, label, onClick) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "wn-chatbot-action";
        button.append(icon(iconName), document.createTextNode(label));
        button.addEventListener("click", onClick);
        return button;
    }
    function renderEntry(entry) {
        const row = document.createElement("div");
        row.className = "wn-chatbot-row wn-chatbot-row-" + (entry.kind === "user" ? "user" : "bot");
        if (entry.kind !== "user") {
            const avatar = document.createElement("span");
            avatar.className = "wn-chatbot-avatar";
            avatar.append(icon("smart_toy"));
            row.append(avatar);
        }
        const column = document.createElement("div");
        column.className = "wn-chatbot-col";
        const bubble = document.createElement("div");
        bubble.className = "wn-chatbot-msg wn-chatbot-msg-" + entry.kind;
        if (entry.kind === "bot") {
            bubble.innerHTML = entry.html;  // sanitized by chatbot.utils.render_reply
            const copy = smallButton("content_copy", text.copy, async () => {
                try {
                    await navigator.clipboard.writeText(entry.markdown);
                    copy.lastChild.textContent = text.copied;
                } catch (e) { copy.lastChild.textContent = text.copyFailed; }
                setTimeout(() => { copy.lastChild.textContent = text.copy; }, 1500);
            });
            const actions = document.createElement("div");
            actions.className = "wn-chatbot-actions";
            actions.append(copy);
            column.append(bubble, actions);
        } else if (entry.kind === "error") {
            bubble.append(icon("error"), document.createTextNode(entry.text));
            column.append(bubble);
            if (entry.retry) {
                const actions = document.createElement("div");
                actions.className = "wn-chatbot-actions";
                actions.append(smallButton("refresh", text.retry, () => retry(entry)));
                column.append(actions);
            }
        } else {
            bubble.textContent = entry.text;
            column.append(bubble);
        }
        row.append(column);
        messages.append(row);
        return row;
    }
    function renderAll() {
        messages.replaceChildren(greeting, greeting.content.cloneNode(true));
        state.entries.forEach(renderEntry);
        messages.scrollTop = messages.scrollHeight;
    }
    function reveal(row) {
        // show a new reply from its first line; the user scrolls on for the rest
        const top = row.offsetTop - messages.offsetTop - 12;
        messages.scrollTop = Math.min(top, messages.scrollHeight);
    }
    function showTyping() {
        const row = document.createElement("div");
        row.className = "wn-chatbot-row wn-chatbot-row-bot";
        row.innerHTML = '<span class="wn-chatbot-avatar"></span><div class="wn-chatbot-msg wn-chatbot-msg-bot wn-chatbot-typing"><span></span><span></span><span></span></div>';
        row.firstChild.append(icon("smart_toy"));
        row.lastChild.setAttribute("role", "status");
        row.lastChild.setAttribute("aria-label", text.thinking);
        messages.append(row);
        messages.scrollTop = messages.scrollHeight;
        return row;
    }
    function updateInput() {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 160) + "px";
        submit.disabled = !!pending || !input.value.trim();
    }

    /* ---------- open / close ---------- */
    function setOpen(open, { focus = true } = {}) {
        panel.hidden = backdrop.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        document.documentElement.classList.toggle("wn-chatbot-lock", open);  // no page scroll behind it
        state.open = open;
        save();
        if (!focus) return;
        if (open) input.focus(); else toggle.focus();
    }
    function trapFocus(e) {
        if (e.key !== "Tab") return;
        const items = [...panel.querySelectorAll("button:not(:disabled), textarea, a[href]")].filter((el) => el.offsetParent);
        if (!items.length) return;
        const first = items[0], last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }

    /* ---------- sending ---------- */
    async function send(message, { echo = true } = {}) {
        if (echo) {
            const entry = { kind: "user", text: message };
            state.entries.push(entry);
            save();
            renderEntry(entry);
        }
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
        const current = { controller, row: showTyping() };
        pending = current;
        updateInput();
        let entry;
        try {
            const response = await fetch(text.url, {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", "X-CSRFToken": text.csrf },
                // history() already ends with this message; the server appends it itself
                body: JSON.stringify({ message, history: history().slice(0, -1) }),
                signal: controller.signal,
            });
            const data = await response.json().catch(() => ({}));
            entry = response.ok
                ? { kind: "bot", html: data.html, markdown: data.markdown }
                : { kind: "error", text: data.error || text.connectionError, retry: response.status !== 400 && response.status !== 403 };
        } catch (err) {
            entry = { kind: "error", text: err.name === "AbortError" && pending === current ? text.timeout : text.connectionError, retry: true };
        } finally {
            clearTimeout(timer);
        }
        if (pending !== current) return;  // conversation was reset meanwhile
        pending = null;
        current.row.remove();
        state.entries.push(entry);
        save();
        reveal(renderEntry(entry));
        updateInput();
        if (!touch) input.focus();
    }
    function retry(errorEntry) {
        if (pending) return;
        const lastUser = [...state.entries].reverse().find((e) => e.kind === "user");
        state.entries.splice(state.entries.indexOf(errorEntry), 1);
        save();
        renderAll();
        if (lastUser) send(lastUser.text, { echo: false });
    }
    function reset() {
        if (pending) { pending.controller.abort(); pending = null; }
        state.entries = [];
        save();
        renderAll();
        updateInput();
        input.focus();
    }

    /* ---------- events ---------- */
    toggle.addEventListener("click", () => setOpen(panel.hidden));
    document.querySelectorAll("[data-chatbot-close]").forEach((el) => el.addEventListener("click", () => setOpen(false)));
    panel.querySelector("[data-chatbot-reset]").addEventListener("click", reset);
    panel.addEventListener("keydown", trapFocus);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) setOpen(false); });
    input.addEventListener("input", updateInput);
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message || pending) return;
        input.value = "";
        updateInput();
        send(message);
    });
    input.addEventListener("keydown", (e) => {
        // phones: Enter is a new line, the send button sends. isComposing: Vietnamese IME
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing && !touch) {
            e.preventDefault();
            form.requestSubmit();
        }
    });

    renderAll();
    if (state.open) setOpen(true, { focus: false });
})();
