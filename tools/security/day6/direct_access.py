#!/usr/bin/env python3
"""Confirm app credentials and direct unauthenticated provider access from its pod."""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).parent))
from local_lab import ROOT, TMP, kubectl

cfg = json.loads((TMP / "infrastructure.json").read_text())
url = cfg["ZENLAYER_BASE_URL"].rstrip("/") + "/models"
code = """import json,os,sys,httpx
from app.core.config import get_settings
s=get_settings()
assert s.litellm_api_key and s.openai_api_key==s.litellm_api_key
assert not any(os.environ.get(k) for k in ["ZENLAYER_API_KEY","GEMINI_API_KEY","ANTHROPIC_API_KEY","LITELLM_MASTER_KEY"])
r=httpx.get(sys.argv[1],timeout=15,trust_env=False,follow_redirects=False)
print(json.dumps({"upstream_credentials_absent":True,"canonical_virtual_key":True,"unauthenticated_provider_status":r.status_code}))
assert r.status_code in (401,403)
"""
result = json.loads(
    kubectl("exec", "deployment/insighthub-api", "--", "python", "-c", code, url)
)
result.update(
    observed_at=time.time(),
    host=urlsplit(url).hostname,
    network_policy="No enforced-CNI claim; endpoint is reachable but unauthenticated access is denied",
)
(ROOT / "docs/evidence/day6/direct-provider-access.json").write_text(
    json.dumps(result, indent=2)
)
print(json.dumps(result))
