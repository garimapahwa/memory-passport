"""Local index of what's been remembered.

Every remembered fact goes into one shared Cognee dataset, not its own
isolated dataset. A separate dataset per fact was tried first and made
recall noticeably worse: each dataset became its own tiny, disconnected
graph, so GRAPH_COMPLETION had nothing to connect facts to (a name in one
dataset, a preference in another -- no shared graph to traverse). One
shared dataset lets cognify build real relationships across everything
you've told it.

Per-item deletion still works on a shared dataset: remember() returns a
data_id for the item it just ingested, and forget() accepts a dataId
scoped to one dataset -- so the popup can still surgically forget a single
fact without wiping the rest of the graph.
"""
from __future__ import annotations

import json
import pathlib
import time
import uuid

LEDGER_PATH = pathlib.Path(__file__).parent / "ledger.json"
PASSPORT_DATASET = "passport_v2"


def _load() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return {}


def _save(data: dict) -> None:
    LEDGER_PATH.write_text(json.dumps(data, indent=2))


def add_item(text: str, source: str, category: str) -> dict:
    item_id = uuid.uuid4().hex[:12]
    data = _load()
    data[item_id] = {
        "id": item_id,
        "text": text,
        "source": source,
        "category": category,
        "dataset": PASSPORT_DATASET,
        "data_id": None,  # filled in once remember() returns Cognee's data id
        "created_at": time.time(),
    }
    _save(data)
    return data[item_id]


def set_data_id(item_id: str, data_id: str | None) -> None:
    data = _load()
    if item_id in data:
        data[item_id]["data_id"] = data_id
        _save(data)


def list_items() -> list[dict]:
    return list(_load().values())


def get_item(item_id: str) -> dict | None:
    return _load().get(item_id)


def remove_item(item_id: str) -> None:
    data = _load()
    data.pop(item_id, None)
    _save(data)


def has_items() -> bool:
    return bool(_load())
