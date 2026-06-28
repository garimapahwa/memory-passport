async function sendToBackground(type, payload) {
  const response = await browser.runtime.sendMessage({ type, payload });
  if (!response) throw new Error("No response from background script");
  if (response.error) throw new Error(response.error);
  return response;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function render() {
  const container = document.getElementById("items");
  try {
    const { items } = await sendToBackground("passport", {});
    if (!items.length) {
      container.textContent = "Nothing remembered yet. Chat in ChatGPT or Claude to start.";
      return;
    }
    container.innerHTML = "";
    items
      .sort((a, b) => b.created_at - a.created_at)
      .forEach((item) => {
        const row = document.createElement("div");
        row.className = "item";
        row.innerHTML = `
          <div class="meta">${escapeHtml(item.source)} · ${escapeHtml(item.category)}</div>
          <div class="text">${escapeHtml(item.text)}</div>
          <button>Forget</button>
        `;
        row.querySelector("button").addEventListener("click", async (e) => {
          e.target.disabled = true;
          e.target.textContent = "Forgetting...";
          await sendToBackground("forget", { item_id: item.id });
          render();
        });
        container.appendChild(row);
      });
  } catch (err) {
    container.textContent = `Error: ${err.message}`;
  }
}

document.getElementById("improve").addEventListener("click", async (e) => {
  const status = document.getElementById("improveStatus");
  e.target.disabled = true;
  status.textContent = "Re-cognifying the graph...";
  try {
    await sendToBackground("improve", {});
    status.textContent = "✅ Memory strengthened.";
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  } finally {
    e.target.disabled = false;
    setTimeout(() => (status.textContent = ""), 3000);
  }
});

render();
