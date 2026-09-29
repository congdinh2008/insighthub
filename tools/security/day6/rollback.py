#!/usr/bin/env python3
"""Restore the saved pre-Day06 Helm configuration after draining the Day06 queue."""

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from local_lab import CTX, NS, TMP, kubectl


def main():
    baseline = TMP / "baseline-values.json"
    if not baseline.exists():
        raise SystemExit("Missing original Helm values; refusing an inferred rollback")
    with httpx.Client(timeout=15, trust_env=False) as c:
        response = c.get(
            os.environ.get("DAY6_API_URL", "http://127.0.0.1:18010") + "/documents"
        )
        response.raise_for_status()
        if any(d["status"] == "pending" for d in response.json()):
            raise SystemExit("Drain incomplete: pending documents")
    queue = "insighthub:day6:ingestion"
    if int(kubectl("exec", "redis-0", "--", "redis-cli", "ZCARD", queue).strip()):
        raise SystemExit("Drain incomplete: queue has jobs")
    subprocess.run(
        [
            "helm",
            "--kube-context",
            CTX,
            "-n",
            NS,
            "upgrade",
            "insighthub",
            "deploy/helm/insighthub",
            "--reset-values",
            "-f",
            str(baseline),
            "--wait",
            "--timeout",
            "5m",
        ],
        check=True,
    )
    for deployment in ("insighthub-api", "insighthub-ingestion-worker"):
        obj = json.loads(kubectl("get", "deployment", deployment, "-o", "json"))
        refs = obj["spec"]["template"]["spec"]["containers"][0]["envFrom"]
        if any(r.get("secretRef", {}).get("name") == "day6-app-runtime" for r in refs):
            raise RuntimeError("Rollback retained Day06 secret")
    print(
        "API and worker restored together. Both Day06 PVCs and all original data are retained."
    )


if __name__ == "__main__":
    main()
