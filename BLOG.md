# Where's My Context? Building a Memory Passport for AI Chat Tools

*Built for WeMakeDevs' "The Hangover Part AI" hackathon, on Cognee.*

## The problem

Every AI chat tool I use forgets me the moment I close the tab. I'll spend twenty minutes explaining a project to ChatGPT, switch to Claude for a second opinion, and have to explain the whole thing again from scratch. Multiply that across however many AI tools you use in a week, and you're basically reintroducing yourself to a stranger every time — which is exactly the hackathon's theme: an AI that woke up with no memory of last night.

So I built **Memory Passport**: a browser extension that watches what you tell ChatGPT and Claude, remembers it in a shared Cognee knowledge graph, and lets you pull that context into whichever tool you're in right now. Talk to ChatGPT, open Claude, click a badge, and Claude already knows what you told ChatGPT five minutes ago.

## What it's made of

- A small FastAPI backend that wraps Cognee's memory API (`remember`, `recall`, `improve`, `forget`) and tracks what's been remembered.
- A cross-browser Manifest V3 extension (Chrome, Edge, Brave, Firefox, Safari) with content scripts that sit on chatgpt.com and claude.ai, capture what you type, and inject recalled context into your draft.

The pitch is simple. Getting there wasn't, and the interesting part of this project ended up being everything I learned about how Cognee Cloud actually behaves versus how the docs describe it.

## Surprise #1: the docs and the live API don't agree

The published Cognee Cloud docs say to authenticate with `Authorization: Bearer <key>`. The real API wants `X-Api-Key: <key>`. The docs don't mention an `/improve` endpoint existing at all in the live tenant API — what actually exists is `/api/v1/cognify`, which is the real graph-enrichment step. I only found this out by pulling the tenant's actual `/openapi.json` and diffing it against what the docs claimed. Lesson: when a hackathon sponsor gives you an SDK and docs, get a real API key on day one and hit the live OpenAPI spec directly — it's the only source of truth that updates as fast as the platform does.

## Surprise #2: a fresh account doesn't have a tenant

Sign up, generate an API key, and the dashboard says "Tenant ID: Not assigned — local mode." There's no hosted memory API until you provision a tenant yourself:

```bash
curl -X POST "https://api.aws.cognee.ai/api/v1/tenants?tenant_name=<name>" \
  -H "X-Api-Key: <key>"
curl "https://api.aws.cognee.ai/api/v1/tenants/current/service-url" \
  -H "X-Api-Key: <key>"
# => {"service_url": "https://tenant-<uuid>.aws.cognee.ai"}
```

That second URL is the actual host your backend talks to. None of this is obvious from the UI alone.

## Surprise #3: one dataset per fact quietly kills recall quality

My first instinct was to give every remembered fact its own Cognee dataset, so I could delete one fact later without nuking everything else. It worked — and recall got noticeably worse. Ask "what's my name and what language do I prefer" across two facts stored in two separate datasets, and you get two disconnected answers instead of one. `GRAPH_COMPLETION` needs a *connected* graph to reason over; a dataset with one fact in it has nothing to connect to.

The fix was a shared dataset for everything, with per-item deletion handled through the `data_id` that `remember()` returns rather than through dataset boundaries. Recall quality jumped immediately — three unrelated facts (a project, a language preference, a teammate's name) came back as one coherent synthesized answer instead of three fragments.

## Surprise #4: forget() doesn't fully forget (yet)

While testing deletion, I found something the docs definitely don't mention: deleting a fact by `data_id` and re-running `cognify` correctly removes it from the raw data list *and* from the graph endpoint — I checked both directly — but `recall()` could still surface the "deleted" fact afterward. Repeatedly. Across different query phrasings. The graph itself was clean; something downstream of it (almost certainly a vector index) wasn't being invalidated.

I tried the obvious nuclear option — delete the whole dataset and rebuild it from what's left — and that backfired worse: deleting and recreating a dataset with the same name raced the backend's own cleanup and left it permanently stuck in an error state. Had to abandon that dataset entirely.

I wrote up the repro steps and [filed it upstream](https://github.com/topoteretes/cognee/issues/3526) rather than just working around it silently, because a memory product where "forget" doesn't reliably forget is a real problem for anyone building on this, not just me.

## What I'd tell someone starting this hackathon today

1. Get a real API key and hit the live `/openapi.json` before writing any code against the published docs.
2. Don't fragment your data across datasets for the sake of easy deletion — Cognee's graph completion needs density to be any good. Use `data_id`-scoped operations instead.
3. Test deletion early and don't trust it blindly — verify against the raw data and graph endpoints directly, not just by eyeballing a recall response.
4. If you find something broken, write it up properly and file it. It's a five-minute investment that's worth more to the ecosystem (and to your own credibility) than quietly working around it.

Repo: [github.com/garimapahwa/memory-passport](https://github.com/garimapahwa/memory-passport)
