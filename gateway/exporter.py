"""Expose bounded metrics from the sanitized durable ledger and authenticated key info."""

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    generate_latest,
)

app = FastAPI(docs_url=None, redoc_url=None)
ALIASES = {
    "insighthub": "day6-insighthub",
    "chatops-bot": "day6-bot",
    "coding-workflow": "day6-coding",
    "guardrail": "day6-guard",
    "evaluator": "day6-evaluator",
}


@app.get("/healthz")
async def health():
    return {"ready": True}


@app.get("/metrics")
async def metrics():
    registry = CollectorRegistry()
    totals = defaultdict(float)
    tokens = defaultdict(int)
    events = Counter()
    unknown = Counter()
    latency = defaultdict(list)
    path = Path(os.environ.get("DAY6_AUDIT_PATH", "/ledger/audit.jsonl"))
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            w = row.get("workload")
            if w not in ALIASES:
                continue
            event = row.get("event")
            events[(w, event)] += 1
            if event == "completion":
                duration = row.get("duration_seconds")
                if isinstance(duration, (int, float)):
                    latency[w].append(duration)
                cost = row.get("cost_usd")
                if isinstance(cost, (int, float)):
                    totals[w] += cost
                else:
                    unknown[w] += 1
                for direction in ("input", "output"):
                    n = row.get(direction + "_tokens")
                    if isinstance(n, int):
                        tokens[(w, str(row.get("model")), direction)] += n
    spend = Gauge(
        "day6_llm_spend_usd_total",
        "Cumulative measured gateway catalog cost",
        ["workload"],
        registry=registry,
    )
    usage = Gauge(
        "day6_llm_tokens_total",
        "Provider token usage",
        ["workload", "model", "direction"],
        registry=registry,
    )
    decision = Gauge(
        "day6_gateway_events_total",
        "Sanitized gateway decisions",
        ["workload", "event"],
        registry=registry,
    )
    missing = Gauge(
        "day6_llm_unknown_cost_total",
        "Completions without known cost",
        ["workload"],
        registry=registry,
    )
    for w in ALIASES:
        spend.labels(w).set(totals[w])
        missing.labels(w).set(unknown[w])
        for event in (
            "admitted",
            "denied",
            "budget_denied",
            "completion",
            "upstream_failure",
        ):
            decision.labels(w, event).set(events[(w, event)])
    for (w, m, d), n in tokens.items():
        usage.labels(w, m, d).set(n)
    for (w, e), n in events.items():
        decision.labels(w, str(e)).set(n)
    durations = Gauge(
        "day6_llm_latency_seconds",
        "Observed ledger latency quantiles",
        ["workload", "quantile"],
        registry=registry,
    )
    for w, values in latency.items():
        ordered = sorted(values)
        for q in (0.5, 0.95):
            durations.labels(w, str(q)).set(
                ordered[min(len(ordered) - 1, int(len(ordered) * q))]
            )
    budget = Gauge(
        "day6_key_budget_usd", "Configured key budget", ["workload"], registry=registry
    )
    dbspend = Gauge(
        "day6_key_spend_usd",
        "Persistent LiteLLM key spend",
        ["workload"],
        registry=registry,
    )
    ready = Gauge(
        "day6_accounting_available",
        "Key accounting endpoint availability",
        registry=registry,
    )
    try:
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:4000",
            timeout=5,
            trust_env=False,
            headers={"Authorization": "Bearer " + os.environ["LITELLM_MASTER_KEY"]},
        ) as client:
            for w, alias in ALIASES.items():
                r = await client.get(
                    "/key/list",
                    params={"key_alias": alias, "return_full_object": "true"},
                )
                r.raise_for_status()
                data = r.json()["keys"][0]
                budget.labels(w).set(data["max_budget"])
                dbspend.labels(w).set(data["spend"])
        ready.set(1)
    except (httpx.HTTPError, KeyError, ValueError, TypeError, IndexError):
        ready.set(0)
    return Response(
        generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST}
    )
