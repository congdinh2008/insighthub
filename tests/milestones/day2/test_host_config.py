"""Project config installation preserves unrelated settings and rejects collisions."""

import importlib.util
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "day2_configure", ROOT / "tools/mcp/day2/configure.py"
)
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)
HOST_PATHS = (".codex/config.toml", ".mcp.json", ".agents/mcp_config.json")


class HostConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="day2 học viên ")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        state = self.root / "tmp/day2"
        state.mkdir(parents=True)
        content = (ROOT / "tools/mcp/day2/codex.config.toml.template").read_text()
        content = content.replace("/ABSOLUTE/PATH/TO/insighthub", str(self.root))
        (state / "codex.config.toml").write_text(content)
        self.servers = tomllib.loads(content)["mcp_servers"]
        for name, value in (("ROOT", self.root), ("STATE", state)):
            override = patch.object(configure, name, value)
            override.start()
            self.addCleanup(override.stop)

    def write(self, relative, text):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def snapshot(self):
        return {name: (self.root / name).read_bytes() for name in HOST_PATHS}

    def test_three_hosts_preserve_settings_and_repeated_install(self):
        self.write(".codex/config.toml", 'model = "keep-model"\n')
        other = {"mcpServers": {"keep-server": {"command": "keep-command"}}}
        for name in HOST_PATHS[1:]:
            self.write(name, json.dumps(other))
        configure.install_project_config()
        before = self.snapshot()
        configure.install_project_config()
        self.assertEqual(before, self.snapshot())
        codex = tomllib.loads(before[HOST_PATHS[0]].decode())
        self.assertEqual(codex["model"], "keep-model")
        self.assertEqual(codex["mcp_servers"], self.servers)
        for name in HOST_PATHS[1:]:
            servers = json.loads(before[name])["mcpServers"]
            self.assertEqual(servers["keep-server"], other["mcpServers"]["keep-server"])
            for key, source in self.servers.items():
                expected = {k: source[k] for k in ("command", "args", "env")}
                if name == ".mcp.json":
                    expected["type"] = "stdio"
                self.assertEqual(servers[key], expected)
        for name in HOST_PATHS:
            self.assertEqual((self.root / name).stat().st_mode & 0o777, 0o600)

    def test_collision_in_each_host_leaves_all_configs_unchanged(self):
        configure.install_project_config()
        original = self.snapshot()
        for name in HOST_PATHS:
            with self.subTest(host=name):
                for path, data in original.items():
                    (self.root / path).write_bytes(data)
                if name.endswith(".toml"):
                    self.write(name, '[mcp_servers.filesystem]\ncommand="other"\n')
                else:
                    self.write(
                        name, '{"mcpServers":{"filesystem":{"command":"other"}}}'
                    )
                before = self.snapshot()
                with self.assertRaises(SystemExit):
                    configure.install_project_config()
                self.assertEqual(before, self.snapshot())

    def test_duplicate_json_key_is_rejected_before_any_write(self):
        configure.install_project_config()
        self.write(".mcp.json", '{"mcpServers":{},"mcpServers":{}}')
        before = self.snapshot()
        with self.assertRaises(SystemExit):
            configure.install_project_config()
        self.assertEqual(before, self.snapshot())

    def test_symlink_target_is_not_overwritten(self):
        outside = self.root / "outside.json"
        outside.write_text('{"keep":true}')
        target = self.root / ".agents/mcp_config.json"
        target.parent.mkdir()
        target.symlink_to(outside)
        with self.assertRaises(SystemExit):
            configure.install_project_config()
        self.assertEqual(outside.read_text(), '{"keep":true}')
        self.assertFalse((self.root / ".codex/config.toml").exists())

    def test_filesystem_definition_is_pinned_and_read_only(self):
        definition = configure.filesystem_definition()
        self.assertEqual(definition["image"], configure.FILESYSTEM_IMAGE)
        self.assertEqual(
            definition["volumes"], [f"{configure.STATE / 'source-view'}:/project:ro"]
        )
        self.assertTrue(definition["disableNetwork"])
        self.assertEqual(definition["metadata"]["owner"], "insighthub")


if __name__ == "__main__":
    unittest.main()
