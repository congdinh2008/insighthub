"""
InsightHub API — Chat router
RAG query: retrieve → generate.
"""
import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.metrics import (
    embedding_tokens_total,
    llm_call_latency,
    llm_tokens_total,
    rag_query_latency,
)
from app.services.llm import generate
from app.services.retrieval import retrieve

logger = logging.getLogger("insighthub.routers.chat")
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    filename: str
    similarity: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    contexts: list[dict]
    latency_ms: int


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.perf_counter()
    with rag_query_latency.time():
        contexts = retrieve(req.question, top_k=req.top_k)
        if not contexts:
            raise HTTPException(
                404, "Chưa có tài liệu nào sẵn sàng. Hãy upload tài liệu trước."
            )

        llm_start = time.perf_counter()
        result = generate(req.question, contexts)
        llm_call_latency.observe(time.perf_counter() - llm_start)

    # Metrics cho FinOps Day 6
    usage = result.get("usage", {})
    llm_tokens_total.labels(direction="input").inc(usage.get("input_tokens", 0))
    llm_tokens_total.labels(direction="output").inc(usage.get("output_tokens", 0))
    # Embedding token approx (1 query ~ số từ)
    embedding_tokens_total.inc(len(req.question.split()))

    # Deduplicate sources, keep max similarity per filename
    seen: dict[str, float] = {}
    for c in contexts:
        seen[c["source"]] = max(seen.get(c["source"], 0.0), c["similarity"])
    sources = [Source(filename=fn, similarity=sim) for fn, sim in seen.items()]

    latency_ms = int((time.perf_counter() - start) * 1000)
    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        contexts=contexts,
        latency_ms=latency_ms,
    )
