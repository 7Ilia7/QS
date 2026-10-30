"""Real clean-Git CLI regressions; external data stays in owned temp fixtures."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

OBSERVATIONS = []
AUTOMATION = Path(__file__).resolve().parents[1] / 'automation'


class BuildCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'repo'
        for name in ['site', 'app/backend', 'release', 'automation']:
            (self.repo / name).mkdir(parents=True, exist_ok=True)
        (self.repo / 'site/index.html').write_text('owned fixture public one')
        (self.repo / 'app/backend/server.py').write_text('# owned fixture private one\n')
        (self.repo / 'release/allowlist.json').write_text(json.dumps({'schema': 'website.source-allowlist.v1', 'public': ['index.html'], 'private': ['backend/server.py']}))
        for name in ['build.py', 'release_lib.py']:
            shutil.copyfile(AUTOMATION / name, self.repo / 'automation' / name)
        self.git('init', '--quiet')

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, text=True).strip()

    def commit(self, paths=('site', 'app', 'release', 'automation')):
        self.git('add', '--', *paths)
        self.git('-c', 'user.name=CI Fixture', '-c', 'user.email=fixture@localhost', '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '--quiet', '-m', 'Owned CLI fixture')
        return self.git('rev-parse', 'HEAD')

    def run_build(self, sha, number):
        output = self.root / ('artifact-' + str(number))
        result = subprocess.run([sys.executable, '-B', str(self.repo / 'automation/build.py'), '--source-sha', sha, '--output', str(output)], cwd=self.repo, capture_output=True, text=True)
        return result, output

    def root_link(self, component, relative):
        outside = self.root / 'external' / component
        outside.parent.mkdir()
        shutil.move(str(self.repo / component), outside)
        target = os.path.relpath(outside, self.repo) if relative else str(outside)
        (self.repo / component).symlink_to(target, target_is_directory=True)
        sha = self.commit()
        record = {'case': component + ('_relative' if relative else '_absolute'), 'HEAD': sha, 'tracked_root': self.git('ls-files', '--stage', '--', component), 'attempts': []}
        for number in [1, 2]:
            self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no'), '')
            result, output = self.run_build(sha, number)
            record['attempts'].append({'exit': result.returncode, 'artifact_directory_created': output.exists(), 'HEAD': self.git('rev-parse', 'HEAD'), 'clean': self.git('status', '--porcelain', '--untracked-files=no') == '', 'payload_digest': json.loads((output / 'release.json').read_text())['payload_digest'] if (output / 'release.json').exists() else None})
            changed = outside / ('index.html' if component == 'site' else 'backend/server.py')
            changed.write_text('owned external untracked bytes changed')
        OBSERVATIONS.append(record)
        self.assertTrue(all(r['exit'] != 0 for r in record['attempts']), record)
        self.assertTrue(all(not r['artifact_directory_created'] for r in record['attempts']), record)
        self.assertTrue(all(r['HEAD'] == sha and r['clean'] for r in record['attempts']))

    def test_site_absolute_root_symlink(self):
        self.root_link('site', False)

    def test_site_relative_root_symlink(self):
        self.root_link('site', True)

    def test_app_absolute_root_symlink(self):
        self.root_link('app', False)

    def test_app_relative_root_symlink(self):
        self.root_link('app', True)

    def test_normal_clean_Git_CLI_build_is_deterministic(self):
        sha = self.commit()
        first, a = self.run_build(sha, 1)
        second, b = self.run_build(sha, 2)
        self.assertEqual((first.returncode, second.returncode), (0, 0), first.stderr + second.stderr)
        self.assertEqual((a / 'website.tar').read_bytes(), (b / 'website.tar').read_bytes())
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no'), '')
        OBSERVATIONS.append({'case': 'normal_clean_git', 'HEAD': sha, 'exit_codes': [first.returncode, second.returncode], 'byte_equal': True})

    def test_nested_symlink_still_rejected_by_CLI(self):
        target = self.root / 'external-file'
        target.write_text('owned outside bytes')
        f = self.repo / 'site/index.html'
        f.unlink()
        f.symlink_to(target)
        sha = self.commit()
        result, output = self.run_build(sha, 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_untracked_declared_source_is_not_HEAD_provenance(self):
        sha = self.commit(('release', 'automation'))
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no'), '')
        result, output = self.run_build(sha, 1)
        OBSERVATIONS.append({'case': 'untracked_declared_source', 'HEAD': sha, 'exit': result.returncode, 'artifact_directory_created': output.exists()})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_assume_unchanged_cannot_hide_non_HEAD_bytes(self):
        sha = self.commit()
        self.git('update-index', '--assume-unchanged', 'site/index.html')
        (self.repo / 'site/index.html').write_text('changed working bytes hidden from status')
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no'), '')
        result, output = self.run_build(sha, 1)
        OBSERVATIONS.append({'case': 'assume_unchanged_source', 'HEAD': sha, 'exit': result.returncode, 'artifact_directory_created': output.exists()})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
