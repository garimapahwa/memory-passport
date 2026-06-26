# Memory Passport

A portable context layer that follows you between AI chat tools, built on Cognee Cloud's `remember()` / `recall()` / `improve()` / `forget()` memory API.

Talk to ChatGPT, then open Claude — click the 🪪 badge and it recalls what Cognee knows about you from the *other* tool and injects it into the message before you send it. No more re-explaining yourself to every AI app.

## How it works

- **backend/** — a small FastAPI server that holds your Cognee Cloud API key and exposes `/api/remember`, `/api/recall`, `/api/improve`, `/api/forget`, `/api/passport`. Every remembered fact gets its own Cognee dataset (`passport_<category>_<id>`) so a single fact can be surgically `forget()`-ten without nuking everything else — tracked in `backend/ledger.json`.
- **extension/** — a cross-browser Manifest V3 extension (Chrome, Edge, Brave, Firefox, Safari) built on [webextension-polyfill](https://github.com/mozilla/webextension-polyfill) (vendored at `extension/browser-polyfill.min.js`), so all code uses the standard `browser.*` promise API instead of Chrome-only callbacks. Content scripts on chatgpt.com and claude.ai watch the composer: hitting Enter sends what you typed to `remember()`; clicking the 🪪 badge calls `recall()` and prepends the result into your draft. The popup lists everything stored and lets you forget individual items.

## Setup

1. **Cognee Cloud**:
   - Sign up at the Cognee Cloud console, create an API key from the **API Keys** page.
   - A fresh account has no tenant assigned (dashboard shows "Tenant ID: Not assigned — local mode"), and the actual memory API only exists per-tenant. Provision one:
     ```bash
     curl -X POST "https://api.aws.cognee.ai/api/v1/tenants?tenant_name=<any-name>" \
       -H "X-Api-Key: <your-api-key>"
     ```
   - Then fetch your tenant's real service URL (this is the host the backend actually talks to):
     ```bash
     curl "https://api.aws.cognee.ai/api/v1/tenants/current/service-url" \
       -H "X-Api-Key: <your-api-key>"
     # => {"service_url": "https://tenant-<uuid>.aws.cognee.ai", ...}
     ```
2. **Backend**:
   ```bash
   cd backend
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # fill in COGNEE_SERVICE_URL (the service_url above) and COGNEE_API_KEY
   uvicorn main:app --reload --port 8000
   ```
3. **Extension** — pick your browser:

   **Chrome / Edge / Brave**
   - `chrome://extensions` (or `edge://extensions`, `brave://extensions`) → enable Developer Mode → "Load unpacked" → select the `extension/` folder.

   **Firefox**
   - `about:debugging#/runtime/this-firefox` → "Load Temporary Add-on" → select `extension/manifest.json`.
   - Or via CLI: `npx web-ext run --source-dir extension/` (auto-reloads on file changes).
   - Note: Firefox doesn't yet support `background.service_worker`, so the manifest also declares `background.scripts`, which Firefox uses instead — same `background.js` file, no extra work needed.

   **Safari**
   - Requires full Xcode (not just Command Line Tools) since Safari extensions ship as native app bundles.
   - From the repo root: `xcrun safari-web-extension-converter extension/` — this generates an Xcode project wrapping the extension.
   - Open the generated project in Xcode, build and run once to register the extension with Safari.
   - In Safari: Settings → Advanced → enable "Show features for web developers", then Settings → Developer → enable "Allow Unsigned Extensions" (needed for local/unsigned builds). Then Settings → Extensions → enable "Memory Passport".
   - Safari sandboxes extensions more strictly around network requests; if `fetch` to `localhost:8000` is blocked, run the backend on `127.0.0.1` instead of `localhost`, or check Safari's extension permissions for the page.

   Backend URL defaults to `http://localhost:8000` everywhere — change it on the extension's options page if needed. If you point it at a non-localhost backend, also add that origin to `host_permissions` in `manifest.json` and reload the extension.

## Before you demo

Chat site DOM selectors drift. `extension/content/chatgpt.js` and `extension/content/claude.js` each have a `findComposer()` with a fallback chain — open DevTools on the live site beforehand and confirm the badge can find the input box; tweak the selector if not.

## Demo script

1. Open ChatGPT, type a few personal facts/preferences ("I'm building a hackathon project with Cognee", "I prefer Python over JS") and send them — each gets remembered.
2. Open Claude, start typing a new message, click the 🪪 badge — watch it inject recalled context from the ChatGPT conversation before you've said anything to Claude.
3. Open the extension popup to show the passport: every fact, tagged by source tool, with a one-click Forget per item.
4. Optionally hit `/api/improve` (e.g. via `curl -X POST localhost:8000/api/improve`) between demo beats to show the graph reconciling/strengthening over time.

## Notes / known gaps

- `remember` → `recall` → `forget` has been live-tested end-to-end against a real tenant (not just docs): remembered "the user's name is Pahwa and they prefer Python", recalled it back correctly via `GRAPH_COMPLETION`, then forgot it. Request shapes in `cognee_client.py` are taken from the tenant's actual `/openapi.json`, not the published docs (which were wrong on a few points — auth header is `X-Api-Key`, not `Bearer`; there's no literal `/improve` endpoint, `/api/v1/cognify` is the real enrichment step and is what `improve()` calls).
- `remember()` blocks until the graph is fully built (~20-25s for a short text in testing) since `run_in_background` defaults to false. Fine for a demo with natural pauses between actions; if facts need to feel instant, pass `run_in_background=true` and accept that `recall()` right after may not see it yet.
- CORS is wide open (`allow_origins=["*"]`) for local demo convenience — tighten before deploying anywhere real.
- The conversation capture currently fires on every Enter keypress in the composer; for a noisier chat it's worth debouncing or filtering trivial messages.
- Cross-browser support has only been validated by static syntax/manifest checks in this environment (no full Xcode here to actually run the Safari converter, no Firefox/Safari install to click-test against). Load it in each target browser before relying on it for a live demo.
- `document.execCommand` (used to inject text into contenteditable composers) is deprecated but still broadly supported across Chrome/Firefox/Safari; if a target site's composer rejects it, the fallback is to directly mutate `textContent`/`innerText` and dispatch an `input` event instead.
