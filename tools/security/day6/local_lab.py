#!/usr/bin/env python3
"""Reproducible Day 06 local additions. Never removes Day 01-05 data."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TMP = ROOT / "tmp/day6"
CTX = "kind-insighthub-local"
NS = "insighthub-dev"
PG = "pgvector/pgvector:0.8.2-pg16@sha256:00ba258a66dac104fd5171074a0084462a64a1369d8513f3d0a634e2f24d15bc"


def kubectl(*args, payload=None):
    return subprocess.run(
        ["kubectl", "--context", CTX, "-n", NS, *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(value, indent=2))
    os.chmod(path, 0o600)


def apply(obj):
    obj.setdefault("metadata", {}).setdefault("labels", {})["day6-owner"] = "insighthub"
    kubectl("apply", "-f", "-", payload=obj)


def service(name, port):
    apply(
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": name},
            "spec": {
                "selector": {"app": name},
                "ports": [
                    {
                        "name": "http" if port != 5432 else "postgres",
                        "port": port,
                        "targetPort": port,
                    }
                ],
            },
        }
    )


def deployment(
    name, image, port, env, *, mounts=None, volumes=None, memory="1Gi", args=None
):
    container = {
        "name": name,
        "image": image,
        "imagePullPolicy": "IfNotPresent",
        "ports": [{"containerPort": port}],
        "env": [{"name": k, **v} for k, v in env.items()],
        "resources": {
            "requests": {"cpu": "50m", "memory": "128Mi"},
            "limits": {"cpu": "1500m", "memory": memory},
        },
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
        },
        "volumeMounts": mounts or [],
        "readinessProbe": {
            "httpGet": {
                "path": "/health/liveliness" if port == 4000 else "/healthz",
                "port": port,
            },
            "periodSeconds": 5,
        },
        "startupProbe": {
            "httpGet": {
                "path": "/health/liveliness" if port == 4000 else "/healthz",
                "port": port,
            },
            "failureThreshold": 90,
            "periodSeconds": 5,
        },
    }
    if args:
        container["args"] = args
    apply(
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": name},
            "spec": {
                "replicas": 1,
                "strategy": {"type": "Recreate"},
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name, "day6-owner": "insighthub"}},
                    "spec": {
                        "automountServiceAccountToken": False,
                        "containers": [container],
                        "volumes": volumes or [],
                    },
                },
            },
        }
    )
    service(name, port)


def secretref(key):
    return {"valueFrom": {"secretKeyRef": {"name": "day6-infrastructure", "key": key}}}


def database(name, password):
    # Separate PostgreSQL instances and PVCs for gateway accounting and RAG index.
    apply(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": name},
            "stringData": {"password": password},
        }
    )
    apply(
        {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {"name": name},
            "spec": {
                "serviceName": name,
                "replicas": 1,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name, "day6-owner": "insighthub"}},
                    "spec": {
                        "automountServiceAccountToken": False,
                        "containers": [
                            {
                                "name": "postgres",
                                "image": PG,
                                "env": [
                                    {"name": "POSTGRES_USER", "value": "day6"},
                                    {"name": "POSTGRES_DB", "value": "day6"},
                                    {
                                        "name": "POSTGRES_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": name,
                                                "key": "password",
                                            }
                                        },
                                    },
                                    {
                                        "name": "PGDATA",
                                        "value": "/var/lib/postgresql/data/pgdata",
                                    },
                                ],
                                "ports": [{"containerPort": 5432}],
                                "volumeMounts": [
                                    {
                                        "name": "data",
                                        "mountPath": "/var/lib/postgresql/data",
                                    }
                                ],
                                "resources": {
                                    "requests": {"cpu": "25m", "memory": "64Mi"},
                                    "limits": {"cpu": "500m", "memory": "512Mi"},
                                },
                                "readinessProbe": {
                                    "exec": {
                                        "command": [
                                            "pg_isready",
                                            "-U",
                                            "day6",
                                            "-d",
                                            "day6",
                                        ]
                                    },
                                    "periodSeconds": 5,
                                },
                            }
                        ],
                    },
                },
                "volumeClaimTemplates": [
                    {
                        "metadata": {"name": "data"},
                        "spec": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": "1Gi"}},
                        },
                    }
                ],
            },
        }
    )
    service(name, 5432)


def up():
    TMP.mkdir(parents=True, exist_ok=True)
    # Explicit source credentials, never print them or put them in argv.
    cfgpath = TMP / "infrastructure.json"
    if cfgpath.exists():
        cfg = json.loads(cfgpath.read_text())
    else:
        cfg = {
            "LITELLM_MASTER_KEY": "sk-" + secrets.token_hex(32),
            "GUARD_API_KEY": secrets.token_hex(32),
            "gateway_password": secrets.token_hex(24),
            "rag_password": secrets.token_hex(24),
            "ZENLAYER_API_KEY": os.environ["ZENLAYER_API_KEY"],
            "ZENLAYER_BASE_URL": os.environ["ZENLAYER_BASE_URL"],
        }
        cfg["DATABASE_URL"] = (
            f"postgresql://day6:{cfg['gateway_password']}@day6-gateway-db:5432/day6"
        )
        private(cfgpath, cfg)
    apply(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "day6-infrastructure"},
            "stringData": cfg,
        }
    )
    for db, p in [
        ("day6-gateway-db", "gateway_password"),
        ("day6-rag-db", "rag_password"),
    ]:
        database(db, cfg[p])
        kubectl("rollout", "status", "statefulset/" + db, "--timeout=180s")
    # Idempotent schema uses the unchanged project DDL against the isolated DB only.
    subprocess.run(
        [
            "kubectl",
            "--context",
            CTX,
            "-n",
            NS,
            "exec",
            "-i",
            "day6-rag-db-0",
            "--",
            "psql",
            "-U",
            "day6",
            "-d",
            "day6",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=(ROOT / "infra/db/init.sql").read_text(),
        text=True,
        check=True,
        capture_output=True,
    )
    apply(
        {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": "day6-ledger"},
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": "256Mi"}},
            },
        }
    )
    deployment(
        "day6-guardrails",
        "insighthub-guardrails:day6",
        8082,
        {"GUARD_API_KEY": secretref("GUARD_API_KEY")},
        memory="2Gi",
    )
    env = {
        k: secretref(k)
        for k in [
            "LITELLM_MASTER_KEY",
            "DATABASE_URL",
            "ZENLAYER_API_KEY",
            "ZENLAYER_BASE_URL",
            "GUARD_API_KEY",
        ]
    }
    env.update(
        {
            "DAY6_ACCOUNTING_URL": secretref("DATABASE_URL"),
            "GUARD_URL": {"value": "http://day6-guardrails:8082"},
            "DAY6_AUDIT_PATH": {"value": "/ledger/audit.jsonl"},
            "DAY6_POLICY_MODE": {"value": "enforce"},
            "DAY6_RUN_ID": {"value": "day6-local"},
        }
    )
    deployment(
        "day6-gateway",
        "insighthub-gateway:day6",
        4000,
        env,
        mounts=[{"name": "ledger", "mountPath": "/ledger"}],
        volumes=[
            {"name": "ledger", "persistentVolumeClaim": {"claimName": "day6-ledger"}}
        ],
        memory="2Gi",
    )
    for d in ["day6-guardrails", "day6-gateway"]:
        kubectl("rollout", "status", "deployment/" + d, "--timeout=450s")
    print(
        "Day 06 gateway and guardrails ready. Application switch is a separate drain-and-overlay step."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["up", "status"])
    args = parser.parse_args()
    if args.action == "up":
        up()
    else:
        print(kubectl("get", "pods,svc,pvc", "-l", "day6-owner=insighthub"))
