#!/usr/bin/env python3
"""Static project context/MCP shape check only. Never starts a host or server."""
import argparse
import json
from pathlib import Path
import re
import sys

SECTIONS = {'Architecture', 'Conventions', 'Commands', 'Constraints', 'Domain', 'References'}


def local_file(root, name):
    raw = Path(name)
    p = (root / raw).resolve()
    if raw.is_absolute() or not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError('Input must be an existing repository-relative file')
    if p.stat().st_size > 1024 * 1024:
        raise ValueError('Input exceeds static-check size limit')
    return p


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def check(root, host, config, context='AGENTS.md'):
    if host not in {'claude', 'codex', 'antigravity'}:
        raise ValueError('Unknown host')
    text = local_file(root, context).read_text(encoding='utf-8')
    headings = re.findall(r'^## ([A-Za-z]+)\s*$', text, re.M)
    if len(text.splitlines()) > 200 or set(headings) != SECTIONS or len(headings) != 6:
        raise ValueError('Context needs exactly six sections and at most 200 lines')
    content = local_file(root, config).read_text(encoding='utf-8')
    if host == 'codex':
        import tomllib  # Python 3.11+
        data = tomllib.loads(content)
        key, remote = 'mcp_servers', 'url'
    else:
        def invalid_constant(value):
            raise ValueError('Non-finite JSON number')
        data = json.loads(content, object_pairs_hook=unique_pairs, parse_constant=invalid_constant)
        key, remote = 'mcpServers', 'serverUrl' if host == 'antigravity' else 'url'
    servers = data.get(key) if isinstance(data, dict) else None
    if not isinstance(servers, dict) or not servers:
        raise ValueError('Expected nonempty server map for selected host')
    for name, server in servers.items():
        if not isinstance(name, str) or not name or not isinstance(server, dict):
            raise ValueError('Invalid server entry')
        command, url = server.get('command'), server.get(remote)
        if bool(command) == bool(url):
            raise ValueError('Server needs exactly one command or host-specific URL')
        if command and not isinstance(command, str) or url and not isinstance(url, str):
            raise ValueError('Transport value must be a string')
        if any(k in server for k in {'url', 'serverUrl', 'httpUrl'} - {remote}):
            raise ValueError('Remote URL field belongs to a different host')
        if 'args' in server and (not isinstance(server['args'], list) or
                                not all(isinstance(a, str) for a in server['args'])):
            raise ValueError('args must be a string array')
        if 'env' in server and (not isinstance(server['env'], dict) or
                               not all(isinstance(v, str) for v in server['env'].values())):
            raise ValueError('env must contain string values')
    return {'status': 'PASS', 'scope': 'static-context-and-config-shape',
            'host': host, 'server_entries': len(servers),
            'context_contains_todo': bool(re.search(r'\bTODO\b', text)),
            'host_verified': False, 'milestone_complete': False,
            'note': 'Host activation, backend coverage, permissions, live calls and context quality require evidence.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, choices=['claude', 'codex', 'antigravity'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--context', default='AGENTS.md')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        result = check(args.repo, args.host, args.config, args.context)
    except (ValueError, OSError, ImportError, RecursionError):
        # Never print parser input: a user config may contain credentials.
        print(json.dumps({'status': 'INCOMPLETE', 'scope': 'static-context-and-config-shape',
                          'host_verified': False, 'milestone_complete': False,
                          'message': 'Check Python 3.11+, context sections/length and config format/paths.'}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())

