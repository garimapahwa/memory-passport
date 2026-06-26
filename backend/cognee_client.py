"""Thin wrapper around the live Cognee tenant API.

Verified against the real OpenAPI spec served at
<tenant-service-url>/openapi.json and a live round-trip
(remember -> recall -> forget) on 2026-06-24. Notes vs. the published docs:
- Auth is `X-Api-Key: <key>`, not `Authorization: Bearer`.
- `remember`'s multipart form fields are snake_case (datasetName is the one
  exception); recall/forget/cognify JSON bodies are camelCase.
- There is no literal `/improve` endpoint. `/api/v1/cognify` is the real
  enrichment step (it's what builds/rebuilds the knowledge graph for a
  dataset), so `improve()` below calls that.
"""
import os

import httpx

COGNEE_SERVICE_URL = os.environ.get("COGNEE_SERVICE_URL", "").rstrip("/")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")


def _client() -> httpx.AsyncClient:
    if not COGNEE_SERVICE_URL or not COGNEE_API_KEY:
        raise RuntimeError("COGNEE_SERVICE_URL / COGNEE_API_KEY not set (check backend/.env)")
    return httpx.AsyncClient(
        base_url=COGNEE_SERVICE_URL,
        headers={"X-Api-Key": COGNEE_API_KEY},
        timeout=60,
    )


async def remember(text: str, dataset_name: str) -> dict:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/remember",
            data={"datasetName": dataset_name},
            files={"data": ("memory.txt", text.encode("utf-8"), "text/plain")},
        )
        resp.raise_for_status()
        return resp.json()


async def recall(query: str, datasets: list[str], search_type: str = "GRAPH_COMPLETION", top_k: int = 10) -> list[dict]:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/recall",
            json={"query": query, "datasets": datasets, "searchType": search_type, "topK": top_k},
        )
        resp.raise_for_status()
        return resp.json()


async def improve(dataset_name: str, run_in_background: bool = False) -> dict:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/cognify",
            json={"datasets": [dataset_name], "runInBackground": run_in_background},
        )
        resp.raise_for_status()
        return resp.json()


async def forget(dataset: str, memory_only: bool = True) -> dict:
    async with _client() as client:
        resp = await client.post(
            "/api/v1/forget",
            json={"dataset": dataset, "memoryOnly": memory_only},
        )
        resp.raise_for_status()
        return resp.json()
