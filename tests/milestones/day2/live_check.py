"""Exercise vendor MCP servers and independently verify live permission boundaries."""

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "tmp/day2"


def http(path, method="GET"):
    try:
        with urllib.request.urlopen(
            urllib.request.Request(path, method=method), timeout=5
        ) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main():
    calls = json.loads(Path(__file__).with_name("calls.json").read_text())
    timestamp = datetime.now(timezone.utc).isoformat()
    for call in calls["prometheus"]:
        if "timestamp" in call.get("arguments", {}):
            call["arguments"]["timestamp"] = timestamp
    (STATE / "calls.json").write_text(json.dumps(calls, indent=2) + "\n")
    subprocess.run(
        ["node", "tools/mcp/day2/probe.mjs", "all", str(STATE / "calls.json")],
        cwd=ROOT,
        check=True,
    )
    probe = json.loads((STATE / "probe-all.json").read_text())
    records = {row["server"]: row for row in probe["results"]}
    assert len(records) == 5 and all(row["passed"] for row in records.values())

    def output(server, index):
        call = records[server]["calls"][index]
        return "\n".join(
            c.get("text", "") for c in call.get("output", {}).get("content", [])
        ) or call.get("error", "")

    assert "/project" in output("filesystem", 0)
    assert "# InsightHub" in output("filesystem", 1)
    for index in (2, 3):
        assert "outside" in output("filesystem", index).lower()
    assert "unknown tool" in output("filesystem", 4)
    assert (STATE / "source-view/DAY2_CANARY.txt").read_text() == "read-only canary\n"
    assert "insighthub-day2-lab" in output("docker-operations", 0)
    assert "DAY2_CONFIG_" in output("docker-operations", 1)
    assert "unknown tool" in output("docker-operations", 2)
    assert "mcp-sample" in output("kubernetes", 0) and "Running" in output(
        "kubernetes", 0
    )
    assert "DAY2_SAMPLE_READY" in output("kubernetes", 1)
    assert "forbidden" in output("kubernetes", 2) and "mcp-readonly" in output(
        "kubernetes", 2
    )
    assert "unknown tool" in output("kubernetes", 3)
    targets = json.loads(output("prometheus", 0))["activeTargets"]
    assert {t["labels"]["job"] for t in targets if t["health"] == "up"} == {
        "insighthub-api",
        "insighthub-worker",
    }
    query = calls["prometheus"][1]["arguments"]["query"]
    status, body = http(
        "http://127.0.0.1:19092/api/v1/query?"
        + urllib.parse.urlencode({"query": query, "time": timestamp})
    )
    assert status == 200
    samples = json.loads(body)["data"]["result"]
    mcp_result = json.loads(output("prometheus", 1))["result"]
    assert len(samples) == 2
    for sample in samples:
        assert sample["value"][1] == "1" and sample["metric"]["job"] in mcp_result
        assert f"=> {sample['value'][1]} @[" in mcp_result
    assert json.loads(output("prometheus", 2))["result"] == ""
    assert "unknown tool" in output("prometheus", 3)
    assert "additional properties" in output("prometheus", 4)
    assert "insighthub-api" in json.loads(output("prometheus", 5))["result"]
    assert "insighthub-worker" in json.loads(output("prometheus", 5))["result"]
    assert all(json.loads(output("insighthub", 0)).values())
    evidence = {
        "observed_at": timestamp,
        "backend_mode": "live",
        "mcp_calls": sum(len(r["calls"]) for r in records.values()),
        "prometheus_http_samples": samples,
        "kubernetes_permissions": [],
        "docker_denials": [],
    }
    kubectl = [
        "kubectl",
        "--kubeconfig",
        str(STATE / "readonly.kubeconfig"),
        "--context",
        "insighthub-day2-readonly",
    ]
    for verb, resource, namespace, expected in [
        ("get", "pods", "insighthub", "yes"),
        ("get", "pods/log", "insighthub", "yes"),
        ("list", "deployments", "insighthub", "yes"),
        ("delete", "pods", "insighthub", "no"),
        ("create", "pods", "insighthub", "no"),
        ("patch", "deployments", "insighthub", "no"),
        ("create", "pods/exec", "insighthub", "no"),
        ("get", "secrets", "insighthub", "no"),
        ("list", "pods", "kube-system", "no"),
    ]:
        result = subprocess.run(
            kubectl + ["auth", "can-i", verb, resource, "-n", namespace],
            capture_output=True,
            text=True,
        )
        actual = result.stdout.strip()
        assert actual == expected, (verb, resource, actual, result.stderr)
        evidence["kubernetes_permissions"].append(
            {
                "verb": verb,
                "resource": resource,
                "namespace": namespace,
                "actual": actual,
            }
        )
    for method, path in [
        ("POST", "/containers/create"),
        ("DELETE", "/containers/canary"),
        ("GET", "/containers/unrelated/json"),
        ("GET", "/events"),
    ]:
        code, _ = http("http://127.0.0.1:23752" + path, method)
        assert code == 403, (method, path, code)
        evidence["docker_denials"].append(
            {"method": method, "path": path, "status": code}
        )
    status, body = http("http://127.0.0.1:23752/containers/json?all=1&filters={}")
    assert status == 200
    rows = json.loads(body)
    assert rows and all(
        name.startswith("/insighthub-day2-lab-")
        for row in rows
        for name in row["Names"]
    )
    assert all("Labels" not in row and "Command" not in row for row in rows)
    status, body = http(
        "http://127.0.0.1:23752/containers/insighthub-day2-lab-debug-case-1/json"
    )
    assert status == 200 and set(json.loads(body)["Config"]) == {"Tty"}
    evidence["passed"] = True
    (STATE / "live-check.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        "PASS: five live MCP backends, content assertions, SA authorization, bounded Docker API, HTTP/PromQL comparison"
    )


if __name__ == "__main__":
    main()
