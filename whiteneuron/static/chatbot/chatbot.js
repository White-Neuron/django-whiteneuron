/* AI assistant panel (whiteneuron.chatbot). Replies arrive as server-sanitized HTML;
   everything the user typed is inserted as text. */
(function () {
    const panel = document.getElementById("wn-chatbot-panel");
    const toggle = document.getElementById("wn-chatbot-toggle");
    if (!panel || !toggle) return;

    const messages = panel.querySelector(".wn-chatbot-messages");
    const form = panel.querySelector("form");
    const input = form.querySelector("textarea");
    const submit = form.querySelector("button[type=submit]");
    const history = [];  // [{role, content}] sent back so the model keeps the context

    function setOpen(open) {
        panel.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        if (open) input.focus();
    }
    toggle.addEventListener("click", () => setOpen(panel.hidden));
    panel.querySelector("[data-chatbot-close]").addEventListener("click", () => setOpen(false));
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) setOpen(false); });

    function addMessage(kind, { text, html }) {
        const div = document.createElement("div");
        div.className = "wn-chatbot-msg wn-chatbot-msg-" + kind;
        if (html !== undefined) div.innerHTML = html; else div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        return div;
    }

    async function send(message) {
        addMessage("user", { text: message });
        const pending = addMessage("bot", { text: panel.dataset.thinking });
        pending.classList.add("wn-chatbot-msg-pending");
        submit.disabled = true;
        try {
            const response = await fetch(panel.dataset.url, {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", "X-CSRFToken": panel.dataset.csrf },
                body: JSON.stringify({ message, history: history.slice(-10) }),
            });
            const data = await response.json().catch(() => ({}));
            pending.remove();
            if (response.ok) {
                addMessage("bot", { html: data.html });
                history.push({ role: "user", content: message }, { role: "assistant", content: data.markdown });
            } else {
                addMessage("error", { text: data.error || panel.dataset.connectionError });
            }
        } catch (err) {
            pending.remove();
            addMessage("error", { text: panel.dataset.connectionError });
        } finally {
            submit.disabled = false;
            input.focus();
        }
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message || submit.disabled) return;
        input.value = "";
        send(message);
    });
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {  // isComposing: Vietnamese IME
            e.preventDefault();
            form.requestSubmit();
        }
    });
})();
