#!/usr/bin/env python3
"""Bounded gateway coding workflow; untrusted code runs only in a networkless container."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).with_name("task.py")
CHECK = Path(__file__).with_name("check.py")
IMAGE = "python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea"


def validate_patch(patch):
    if not isinstance(patch, str) or not 0 < len(patch) < 12000:
        raise ValueError("patch size")
    if any(
        x in patch
        for x in [
            "GIT binary patch",
            "new file mode",
            "deleted file mode",
            "old mode",
            "new mode",
            "rename from",
            "rename to",
            "copy from",
            "copy to",
        ]
    ):
        raise ValueError("patch metadata")
    headers = re.findall(r"^(?:---|\+\+\+) (.*)$", patch, re.M)
    if headers != ["a/task.py", "b/task.py"]:
        raise ValueError("patch path allowlist")
    diffs = re.findall(r"^diff --git (.*)$", patch, re.M)
    if diffs and diffs != ["a/task.py b/task.py"]:
        raise ValueError("diff path allowlist")
    if len(re.findall(r"^@@ ", patch, re.M)) < 1:
        raise ValueError("missing hunk")
    return patch.rstrip() + "\n"


def main():
    keys = json.loads((ROOT / "tmp/day6/keys.json").read_text())
    prompt = (
        "Fix only task.py. Correct billing so cached tokens replace regular input tokens, never double-charge. "
        "Reject non-integer/bool/negative usage and cached_tokens > input_tokens with ValueError. "
        "Return ONLY a valid unified diff for a/task.py and b/task.py, including correct hunk line counts. No Markdown fences.\n"
        "<task.py>\n"
        + TASK.read_text()
        + "</task.py>\n<acceptance tests>\n"
        + CHECK.read_text()
        + "</acceptance tests>"
    )
    started = time.monotonic()
    with httpx.Client(timeout=90, trust_env=False) as client:
        response = client.post(
            os.environ.get("DAY6_GATEWAY_URL", "http://127.0.0.1:14010")
            + "/v1/chat/completions",
            headers={"Authorization": "Bearer " + keys["coding"]},
            json={
                "model": "coding-chat",
                "temperature": 0,
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "system",
                        "content": "You review code and return bounded patches. You have no execution tools.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
    patch = validate_patch(data["choices"][0]["message"]["content"])
    folder = ROOT / "docs/evidence/day6/coding"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "proposed.patch").write_text(patch)
    with tempfile.TemporaryDirectory(prefix="coding-", dir=ROOT / "tmp/day6") as tmp:
        scratch = Path(tmp)
        (scratch / "task.py").write_text(TASK.read_text())
        (scratch / "check.py").write_text(CHECK.read_text())
        for file in scratch.iterdir():
            if file.is_symlink():
                raise ValueError("symlink not allowed")
        subprocess.run(
            ["git", "apply", "--recount", "--check", "-"],
            cwd=scratch,
            input=patch,
            text=True,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "apply", "--recount", "-"],
            cwd=scratch,
            input=patch,
            text=True,
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--cpus",
                "1",
                "--memory",
                "128m",
                "--user",
                "65534:65534",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                "-v",
                str(scratch) + ":/work:ro",
                "-w",
                "/work",
                IMAGE,
                "python",
                "check.py",
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
    evidence = {
        "model": data["model"],
        "provider_request_id": data["id"],
        "usage": data["usage"],
        "gateway_request_id": response.headers.get("x-litellm-call-id"),
        "exit_code": result.returncode,
        "test_output": result.stdout,
        "duration_seconds": time.monotonic() - started,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "sandbox": {
            "network": "none",
            "read_only": True,
            "user": "65534",
            "memory": "128m",
            "allowlist": ["task.py"],
        },
    }
    (folder / "result.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence))
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
