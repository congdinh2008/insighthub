"""Install pinned Day 03 IaC binaries into tmp/day3/bin after checksum verification."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("toolchain.lock.json")
DESTINATION = ROOT / "tmp" / "day3" / "bin"


def platform_key() -> str:
    operating_system = platform.system().lower()
    architecture = platform.machine().lower()
    architecture = "arm64" if architecture in {"arm64", "aarch64"} else "amd64"
    key = f"{operating_system}_{architecture}"
    if key not in {"darwin_arm64", "linux_amd64"}:
        raise SystemExit(f"Unsupported Day 03 toolchain platform: {key}")
    return key


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def extract_binary(
    archive: Path, archive_format: str, name: str, target: Path, binary_name: str
) -> None:
    with tempfile.TemporaryDirectory(prefix="insighthub-day3-") as temp:
        directory = Path(temp)
        if archive_format == "zip":
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(directory)
        elif archive_format == "tar.gz":
            with tarfile.open(archive, "r:gz") as bundle:
                bundle.extractall(directory, filter="data")
        else:
            raise SystemExit(f"Unsupported archive format: {archive_format}")
        candidates = [path for path in directory.rglob(binary_name) if path.is_file()]
        if len(candidates) != 1:
            raise SystemExit(f"Expected one {name} binary, found {len(candidates)}")
        shutil.copy2(candidates[0], target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    key = platform_key()
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, metadata in lock["tools"].items():
        target = DESTINATION / name
        asset = metadata["assets"].get(key)
        if not asset:
            raise SystemExit(f"{name} has no pinned asset for {key}")
        if target.is_file():
            continue
        request = urllib.request.Request(asset["url"], headers={"User-Agent": "InsightHub-Day03"})
        with tempfile.NamedTemporaryFile(prefix=f"{name}-", delete=False) as stream:
            archive = Path(stream.name)
            with urllib.request.urlopen(request, timeout=60) as response:
                shutil.copyfileobj(response, stream)
        try:
            actual = digest(archive)
            if actual != asset["sha256"]:
                raise SystemExit(f"Checksum mismatch for {name}: {actual}")
            extract_binary(
                archive, asset["format"], name, target, asset.get("binary", name)
            )
        finally:
            archive.unlink(missing_ok=True)
    checkov = DESTINATION / "checkov"
    checkov.write_text(
        '#!/bin/sh\nexec "$(dirname "$0")/../venv/bin/python" -c '
        "'from checkov.main import Checkov; Checkov().run()' \"$@\"\n",
        encoding="utf-8",
    )
    checkov.chmod(0o755)
    print(str(DESTINATION))


if __name__ == "__main__":
    os.umask(0o077)
    install()
