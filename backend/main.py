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
    datasets: Optional[list[str]] = None
    categories: Optional[list[str]] = None
    sources: Optional[list[str]] = None
    top_k: int = 10


class ForgetRequest(BaseModel):
    item_id: str


@app.post("/api/remember")
async def api_remember(req: RememberRequest):
    item = ledger.add_item(text=req.text, source=req.source, category=req.category)
    result = await cognee_client.remember(req.text, dataset_name=item["dataset"])
    return {"item": item, "cognee": result}


@app.post("/api/recall")
async def api_recall(req: RecallRequest):
    datasets = req.datasets or ledger.datasets_for(categories=req.categories, sources=req.sources)
    if not datasets:
        return {"results": [], "datasets_used": [], "note": "nothing remembered yet"}
    result = await cognee_client.recall(req.query, datasets=datasets, top_k=req.top_k)
    return {"cognee": result, "datasets_used": datasets}  # cognee.recall returns a plain list


@app.post("/api/improve")
async def api_improve(dataset: str = "all"):
    datasets = ledger.datasets_for() if dataset == "all" else [dataset]
    results = []
    for ds in datasets:
        results.append(await cognee_client.improve(dataset_name=ds))
    return {"improved": datasets, "cognee": results}


@app.get("/api/passport")
async def api_passport():
    return {"items": ledger.list_items()}


@app.post("/api/forget")
async def api_forget(req: ForgetRequest):
    item = ledger.get_item(req.item_id)
    if not item:
        raise HTTPException(404, "item not found")
    result = await cognee_client.forget(dataset=item["dataset"], memory_only=True)
    ledger.remove_item(req.item_id)
    return {"status": "forgotten", "item_id": req.item_id, "cognee": result}
