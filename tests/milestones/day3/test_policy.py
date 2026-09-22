"""Day 03 policy contract. Conftest evaluates real Rego, not keyword proxies."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(os.environ.get("INSIGHTHUB_REPO_ROOT", Path(__file__).parents[3])).resolve()
POLICY = ROOT / "infra" / "policies" / "terraform"
FIXTURES = ROOT / "infra" / "policies" / "fixtures"


def conftest() -> str:
    configured = os.environ.get("CONFTEST_BIN")
    candidate = configured or shutil.which("conftest")
    if not candidate:
        local = ROOT / "tmp" / "day3" / "bin" / "conftest"
        candidate = str(local) if local.is_file() else None
    assert candidate, "Conftest is required; run make tools-day3"
    return candidate


def run_policy(fixture: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [conftest(), "test", "--policy", str(POLICY), str(FIXTURES / fixture)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_policy_allows_valid() -> None:
    result = run_policy("valid-plan.json")
    assert result.returncode == 0, result.stdout + result.stderr


def test_policy_denies_unsafe() -> None:
    result = run_policy("unsafe-plan.json")
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "exposes RDS publicly" in output
    assert "must encrypt RDS storage" in output
    assert "world-open ingress" in output
    assert "missing required tags" in output
