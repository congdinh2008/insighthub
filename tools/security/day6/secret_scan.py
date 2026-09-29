#!/usr/bin/env python3
"""Reject any known runtime credential in public evidence without printing its value."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
values = set()
for name in ("ZENLAYER_API_KEY", "DAY6_ZENLAYER_API_KEY"):
    if os.environ.get(name):
        values.add(os.environ[name])
for filename in ("keys.json", "infrastructure.json", "grafana-login.json"):
    path = ROOT / "tmp/day6" / filename
    if not path.exists():
        continue
    for key, value in json.loads(path.read_text()).items():
        if filename == "keys.json" or "KEY" in key or "password" in key.lower():
            if isinstance(value, str) and len(value) >= 8:
                values.add(value)
failures = []
for item in sys.argv[1:]:
    root = Path(item)
    files = list(root.rglob("*")) if root.is_dir() else [root]
    for path in files:
        if path.is_file() and any(
            secret.encode() in path.read_bytes() for secret in values
        ):
            failures.append(str(path))
if failures:
    print("Known credential found in public artifact paths:", *failures, sep="\n")
    raise SystemExit(1)
print("Known-credential scan passed")
