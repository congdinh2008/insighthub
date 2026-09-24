#!/usr/bin/env python3
"""Build, deploy and inspect the isolated InsightHub Day 04 local lab."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLUSTER = "insighthub-local"
CONTEXT = f"kind-{CLUSTER}"
APP_NAMESPACE = "insighthub-dev"
MONITORING_NAMESPACE = "monitoring"
STACK_VERSION = "89.2.0"
IMAGES = {
    "insighthub-api:day4": ["docker", "build", "-t", "insighthub-api:day4", "api"],
    "insighthub-worker:day4": [
        "docker",
        "build",
        "--target",
        "runtime",
        "-t",
        "insighthub-worker:day4",
        "-f",
        "ingestion-worker/Dockerfile",
        ".",
    ],
    "insighthub-web:day4": ["docker", "build", "-t", "insighthub-web:day4", "web"],
}


def executable(name: str) -> str:
    for candidate in (
        ROOT / "tmp" / "day3" / "bin" / name,
        ROOT / "tmp" / "day2" / "bin" / name,
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise SystemExit(f"Missing required executable: {name}")


def run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
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


def export_context(kind: str) -> None:
    run([kind, "export", "kubeconfig", "--name", CLUSTER])


def kubectl(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return run(
        [executable("kubectl"), "--context", CONTEXT, *arguments], capture=capture
    )


def slack_secret_exists() -> bool:
    result = subprocess.run(
        [
            executable("kubectl"),
            "--context",
            CONTEXT,
            "-n",
            MONITORING_NAMESPACE,
            "get",
            "secret",
            "insighthub-alertmanager-slack",
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def up() -> None:
    kind, helm = executable("kind"), executable("helm")
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
    export_context(kind)
    for image in IMAGES:
        run([kind, "load", "docker-image", "--name", CLUSTER, image])

    application = [
        helm,
        "upgrade",
        "--install",
        "insighthub",
        "deploy/helm/insighthub",
        "--namespace",
        APP_NAMESPACE,
        "--create-namespace",
        "--values",
        "deploy/helm/insighthub/values-local.yaml",
        "--values",
        "deploy/helm/insighthub/values-day4-local.yaml",
    ]
    extra_application_values = os.environ.get("DAY4_APP_VALUES")
    if extra_application_values:
        application += ["--values", extra_application_values]
    application += [
        "--wait",
        "--timeout",
        "10m",
    ]
    run(application)
    run(
        [
            helm,
            "upgrade",
            "--install",
            "kube-prom-stack",
            "oci://ghcr.io/prometheus-community/charts/kube-prometheus-stack",
            "--version",
            STACK_VERSION,
            "--namespace",
            MONITORING_NAMESPACE,
            "--create-namespace",
            "--values",
            "observability/kube-prometheus-stack-values.yaml",
            "--wait",
            "--timeout",
            "15m",
        ]
    )
    observability = [
        helm,
        "upgrade",
        "--install",
        "insighthub-observability",
        "observability/chart",
        "--namespace",
        MONITORING_NAMESPACE,
        "--values",
        "observability/values-day4-local.yaml",
        "--wait",
        "--timeout",
        "5m",
    ]
    extra_observability_values = os.environ.get("DAY4_OBSERVABILITY_VALUES")
    if extra_observability_values:
        observability += ["--values", extra_observability_values]
    if slack_secret_exists():
        observability += ["--set", "alerting.slack.enabled=true"]
    run(observability)
    status()


def status() -> None:
    kind = executable("kind")
    if not cluster_exists(kind):
        raise SystemExit(f"Kind cluster does not exist: {CLUSTER}")
    export_context(kind)
    kubectl("get", "pods", "-n", APP_NAMESPACE, "-o", "wide")
    kubectl("get", "pods", "-n", MONITORING_NAMESPACE, "-o", "wide")
    kubectl("get", "servicemonitor", "-n", MONITORING_NAMESPACE)
    kubectl("get", "prometheusrule", "-n", MONITORING_NAMESPACE)
    kubectl("get", "alertmanagerconfig", "-n", MONITORING_NAMESPACE)


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
