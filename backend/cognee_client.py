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
from __future__ import annotations

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


async def newest_data_id(dataset_id: str) -> str | None:
    """The `items` list in remember()'s response is the whole dataset, not
    just what was just added, and isn't reliably ordered -- so to know which
    data_id is the new one, ask for the dataset's data list (which has real
    timestamps) and take the most recently created record.
    """
    async with _client() as client:
        resp = await client.get(f"/api/v1/datasets/{dataset_id}/data")
        resp.raise_for_status()
        records = resp.json()
        if not records:
            return None
        return max(records, key=lambda r: r["createdAt"])["id"]


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


async def forget(dataset: str, data_id: str | None = None, memory_only: bool = True) -> dict:
    payload = {"dataset": dataset, "memoryOnly": memory_only}
    if data_id:
        payload["dataId"] = data_id
    async with _client() as client:
        resp = await client.post("/api/v1/forget", json=payload)
        resp.raise_for_status()
        return resp.json()
