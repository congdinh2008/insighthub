#!/usr/bin/env python3
"""Supervise localhost-only forwards across pod restarts; stop with Ctrl-C."""

import signal
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STOP = threading.Event()
CHILDREN = []
TARGETS = {
    "api": ("insighthub-dev", "service/insighthub-api", ["18010:8000"]),
    "baseline": ("insighthub-dev", "deployment/day6-baseline-api", ["18011:8000"]),
    "gateway": (
        "insighthub-dev",
        "deployment/day6-gateway",
        ["14010:4000", "19091:9091"],
    ),
    "guard": ("insighthub-dev", "service/day6-guardrails", ["18083:8082"]),
    "redis": ("insighthub-dev", "service/redis", ["16380:6379"]),
    "web": ("insighthub-dev", "service/insighthub-web", ["13000:3000"]),
    "prometheus": (
        "monitoring",
        "service/kube-prom-stack-kube-prome-prometheus",
        ["19090:9090"],
    ),
    "grafana": ("monitoring", "service/kube-prom-stack-grafana", ["13001:80"]),
}


def forward(name, namespace, target, ports):
    with (ROOT / "tmp/day6" / ("forward-" + name + ".log")).open("a") as log:
        while not STOP.is_set():
            process = subprocess.Popen(
                [
                    "kubectl",
                    "--context",
                    "kind-insighthub-local",
                    "-n",
                    namespace,
                    "port-forward",
                    "--address",
                    "127.0.0.1",
                    target,
                    *ports,
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            CHILDREN.append(process)
            process.wait()
            CHILDREN.remove(process)
            STOP.wait(2)


def stop(*_):
    STOP.set()
    for child in list(CHILDREN):
        child.terminate()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with ThreadPoolExecutor(max_workers=len(TARGETS)) as pool:
        jobs = [pool.submit(forward, name, *value) for name, value in TARGETS.items()]
        print(
            "Day06 localhost forwards supervised: API 18010, baseline 18011, gateway 14010, metrics 19091, guard 18083, web 13000, Redis 16380, Prometheus 19090, Grafana 13001",
            flush=True,
        )
        for job in jobs:
            job.result()
