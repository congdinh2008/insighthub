#!/usr/bin/env python3
"""Install Day06 ledger exporter and standalone Grafana dashboard."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from local_lab import NS, ROOT, apply, kubectl, secretref

PANELS = [
    ("LLM total cost", "sum(day6_llm_spend_usd_total)", "currencyUSD", "stat"),
    (
        "LLM Cost rate USD/hour",
        "sum(rate(day6_llm_spend_usd_total[5m])) * 3600",
        "currencyUSD",
        "timeseries",
    ),
    ("Cost by workload", "day6_llm_spend_usd_total", "currencyUSD", "timeseries"),
    (
        "Remaining key budget",
        "clamp_min(day6_key_budget_usd - day6_key_spend_usd, 0)",
        "currencyUSD",
        "timeseries",
    ),
    ("PostgreSQL key spend", "day6_key_spend_usd", "currencyUSD", "timeseries"),
    ("Tokens by model and workload", "day6_llm_tokens_total", "short", "timeseries"),
    (
        "Policy denials",
        'sum by (workload) (day6_gateway_events_total{event="denied"})',
        "short",
        "timeseries",
    ),
    (
        "Budget denials",
        'sum by (workload) (day6_gateway_events_total{event="budget_denied"})',
        "short",
        "timeseries",
    ),
    (
        "Completions",
        'day6_gateway_events_total{event="completion"}',
        "short",
        "timeseries",
    ),
    (
        "Upstream errors",
        'day6_gateway_events_total{event="upstream_failure"}',
        "short",
        "timeseries",
    ),
    ("Unknown cost events", "sum(day6_llm_unknown_cost_total)", "short", "stat"),
    ("Accounting endpoint available", "day6_accounting_available", "short", "stat"),
    (
        "Provider call latency p95",
        'day6_llm_latency_seconds{quantile="0.95"}',
        "s",
        "timeseries",
    ),
    (
        "Cost per completed call",
        'day6_llm_spend_usd_total / on(workload) day6_gateway_events_total{event="completion"}',
        "currencyUSD",
        "timeseries",
    ),
    (
        "Accounting reconciliation delta",
        "day6_llm_spend_usd_total - day6_key_spend_usd",
        "currencyUSD",
        "timeseries",
    ),
]


def dashboard():
    panels = []
    for i, (title, expr, unit, kind) in enumerate(PANELS):
        panels.append(
            {
                "id": i + 1,
                "title": title,
                "type": kind,
                "gridPos": {"x": i % 2 * 12, "y": i // 2 * 8, "w": 12, "h": 8},
                "datasource": {"type": "prometheus", "uid": "prometheus"},
                "targets": [
                    {
                        "refId": "A",
                        "expr": expr,
                        "legendFormat": "{{workload}} {{model}} {{direction}} {{event}}",
                    }
                ],
                "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
                "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
            }
        )
    return {
        "uid": "insighthub-day6-finops",
        "title": "InsightHub Day06 - LLM Security and Cost",
        "schemaVersion": 39,
        "version": 1,
        "tags": ["insighthub", "day6", "finops"],
        "refresh": "10s",
        "time": {"from": "now-1h", "to": "now"},
        "panels": panels,
        "description": "Local catalog-estimated gateway cost, persistent key budgets, and sanitized policy decisions. Not provider invoice. Cost per completion is transport success, not semantic correctness.",
    }


def main():
    data = dashboard()
    path = ROOT / "observability/day6/llm-cost.json"
    path.write_text(json.dumps(data, indent=2))
    container = {
        "name": "cost-exporter",
        "image": "insighthub-gateway:day6",
        "imagePullPolicy": "IfNotPresent",
        "command": [
            "python",
            "-m",
            "uvicorn",
            "day6_exporter:app",
            "--host",
            "0.0.0.0",
            "--port",
            "9091",
            "--no-access-log",
        ],
        "env": [
            {"name": "LITELLM_MASTER_KEY", **secretref("LITELLM_MASTER_KEY")},
            {"name": "DAY6_AUDIT_PATH", "value": "/ledger/audit.jsonl"},
        ],
        "volumeMounts": [{"name": "ledger", "mountPath": "/ledger", "readOnly": True}],
        "ports": [{"name": "cost-metrics", "containerPort": 9091}],
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
        },
        "resources": {
            "requests": {"cpu": "25m", "memory": "64Mi"},
            "limits": {"cpu": "250m", "memory": "256Mi"},
        },
        "readinessProbe": {
            "httpGet": {"path": "/healthz", "port": 9091},
            "periodSeconds": 5,
        },
    }
    kubectl(
        "patch",
        "deployment",
        "day6-gateway",
        "--type=strategic",
        "-p",
        json.dumps({"spec": {"template": {"spec": {"containers": [container]}}}}),
    )
    apply(
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": "day6-cost", "labels": {"app": "day6-cost"}},
            "spec": {
                "selector": {"app": "day6-gateway"},
                "ports": [{"name": "metrics", "port": 9091, "targetPort": 9091}],
            },
        }
    )
    apply(
        {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "ServiceMonitor",
            "metadata": {"name": "day6-cost", "labels": {"release": "kube-prom-stack"}},
            "spec": {
                "selector": {"matchLabels": {"app": "day6-cost"}},
                "endpoints": [{"port": "metrics", "interval": "15s"}],
            },
        }
    )
    apply(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "day6-cost-dashboard",
                "namespace": NS,
                "labels": {"grafana_dashboard": "1"},
            },
            "data": {"day6-cost.json": json.dumps(data)},
        }
    )
    apply(
        {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {
                "name": "day6-budget",
                "labels": {"release": "kube-prom-stack"},
            },
            "spec": {
                "groups": [
                    {
                        "name": "day6-finops",
                        "rules": [
                            {
                                "alert": "Day6KeyBudgetNearLimit",
                                "expr": "day6_key_spend_usd / day6_key_budget_usd >= 0.8",
                                "for": "30s",
                                "labels": {
                                    "severity": "warning",
                                    "scope": "day6-local",
                                },
                                "annotations": {
                                    "summary": "Day06 workload is at or above 80% of its measured key budget"
                                },
                            }
                        ],
                    }
                ]
            },
        }
    )
    kubectl("rollout", "status", "deployment/day6-gateway", "--timeout=180s")
    print("Dashboard UID insighthub-day6-finops installed")


if __name__ == "__main__":
    main()
