from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

import cognee_client  # noqa: E402  (must load env first)
import ledger  # noqa: E402

app = FastAPI(title="Memory Passport Backend")

# Extension calls this from a chrome-extension:// origin -- permissive CORS is
# fine for a local hackathon demo, tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RememberRequest(BaseModel):
    text: str
    source: str  # "chatgpt" | "claude" | ...
    category: str = "general"  # "fact" | "project" | "conversation"


class RecallRequest(BaseModel):
    query: str
    top_k: int = 10


class ForgetRequest(BaseModel):
    item_id: str


@app.post("/api/remember")
async def api_remember(req: RememberRequest):
    item = ledger.add_item(text=req.text, source=req.source, category=req.category)
    result = await cognee_client.remember(req.text, dataset_name=item["dataset"])
    data_id = await cognee_client.newest_data_id(result["dataset_id"]) if result.get("dataset_id") else None
    ledger.set_data_id(item["id"], data_id)
    return {"item": {**item, "data_id": data_id}, "cognee": result}


@app.post("/api/recall")
async def api_recall(req: RecallRequest):
    if not ledger.has_items():
        return {"results": [], "note": "nothing remembered yet"}
    result = await cognee_client.recall(req.query, datasets=[ledger.PASSPORT_DATASET], top_k=req.top_k)
    return {"cognee": result}  # cognee.recall returns a plain list


@app.post("/api/improve")
async def api_improve():
    result = await cognee_client.improve(dataset_name=ledger.PASSPORT_DATASET)
    return {"improved": ledger.PASSPORT_DATASET, "cognee": result}


@app.get("/api/passport")
async def api_passport():
    return {"items": ledger.list_items()}


@app.post("/api/forget")
async def api_forget(req: ForgetRequest):
    item = ledger.get_item(req.item_id)
    if not item:
        raise HTTPException(404, "item not found")
    result = await cognee_client.forget(dataset=item["dataset"], data_id=item.get("data_id"), memory_only=False)
    # Best-effort: re-cognify so the graph reflects the deletion. In testing
    # this reliably removes the item from the raw data list and the graph
    # endpoint, but recall's search layer can still surface the forgotten
    # fact for a while afterward -- see README's known gaps.
    await cognee_client.improve(dataset_name=item["dataset"])
    ledger.remove_item(req.item_id)
    return {"status": "forgotten", "item_id": req.item_id, "cognee": result}
