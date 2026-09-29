"""One exact Kubernetes scale action using a separate scoped kubeconfig."""

import asyncio
import json
from typing import Any

from .config import Settings


class ScaleError(Exception):
    pass


async def _kubectl(settings: Settings, *args: str) -> str:
    if not settings.kubeconfig_scale:
        raise ScaleError("scale identity unavailable")
    command = ["kubectl", "--kubeconfig", settings.kubeconfig_scale,
               "--context", settings.cluster_context, "-n", settings.namespace, *args]
    proc = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.DEVNULL)
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
    except (TimeoutError, asyncio.CancelledError):
        if proc.returncode is None:
            proc.kill()
        await proc.communicate()
        raise
    if proc.returncode != 0:
        raise ScaleError("Kubernetes rejected scoped action")
    return stdout.decode()


async def inspect_api(settings: Settings) -> dict[str, Any]:
    data = json.loads(await _kubectl(settings, "get", "deployment", "insighthub-api", "-o", "json"))
    metadata, spec = data["metadata"], data["spec"]
    return {"uid": str(metadata["uid"]), "resource_version": str(metadata["resourceVersion"]),
            "replicas": int(spec.get("replicas", 1))}


async def scale_api(settings: Settings, approval: dict[str, Any]) -> dict[str, Any]:
    if (approval.get("action") != "scale_api" or approval.get("target") != "insighthub-api"
            or approval.get("namespace") != settings.namespace
            or approval.get("cluster") != settings.cluster_context
            or type(approval.get("replicas")) is not int
            or not 1 <= approval["replicas"] <= 5):
        raise ScaleError("approval action mismatch")
    current = await inspect_api(settings)
    if (current["uid"] != approval["target_uid"]
            or current["resource_version"] != approval["resource_version"]
            or current["replicas"] != approval["current_replicas"]):
        raise ScaleError("deployment changed since approval")
    await _kubectl(settings, "scale", "deployment/insighthub-api",
                   "--replicas", str(approval["replicas"]),
                   "--current-replicas", str(current["replicas"]),
                   "--resource-version", current["resource_version"])
    after = await inspect_api(settings)
    if after["uid"] != current["uid"] or after["replicas"] != approval["replicas"]:
        raise ScaleError("scale outcome uncertain; inspect deployment")
    return after
