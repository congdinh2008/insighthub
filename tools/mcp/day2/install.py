#!/usr/bin/env python3
"""Install exact upstream binaries, verifying release checksums before extraction."""

import hashlib
import json
import os
import platform
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = Path(os.environ.get("INSIGHTHUB_DAY2_STATE", ROOT / "tmp/day2")).resolve()


def main():
    system = platform.system().lower()
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64"}.get(
        platform.machine()
    )
    if system not in {"darwin", "linux"} or arch is None:
        raise SystemExit("Supported: macOS/Linux arm64/amd64; use WSL2 on Windows")
    manifest = json.loads((Path(__file__).with_name("artifacts.lock.json")).read_text())
    target = STATE / "bin"
    target.mkdir(parents=True, exist_ok=True)
    names = {
        "kind": f"kind-{system}-{arch}",
        "kubernetes": f"kubernetes-mcp-server-{system}-{arch}",
        "prometheus": f"prometheus-mcp-server_0.18.0_{system}_{'all' if system == 'darwin' else arch}.tar.gz",
        "gateway": f"docker-mcp-{system}-{arch}.tar.gz",
    }
    for key, filename in names.items():
        artifact = next(
            a for a in manifest["artifacts"][key]["assets"] if a["name"] == filename
        )
        destination = target / filename
        if (
            not destination.exists()
            or hashlib.sha256(destination.read_bytes()).hexdigest()
            != artifact["sha256"]
        ):
            with urllib.request.urlopen(artifact["url"], timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != artifact["sha256"]:
                raise SystemExit(f"Checksum mismatch: {filename}")
            destination.write_bytes(data)
        if filename.endswith(".tar.gz"):
            with tarfile.open(destination) as archive:
                binary = "docker-mcp" if key == "gateway" else "prometheus-mcp-server"
                candidates = [
                    m
                    for m in archive.getmembers()
                    if m.isfile() and Path(m.name).name == binary
                ]
                if len(candidates) != 1:
                    raise SystemExit(f"Unexpected {key} release layout")
                reader = archive.extractfile(candidates[0])
                assert reader is not None
                executable = target / binary
                executable.write_bytes(reader.read())
        else:
            executable = target / ("kind" if key == "kind" else "kubernetes-mcp-server")
            executable.write_bytes(destination.read_bytes())
        executable.chmod(0o755)
        print(
            f"Verified {key}: {manifest['artifacts'][key]['version']} ({system}/{arch})"
        )


if __name__ == "__main__":
    main()
