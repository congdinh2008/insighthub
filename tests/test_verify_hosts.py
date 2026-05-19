"""Host portability and evidence regression checks; no model/account required."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


c = module('host_check', ROOT / 'scripts/check-agent-setup.py')
v = module('host_fingerprint', ROOT / 'scripts/verify.py')


class HostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='Insight Hub tiếng Việt ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('AGENTS.md', '\n'.join('## ' + x + '\nConstraint for this section.' for x in sorted(c.SECTIONS)))
        self.write('api/a.py', 'print("baseline")\n')

    def write(self, path, content):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def config(self, obj):
        self.write('config.json', json.dumps(obj))

    def test_helper_three_hosts_same_backend_unicode_paths(self):
        import tomllib
        shutil.copy2(ROOT / 'tools/mcp/host-config.mjs', self.root / 'host-config.mjs')
        configs = []
        for host in ['claude', 'codex', 'antigravity']:
            result = subprocess.run(['node', str(self.root / 'host-config.mjs'), host],
                                    cwd='/tmp', text=True, capture_output=True, check=True)
            self.write('config.txt', result.stdout)
            checked = c.check(self.root, host, 'config.txt')
            self.assertFalse(checked['host_verified'])
            self.assertFalse(checked['milestone_complete'])
            obj = tomllib.loads(result.stdout) if host == 'codex' else json.loads(result.stdout)
            entry = obj['mcp_servers' if host == 'codex' else 'mcpServers']['insighthub-readonly']
            self.assertTrue(Path(entry['command']).is_absolute())
            self.assertEqual(entry['args'], [str(self.root.resolve() / 'src/server.mjs')])
            configs.append({k: entry[k] for k in ['command', 'args', 'env']})
        self.assertEqual(configs[0], configs[1])
        self.assertEqual(configs[1], configs[2])
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         ['AGENTS.md', 'api', 'config.txt', 'host-config.mjs'])

    def test_helper_rejects_unknown_host(self):
        proc = subprocess.run(['node', str(ROOT/'tools/mcp/host-config.mjs'), 'unknown'],
                              text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, '')

    def test_cross_host_format_rejected(self):
        self.config({'mcpServers': {'x': {'command': 'node'}}})
        with self.assertRaises(ValueError):
            c.check(self.root, 'codex', 'config.json')

    def test_remote_host_fields(self):
        for host, field in [('claude', 'url'), ('antigravity', 'serverUrl')]:
            self.config({'mcpServers': {'x': {field: 'https://example.invalid/mcp'}}})
            self.assertEqual(c.check(self.root, host, 'config.json')['server_entries'], 1)
            self.config({'mcpServers': {'x': {'httpUrl': 'https://example.invalid/mcp'}}})
            with self.assertRaises(ValueError):
                c.check(self.root, host, 'config.json')

    def test_duplicate_json_rejected(self):
        self.write('config.json', '{"mcpServers":{"x":{"command":"node"}},"mcpServers":{}}')
        with self.assertRaises(ValueError):
            c.check(self.root, 'claude', 'config.json')

    def test_missing_or_duplicate_section_rejected(self):
        self.config({'mcpServers': {'x': {'command': 'node'}}})
        original = (self.root/'AGENTS.md').read_text()
        for text in [original.replace('## Domain', '## Other'), original+'\n## Domain\nDuplicate']:
            self.write('AGENTS.md', text)
            with self.assertRaises(ValueError):
                c.check(self.root, 'claude', 'config.json')

    def test_length_limit_and_todo_not_milestone(self):
        self.config({'mcpServers': {'x': {'command': 'node'}}})
        original = (self.root/'AGENTS.md').read_text()
        self.write('AGENTS.md', original+'\nTODO learner work\n')
        result = c.check(self.root, 'claude', 'config.json')
        self.assertTrue(result['context_contains_todo'])
        self.assertFalse(result['milestone_complete'])
        self.write('AGENTS.md', original+'\n'*201)
        with self.assertRaises(ValueError):
            c.check(self.root, 'claude', 'config.json')

    def test_config_cannot_escape_repo(self):
        with self.assertRaises(ValueError):
            c.check(self.root, 'claude', '/etc/passwd')
        with self.assertRaises(ValueError):
            c.check(self.root, 'claude', '../config.json')

    def test_malformed_transport_rejected(self):
        for server in [{'command': ['node']}, {'command': 'node', 'args': 'x'},
                       {'command': 'node', 'env': {'KEY': 7}},
                       {'command': 'node', 'serverUrl': 'https://example.invalid'}]:
            self.config({'mcpServers': {'x': server}})
            with self.assertRaises(ValueError):
                c.check(self.root, 'antigravity', 'config.json')

    def test_host_artifacts_change_fingerprint(self):
        for path in ['AGENTS.md', 'CLAUDE.md', '.codex/config.toml',
                     '.agents/mcp_config.json', '.agents/rules/project.md',
                     'Running-Project-Specification-Student.md']:
            before = v.fingerprint(self.root)
            self.write(path, 'Updated host source for ' + path)
            self.assertNotEqual(v.fingerprint(self.root), before, path)

    def test_external_config_symlink_rejected(self):
        (self.root/'.codex').mkdir()
        (self.root/'.codex/config.toml').symlink_to('/etc/passwd')
        with self.assertRaises(v.Incomplete):
            v.fingerprint(self.root)

