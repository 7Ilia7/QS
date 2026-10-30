"""Owner-selected automatic CI→CD trust, ordering and bootstrap behavior."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from delivery_policy import delivery_context, is_new_auto_run, selected_head_is_current
from deploy import deploy
from release_lib import canonical
from receiver import PUBLIC, PRIVATE, CONTROL
import test_release as fixtures

A, B, C = fixtures.A, fixtures.B, fixtures.C


def event():
    return {'action': 'completed', 'workflow_run': {'id': 102, 'name': 'Website CI', 'status': 'completed', 'conclusion': 'success', 'event': 'push', 'head_branch': 'main', 'head_sha': B, 'head_repository': {'full_name': '7Ilia7/QS'}}}


class EventPolicy(unittest.TestCase):
    def decide(self, value, ready=True, ref='refs/heads/main'):
        return delivery_context('workflow_run', value, '7Ilia7/QS', ref, ready)

    def test_successful_main_push_is_automatic_without_per_release_approval(self):
        d = self.decide(event())
        self.assertEqual((d['kind'], d['source_sha'], d['run_id']), ('automatic', B, 102))

    def test_PR_fork_failure_cancellation_nonmain_pending_other_workflow_excluded(self):
        for key, value in [('event', 'pull_request'), ('event', 'workflow_dispatch'), ('head_repository', {'full_name': 'other/fork'}), ('conclusion', 'failure'), ('conclusion', 'cancelled'), ('head_branch', 'feature'), ('status', 'in_progress'), ('name', 'Different CI')]:
            e = event();e['workflow_run'][key] = value
            with self.subTest(key=key, value=value):self.assertIsNone(self.decide(e))
        self.assertIsNone(self.decide(event(), ref='refs/heads/other-default'))

    def test_missing_bootstrap_readiness_skips_auto_before_transport(self):
        self.assertIsNone(self.decide(event(), ready=False))

    def test_bootstrap_is_one_time_and_manual_promotion_not_routine_interface(self):
        e = {'inputs': {'action': 'bootstrap', 'source_sha': A, 'ci_run_id': '101'}}
        self.assertEqual(delivery_context('workflow_dispatch', e, '7Ilia7/QS', 'refs/heads/main', False)['kind'], 'bootstrap')
        with self.assertRaisesRegex(ValueError, 'already_enabled'):
            delivery_context('workflow_dispatch', e, '7Ilia7/QS', 'refs/heads/main', True)
        e['inputs']['action'] = 'promote'
        with self.assertRaisesRegex(ValueError, 'manual_action'):
            delivery_context('workflow_dispatch', e, '7Ilia7/QS', 'refs/heads/main', True)

    def test_manual_rollback_requires_explicit_current_SHA(self):
        e = {'inputs': {'action': 'rollback', 'source_sha': A, 'ci_run_id': '101', 'expected_current': C}}
        self.assertEqual(delivery_context('workflow_dispatch', e, '7Ilia7/QS', 'refs/heads/main', True)['expected_current'], C)
        del e['inputs']['expected_current']
        with self.assertRaises(ValueError):delivery_context('workflow_dispatch', e, '7Ilia7/QS', 'refs/heads/main', True)

    def test_stale_main_is_skipped_but_older_rollback_target_is_allowed(self):
        self.assertFalse(selected_head_is_current('automatic', B, C))
        self.assertFalse(selected_head_is_current('bootstrap', B, C))
        self.assertTrue(selected_head_is_current('rollback', A, C))


class AutoOrdering(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReleaseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.m, self.root = self.fixture.manager, self.fixture.root

    def maximum(self):
        return self.m.status()['last_operation']['max_automatic_run']

    def test_delayed_older_run_cannot_replace_newer_production(self):
        f = self.fixture;b = f.artifact();c = f.artifact(sha=C, text='newest')
        self.m.operate(f.header(c, sha=C), c)
        before = f.protected_bytes()
        with self.assertRaisesRegex(ValueError, 'stale_or_duplicate'):
            self.m.operate(f.header(b, current=C), b)
        self.assertEqual(self.m.current()['source_sha'], C)
        self.assertEqual(self.maximum()['run_number'], 3)
        self.assertEqual(f.protected_bytes(), before)

    def test_manual_rollback_preserves_maximum_and_blocks_old_rerun(self):
        f = self.fixture;c = f.artifact(sha=C, text='third')
        self.m.operate(f.header(c, sha=C), c)
        baseline = self.root / 'baseline/website.tar'
        self.m.operate(f.header(baseline, sha=A, current=C, action='rollback'), baseline)
        self.assertEqual(self.maximum()['run_number'], 3)
        with self.assertRaisesRegex(ValueError, 'stale_or_duplicate'):
            self.m.operate(f.header(c, sha=C, current=A), c)
        self.assertEqual(self.m.current()['source_sha'], A)
        d = 'd' * 40
        fixtures.fixture(f.source, 'new merge after rollback')
        out = self.root / 'new-merge';fixtures.build(f.source, d, out)
        self.m.operate(f.header(out / 'website.tar', sha=d, current=A, number=4), out / 'website.tar')
        self.assertEqual(self.m.current()['source_sha'], d)

    def test_unconfirmed_auto_requires_reconciliation_and_keeps_reserved_run(self):
        f = self.fixture;b = f.artifact();c = f.artifact(sha=C, text='third')
        original = self.m.stage
        def fail(*args):raise OSError('owned interrupted stage')
        self.m.stage = fail
        with self.assertRaises(OSError):self.m.operate(f.header(b), b)
        self.m.stage = original
        self.assertEqual(self.maximum()['run_number'], 2)
        with self.assertRaisesRegex(ValueError, 'prior_operation_unconfirmed'):
            self.m.operate(f.header(c, sha=C), c)
        self.assertEqual(self.m.current()['source_sha'], A)

    def test_bootstrap_registration_is_no_switch_and_auto_cannot_race_it(self):
        f = self.fixture;b = f.artifact();baseline = self.root / 'baseline/website.tar'
        self.m.p(CONTROL + '/last-operation.json').unlink()
        with self.assertRaisesRegex(ValueError, 'bootstrap_not_registered'):
            self.m.operate(f.header(b), b)
        before = f.protected_bytes();targets = (self.m.pointer(PUBLIC), self.m.pointer(PRIVATE))
        result = self.m.operate(f.header(baseline, sha=A, current=A, kind='bootstrap'), baseline)
        self.assertEqual(result['status'], 'bootstrap_verified')
        self.assertEqual(targets, (self.m.pointer(PUBLIC), self.m.pointer(PRIVATE)))
        self.assertEqual(before, f.protected_bytes())
        self.assertFalse(any('systemctl' in c[0] for c in f.calls))
        with self.assertRaisesRegex(ValueError, 'bootstrap_already_registered'):
            self.m.operate(f.header(baseline, sha=A, current=A, kind='bootstrap'), baseline)

    def test_different_CI_workflow_identity_is_not_an_ordering_reset(self):
        f = self.fixture;b = f.artifact();header = f.header(b);header['delivery']['workflow_id'] = 99
        with self.assertRaisesRegex(ValueError, 'workflow_identity_changed'):
            self.m.operate(header, b)
        self.assertEqual(self.m.current()['source_sha'], A)

    def driver(self, path, latest, ancestor=True):
        f = self.fixture;report = self.root / 'driver-report'
        calls = []
        def ssh(command, input, **kwargs):
            calls.append(input)
            self.assertEqual(input, b'{"action":"status"}\n')
            return SimpleNamespace(returncode=0, stdout=canonical(self.m.status()))
        with patch.dict(os.environ, {'QS_DEPLOY_SSH_KEY': 'owned-synthetic-key', 'QS_KNOWN_HOSTS': '165.245.223.138 ssh-ed25519 owned-public-fixture'}), patch('deploy.subprocess.run', side_effect=ssh), patch('deploy.latest_main', return_value=latest), patch('deploy.is_ancestor', return_value=ancestor):
            result = deploy('promote', path.parent, None, report)
        self.assertEqual(len(calls), 1)
        return result

    def test_main_advancing_after_selection_never_calls_mutation(self):
        b = self.fixture.artifact()
        result = self.driver(b, C)
        self.assertEqual(result['status'], 'SKIPPED_main_advanced_before_mutation')
        self.assertEqual(self.m.current()['source_sha'], A)

    def test_duplicate_after_newer_success_is_status_only(self):
        f = self.fixture;b = f.artifact();c = f.artifact(sha=C, text='third')
        self.m.operate(f.header(c, sha=C), c)
        result = self.driver(b, C)
        self.assertEqual(result['status'], 'SKIPPED_stale_or_duplicate_CI_run')
        self.assertEqual(self.m.current()['source_sha'], C)

    def test_automatic_downgrade_fails_before_mutating_SSH(self):
        b = self.fixture.artifact()
        with self.assertRaisesRegex(ValueError, 'downgrade'):
            self.driver(b, B, ancestor=False)
        self.assertEqual(self.m.current()['source_sha'], A)


if __name__ == '__main__':
    unittest.main()
