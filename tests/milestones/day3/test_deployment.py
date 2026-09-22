"""Static chart and workflow contracts that support Day 03 runtime evidence."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml


ROOT = Path(os.environ.get("INSIGHTHUB_REPO_ROOT", Path(__file__).parents[3])).resolve()
CHART = ROOT / "deploy" / "helm" / "insighthub"


def render(*values: str) -> list[dict[str, object]]:
    command = ["helm", "template", "insighthub", str(CHART), "--namespace", "insighthub-dev"]
    for path in values:
        command.extend(["-f", str(CHART / path)])
    if "values-dev.yaml" in values:
        command.extend(
            [
                "--set",
                "awsSecrets.secretArn=arn:aws:secretsmanager:ap-southeast-1:123456789012:secret:insighthub/dev/application-ABCDEF",
                "--set-string",
                "ingress.host=",
            ]
        )
    result = subprocess.run(
        command, cwd=ROOT, check=False, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return [item for item in yaml.safe_load_all(result.stdout) if item]


def test_local_chart_has_five_components_and_probes() -> None:
    resources = render("values-local.yaml")
    workloads = {
        item["metadata"]["name"]: item
        for item in resources
        if item["kind"] in {"Deployment", "StatefulSet"}
    }
    assert set(workloads) == {
        "insighthub-api",
        "insighthub-ingestion-worker",
        "insighthub-web",
        "postgres",
        "redis",
    }
    for name in ("insighthub-api", "insighthub-ingestion-worker", "insighthub-web"):
        container = workloads[name]["spec"]["template"]["spec"]["containers"][0]
        assert {"startupProbe", "readinessProbe", "livenessProbe"} <= set(container)
        assert container["resources"]["requests"]
        assert container["resources"]["limits"]


def test_cloud_chart_uses_managed_data_and_irsa_secret() -> None:
    resources = render("values-dev.yaml")
    kinds = {(item["kind"], item["metadata"]["name"]) for item in resources}
    assert ("StatefulSet", "postgres") not in kinds
    assert ("StatefulSet", "redis") not in kinds
    assert ("SecretProviderClass", "insighthub-runtime") in kinds
    assert ("Job", "insighthub-database-migration-0-3-0") in kinds
    assert ("Ingress", "insighthub") in kinds
    assert ("HorizontalPodAutoscaler", "insighthub-api") in kinds

    ingress = next(item for item in resources if item["kind"] == "Ingress")
    assert "host" not in ingress["spec"]["rules"][0]
    services = {
        item["metadata"]["name"]: item
        for item in resources
        if item["kind"] == "Service"
    }
    assert services["insighthub-api"]["metadata"]["annotations"][
        "alb.ingress.kubernetes.io/healthcheck-path"
    ] == "/healthz"
    assert services["insighthub-web"]["metadata"]["annotations"][
        "alb.ingress.kubernetes.io/healthcheck-path"
    ] == "/api/health"


def test_workflow_has_required_gates() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "iac.yml").read_text())
    jobs = workflow["jobs"]
    assert {
        "fmt",
        "lint",
        "security-scan",
        "policy-check",
        "plan",
        "cost-estimate",
        "apply",
    } <= set(jobs)
    assert jobs["apply"]["environment"] == "insighthub-dev"
    assert jobs["apply"]["permissions"]["id-token"] == "write"
    assert jobs["cost-estimate"]["permissions"]["pull-requests"] == "write"

    workflow_text = (ROOT / ".github" / "workflows" / "iac.yml").read_text()
    assert "name: verification-source" in workflow_text
    assert "infracost comment github" in workflow_text
    assert "scripts/verify.py smoke" in workflow_text
    assert "github.event.label.name == 'lab-deploy'" in workflow_text
    assert "terraform -chdir=infra/edge apply" in workflow_text
    assert "repository_key" in workflow_text and "'.[$key]'" in workflow_text

    edge = (ROOT / "infra" / "edge" / "main.tf").read_text()
    assert 'resource "aws_cloudfront_distribution" "insighthub"' in edge
    assert "cloudfront_default_certificate = true" in edge
