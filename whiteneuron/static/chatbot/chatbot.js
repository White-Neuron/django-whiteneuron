/* AI assistant panel (whiteneuron.chatbot). Replies arrive as server-sanitized HTML;
   everything the user typed is inserted as text. */
(function () {
    const panel = document.getElementById("wn-chatbot-panel");
    const toggle = document.getElementById("wn-chatbot-toggle");
    if (!panel || !toggle) return;

    const backdrop = document.querySelector(".wn-chatbot-backdrop");
    const messages = panel.querySelector(".wn-chatbot-messages");
    const greeting = panel.querySelector("template[data-chatbot-greeting]");
    const form = panel.querySelector("form");
    const input = form.querySelector("textarea");
    const submit = form.querySelector("button[type=submit]");
    let history = [];  // [{role, content}] sent back so the model keeps the context
    let busy = false;

    function setOpen(open) {
        panel.hidden = backdrop.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        if (open) input.focus(); else toggle.focus();
    }
    function reset() {
        history = [];
        messages.replaceChildren(greeting, greeting.content.cloneNode(true));
    }
    function updateInput() {
        input.style.height = "auto";
        input.style.height = Math.min(input.scrollHeight, 160) + "px";
        submit.disabled = busy || !input.value.trim();
    }

    function icon(name) {
        const span = document.createElement("span");
        span.className = "material-symbols-outlined";
        span.setAttribute("aria-hidden", "true");
        span.textContent = name;
        return span;
    }
    function addRow(kind) {
        const row = document.createElement("div");
        row.className = "wn-chatbot-row wn-chatbot-row-" + (kind === "user" ? "user" : "bot");
        if (kind !== "user") {
            const avatar = document.createElement("span");
            avatar.className = "wn-chatbot-avatar";
            avatar.append(icon("smart_toy"));
            row.append(avatar);
        }
        const bubble = document.createElement("div");
        bubble.className = "wn-chatbot-msg wn-chatbot-msg-" + kind;
        row.append(bubble);
        messages.append(row);
        messages.scrollTop = messages.scrollHeight;
        return { row, bubble };
    }
    function addError(text) {
        const { bubble } = addRow("error");
        bubble.append(icon("error"), document.createTextNode(text));
    }

    async function send(message) {
        addRow("user").bubble.textContent = message;
        const pending = addRow("bot");
        pending.bubble.classList.add("wn-chatbot-typing");
        pending.bubble.setAttribute("aria-label", panel.dataset.thinking);
        pending.bubble.innerHTML = "<span></span><span></span><span></span>";
        busy = true;
        updateInput();
        try {
            const response = await fetch(panel.dataset.url, {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", "X-CSRFToken": panel.dataset.csrf },
                body: JSON.stringify({ message, history: history.slice(-10) }),
            });
            const data = await response.json().catch(() => ({}));
            pending.row.remove();
            if (response.ok) {
                addRow("bot").bubble.innerHTML = data.html;  // sanitized by chatbot.utils.render_reply
                history.push({ role: "user", content: message }, { role: "assistant", content: data.markdown });
            } else {
                addError(data.error || panel.dataset.connectionError);
            }
        } catch (err) {
            pending.row.remove();
            addError(panel.dataset.connectionError);
        } finally {
            busy = false;
            updateInput();
            input.focus();
        }
    }

    toggle.addEventListener("click", () => setOpen(panel.hidden));
    document.querySelectorAll("[data-chatbot-close]").forEach((el) => el.addEventListener("click", () => setOpen(false)));
    panel.querySelector("[data-chatbot-reset]").addEventListener("click", () => { reset(); input.focus(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) setOpen(false); });
    input.addEventListener("input", updateInput);
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message || busy) return;
        input.value = "";
        updateInput();
        send(message);
    });
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {  // isComposing: Vietnamese IME
            e.preventDefault();
            form.requestSubmit();
        }
    });
    reset();
})();
