"""Local index of what's been remembered.

Cognee's forget() operates on a whole dataset, not a single fact. To let the
popup UI forget one memory surgically, every remembered item gets its own
tiny dataset; this ledger maps item_id -> dataset (plus the metadata needed
to render the passport list) so we know which dataset to forget.
"""
from __future__ import annotations

import json
import pathlib
import time
import uuid

LEDGER_PATH = pathlib.Path(__file__).parent / "ledger.json"


def _load() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return {}


def _save(data: dict) -> None:
    LEDGER_PATH.write_text(json.dumps(data, indent=2))


def add_item(text: str, source: str, category: str) -> dict:
    item_id = uuid.uuid4().hex[:12]
    dataset = f"passport_{category}_{item_id}"
    data = _load()
    data[item_id] = {
        "id": item_id,
        "text": text,
        "source": source,
        "category": category,
        "dataset": dataset,
        "created_at": time.time(),
    }
    _save(data)
    return data[item_id]


def list_items() -> list[dict]:
    return list(_load().values())


def get_item(item_id: str) -> dict | None:
    return _load().get(item_id)


def remove_item(item_id: str) -> None:
    data = _load()
    data.pop(item_id, None)
    _save(data)


def datasets_for(categories: list[str] | None = None, sources: list[str] | None = None) -> list[str]:
    items = list(_load().values())
    if categories:
        items = [i for i in items if i["category"] in categories]
    if sources:
        items = [i for i in items if i["source"] in sources]
    return sorted({i["dataset"] for i in items})
