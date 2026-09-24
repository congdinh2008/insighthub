"""Static Day 04 contracts before collecting live baseline and incident evidence."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("INSIGHTHUB_REPO_ROOT", Path(__file__).parents[3])).resolve()
APP_CHART = ROOT / "deploy" / "helm" / "insighthub"
OBS_CHART = ROOT / "observability" / "chart"


def render(chart: Path, *arguments: str) -> list[dict[str, object]]:
    result = subprocess.run(
        ["helm", "template", "test", str(chart), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return [document for document in yaml.safe_load_all(result.stdout) if document]


def test_application_chart_exposes_bounded_exporters() -> None:
    resources = render(
        APP_CHART,
        "-f",
        str(APP_CHART / "values-local.yaml"),
        "-f",
        str(APP_CHART / "values-day4-local.yaml"),
    )
    workloads = {
        item["metadata"]["name"]: item
        for item in resources
        if item["kind"] in {"Deployment", "StatefulSet"}
    }
    services = {
        item["metadata"]["name"]: item
        for item in resources
        if item["kind"] == "Service"
    }
    postgres = workloads["postgres"]["spec"]["template"]["spec"]["containers"]
    redis = workloads["redis"]["spec"]["template"]["spec"]["containers"]
    assert {container["name"] for container in postgres} == {
        "postgres",
        "postgres-exporter",
    }
    assert {container["name"] for container in redis} == {"redis", "redis-exporter"}
    for exporter in (postgres[1], redis[1]):
        assert exporter["resources"]["requests"]
        assert exporter["resources"]["limits"]
        assert exporter["securityContext"]["readOnlyRootFilesystem"] is True
    redis_environment = {item["name"]: item["value"] for item in redis[1]["env"]}
    assert redis_environment["REDIS_EXPORTER_CHECK_SINGLE_KEYS"] == (
        "db0=insighthub:ingestion"
    )
    assert (
        services["postgres"]["metadata"]["labels"]["app.kubernetes.io/component"]
        == "postgres"
    )
    assert (
        services["redis"]["metadata"]["labels"]["app.kubernetes.io/component"]
        == "redis"
    )


def test_observability_chart_selects_all_required_signals() -> None:
    resources = render(
        OBS_CHART,
        "--namespace",
        "monitoring",
        "-f",
        str(ROOT / "observability" / "values-day4-local.yaml"),
        "--set",
        "alerting.slack.enabled=true",
    )
    monitors = [item for item in resources if item["kind"] == "ServiceMonitor"]
    assert {item["metadata"]["name"] for item in monitors} == {
        "insighthub-api",
        "insighthub-ingestion-worker",
        "insighthub-postgres",
        "insighthub-redis",
    }
    assert all(
        item["spec"]["namespaceSelector"]["matchNames"] == ["insighthub-dev"]
        for item in monitors
    )
    assert all(
        item["metadata"]["labels"]["release"] == "kube-prom-stack" for item in monitors
    )
    monitor_by_name = {item["metadata"]["name"]: item for item in monitors}
    assert (
        monitor_by_name["insighthub-api"]["spec"]["endpoints"][0]["honorLabels"] is True
    )
    assert (
        monitor_by_name["insighthub-ingestion-worker"]["spec"]["endpoints"][0][
            "honorLabels"
        ]
        is True
    )
    kinds = {item["kind"] for item in resources}
    assert {"PrometheusRule", "AlertmanagerConfig", "ConfigMap", "Deployment"} <= kinds
    alert_config = next(
        item for item in resources if item["kind"] == "AlertmanagerConfig"
    )
    selector = alert_config["spec"]["receivers"][0]["slackConfigs"][0]["apiURL"]
    assert selector == {"name": "insighthub-alertmanager-slack", "key": "api-url"}


def test_dashboard_has_exact_required_panel_topics_and_real_queries() -> None:
    dashboard = json.loads(
        (OBS_CHART / "files" / "insighthub-dashboard.json").read_text()
    )
    assert len(dashboard["panels"]) == 9
    assert all(
        panel.get("targets")
        and all(target.get("expr", "").strip() for target in panel["targets"])
        for panel in dashboard["panels"]
    )
    titles = " ".join(panel["title"].lower() for panel in dashboard["panels"])
    for topic in (
        "request rate",
        "error ratio",
        "duration",
        "queue depth",
        "tokens",
        "latency p95",
        "cost",
        "resources",
        "deployment",
    ):
        assert topic in titles
    assert dashboard["annotations"]["list"][0]["expr"]


def test_rules_have_three_anomalies_and_one_hour_offset_baselines() -> None:
    rules = yaml.safe_load((OBS_CHART / "files" / "anomaly-rules.yaml").read_text())
    rule_list = [rule for group in rules["groups"] for rule in group["rules"]]
    alerts = [rule for rule in rule_list if "alert" in rule]
    assert {rule["alert"] for rule in alerts} == {
        "InsightHubLLMLatencyAnomaly",
        "InsightHubQueueBacklogAnomaly",
        "InsightHubErrorBurstAnomaly",
    }
    assert all(rule["for"] == "2m" for rule in alerts)
    expressions = "\n".join(str(rule["expr"]) for rule in rule_list)
    assert expressions.count("[1h] offset 10m") >= 6
    assert "count_over_time" in expressions
    assert "redis_key_size" in expressions
    assert "ih:llm_p95_seconds == ih:llm_p95_seconds" in expressions
    assert "or vector(0)" in expressions
    assert "count_over_time(ih:http_requests_5m[1h] offset 10m)" in expressions
    assert "max(redis_up == 1) * 0" in expressions
    assert "max(redis_up) == 1" in expressions
    assert "count_over_time((ih:llm_p95_seconds == ih:llm_p95_seconds)[1h:1m] offset 10m)" in expressions


def test_incident_scripts_are_bounded_and_recoverable() -> None:
    chaos = ROOT / "scripts" / "chaos"
    expected = {
        "inject-llm-latency.sh",
        "inject-queue-backlog.sh",
        "inject-error-burst.sh",
    }
    assert expected <= {path.name for path in chaos.glob("*.sh")}
    for name in expected:
        source = (chaos / name).read_text()
        assert "start|stop" in source
        assert "day4_require_lab" in source
        assert "trap" in source
    assert "replicas=0" in (chaos / "inject-queue-backlog.sh").read_text()
    assert (
        "DAY4_DOCUMENTS must be 11..50"
        in (chaos / "inject-queue-backlog.sh").read_text()
    )
