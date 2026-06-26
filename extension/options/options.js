const input = document.getElementById("backendUrl");
const status = document.getElementById("status");

(async () => {
  const { backendUrl } = await browser.storage.sync.get("backendUrl");
  input.value = backendUrl || "http://localhost:8000";
})();

document.getElementById("save").addEventListener("click", async () => {
  await browser.storage.sync.set({ backendUrl: input.value.trim() });
  status.textContent = "Saved.";
  setTimeout(() => (status.textContent = ""), 1500);
});
