#!/usr/bin/env python3
"""Build, deploy and remove the isolated InsightHub local Kubernetes lab."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLUSTER = "insighthub-local"
NAMESPACE = "insighthub-dev"
IMAGES = {
    "insighthub-api:day3": ["docker", "build", "-t", "insighthub-api:day3", "api"],
    "insighthub-worker:day3": [
        "docker",
        "build",
        "--target",
        "runtime",
        "-t",
        "insighthub-worker:day3",
        "-f",
        "ingestion-worker/Dockerfile",
        ".",
    ],
    "insighthub-web:day3": ["docker", "build", "-t", "insighthub-web:day3", "web"],
}


def executable(name: str) -> str:
    candidates = [
        ROOT / "tmp" / "day3" / "bin" / name,
        ROOT / "tmp" / "day2" / "bin" / name,
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(f"Missing required executable: {name}")


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def cluster_exists(kind: str) -> bool:
    result = run([kind, "get", "clusters"], capture=True)
    return CLUSTER in result.stdout.splitlines()


def up() -> None:
    kind = executable("kind")
    for command in IMAGES.values():
        run(command)
    if not cluster_exists(kind):
        run(
            [
                kind,
                "create",
                "cluster",
                "--name",
                CLUSTER,
                "--config",
                "deploy/kind/cluster.yaml",
                "--wait",
                "180s",
            ]
        )
    for image in IMAGES:
        run([kind, "load", "docker-image", "--name", CLUSTER, image])
    run(
        [
            "helm",
            "upgrade",
            "--install",
            "insighthub",
            "deploy/helm/insighthub",
            "--namespace",
            NAMESPACE,
            "--create-namespace",
            "--values",
            "deploy/helm/insighthub/values-local.yaml",
            "--wait",
            "--timeout",
            "10m",
        ]
    )
    status()


def status() -> None:
    context = f"kind-{CLUSTER}"
    run(["kubectl", "--context", context, "get", "pods", "-n", NAMESPACE, "-o", "wide"])
    run(["kubectl", "--context", context, "get", "services", "-n", NAMESPACE])


def down() -> None:
    kind = executable("kind")
    if cluster_exists(kind):
        run([kind, "delete", "cluster", "--name", CLUSTER])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("up", "status", "down"))
    action = parser.parse_args().action
    {"up": up, "status": status, "down": down}[action]()


if __name__ == "__main__":
    main()
