# Memory Passport

*Your AI woke up with no memory of last night. This gives it one.*

Built for WeMakeDevs' **"The Hangover Part AI: Where's My Context?"** hackathon, on [Cognee](https://www.cognee.ai/)'s hybrid graph-vector memory layer.

Every AI chat tool forgets you the second you close the tab. Explain your project to ChatGPT, switch to Claude for a second opinion, and you're re-introducing yourself from scratch — every single time. Memory Passport is a portable context layer that follows you between AI tools, built on Cognee's `remember()` / `recall()` / `improve()` / `forget()` memory API.

Talk to ChatGPT, then open Claude — click the 🪪 badge and it recalls what Cognee knows about you from the *other* tool and injects it into the message before you send it. No more re-explaining yourself to every AI app.

**See [BLOG.md](BLOG.md) for the build story** — including the undocumented auth header, the tenant-provisioning gotcha, the architecture mistake that quietly wrecked recall quality, and a real platform bug we found and [filed upstream](https://github.com/topoteretes/cognee/issues/3526).

<!--
TODO before submitting: drop a screenshot or short GIF here showing the
🪪 badge live on chatgpt.com/claude.ai with a real recall in action.
Needs an authenticated browser session, so this has to be captured by
hand rather than generated -- e.g. `![demo](docs/demo.gif)`.
-->

## How it works

- **backend/** — a small FastAPI server that holds your Cognee Cloud API key and exposes `/api/remember`, `/api/recall`, `/api/improve`, `/api/forget`, `/api/passport`. Every remembered fact goes into one shared dataset (`passport_v2`) so cognify can build real relationships across everything you've told it — a separate dataset per fact was tried first and made recall noticeably worse, since each dataset was its own tiny disconnected graph with nothing to connect a name in one fact to a preference in another. Per-item deletion still works on the shared dataset: `remember()`'s returned `data_id` lets `forget()` target one fact without wiping the rest — tracked in `backend/ledger.json`.
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
   - Firefox doesn't support `background.service_worker`, and Chrome warns on `background.scripts` under Manifest V3 — so there are two manifest files: `manifest.json` (Chrome/Edge/Brave/Safari) and `manifest.firefox.json` (Firefox). Everything else (`background.js`, content scripts, polyfill) is shared.
   - Easiest: copy the whole `extension/` folder, then in the copy run `mv manifest.json manifest.chrome.json.bak && mv manifest.firefox.json manifest.json`. Load that copy via `about:debugging#/runtime/this-firefox` → "Load Temporary Add-on" → select its `manifest.json`.
   - Or via CLI on that same copy: `npx web-ext run --source-dir <copy-dir>/`.

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

1. Open ChatGPT, type a few distinct personal facts ("I'm building a hackathon project called Memory Passport with Cognee", "I prefer Python over JS", "My teammate is named Garima") and send them one at a time — each gets remembered into the shared graph.
2. Open Claude, start typing a new message, click the 🪪 badge — watch it inject one coherent answer pulling together *all* of those facts (not just the last one), proving it's a connected graph and not isolated lookups.
3. Open the extension popup to show the passport: every fact, tagged by source tool, with a one-click Forget per item.
4. **Skip demoing forget→recall as an instant before/after** — per the known gap below, recall can keep surfacing a forgotten fact for a while even though the underlying record and graph node are already gone. If you want to show forget working, show it via the popup list (the item disappears) or via `curl http://localhost:8000/api/passport`, not via an immediate recall query.
5. Optionally hit `/api/improve` (`curl -X POST localhost:8000/api/improve`) between demo beats to show the graph reconciling explicitly.

## Notes / known gaps

- `remember` → `recall` → `forget` has been live-tested end-to-end against a real tenant (not just docs): remembered three distinct facts (a project, a language preference, a teammate's name) into the shared dataset and got back one coherent answer combining all three via `GRAPH_COMPLETION`. Request shapes in `cognee_client.py` are taken from the tenant's actual `/openapi.json`, not the published docs (which were wrong on a few points — auth header is `X-Api-Key`, not `Bearer`; there's no literal `/improve` endpoint, `/api/v1/cognify` is the real enrichment step and is what `improve()` calls).
- **`forget()` has a confirmed staleness gap on the live API**: deleting a fact's `data_id` reliably removes it from the raw data list (`GET /datasets/{id}/data`) and from the graph endpoint (`GET /datasets/{id}/graph`) immediately — verified directly. But `recall()` could still surface the forgotten fact afterward, even after an explicit re-`cognify`, in repeated testing. This looks like a stale vector/search index that isn't invalidated by `forget`+`cognify` on Cognee Cloud's current backend, not a bug in this code — filed upstream as [topoteretes/cognee#3526](https://github.com/topoteretes/cognee/issues/3526) with full repro steps. Don't rely on "forget, then immediately recall" as a live demo beat — it may visibly fail. A full dataset delete-and-rebuild was tried as a workaround and is *not* recommended: rapidly deleting and recreating a dataset with the same name hit a server-side `ProgrammingError` and left that dataset permanently stuck in an errored processing state (had to abandon `passport_main` for `passport_v2` to recover) — same-named recreation right after deletion looks like it races the backend's own cleanup.
- `remember()` blocks until the graph is fully built (~20-25s for a short text in testing) since `run_in_background` defaults to false. Fine for a demo with natural pauses between actions; if facts need to feel instant, pass `run_in_background=true` and accept that `recall()` right after may not see it yet.
- CORS is wide open (`allow_origins=["*"]`) for local demo convenience — tighten before deploying anywhere real.
- The conversation capture currently fires on every Enter keypress in the composer; for a noisier chat it's worth debouncing or filtering trivial messages.
- Cross-browser support has only been validated by static syntax/manifest checks in this environment (no full Xcode here to actually run the Safari converter, no Firefox/Safari install to click-test against). Load it in each target browser before relying on it for a live demo.
- `document.execCommand` (used to inject text into contenteditable composers) is deprecated but still broadly supported across Chrome/Firefox/Safari; if a target site's composer rejects it, the fallback is to directly mutate `textContent`/`innerText` and dispatch an `input` event instead.
