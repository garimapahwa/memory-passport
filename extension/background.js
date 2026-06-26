// Chrome/Safari run this as a true service worker (importScripts works,
// no native `browser`). Firefox loads it as a plain background script via
// manifest's "scripts" array, where the polyfill is already loaded and
// `browser` already exists -- importScripts would throw there, so skip it.
if (typeof importScripts === "function" && typeof browser === "undefined") {
  importScripts("browser-polyfill.min.js");
}

const DEFAULT_BACKEND_URL = "http://localhost:8000";

const ROUTES = {
  remember: { path: "/api/remember", method: "POST" },
  recall: { path: "/api/recall", method: "POST" },
  improve: { path: "/api/improve", method: "POST" },
  forget: { path: "/api/forget", method: "POST" },
  passport: { path: "/api/passport", method: "GET" },
};

async function getBackendUrl() {
  const { backendUrl } = await browser.storage.sync.get("backendUrl");
  return backendUrl || DEFAULT_BACKEND_URL;
}

async function handleMessage(message) {
  const route = ROUTES[message.type];
  if (!route) throw new Error(`Unknown message type: ${message.type}`);

  const backendUrl = await getBackendUrl();
  const resp = await fetch(`${backendUrl}${route.path}`, {
    method: route.method,
    headers: { "Content-Type": "application/json" },
    body: route.method === "GET" ? undefined : JSON.stringify(message.payload || {}),
  });

  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new Error(`Backend ${resp.status}: ${body}`);
  }
  return resp.json();
}

browser.runtime.onMessage.addListener((message) => handleMessage(message));
