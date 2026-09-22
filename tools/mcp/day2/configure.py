#!/usr/bin/env python3
"""Generate Day 02 launch definitions and install project-scoped host configs."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = Path(os.environ.get("INSIGHTHUB_DAY2_STATE", ROOT / "tmp/day2")).resolve()
PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "insighthub-day2-lab")
DOCKER_IMAGE = "docker:29.7.2-cli@sha256:3f4743208d2338c934d7b8bcfbe1bb54c0b2355c510ad5e0f31c0c4a54bd704e"
FILESYSTEM_IMAGE = "mcp/filesystem@sha256:35fcf0217ca0d5bf7b0a5bd68fb3b89e08174676c0e0b4f431604512cf7b3f67"
TOOLKIT_PROFILE_ID = "insighthub-dev"
TOOLKIT_PROFILE_NAME = "InsightHub Development"
FILESYSTEM_TOOLS = ("read_file", "list_directory", "list_allowed_directories")


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def filesystem_definition():
    template = Path(__file__).with_name("toolkit") / "filesystem.json.template"
    return json.loads(
        template.read_text().replace("__SOURCE_VIEW__", str(STATE / "source-view"))
    )


def install_toolkit_profile():
    """Install the project-owned, read-only Filesystem server and Docker profile."""
    if not (STATE / "source-view").is_dir():
        raise SystemExit("Generate tmp/day2/source-view before installing the profile")
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker CLI is required for the MCP Toolkit profile")
    if sys.platform == "darwin" and not shutil.which("socat"):
        raise SystemExit("Docker MCP Gateway on macOS requires socat in PATH")

    definition = filesystem_definition()
    if definition.get("image") != FILESYSTEM_IMAGE:
        raise SystemExit("Filesystem image digest does not match configure.py")
    catalog_path = Path.home() / ".docker/mcp/catalogs/insighthub/filesystem.json"
    if catalog_path.is_symlink() or catalog_path.parent.is_symlink():
        raise SystemExit("Refusing a symlink as Docker MCP catalog path")
    if catalog_path.exists():
        current = json.loads(catalog_path.read_text())
        if (
            current.get("name") != "filesystem"
            or current.get("metadata", {}).get("owner") != "insighthub"
        ):
            raise SystemExit("Refusing to overwrite an unrelated Docker MCP server")
    write_json(catalog_path, definition)
    gateway_catalog_path = (
        Path.home() / ".docker/mcp/catalogs/insighthub-filesystem.json"
    )
    if gateway_catalog_path.is_symlink():
        raise SystemExit("Refusing a symlink as Docker MCP gateway catalog")
    if gateway_catalog_path.exists():
        current = json.loads(gateway_catalog_path.read_text())
        if current.get("name") != "insighthub-filesystem":
            raise SystemExit("Refusing to overwrite an unrelated Docker MCP catalog")
    write_json(
        gateway_catalog_path,
        {
            "version": 3,
            "name": "insighthub-filesystem",
            "displayName": "InsightHub Filesystem",
            "registry": {"filesystem": definition},
        },
    )

    profiles = json.loads(run(docker, "mcp", "profile", "list", "--format", "json"))
    ids = {item["id"] for item in profiles}
    if TOOLKIT_PROFILE_ID not in ids:
        subprocess.run(
            [
                docker,
                "mcp",
                "profile",
                "create",
                "--name",
                TOOLKIT_PROFILE_NAME,
                "--id",
                TOOLKIT_PROFILE_ID,
                "--server",
                "file://insighthub/filesystem.json",
            ],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [
                docker,
                "mcp",
                "profile",
                "tools",
                TOOLKIT_PROFILE_ID,
                "--disable-all",
                "filesystem",
                *sum(
                    (["--enable", f"filesystem.{tool}"] for tool in FILESYSTEM_TOOLS),
                    [],
                ),
            ],
            cwd=ROOT,
            check=True,
        )

    profile = json.loads(
        run(docker, "mcp", "profile", "show", TOOLKIT_PROFILE_ID, "--format", "json")
    )
    servers = profile.get("servers", [])
    expected_volume = f"{STATE / 'source-view'}:/project:ro"
    if (
        profile.get("id") != TOOLKIT_PROFILE_ID
        or profile.get("name") != TOOLKIT_PROFILE_NAME
        or len(servers) != 1
        or servers[0].get("snapshot", {}).get("server", {}).get("name") != "filesystem"
        or servers[0].get("image") != FILESYSTEM_IMAGE
        or servers[0].get("snapshot", {}).get("server", {}).get("volumes")
        != [expected_volume]
        or servers[0].get("snapshot", {}).get("server", {}).get("disableNetwork")
        is not True
        or set(servers[0].get("tools") or ()) != set(FILESYSTEM_TOOLS)
    ):
        raise SystemExit(
            "Existing insighthub-dev profile differs from the managed read-only profile"
        )
    write_json(
        STATE / "toolkit-profile.json",
        {
            "id": profile["id"],
            "name": profile["name"],
            "server": "filesystem",
            "image": FILESYSTEM_IMAGE,
            "volume": expected_volume,
            "disableNetwork": True,
            "tools": list(FILESYSTEM_TOOLS),
        },
    )
    print("Installed and verified Docker MCP profile insighthub-dev.")


def ensure_docker_operations_image():
    """Ensure POCI can start its immutable Docker CLI image without fallback."""
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker CLI is required for Docker operations MCP")
    present = subprocess.run(
        [docker, "image", "inspect", DOCKER_IMAGE],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if present.returncode:
        subprocess.run([docker, "pull", DOCKER_IMAGE], cwd=ROOT, check=True)
    image_id = run(docker, "image", "inspect", DOCKER_IMAGE, "--format", "{{.Id}}")
    write_json(
        STATE / "docker-operations-image.json",
        {"reference": DOCKER_IMAGE, "image_id": image_id},
    )


def prepare_codex_config(generated):
    servers = tomllib.loads(generated)["mcp_servers"]
    target = ROOT / ".codex/config.toml"
    if target.is_symlink() or target.parent.is_symlink():
        raise SystemExit("Refusing a symlink as project Codex config")
    begin = "# BEGIN InsightHub Day 02 MCP (generated)"
    end = "# END InsightHub Day 02 MCP"
    current = target.read_text() if target.exists() else ""
    tomllib.loads(current)
    if begin in current or end in current:
        if current.count(begin) != 1 or current.count(end) != 1:
            raise SystemExit("Invalid managed Day 02 config block")
        before, block = current.split(begin)
        _, after = block.split(end)
        remaining = before + after
    else:
        remaining = current
    retained = tomllib.loads(remaining)
    if set(retained.get("mcp_servers", {})) & set(servers):
        raise SystemExit("InsightHub MCP names already exist outside the managed block")
    merged = remaining.rstrip() + "\n\n" + begin + "\n" + generated + "\n" + end + "\n"
    expected = dict(retained)
    expected["mcp_servers"] = {**retained.get("mcp_servers", {}), **servers}
    if tomllib.loads(merged) != expected:
        raise SystemExit("Project config merge would alter unrelated settings")
    return target, merged.lstrip("\n")


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SystemExit("Duplicate key in project MCP JSON; review before setup")
        value[key] = item
    return value


def prepare_json_config(relative_path, servers, *, claude=False):
    target = ROOT / relative_path
    if target.is_symlink() or target.parent.is_symlink():
        raise SystemExit("Refusing a symlink as project MCP config")
    current = (
        json.loads(target.read_text(), object_pairs_hook=unique_pairs)
        if target.exists()
        else {}
    )
    if not isinstance(current, dict) or not isinstance(
        current.get("mcpServers", {}), dict
    ):
        raise SystemExit("Project MCP config must contain an mcpServers object")
    existing = current.get("mcpServers", {})
    generated = {
        name: {
            **({"type": "stdio"} if claude else {}),
            **{key: server[key] for key in ("command", "args", "env")},
        }
        for name, server in servers.items()
    }
    for name in existing.keys() & generated.keys():
        if existing[name] != generated[name]:
            raise SystemExit(
                f"Conflicting InsightHub MCP entry in {relative_path}; review before setup"
            )
    current["mcpServers"] = {**existing, **generated}
    return target, json.dumps(current, indent=2) + "\n"


def install_project_config():
    generated = (STATE / "codex.config.toml").read_text().strip()
    servers = tomllib.loads(generated)["mcp_servers"]
    # Validate every merge before writing; never silently replace another server.
    configs = [
        prepare_codex_config(generated),
        prepare_json_config(".mcp.json", servers, claude=True),
        prepare_json_config(".agents/mcp_config.json", servers),
    ]
    for target, content in configs:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        target.chmod(0o600)
        print(f"Installed five MCP servers in project {target.relative_to(ROOT)}.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-config-only",
        action="store_true",
        help="Install all three host configs from existing definitions without changing the lab",
    )
    parser.add_argument(
        "--toolkit-profile-only",
        action="store_true",
        help="Install and verify the Docker MCP Toolkit profile from an existing source snapshot",
    )
    options = parser.parse_args()
    if options.project_config_only:
        install_project_config()
        return
    if options.toolkit_profile_only:
        install_toolkit_profile()
        return
    if not re.fullmatch(r"insighthub-day2-[a-z0-9-]+", PROJECT):
        raise SystemExit("Use an explicit insighthub-day2-* lab project")
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    admin = STATE / "admin.kubeconfig"
    kubectl = shutil.which("kubectl")
    if not kubectl or not admin.is_file():
        raise SystemExit("Create the dedicated kind cluster first")
    base = [kubectl, "--kubeconfig", str(admin), "--context", "kind-insighthub-day2"]
    for name in ("rbac.yml", "sample.yml"):
        subprocess.run(
            base + ["apply", "-f", str(ROOT / "infra/k8s/mcp-readonly" / name)],
            check=True,
        )
    subprocess.run(
        base
        + [
            "wait",
            "--for=condition=Ready",
            "pod/mcp-sample",
            "-n",
            "insighthub",
            "--timeout=120s",
        ],
        check=True,
    )
    cluster = json.loads(
        run(*base, "config", "view", "--raw", "--minify", "-o", "json")
    )["clusters"][0]["cluster"]
    token = run(
        *base, "create", "token", "mcp-readonly", "-n", "insighthub", "--duration=6h"
    )
    kubeconfig = STATE / "readonly.kubeconfig"
    write_json(
        kubeconfig,
        {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [{"name": "day2", "cluster": cluster}],
            "users": [{"name": "mcp-readonly", "user": {"token": token}}],
            "contexts": [
                {
                    "name": "insighthub-day2-readonly",
                    "context": {
                        "cluster": "day2",
                        "user": "mcp-readonly",
                        "namespace": "insighthub",
                    },
                }
            ],
            "current-context": "insighthub-day2-readonly",
        },
    )
    kubeconfig.chmod(0o600)
    admin.chmod(0o600)

    # Copy source only: no Git internals, ignored runtime files or private .env.
    view = STATE / "source-view"
    if view.is_symlink():
        raise SystemExit("Refusing a symlink as generated source-view")
    if view.exists():
        shutil.rmtree(view)
    view.mkdir(exist_ok=True)
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    source_hash = hashlib.sha256()
    for name in sorted(set(names)):
        if not name or name.startswith(("docs/evidence/", "evidence/", ".codex/")):
            continue
        original = ROOT / name
        if (
            original.is_symlink()
            or not original.is_file()
            or original.name.startswith(".env")
            and not original.name.endswith(("example", "template"))
        ):
            continue
        data = original.read_bytes()
        source_hash.update(name.encode() + b"\0" + data)
        target = view / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (view / "DAY2_CANARY.txt").write_text("read-only canary\n")
    write_json(
        STATE / "source-view.json",
        {
            "sha256": source_hash.hexdigest(),
            "purpose": "MCP project source snapshot; no runtime secrets",
        },
    )
    install_toolkit_profile()
    ensure_docker_operations_image()

    # Docker MCP Gateway POCI mechanism, narrowed to constant read commands.
    # No model-controlled argv, paths, Go templates, container IDs or shell.
    commands = {
        "list_containers": [
            "ps",
            "-a",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
            "--format",
            "json",
        ],
        "get_diagnostic_logs": ["logs", "--tail", "100", f"{PROJECT}-debug-case-1"],
        "get_worker_logs": ["logs", "--tail", "50", f"{PROJECT}-ingestion-worker-1"],
    }
    catalog = {
        "version": 3,
        "name": "insighthub-operations",
        "displayName": "InsightHub Docker operations",
        "registry": {
            "docker-operations": {
                "name": "docker-operations",
                "type": "poci",
                "tools": [
                    {
                        "name": name,
                        "description": f"Read the selected InsightHub lab: {name}",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        },
                        "container": {
                            "image": DOCKER_IMAGE,
                            "command": [
                                "--host",
                                "tcp://host.docker.internal:23752",
                                *argv,
                            ],
                        },
                    }
                    for name, argv in commands.items()
                ],
            }
        },
    }
    catalog_path = Path.home() / ".docker/mcp/catalogs/insighthub-operations.json"
    if catalog_path.exists():
        old = json.loads(catalog_path.read_text())
        if old.get("name") != "insighthub-operations":
            raise SystemExit("Refusing to overwrite an unrelated Docker catalog")
    write_json(catalog_path, catalog)
    write_json(STATE / "docker-catalog.json", catalog)
    for name in ("gateway-config.json", "gateway-registry.json", "gateway-tools.json"):
        write_json(STATE / name, {})
    (STATE / "gateway-secrets.env").write_text("")

    python = str(Path(sys.executable).resolve())
    launcher = str(Path(__file__).with_name("launch.py"))
    enabled = {
        "filesystem": list(FILESYSTEM_TOOLS),
        "docker": list(commands),
        "kubernetes": ["pods_list_in_namespace", "pods_get", "pods_log", "events_list"],
        "prometheus": ["query", "range_query", "list_targets"],
        "insighthub": ["insighthub_health", "insighthub_list_documents"],
    }
    servers = {
        ("docker-operations" if name == "docker" else name): {
            "command": python,
            "args": [launcher, name],
            "env": {"INSIGHTHUB_DAY2_STATE": str(STATE)},
            "enabled_tools": names,
            "startup_timeout_sec": 60,
            "tool_timeout_sec": 30,
        }
        for name, names in enabled.items()
    }
    write_json(STATE / "servers.json", servers)
    toml = []
    for name, value in servers.items():
        toml += [f"[mcp_servers.{name}]"]
        toml += [
            f"{key} = {json.dumps(val)}" for key, val in value.items() if key != "env"
        ]
        toml += [
            f"[mcp_servers.{name}.env]",
            f"INSIGHTHUB_DAY2_STATE = {json.dumps(str(STATE))}",
            "",
        ]
    (STATE / "codex.config.toml").write_text("\n".join(toml))
    install_project_config()
    write_json(
        STATE / "inspector.json",
        {
            "mcpServers": {
                name: {
                    k: v for k, v in server.items() if k in {"command", "args", "env"}
                }
                for name, server in servers.items()
            }
        },
    )
    print(
        "Generated five launch definitions and configs for Codex, Claude and Antigravity."
    )


if __name__ == "__main__":
    main()
