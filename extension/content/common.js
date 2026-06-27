async function sendToBackground(type, payload) {
  const response = await browser.runtime.sendMessage({ type, payload });
  if (!response) throw new Error("No response from background script");
  if (response.error) throw new Error(response.error);
  return response;
}

function createPassportBadge(toolLabel) {
  const badge = document.createElement("div");
  badge.id = "memory-passport-badge";
  badge.textContent = `🪪 Passport: ${toolLabel}`;
  badge.title = "Click to recall your context and inject it into this chat";
  Object.assign(badge.style, {
    position: "fixed",
    bottom: "16px",
    right: "16px",
    zIndex: "999999",
    padding: "8px 12px",
    borderRadius: "8px",
    background: "#111",
    color: "#fff",
    fontFamily: "sans-serif",
    fontSize: "12px",
    cursor: "pointer",
    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
  });
  document.body.appendChild(badge);
  return badge;
}

// Briefly shows a status on the badge, then reverts to the idle label.
// Clears any pending revert first so rapid actions (e.g. fast typing +
// Enter) don't fight over the badge text.
function flashBadge(badge, text, idleText, durationMs = 2000) {
  clearTimeout(badge._passportRevertTimer);
  badge.textContent = text;
  badge._passportRevertTimer = setTimeout(() => {
    badge.textContent = idleText;
  }, durationMs);
}

function getElementText(el) {
  if (!el) return "";
  return el.tagName === "TEXTAREA" ? el.value : el.innerText;
}

function setElementText(el, text) {
  if (!el) return;
  if (el.tagName === "TEXTAREA") {
    el.value = text;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    el.focus();
    document.execCommand("selectAll", false, null);
    document.execCommand("insertText", false, text);
  }
}

// Shared engine: each site's content script just supplies a composer finder.
function initMemoryPassport({ toolLabel, source, findComposer }) {
  const badge = createPassportBadge(toolLabel);

  badge.addEventListener("click", async () => {
    const composer = findComposer();
    if (!composer) {
      console.warn("Memory Passport: couldn't find the chat composer on this page");
      return;
    }
    const idleText = `🪪 Passport: ${toolLabel}`;
    const draft = getElementText(composer).trim();
    badge.textContent = "🪪 Recalling...";
    try {
      const { cognee } = await sendToBackground("recall", {
        query: draft || "Summarize everything you know about this user from past conversations: their projects, preferences, and any people they've mentioned.",
      });
      // cognee.recall returns a plain array of result entries, each with a `text` field.
      const hits = Array.isArray(cognee) ? cognee.filter((r) => r.text) : [];
      const context = hits.length ? hits.map((r) => r.text).join("\n") : "(no memories stored yet)";
      setElementText(composer, `[Memory Passport context: ${context}]\n\n${draft}`);
      flashBadge(badge, hits.length ? `✅ Injected ${hits.length} memor${hits.length === 1 ? "y" : "ies"}` : "🪪 Nothing remembered yet", idleText);
    } catch (err) {
      console.error("Memory Passport recall failed", err);
      flashBadge(badge, "⚠️ Recall failed (see console)", idleText, 3000);
    }
  });

  // Capture what the user sends so the next tool can recall it later.
  document.addEventListener(
    "keydown",
    (e) => {
      if (e.key !== "Enter" || e.shiftKey) return;
      const composer = findComposer();
      const text = getElementText(composer).trim();
      if (!text) return;
      const idleText = `🪪 Passport: ${toolLabel}`;
      flashBadge(badge, "🪪 Remembering...", idleText, 15000);
      sendToBackground("remember", { text, source, category: "conversation" })
        .then(() => flashBadge(badge, "✅ Remembered", idleText))
        .catch((err) => {
          console.error("Memory Passport remember failed", err);
          flashBadge(badge, "⚠️ Remember failed (see console)", idleText, 3000);
        });
    },
    true
  );
}
