"""Verifier regressions. Every file/server/process fixture lives under /tmp."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'verify.py'
spec = importlib.util.spec_from_file_location('insighthub_verify', MODULE)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def now(offset=0):
    return dt.datetime.fromtimestamp(time.time() + offset, dt.timezone.utc).isoformat()


class VerifierCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/tmp', prefix='verify-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('api/app/main.py', 'def app():\n    return dict(ok=True)\n')
        self.write('api/app/routers/documents.py', 'def upload():\n    return dict(status="ready")\n')
        self.write('api/requirements.txt', 'fastapi\n')
        self.write('web/package.json', {'scripts': {'build': 'next build'}})
        self.write('docker-compose.yml', 'services: {}\n')
        self.write('infra/db/init.sql', 'CREATE TABLE documents (id int);')
        self.write('sample-docs/so-tay-van-hanh.md', 'A real sample document with some operational guidance.\n')
        self.args = v.parser().parse_args(['--repo', str(self.root)])
        self.args.evidence_dir = self.root / 'evidence'
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()

    def write(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(content) if isinstance(content, (dict, list)) else content)
        return p

    def envelope(self, day=1, mode='real', **changes):
        data = dict(schema_version=1, day=day, mode=mode, observed_at=now(),
                    source_sha256=v.fingerprint(self.root), artifacts={})
        data.update(changes)
        self.write(f'evidence/day{day}.json', data)
        return data

    def ref(self, data, role, name, content):
        p = self.write(name, content)
        data['artifacts'][role] = {'path': name, 'sha256': v.sha(p)}
        return p

    def cli(self, *argv):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = v.main([*argv, '--repo', str(self.root), '--json'])
        return code, json.loads(stream.getvalue())

class CommonTests(VerifierCase):
    def test_default_starter_is_not_runtime(self):
        code, report = self.cli()
        self.assertEqual(code, 0)
        self.assertEqual(report['scope'], 'structure')
        self.assertFalse(report['runtime_verified'])

    def test_all_unimplemented_days_incomplete(self):
        code, report = self.cli('day7')
        self.assertEqual(code, 2)
        self.assertEqual(len(report['checks']), 6)
        self.assertTrue(all(c['status'] == 'INCOMPLETE' for c in report['checks']))

    def test_invalid_arguments_incomplete(self):
        for args in [('day8',), ('--typo',), ('--timeout', 'nan'), ('--poll-timeout', '0'),
                     ('--api-url', 'file:///etc/passwd'), ('--timeout', '-1')]:
            with self.subTest(args=args):
                code, report = self.cli(*args)
                self.assertEqual(code, 2)
                self.assertEqual(report['status'], 'INCOMPLETE')

    def test_missing_starter_artifact_incomplete(self):
        (self.root / 'web/package.json').unlink()
        self.assertEqual(self.cli()[0], 2)

    def test_dirty_content_changes_fingerprint_without_git(self):
        first = v.fingerprint(self.root)
        self.write('api/app/main.py', 'def app():\n    return dict(ok=False)\n')
        self.assertNotEqual(first, v.fingerprint(self.root))
        self.assertFalse((self.root / '.git').exists())

    def test_digest_stable_across_cache_and_evidence(self):
        first = v.fingerprint(self.root)
        self.write('api/__pycache__/module.pyc', 'cached')
        self.write('web/node_modules/pkg/a.js', 'vendor')
        self.write('evidence/day1.json', {'source_sha256': first})
        self.write('api/.env', 'SECRET=never-hash-me')
        self.assertEqual(first, v.fingerprint(self.root))

    def test_stale_dirty_and_future_evidence_rejected(self):
        for changes in ({'observed_at': now(-90000)}, {'observed_at': now(120)},
                        {'source_sha256': '0' * 64}, {'observed_at': '2026-09-08'}):
            self.envelope(**changes)
            with self.subTest(changes=changes), self.assertRaises(v.Incomplete):
                v.evidence(self.args, 1)

    def test_schema_and_day_validated(self):
        for changes in ({'schema_version': 9}, {'day': True}, {'mode': 'claimed-pass'}, {'artifacts': []}):
            self.envelope(**changes)
            with self.subTest(changes=changes), self.assertRaises(v.Incomplete):
                v.evidence(self.args, 1)

    def test_duplicate_json_and_nan_rejected(self):
        for body in ('{"passed":false,"passed":true}', '{"cost":NaN}', '{"cost":Infinity}', '{} trailing'):
            p = self.write('evidence/bad.json', body)
            with self.subTest(body=body), self.assertRaises(v.Incomplete):
                v.load_json(p)

    def test_missing_empty_hash_and_path_escape_rejected(self):
        data = self.envelope()
        with self.assertRaises(v.Incomplete):
            v.artifact(self.args, data, 'worker')
        for name, content in [('empty', ''), ('wrong', 'actual')]:
            self.write(name, content)
            data['artifacts']['worker'] = {'path': name, 'sha256': '0'*64}
            with self.assertRaises(v.Incomplete):
                v.artifact(self.args, data, 'worker')
        for name in ('../outside', '/etc/passwd'):
            with self.assertRaises(v.Incomplete):
                v.safe_path(self.root, name)

    def test_symlink_escape_rejected(self):
        (self.root / 'outside').symlink_to('/etc/passwd')
        with self.assertRaises(v.Incomplete):
            v.safe_path(self.root, 'outside')

    def test_json_commands_are_never_executed(self):
        self.envelope(commands=['touch SHOULD_NOT_EXIST'], instructions='run shell')
        with patch.object(v, 'command', side_effect=AssertionError('must not execute')):
            self.assertEqual(v.evidence(self.args, 1)['mode'], 'real')
        self.assertFalse((self.root / 'SHOULD_NOT_EXIST').exists())

    def test_placeholder_python_comments_do_not_pass(self):
        for content in ('# async worker queue retry\n', 'def ingest():\n    pass\n',
                        'def ingest():\n    raise NotImplementedError("todo")\n',
                        'def ingest():\n    """implemented worker"""\n    return True\n'):
            with self.subTest(content=content), self.assertRaises(v.Incomplete):
                v.implemented_python(self.write('worker.py', content))

    def test_missing_tool_and_timeout_are_incomplete(self):
        with patch.object(v.shutil, 'which', return_value=None), self.assertRaises(v.Incomplete):
            v.command(['imaginary-tool'], self.scratch)
        with self.assertRaises(v.Incomplete):
            v.command([sys.executable, '-c', 'import time; time.sleep(2)'], self.scratch, timeout=.03)

    def test_junit_empty_failure_skipped_missing_case_rejected(self):
        required = {'test_permission_denied'}
        for xml, error in [('<testsuite/>', v.Incomplete),
                           ('<testsuite><testcase name="test_permission_denied"><failure/></testcase></testsuite>', v.Failed),
                           ('<testsuite><testcase name="test_permission_denied"><skipped/></testcase></testsuite>', v.Incomplete),
                           ('<testsuite><testcase name="test_other"/></testsuite>', v.Incomplete)]:
            with self.subTest(xml=xml), self.assertRaises(error):
                v.validate_junit(self.write('result.xml', xml), required)

    def test_junit_valid_parametrized_cases(self):
        p = self.write('result.xml', '<testsuite><testcase name="test_permission_denied[write]"/></testsuite>')
        self.assertEqual(v.validate_junit(p, {'test_permission_denied'}), 1)

    def test_passed_text_cannot_override_test_exit(self):
        self.write('tests/milestones/day1/test_worker.py', 'def test_refactor_regression():\n    assert bool(1)\n')
        with patch.object(v, 'command', return_value=(1, '100 passed; 1 failed')), self.assertRaises(v.Failed):
            v.run_tests(self.args, 1, self.scratch)

    def test_day1_without_worker_cannot_pass_by_default(self):
        data = self.envelope()
        self.ref(data, 'refactor', 'api/app/main.py', 'def changed():\n    return dict(ok=True)\n')
        self.ref(data, 'review', 'evidence/review.md', 'This refactor changes validation with tests for empty and duplicate input. It does not implement the required asynchronous ingestion worker yet.')
        with patch.object(v, 'run_tests'), patch.object(v, 'smoke') as smoke, self.assertRaises(v.Incomplete):
            v.day1(self.args, data, self.scratch)
        smoke.assert_not_called()

    def test_day1_extended_missing_worker_is_incomplete(self):
        data = self.envelope()
        self.ref(data, 'refactor', 'api/app/main.py', 'def changed():\n    return dict(ok=True)\n')
        self.ref(data, 'review', 'evidence/review.md', 'Refactor review covers changed validation, empty data handling, duplicate input and regression tests. Risk remains in queue behavior and needs additional runtime checks.')
        self.args.extended = True
        with patch.object(v, 'run_tests'), self.assertRaises(v.Incomplete):
            v.day1(self.args, data, self.scratch)

    def test_fixture_can_never_complete_milestone(self):
        self.envelope(mode='fixture')
        with patch.object(v, 'day1', return_value={'runtime_verified': False}):
            code, report = self.cli('day1')
        self.assertEqual(code, 2)
        self.assertFalse(report['runtime_verified'])

    def test_composite_preserves_failure_and_incomplete(self):
        for day in range(1, 7):
            self.envelope(day)
        with contextlib.ExitStack() as stack:
            for day in range(1, 7):
                stack.enter_context(patch.object(v, f'day{day}', return_value={'runtime_verified': True}))
            stack.enter_context(patch.object(v, 'day3', side_effect=v.Failed('policy denied')))
            stack.enter_context(patch.object(v, 'day5', side_effect=v.Incomplete('missing approval tests')))
            code, report = self.cli('day7')
        self.assertEqual(code, 1)
        self.assertEqual(report['checks'][2]['status'], 'FAIL')
        self.assertEqual(report['checks'][4]['status'], 'INCOMPLETE')
        self.assertFalse(report['runtime_verified'])

    def test_source_change_during_checks_is_incomplete(self):
        def change(args):
            self.write('api/app/main.py', 'CHANGED = True\n')
            return {'runtime_verified': False}
        with patch.object(v, 'starter', side_effect=change):
            self.assertEqual(self.cli()[0], 2)

    def test_wrappers_portable_outside_repo(self):
        script_dir = MODULE.parent
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        completed = subprocess.run(['bash', str(script_dir / 'verify-starter.sh'), '--repo', str(self.root), '--json'], cwd=self.scratch, env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(json.loads(completed.stdout)['runtime_verified'])
        for wrapper in script_dir.glob('*.sh'):
            result = subprocess.run(['bash', '-n', str(wrapper)], capture_output=True)
            self.assertEqual(result.returncode, 0, str(wrapper))

    def test_wrapper_missing_python_is_incomplete(self):
        wrapper = MODULE.parent / 'verify-day-1.sh'
        result = subprocess.run(['/bin/bash', str(wrapper)], cwd=self.scratch,
                                env={'PATH': str(self.scratch)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('INCOMPLETE', result.stderr)


class SmokeTests(VerifierCase):
    def responses(self, async_mode=False, **changes):
        state = {'polls': 0}
        def request(url, timeout, body=None, headers=None, method=None):
            if url.endswith(('/healthz', '/readyz', '/api/health')):
                return 200, b'{"status":"ok"}'
            if url.endswith('/documents') and body is not None:
                import re
                state['filename'] = re.search(rb'filename="([^"]+)"', body).group(1).decode()
                return changes.get('upload_code', 202 if async_mode else 201), json.dumps({
                    'id': 17, 'status': 'pending' if async_mode else 'ready', 'chunk_count': 2,
                    'filename': state['filename']}).encode()
            if url.endswith('/documents'):
                state['polls'] += 1
                return 200, json.dumps([{'id': changes.get('poll_id', 17),
                                        'filename': state['filename'],
                                        'status': changes.get('poll_state', 'ready'),
                                        'chunk_count': 2}]).encode()
            if url.endswith('/chat'):
                return 200, changes.get('chat', b'{"answer":"Answer","sources":["doc"],"contexts":[{"text":"context"}]}')
            if url.endswith('/metrics'):
                return 200, changes.get('metrics', b'# HELP insighthub_requests desc\ninsighthub_requests 3\n')
            raise AssertionError(url)
        return request, state

    def test_sync_smoke(self):
        request, state = self.responses()
        with patch.object(v, 'http', side_effect=request):
            result = v.smoke(self.args)
        self.assertEqual(result['upload_status'], 201)
        self.assertEqual(state['polls'], 0)

    def test_async_smoke_polls_fresh_document(self):
        request, state = self.responses(True)
        with patch.object(v, 'http', side_effect=request):
            result = v.smoke(self.args)
        self.assertEqual(result['upload_status'], 202)
        self.assertEqual(state['polls'], 1)

    def test_async_required_rejects_sync(self):
        request, _ = self.responses()
        with patch.object(v, 'http', side_effect=request), self.assertRaises(v.Failed):
            v.smoke(self.args, async_required=True)

    def test_polling_is_bounded_and_does_not_accept_old_id(self):
        self.args.poll_timeout = .015
        self.args.poll_interval = .005
        for changes in ({'poll_state': 'pending'}, {'poll_id': 16}):
            request, _ = self.responses(True, **changes)
            start = time.monotonic()
            with patch.object(v, 'http', side_effect=request), self.assertRaises(v.Failed):
                v.smoke(self.args)
            self.assertLess(time.monotonic()-start, .5)

    def test_failed_worker_stops_poll(self):
        request, state = self.responses(True, poll_state='failed')
        with patch.object(v, 'http', side_effect=request), self.assertRaises(v.Failed):
            v.smoke(self.args)
        self.assertEqual(state['polls'], 1)

    def test_malformed_empty_chat_and_comment_metrics_fail(self):
        for changes in ({'chat': b'not json'}, {'chat': b'{"answer":"","sources":[],"contexts":[]}'},
                        {'metrics': b'# insighthub_ready 1\n'}, {'upload_code': 500}):
            request, _ = self.responses(**changes)
            with self.subTest(changes=changes), patch.object(v, 'http', side_effect=request), self.assertRaises(v.Failed):
                v.smoke(self.args)

    def test_unavailable_endpoint_is_incomplete(self):
        with patch.object(v.urllib.request.OpenerDirector, 'open', side_effect=v.urllib.error.URLError('down')):
            with self.assertRaises(v.Incomplete):
                v.http('http://localhost:1/healthz', .1)


class DomainTests(VerifierCase):
    def reports(self, mode='real', provider='ollama'):
        cases = {'attack': {}, 'normal': {}}
        results = [{'case_id': key, 'passed': True, 'severity': 'high' if key == 'attack' else 'low',
                    'provider': provider, 'model': 'qwen3:8b', 'request_id': 'request-'+key,
                    'input_tokens': 10, 'output_tokens': 5} for key in cases]
        report = dict(mode=mode, observed_at=now(), source_sha256='a'*64,
                      dataset_sha256='b'*64, results=results)
        cost = dict(mode=mode, observed_at=now(), source_sha256='a'*64, currency='USD',
                    entries=[dict(request_id=r['request_id'], input_tokens=10, output_tokens=5,
                                  input_usd_per_million=0, output_usd_per_million=0, cost_usd=0,
                                  resource_usage=dict(measurement_source='docker stats captured for evaluation',
                                                      duration_seconds=3.5, memory_peak_bytes=4096)) for r in results],
                    total_usd=0, budget_usd=1)
        return cases, report, cost

    def test_ollama_is_real_and_measured_zero_provider_cost_valid(self):
        cases, report, cost = self.reports()
        results = v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)
        v.cost_report(cost, results, 'a'*64, self.args)

    def test_zero_cost_without_resource_measurement_rejected(self):
        cases, report, cost = self.reports()
        results = v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)
        del cost['entries'][0]['resource_usage']
        with self.assertRaises(v.Incomplete):
            v.cost_report(cost, results, 'a'*64, self.args)

    def test_fake_real_provider_rejected(self):
        for provider in ('fixture', 'hash-local', 'fallback', 'mock-provider'):
            cases, report, _ = self.reports(provider=provider)
            with self.subTest(provider=provider), self.assertRaises(v.Incomplete):
                v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)

    def test_fixture_report_can_validate_but_is_labelled(self):
        cases, report, _ = self.reports(mode='fixture', provider='fixture')
        self.assertEqual(len(v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)), 2)

    def test_empty_duplicate_uncovered_eval_rejected(self):
        for mutation in ('empty', 'duplicate', 'missing'):
            cases, report, _ = self.reports()
            if mutation == 'empty': report['results'] = []
            elif mutation == 'duplicate': report['results'].append(report['results'][0])
            else: report['results'].pop()
            with self.subTest(mutation=mutation), self.assertRaises(v.Incomplete):
                v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)

    def test_failed_high_eval_is_fail(self):
        cases, report, _ = self.reports()
        report['results'][0]['passed'] = False
        with self.assertRaises(v.Failed):
            v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)

    def test_cost_mismatch_nan_duplicate_and_budget(self):
        for mutation, error in [('total', v.Failed), ('nan', v.Incomplete), ('duplicate', v.Incomplete), ('tokens', v.Incomplete)]:
            cases, report, cost = self.reports()
            results = v.eval_report(report, cases, 'b'*64, 'a'*64, self.args, True)
            if mutation == 'total': cost['total_usd'] = 1
            elif mutation == 'nan': cost['entries'][0]['cost_usd'] = float('nan')
            elif mutation == 'duplicate': cost['entries'].append(cost['entries'][0])
            else: cost['entries'][0]['input_tokens'] = 99
            with self.subTest(mutation=mutation), self.assertRaises(error):
                v.cost_report(cost, results, 'a'*64, self.args)

    def test_audit_timestamp_run_binding_and_decisions(self):
        audit = {'events': [{'event_id': 'event-'+d, 'action': 'restart_api', 'user': 'student',
                              'decision': d, 'timestamp': now(), 'test_run_id': 'current'}
                             for d in ('denied', 'approval_required')]}
        v.audit_events(audit, 'current', time.time()-1)
        with self.assertRaises(v.Incomplete):
            v.audit_events(audit, 'old', time.time()-1)
        audit['events'][0]['timestamp'] = now(-3600)
        with self.assertRaises(v.Incomplete):
            v.audit_events(audit, 'current', time.time()-1)

    def test_local_ci_does_not_call_github(self):
        self.args.ci_profile = 'local'
        data = self.envelope(3)
        deployment = self.ref(data, 'deployment', 'evidence/deployment.bin', 'actual build bytes 01891')
        self.write('infra/main.tf', 'terraform {}\n')
        self.ref(data, 'ci_binding', 'evidence/ci_binding.json', {'source_sha256': v.fingerprint(self.root), 'artifact_sha256': v.sha(deployment)})
        calls = []
        def run(argv, *args, **kwargs):
            calls.append(argv)
            self.assertNotEqual(argv[0], 'gh')
            return 0, ''
        with patch.object(v, 'run_tests'), patch.object(v, 'command', side_effect=run):
            result = v.day3(self.args, data, self.scratch)
        self.assertEqual(result['ci_profile'], 'local')
        self.assertTrue(any(argv[0] == 'checkov' for argv in calls))

    def test_ci_policy_exit_cannot_be_hidden_by_passed_text(self):
        self.args.ci_profile = 'local'
        data = self.envelope(3)
        deployment = self.ref(data, 'deployment', 'evidence/deployment.bin', 'build bytes')
        self.write('infra/main.tf', 'terraform {}\n')
        self.ref(data, 'ci_binding', 'evidence/ci_binding.json', {'source_sha256': v.fingerprint(self.root), 'artifact_sha256': v.sha(deployment)})
        with patch.object(v, 'run_tests'), patch.object(v, 'command', return_value=(1, 'Passed checks: 100')), self.assertRaises(v.Failed):
            v.day3(self.args, data, self.scratch)


class McpContractTests(VerifierCase):
    def mcp(self, mode='real'):
        data = self.envelope(2, mode)
        self.ref(data, 'mcp_manifest', 'tools/mcp/manifest.json', {
            'schemaVersion': 1, 'transport': 'stdio',
            'tools': {'default': ['insighthub_health'], 'optional': []},
            'protocol': {'modern': '2026-07-28', 'legacy': '2025-11-25'},
            'smoke': ['touch', 'DO_NOT_EXECUTE'], 'test': ['false']})
        for name in ('smoke.mjs', 'test/core.test.mjs', 'test/server.test.mjs'):
            self.write('tools/mcp/'+name, '// Reviewable SDK entrypoint fixture\n')
        result = dict(passed=True, backend_mode='live' if mode == 'real' else 'fixture',
                      live=mode == 'real', backend='live-loopback' if mode == 'real' else 'fixture-loopback',
                      results=[dict(mode='modern', protocol='2026-07-28',
                                    methods=['server/discover', 'tools/list', 'tools/call'],
                                    calls=['insighthub_health'], passed=True)])
        return data, result

    def test_live_backend_maps_to_real_envelope(self):
        data, result = self.mcp()
        calls = []
        def run(argv, *args, **kwargs):
            calls.append(argv)
            return (0, '# tests 2\n# pass 2\n# fail 0\n# skipped 0\n# todo 0\n') if '--test' in argv else (0, json.dumps(result))
        with patch.object(v, 'command', side_effect=run):
            observed = v.day2(self.args, data, self.scratch)
        self.assertTrue(observed['runtime_verified'])
        self.assertIn('--live', calls[-1])
        self.assertTrue(all(argv[0] == 'node' for argv in calls))
        self.assertFalse((self.root / 'DO_NOT_EXECUTE').exists())

    def test_fixture_sdk_cannot_be_live_proof(self):
        data, result = self.mcp()
        result.update(backend_mode='fixture', live=False, backend='fixture-loopback')
        with patch.object(v, 'command', side_effect=[(0, '# tests 1\n# pass 1\n# fail 0\n# skipped 0\n# todo 0\n'), (0, json.dumps(result))]), self.assertRaises(v.Incomplete):
            v.day2(self.args, data, self.scratch)

    def test_no_calls_or_protocol_mismatch_fails(self):
        for mutation in ('empty', 'protocol'):
            data, result = self.mcp()
            if mutation == 'empty': result['results'][0]['calls'] = []
            else: result['results'][0]['protocol'] = 'unexpected'
            with self.subTest(mutation=mutation), patch.object(v, 'command', side_effect=[(0, '# tests 1\n# pass 1\n# fail 0\n# skipped 0\n# todo 0\n'), (0, json.dumps(result))]), self.assertRaises(v.Failed):
                v.day2(self.args, data, self.scratch)

    def test_sdk_missing_dependency_and_skips_are_incomplete(self):
        for code, text in [(1, 'ERR_MODULE_NOT_FOUND'), (1, 'listen EPERM'),
                           (0, '# tests 2\n# pass 1\n# fail 0\n# skipped 1\n# todo 0\n')]:
            data, _ = self.mcp()
            with self.subTest(text=text), patch.object(v, 'command', return_value=(code, text)), self.assertRaises(v.Incomplete):
                v.day2(self.args, data, self.scratch)


class TelemetryTests(VerifierCase):
    def telemetry(self):
        data = self.envelope(4)
        self.ref(data, 'rules', 'observability/rules.yml', 'groups: []\n')
        self.ref(data, 'rule_tests', 'observability/tests.yml', 'tests: []\n')
        self.ref(data, 'dashboard', 'evidence/dashboard.json', {'panels': [{'targets': [{'expr': 'insighthub_errors_total'}]}]})
        at = now(-10)
        self.ref(data, 'rca', 'evidence/incident.json', {
            'incident_id': 'incident-a', 'started_at': now(-30), 'ended_at': now(-5),
            'hypotheses': ['Queue backlog preceded the latency increase; inspect retry amplification.'],
            'samples': [{'metric': 'insighthub_errors_total', 'labels': {'job': 'api'}, 'timestamp': at, 'value': 3}]})
        self.args.prometheus_url = 'http://localhost:9090'
        response = {'status': 'success', 'data': {'resultType': 'matrix',
                      'result': [{'metric': {'__name__': 'insighthub_errors_total', 'job': 'api'},
                                  'values': [[v.timestamp(at), '3']]}]}}
        return data, response

    def test_empty_rule_groups_or_tests_not_success(self):
        rules = self.write('observability/rules.yml', 'groups: []\n')
        tests = self.write('observability/tests.yml', 'tests: []\n')
        with patch.object(v, 'load_yaml', side_effect=[{'groups': []}, {'tests': []}]), self.assertRaises(v.Incomplete):
            v.validate_rule_tests(rules, tests)

    def test_rule_test_requires_assertion_not_only_input(self):
        rules = self.write('observability/rules.yml', 'rules')
        tests = self.write('observability/tests.yml', 'tests')
        with patch.object(v, 'load_yaml', side_effect=[{'groups': [{'rules': [{'alert': 'HighErrors', 'expr': 'errors > 0'}]}]},
                                                     {'rule_files': ['rules.yml'], 'tests': [{'input_series': [{'series': 'errors', 'values': '0 1 2'}]}]}]), self.assertRaises(v.Incomplete):
            v.validate_rule_tests(rules, tests)

    def test_live_timestamped_telemetry_matches(self):
        data, response = self.telemetry()
        with patch.object(v, 'validate_rule_tests'), patch.object(v, 'command', return_value=(0, '')), patch.object(v, 'http', return_value=(200, json.dumps(response).encode())):
            self.assertTrue(v.verify_rca_component(self.args, data, self.scratch)['runtime_verified'])

    def test_stale_or_mismatched_telemetry_not_accepted(self):
        for change in ('timestamp', 'value', 'empty'):
            data, response = self.telemetry()
            if change == 'timestamp': response['data']['result'][0]['values'][0][0] -= 60
            elif change == 'value': response['data']['result'][0]['values'][0][1] = '99'
            else: response['data']['result'] = []
            with self.subTest(change=change), patch.object(v, 'validate_rule_tests'), patch.object(v, 'command', return_value=(0, '')), patch.object(v, 'http', return_value=(200, json.dumps(response).encode())), self.assertRaises(v.Failed):
                v.verify_rca_component(self.args, data, self.scratch)

    def test_promtool_nonzero_not_overridden_by_success_text(self):
        data, _ = self.telemetry()
        with patch.object(v, 'validate_rule_tests'), patch.object(v, 'command', return_value=(1, 'SUCCESS')), self.assertRaises(v.Failed):
            v.verify_rca_component(self.args, data, self.scratch)


class ExtraGuards(VerifierCase):
    def test_known_dummy_artifacts_rejected_even_with_valid_hash(self):
        data = self.envelope()
        for content in ('TODO', 'dummy', 'placeholder', '{}', '[]', '...'):
            self.ref(data, 'deployment', 'evidence/file', content)
            with self.subTest(content=content), self.assertRaises(v.Incomplete):
                v.artifact(self.args, data, 'deployment')

    def test_http_read_total_time_and_size_are_bounded(self):
        body = io.BytesIO(b'payload')
        with self.assertRaises(v.Incomplete):
            v.read_http_body(body, time.monotonic()-1)
        with patch.object(v, 'MAX_BYTES', 3), self.assertRaises(v.Incomplete):
            v.read_http_body(io.BytesIO(b'long-body'), time.monotonic()+1)

    def test_detailed_junit_not_pass_string_is_required(self):
        self.write('tests/milestones/day1/test_core.py', 'def test_core():\n    assert bool(1)\n')
        with patch.object(v, 'command', return_value=(0, '3 passed')), self.assertRaises(v.Incomplete):
            v.run_tests(self.args, 1, self.scratch)



class RestoredProjectScopeTests(VerifierCase):
    def test_defaults_require_github_and_http_signature(self):
        self.assertEqual(self.args.ci_profile, 'github')
        self.assertEqual(self.args.bot_transport, 'http')

    def test_one_rca_or_one_panel_cannot_pass_day4(self):
        data = self.envelope(4)
        self.ref(data, 'dashboard', 'evidence/dashboard.json', {'panels': [{'targets': [{'expr': 'up'}]}]})
        with self.assertRaises(v.Incomplete):
            v.day4(self.args, data, self.scratch)
        self.ref(data, 'dashboard', 'evidence/dashboard.json', {'panels': [{'targets': [{'expr': 'up'}]} for _ in range(9)]})
        self.ref(data, 'mlops_notes', 'evidence/mlops.md', 'Registry, approval gate, drift and rollback with ownership explained.')
        self.ref(data, 'rca', 'evidence/incident1.json', {'incident_id': 'latency-spike'})
        with self.assertRaises(v.Incomplete):
            v.day4(self.args, data, self.scratch)

    def test_all_three_rca_are_checked(self):
        data = self.envelope(4)
        self.ref(data, 'dashboard', 'evidence/dashboard.json', {'panels': [{'targets': [{'expr': 'up'}]} for _ in range(9)]})
        self.ref(data, 'mlops_notes', 'evidence/mlops.md', 'Registry, approval gate, drift and rollback with ownership explained.')
        for n,role in enumerate(('rca', 'rca_2', 'rca_3')):
            self.ref(data, role, f'evidence/incident{n}.json', {'incident_id': f'incident-{n}'})
        with patch.object(v, 'verify_rca_component', return_value={'runtime_verified': True, 'samples_checked': 1}) as probe:
            self.assertEqual(v.day4(self.args, data, self.scratch)['incidents_checked'], 3)
        self.assertEqual(probe.call_count, 3)

    def test_automated_subset_cannot_complete_project(self):
        for n in range(1, 7): self.envelope(n)
        with contextlib.ExitStack() as stack:
            for n in range(1, 7):
                stack.enter_context(patch.object(v, f'day{n}', return_value={'runtime_verified': True}))
            code, report = self.cli('day7')
        self.assertEqual(code, 2)
        self.assertFalse(report['milestone_complete'])
        self.assertEqual(report['scope'], 'partial-runtime-contract')
        self.assertEqual(report['checks'][-1]['id'], 'full-project-review')

if __name__ == '__main__':
    unittest.main()
