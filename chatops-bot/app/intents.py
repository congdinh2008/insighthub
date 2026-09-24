"""Evidence-first handlers for the three Day 05 operational questions."""

import json
import re
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import Settings
from .mcp_backend import MCPUnavailable, call

ICT = ZoneInfo("Asia/Ho_Chi_Minh")
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


def count_created_today_ready(rows: Any, now: datetime) -> tuple[int, datetime]:
    if not isinstance(rows, list):
        raise ValueError("documents response is not a list")
    local = now.astimezone(ICT)
    start = datetime.combine(local.date(), time.min, ICT).astimezone(UTC)
    end = now.astimezone(UTC)
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            raise ValueError("invalid document row")
        if row.get("status") not in {"ready", "pending", "failed"}:
            raise ValueError("invalid document status")
        stamp = datetime.fromisoformat(str(row.get("created_at", "")).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("missing timezone")
        if row["status"] == "ready" and start <= stamp.astimezone(UTC) < end:
            seen.add(row["id"])
    return len(seen), start


async def _fixed_get(url: str, max_bytes: int = 32768) -> Any:
    async with httpx.AsyncClient(timeout=5) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError("upstream response too large")
            return json.loads(data)


def _pod_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        lines = value.splitlines()
        if not lines or "NAME" not in lines[0].split():
            return []
        parsed = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 7 and parts[2] == "Pod":
                parsed.append({"metadata": {"name": parts[3]},
                               "status": {"phase": parts[5], "ready_ratio": parts[4],
                                          "restarts": parts[6]}})
        return parsed
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        if isinstance(value.get("items"), list):
            return _pod_rows(value["items"])
        for key in ("pods", "result"):
            if isinstance(value.get(key), list):
                return _pod_rows(value[key])
    return []


def failing_pods(value: Any) -> list[str]:
    failed: list[str] = []
    for pod in _pod_rows(value):
        meta, status = pod.get("metadata", {}), pod.get("status", {})
        name = str(meta.get("name", "unknown"))
        reasons: list[str] = []
        phase = status.get("phase")
        if phase in {"Failed", "Unknown"}:
            reasons.append(str(phase))
        if status.get("ready_ratio"):
            ready, total = str(status["ready_ratio"]).split("/", 1)
            if ready != total:
                reasons.append(f"ready {ready}/{total}")
            if phase not in {"Running", "Succeeded", "Failed", "Unknown"}:
                reasons.append(str(phase))
        for item in status.get("containerStatuses", []) or []:
            if item.get("ready") is False:
                reasons.append(str(item.get("state", {}).get("waiting", {}).get("reason")
                                   or item.get("state", {}).get("terminated", {}).get("reason")
                                   or "container not ready"))
        for item in status.get("conditions", []) or []:
            if item.get("type") == "Ready" and item.get("status") == "False":
                reasons.append("pod not ready")
        if reasons:
            failed.append(f"{name}: {', '.join(dict.fromkeys(reasons))}")
    return failed[:20]


def _scalar(value: Any) -> float | None:
    if not isinstance(value, dict) or not isinstance(value.get("result"), str):
        return None
    found = re.search(r"=>\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*@", value["result"])
    return float(found.group(1)) if found else None


async def answer(intent: str, settings: Settings) -> tuple[str, list[tuple[str, str]]]:
    now = datetime.now(UTC)
    observed = now.isoformat(timespec="seconds")
    calls: list[tuple[str, str]] = []
    if intent == "ingestion":
        rows = await _fixed_get(settings.api_url.rstrip("/") + "/documents", MAX_DOCUMENT_BYTES)
        count, start = count_created_today_ready(rows, now)
        calls.append(("insighthub.GET /documents", f"count={count}"))
        try:
            await call(settings.mcp_config, "prometheus", "query",
                       {"query": 'sum(insighthub_documents_total{status="ready"})'})
            calls.append(("prometheus.query", "ready inventory observed"))
        except MCPUnavailable:
            calls.append(("prometheus.query", "unavailable; count from API only"))
        return (f"InsightHub {settings.namespace}: {count} tài liệu được *tạo hôm nay và hiện đã ready*. "
                f"Ngày ICT từ {start.astimezone(ICT):%H:%M %d/%m/%Y} đến "
                f"{now.astimezone(ICT):%H:%M:%S}; quan sát {observed} UTC. "
                "Đây là inventory hiện tại, không phải số hoàn tất ingestion lần đầu hôm nay."), calls
    if intent == "pods":
        raw = await call(settings.mcp_config, "kubernetes", "pods_list_in_namespace",
                         {"namespace": settings.namespace})
        rows = _pod_rows(raw)
        if not rows:
            raise MCPUnavailable("pods result empty or unrecognized")
        failed = failing_pods(raw)
        calls.append(("kubernetes.pods_list_in_namespace", f"pods={len(rows)} failed={len(failed)}"))
        text = "; ".join(failed) if failed else f"Không thấy pod/container lỗi trong {len(rows)} pod."
        return (f"InsightHub {settings.namespace}, {observed} UTC: {text} "
                "Nguồn: Kubernetes MCP; nếu cần, kiểm events/logs đọc giới hạn."), calls
    if intent == "health":
        state: list[str] = []
        api_ready = False
        pods_known = False
        pod_failures = 0
        errors: float | None = None
        try:
            health = await _fixed_get(settings.api_url.rstrip("/") + "/readyz")
            api_ready = health.get("status") == "ready" and health.get("db") is True
            state.append("API ready" if api_ready else "API chưa ready")
            calls.append(("insighthub.GET /readyz", state[-1]))
        except Exception:
            state.append("API readiness chưa xác minh")
            calls.append(("insighthub.GET /readyz", "unknown"))
        try:
            pods = await call(settings.mcp_config, "kubernetes", "pods_list_in_namespace",
                              {"namespace": settings.namespace})
            bad = failing_pods(pods)
            if not _pod_rows(pods):
                state.append("pods chưa xác minh")
            else:
                pods_known = True
                pod_failures = len(bad)
                state.append(f"{len(bad)} pod/container lỗi")
            calls.append(("kubernetes.pods_list_in_namespace", state[-1]))
        except MCPUnavailable:
            state.append("pods chưa xác minh")
            calls.append(("kubernetes.pods_list_in_namespace", "unknown"))
        try:
            metric = await call(settings.mcp_config, "prometheus", "query",
                                {"query": 'sum(increase(insighthub_http_requests_total{status=~"5.."}[5m])) or vector(0)'})
            errors = _scalar(metric)
            if errors is None:
                state.append("Prometheus 5xx chưa xác minh")
                calls.append(("prometheus.query", "5xx/5m unknown"))
            else:
                state.append(f"5xx/5m={errors:g}")
                calls.append(("prometheus.query", f"5xx/5m={errors:g}"))
        except MCPUnavailable:
            state.append("Prometheus chưa xác minh")
            calls.append(("prometheus.query", "unknown"))
        if not (api_ready and pods_known and errors is not None):
            verdict = "unknown/partial"
        elif pod_failures > 0 or errors > 0:
            verdict = "degraded"
        else:
            verdict = "API/pods ổn theo tín hiệu kiểm tra; chưa kết luận toàn hệ thống"
        return (f"InsightHub {settings.namespace}, {observed} UTC: {verdict}. "
                + "; ".join(state) + ". Nguồn: API, Kubernetes MCP, Prometheus MCP."), calls
    raise ValueError("unsupported intent")
