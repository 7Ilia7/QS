import copy
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
from build import build
from receiver import Manager, PUBLIC, PRIVATE, CONTROL
from release_lib import canonical, digest, verify_archive
from select_ci import select_metadata, unpack
from deploy import public_readback, deploy

A, B, C = 'a' * 40, 'b' * 40, 'c' * 40


def fixture(root, text='baseline', backend='pass\n'):
    for folder in ['site', 'app/backend', 'release']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / 'site/index.html').write_text(text)
    (root / 'app/backend/server.py').write_text(backend)
    (root / 'release/allowlist.json').write_text(json.dumps({'schema': 'website.source-allowlist.v1', 'public': ['index.html'], 'private': ['backend/server.py']}))


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'source'
        fixture(self.source)
        self.baseline = build(self.source, A, self.root / 'baseline')
        self.host = self.root / 'host'
        self.calls = []
        self.config = {'baseline_label': 'qc-20261030-existing-v1', 'baseline_manifest': self.baseline, 'mono_id': 'd' * 64}
        self.manager = Manager(self.config, self.host, runner=self.run_fake, health=lambda: True)
        self.public, self.private = self.manager.baseline_paths()
        self.public.mkdir(parents=True)
        (self.private / 'backend').mkdir(parents=True)
        (self.public / 'index.html').write_text('baseline')
        (self.private / 'backend/server.py').write_text('pass\n')
        for base, target in [(PUBLIC, self.public), (PRIVATE, self.private)]:
            self.manager.p(base + '/current').symlink_to(os.path.relpath(target, self.manager.p(base)))
        for folder in [CONTROL, '/etc/caddy', '/etc/qs-forms', '/var/lib/qs-forms', '/srv/hair-sites/course/releases/old']:
            self.manager.p(folder).mkdir(parents=True, exist_ok=True)
        self.manager.p(CONTROL).chmod(0o700)
        self.manager.p('/etc/caddy/Caddyfile').write_text('unchanged config')
        self.manager.p('/etc/qs-forms/telegram.env').write_text('synthetic private sentinel')
        self.manager.p('/etc/qs-forms/telegram.env').chmod(0o600)
        self.manager.p('/var/lib/qs-forms').chmod(0o700)
        self.state = self.manager.p('/var/lib/qs-forms/outcomes.json')
        self.state.write_bytes(b'synthetic latest state/HMAC/spent receipts sentinel')
        self.state.chmod(0o600)
        course = self.manager.p('/srv/hair-sites/course/releases/old')
        (course / 'index.html').write_text('unchanged course')
        self.manager.p('/srv/hair-sites/course/current').symlink_to('releases/old')

    def run_fake(self, command):
        self.calls.append(command)
        return 'stable mono identity/start/restarts/health' if 'docker' in command[0] else ''

    def artifact(self, sha=B, text='next', backend='pass\n'):
        fixture(self.source, text, backend)
        out = self.root / ('artifact-' + sha[0])
        build(self.source, sha, out)
        return out / 'website.tar'

    def header(self, path, sha=B, current=A, action='promote'):
        return {'action': action, 'source_sha': sha, 'expected_current': current, 'archive_sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size}

    def protected_bytes(self):
        return {p: self.manager.p(p).read_bytes() for p in ['/var/lib/qs-forms/outcomes.json', '/etc/qs-forms/telegram.env', '/etc/caddy/Caddyfile', '/srv/hair-sites/course/current/index.html']}

    def test_deterministic_build_and_exact_allowlist(self):
        other = self.root / 'same'
        build(self.source, A, other)
        self.assertEqual((other / 'website.tar').read_bytes(), (self.root / 'baseline/website.tar').read_bytes())
        (self.source / 'site/forgotten.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'source_allowlist'):
            build(self.source, A, self.root / 'bad')

    def test_source_symlink_and_credential_never_packaged(self):
        (self.source / 'site/index.html').unlink()
        (self.source / 'site/index.html').symlink_to(self.state)
        with self.assertRaisesRegex(ValueError, 'source_symlink'):
            build(self.source, A, self.root / 'bad-link')
        (self.source / 'site/index.html').unlink()
        (self.source / 'site/index.html').write_text('123456789:' + 'x' * 35)
        with self.assertRaisesRegex(ValueError, 'credential_pattern'):
            build(self.source, A, self.root / 'bad-token')

    def test_tar_tamper_extra_path_and_links_rejected(self):
        archive = self.artifact()
        with tarfile.open(archive, 'r:') as source:
            members = [(m, source.extractfile(m).read()) for m in source.getmembers()]
        for kind in ['tamper', 'traversal', 'symlink', 'duplicate']:
            bad = self.root / (kind + '.tar')
            with tarfile.open(bad, 'w', format=tarfile.USTAR_FORMAT) as out:
                for member, data in members:
                    if kind == 'tamper' and member.name == 'public/index.html':
                        data = b'evil';member.size = len(data)
                    out.addfile(member, io.BytesIO(data))
                if kind != 'tamper':
                    member = tarfile.TarInfo('../outside' if kind == 'traversal' else 'public/index.html')
                    member.mode = 0o644
                    if kind == 'symlink':
                        member.type = tarfile.SYMTYPE;member.linkname = '/etc/qs-forms/telegram.env'
                    out.addfile(member, io.BytesIO(b''))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify_archive(bad, B)

    def test_static_promotion_no_restart_and_protected_state_unchanged(self):
        before = self.protected_bytes()
        path = self.artifact()
        old_umask = os.umask(0o077)
        try:
            result = self.manager.operate(self.header(path), path)
        finally:
            os.umask(old_umask)
        self.assertEqual(result['source_sha'], B)
        self.assertEqual((self.manager.pointer(PUBLIC) / 'index.html').read_text(), 'next')
        self.assertFalse(any('systemctl' in c[0] for c in self.calls))
        self.assertEqual(before, self.protected_bytes())
        self.assertEqual(self.manager.pointer(PRIVATE).stat().st_mode & 0o777, 0o755)

    def test_backend_change_restarts_only_handler_before_UI_switch(self):
        path = self.artifact(backend='new code\n')
        observations = []
        def run(command):
            if 'systemctl' in command[0]:
                observations.append(self.manager.pointer(PUBLIC) == self.public)
            return self.run_fake(command)
        self.manager.runner = run
        before = self.protected_bytes()
        self.manager.operate(self.header(path), path)
        self.assertEqual(observations, [True])
        self.assertEqual([c for c in self.calls if 'systemctl' in c[0]], [['/usr/bin/systemctl', 'restart', 'qs-forms.service']])
        self.assertEqual(before, self.protected_bytes())

    def test_stale_current_SHA_stops_before_staging(self):
        path = self.artifact()
        with self.assertRaisesRegex(ValueError, 'stale_current_SHA'):
            self.manager.operate(self.header(path, current=C), path)
        self.assertEqual(self.manager.pointer(PUBLIC), self.public)
        self.assertFalse(self.manager.paths(B)[1].exists())

    def test_failed_backend_never_exposes_UI_and_manual_rollback_preserves_latest_state(self):
        path = self.artifact(backend='broken code\n')
        health = iter([True, False])
        self.manager.health = lambda: next(health)
        with self.assertRaisesRegex(ValueError, 'backend_unconfirmed'):
            self.manager.operate(self.header(path), path)
        self.assertEqual(self.manager.pointer(PUBLIC), self.public)
        self.assertEqual(self.manager.pointer(PRIVATE), self.manager.paths(B)[1])
        self.state.write_bytes(b'newer live state/HMAC/receipt must survive rollback')
        self.manager.health = lambda: True
        baseline_archive = self.root / 'baseline/website.tar'
        self.manager.operate(self.header(baseline_archive, sha=A, current=A, action='rollback'), baseline_archive)
        self.assertEqual(self.manager.pointer(PRIVATE), self.private)
        self.assertEqual(self.state.read_bytes(), b'newer live state/HMAC/receipt must survive rollback')

    def test_rollback_only_installed_exact_code(self):
        path = self.artifact()
        with self.assertRaises((ValueError, OSError)):
            self.manager.operate(self.header(path, action='rollback'), path)
        self.assertEqual(self.manager.pointer(PUBLIC), self.public)

    def test_transport_digest_rejects_without_mutation(self):
        path = self.artifact(); header = self.header(path);header['archive_sha256'] = '0' * 64
        before = self.protected_bytes()
        with self.assertRaisesRegex(ValueError, 'transport_digest'):
            self.manager.operate(header, path)
        self.assertEqual(self.manager.pointer(PUBLIC), self.public)
        self.assertEqual(before, self.protected_bytes())

    def test_rollback_to_previously_activated_SHA_and_unactivated_stage_refused(self):
        path_b = self.artifact()
        self.manager.operate(self.header(path_b), path_b)
        path_c = self.artifact(sha=C, text='third')
        self.manager.operate(self.header(path_c, sha=C, current=B), path_c)
        self.state.write_bytes(b'latest customer outcome after both releases')
        result = self.manager.operate(self.header(path_b, sha=B, current=C, action='rollback'), path_b)
        self.assertEqual(result['source_sha'], B)
        self.assertEqual(self.state.read_bytes(), b'latest customer outcome after both releases')
        (self.manager.paths(C)[0].parent / 'activation.json').unlink()
        with self.assertRaisesRegex(ValueError, 'not_previously_activated'):
            self.manager.operate(self.header(path_c, sha=C, current=B, action='rollback'), path_c)

    def test_interrupted_staging_is_journaled_before_any_pointer_change(self):
        path = self.artifact()
        def fail(archive, manifest):
            journal = json.loads(self.manager.p(CONTROL + '/last-operation.json').read_text())
            self.assertEqual(journal['phase'], 'staging_reserved')
            raise OSError('simulated interrupted staging')
        self.manager.stage = fail
        with self.assertRaises(OSError):self.manager.operate(self.header(path), path)
        self.assertEqual(self.manager.pointer(PUBLIC), self.public)
        self.assertEqual(self.manager.pointer(PRIVATE), self.private)

    def test_idempotent_confirmed_same_SHA_does_not_restart(self):
        path = self.artifact()
        self.manager.operate(self.header(path), path)
        self.calls.clear()
        result = self.manager.operate(self.header(path, current=B), path)
        self.assertEqual(result['status'], 'already_current_verified')
        self.assertFalse(any('systemctl' in c[0] for c in self.calls))

    def test_selected_CI_rejects_PR_fork_wrong_SHA_failure_or_expiry(self):
        run = {'id': 1, 'repository': {'full_name': '7Ilia7/QS'}, 'head_repository': {'full_name': '7Ilia7/QS'}, 'event': 'push', 'head_branch': 'main', 'head_sha': B, 'path': '.github/workflows/ci.yml', 'status': 'completed', 'conclusion': 'success'}
        artifact = {'id': 2, 'name': 'website-' + B, 'expired': False, 'size_in_bytes': 1000, 'digest': 'sha256:' + 'f' * 64, 'workflow_run': {'id': 1, 'head_sha': B}}
        self.assertEqual(select_metadata(run, [artifact], '7Ilia7/QS', B)['id'], 2)
        for key, value in [('event', 'pull_request'), ('head_repository', {'full_name': 'attacker/fork'}), ('head_sha', C), ('conclusion', 'failure'), ('path', '.github/workflows/other.yml')]:
            bad = copy.deepcopy(run);bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):select_metadata(bad, [artifact], '7Ilia7/QS', B)
        artifact['expired'] = True
        with self.assertRaises(ValueError):select_metadata(run, [artifact], '7Ilia7/QS', B)

    def test_zip_digest_verified_before_extract(self):
        archive = self.artifact();z = self.root / 'artifact.zip'
        with zipfile.ZipFile(z, 'w') as out:
            for name in ['website.tar', 'release.json', 'SHA256SUMS']:out.write(archive.parent / name, name)
        with self.assertRaisesRegex(ValueError, 'GitHub_artifact_digest'):
            unpack(z, self.root / 'bad-download', {'digest': 'sha256:' + '0' * 64}, B)
        self.assertFalse((self.root / 'bad-download').exists())
        m = unpack(z, self.root / 'good-download', {'digest': 'sha256:' + digest(z.read_bytes())}, B)
        self.assertEqual(m['source_sha'], B)

    def test_public_readback_checks_body_and_MIME_not_just_200(self):
        class Response(io.BytesIO):
            status = 200
            class Headers:
                def get_content_type(self):return 'text/html'
            headers = Headers()
        class Opener:
            def __init__(self, data):self.data = data
            def open(self, url, timeout):return Response(self.data)
        result = public_readback(self.baseline, opener=Opener(b'baseline'))
        self.assertEqual(len(result), 1)
        with self.assertRaisesRegex(ValueError, 'HTTPS_hash'):
            public_readback(self.baseline, opener=Opener(b'badbytes'))

    def test_lost_SSH_result_is_not_retried_and_private_temp_key_is_removed(self):
        archive = self.artifact();report = self.root / 'driver-report'
        class Reply:
            returncode = 255
            stdout = b''
        with patch.dict(os.environ, {'QS_DEPLOY_SSH_KEY': 'synthetic-local-key', 'QS_KNOWN_HOSTS': '165.245.223.138 ssh-ed25519 synthetic-public-key'}), patch('deploy.subprocess.run', return_value=Reply()) as run, patch('deploy.public_readback') as readback:
            with self.assertRaisesRegex(ValueError, 'unconfirmed'):
                deploy('promote', archive.parent, A, report)
            self.assertEqual(run.call_count, 1)
            readback.assert_not_called()
            args = run.call_args.args[0]
            self.assertFalse(Path(args[args.index('-i') + 1]).exists())
        data = (report / 'result.json').read_text()
        self.assertNotIn('synthetic-local-key', data)
        self.assertEqual(json.loads(data)['status'], 'SSH_invocation_started_unknown_until_receipt')


if __name__ == '__main__':
    unittest.main()
