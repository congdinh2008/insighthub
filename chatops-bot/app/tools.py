"""Operational query tools — K8s + Prometheus + API health (reuse Day 2 MCP setup)."""
import json
import logging
import os
import subprocess
from typing import Any

import httpx

logger = logging.getLogger("chatops-bot.tools")

INSIGHTHUB_API_URL = os.getenv("INSIGHTHUB_API_URL", "http://api:8000")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "insighthub")


async def check_api_health(client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Check InsightHub API health status."""
    close = client is None
    c = client or httpx.AsyncClient(timeout=5.0)
    try:
        resp = await c.get(f"{INSIGHTHUB_API_URL}/healthz")
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        return {"status": "ok" if resp.status_code == 200 else "degraded", "http_code": resp.status_code, "details": data}
    except httpx.ConnectError:
        return {"status": "unreachable", "error": "Connection refused"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        if close:
            await c.aclose()


async def get_ingest_count_today(client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Get today's document ingest count via Prometheus (reuse Day 2 Prometheus MCP)."""
    close = client is None
    c = client or httpx.AsyncClient(timeout=10.0)
    try:
        query = "sum(increase(insighthub_ingestion_jobs_total[24h]))"
        resp = await c.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
        data = resp.json()
        if data.get("status") == "success":
            results = data.get("data", {}).get("result", [])
            count = int(float(results[0]["value"][1])) if results else 0
            return {"count": count, "source": "prometheus", "query": query}
        return {"count": 0, "source": "prometheus_error", "error": data.get("error", "no data")}
    except Exception as e:
        return {"count": 0, "source": "unavailable", "error": str(e)}
    finally:
        if close:
            await c.aclose()


def get_failing_pods(namespace: str = K8S_NAMESPACE) -> dict[str, Any]:
    """List failing K8s pods via kubectl (reuse Day 2 mcp-readonly ServiceAccount)."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return {"failing": [], "error": result.stderr.strip(), "namespace": namespace}
        data = json.loads(result.stdout)
        failing = []
        for pod in data.get("items", []):
            phase = pod["status"].get("phase", "Unknown")
            ready = _is_pod_ready(pod)
            if phase not in ("Running", "Succeeded") or not ready:
                failing.append({
                    "name": pod["metadata"]["name"],
                    "phase": phase,
                    "ready": ready,
                    "restart_count": _get_restart_count(pod),
                })
        total = len(data.get("items", []))
        return {"failing": failing, "failing_count": len(failing), "total_pods": total, "namespace": namespace}
    except FileNotFoundError:
        return {"failing": [], "error": "kubectl not found — configure kubeconfig", "namespace": namespace}
    except subprocess.TimeoutExpired:
        return {"failing": [], "error": "kubectl timed out after 15s", "namespace": namespace}
    except Exception as e:
        return {"failing": [], "error": str(e), "namespace": namespace}


def _is_pod_ready(pod: dict) -> bool:
    for cond in pod["status"].get("conditions", []):
        if cond["type"] == "Ready":
            return cond["status"] == "True"
    return False


def _get_restart_count(pod: dict) -> int:
    return sum(cs.get("restartCount", 0) for cs in pod["status"].get("containerStatuses", []))


# Claude tool definitions (used in handler.py tool-calling loop)
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "check_api_health",
        "description": (
            "Check InsightHub API health and all services status. "
            "Use when asked: 'healthy?', 'OK?', 'có lỗi không?', 'running?'."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_ingest_count_today",
        "description": (
            "Get the number of documents ingested in the last 24h via Prometheus metrics. "
            "Use when asked about document count, ingestion activity, 'bao nhiêu doc'."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_failing_pods",
        "description": (
            "List Kubernetes pods that are failing, crashing, or not ready. "
            "Use when asked about pod errors, crashes, 'pod nào lỗi', 'pod failing'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": f"Kubernetes namespace to inspect (default: {K8S_NAMESPACE})",
                }
            },
            "required": [],
        },
    },
]
