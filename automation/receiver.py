"""Fixed QS deployment endpoint. Install root-owned; invoke only by forced SSH command.

Never imports artifact code, reads an environment/ledger, initializes state, changes
Caddy or executes a caller-provided command. Test roots exist only as library API.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_lib import MAX_BYTES, SHA, HASH, canonical, digest, require, validate_manifest, verify_archive

PUBLIC = '/srv/hair-sites/qc'
PRIVATE = '/srv/hair-sites/qc-backend'
CONTROL = '/var/lib/qs-release'


def system(command):
    return subprocess.check_output(command, text=True, timeout=35).strip()


def private_health():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(12):
        try:
            with opener.open('http://127.0.0.1:8787/health', timeout=2) as response:
                if response.status == 200 and json.load(response) == {'status': 'ok', 'service': 'qs-forms', 'version': 1}:
                    return True
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    return False


def atomic_json(path, value):
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        os.chmod(temporary, 0o600)
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Manager:
    def __init__(self, config, root=Path('/'), runner=system, health=private_health):
        self.config, self.root, self.runner, self.health = config, root.resolve(), runner, health
        validate_manifest(config['baseline_manifest'])
        require(SHA.fullmatch(config['baseline_manifest']['source_sha']), 'baseline_SHA')
        require(config['baseline_label'] == 'qc-20261030-existing-v1', 'baseline_label')
        require(HASH.fullmatch(config['mono_id']), 'shared_identity')
        self.owner = 0 if root == Path('/') else os.getuid()

    def p(self, value):
        return self.root / value.lstrip('/')

    def secure_directory(self, path):
        s = path.lstat()
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == self.owner and not s.st_mode & 0o022, 'unsafe_directory')

    def baseline_paths(self):
        label = self.config['baseline_label']
        return self.p(PUBLIC + '/releases/' + label + '/dist'), self.p(PRIVATE + '/releases/' + label)

    def paths(self, sha):
        require(bool(SHA.fullmatch(sha)), 'target_SHA')
        if sha == self.config['baseline_manifest']['source_sha']:
            return self.baseline_paths()
        return self.p(PUBLIC + '/releases/' + sha + '/dist'), self.p(PRIVATE + '/releases/' + sha)

    def pointer(self, base):
        p = self.p(base + '/current')
        s = p.lstat()
        require(stat.S_ISLNK(s.st_mode) and s.st_uid == self.owner, 'unsafe_pointer')
        resolved = p.resolve(strict=True)
        require(resolved.is_relative_to(self.p(base + '/releases').resolve()), 'pointer_escape')
        return resolved

    def current(self):
        public = self.pointer(PUBLIC)
        if public == self.baseline_paths()[0]:
            return self.config['baseline_manifest']
        require(public.name == 'dist' and SHA.fullmatch(public.parent.name), 'unknown_current')
        return validate_manifest(json.loads((public.parent / 'release.json').read_text()), public.parent.name)

    def verify_installed(self, manifest, public, private):
        for component, base in [('public', public), ('private', private)]:
            self.secure_directory(base)
            rows = [r for r in manifest['files'] if r['component'] == component]
            actual = set()
            for path in base.rglob('*'):
                require(not path.is_symlink(), 'installed_symlink')
                if path.is_file():
                    actual.add(path.relative_to(base).as_posix())
                else:
                    self.secure_directory(path)
            require(actual == {r['path'] for r in rows}, 'installed_allowlist')
            for row in rows:
                f = base / row['path']
                s = f.lstat()
                require(stat.S_ISREG(s.st_mode) and s.st_uid == self.owner and not s.st_mode & 0o022, 'installed_permissions')
                require(s.st_size == row['bytes'] and digest(f.read_bytes()) == row['sha256'], 'installed_hash')

    def shared(self):
        course = self.p('/srv/hair-sites/course/current').resolve(strict=True)
        result = {'caddy': digest(self.p('/etc/caddy/Caddyfile').read_bytes()), 'course_target': str(course),
                  'course_files': [(str(f.relative_to(course)), digest(f.read_bytes())) for f in sorted(course.rglob('*')) if f.is_file()]}
        result['mono'] = self.runner(['/usr/bin/docker', 'inspect', '--format', '{{.Id}}|{{.State.StartedAt}}|{{.RestartCount}}|{{.State.OOMKilled}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}', self.config['mono_id']])
        for name, mode, directory in [('/etc/qs-forms/telegram.env', 0o600, False), ('/var/lib/qs-forms', 0o700, True), ('/var/lib/qs-forms/outcomes.json', 0o600, False)]:
            s = self.p(name).lstat()
            owner = self.owner if name.startswith('/etc/') else (33 if self.root == Path('/') else os.getuid())
            require((stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode)) and stat.S_IMODE(s.st_mode) == mode and s.st_uid == owner, 'private_permissions')
        return result

    def status(self):
        m = self.current()
        public, private = self.pointer(PUBLIC), self.pointer(PRIVATE)
        try:
            self.verify_installed(m, public, private)
            matched = True
        except (ValueError, OSError):
            matched = False
        journal = self.p(CONTROL + '/last-operation.json')
        return {'source_sha': m['source_sha'], 'payload_digest': m['payload_digest'], 'public_target': str(public),
                'private_target': str(private), 'code_matches_current_manifest': matched, 'private_health': self.health(),
                'last_operation': json.loads(journal.read_text()) if journal.exists() else None}

    def switch(self, base, target):
        p = self.p(base + '/current')
        temporary = p.with_name('.current.' + uuid.uuid4().hex)
        temporary.symlink_to(os.path.relpath(target, p.parent))
        os.replace(temporary, p)
        fd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def stage(self, archive, m):
        sha = m['source_sha']
        public, private = self.paths(sha)
        require(not public.parent.exists() and not private.exists(), 'existing_release_no_overwrite')
        stages = [self.p(PUBLIC + '/releases/.stage-' + uuid.uuid4().hex), self.p(PRIVATE + '/releases/.stage-' + uuid.uuid4().hex)]
        for f in stages:
            f.mkdir(mode=0o755)
            f.chmod(0o755)
        (stages[0] / 'dist').mkdir(mode=0o755)
        (stages[0] / 'dist').chmod(0o755)
        with tarfile.open(archive, 'r:') as tf:
            for row in m['files']:
                name = row['component'] + '/' + row['path']
                dest = (stages[0] / 'dist' if row['component'] == 'public' else stages[1]) / row['path']
                dest.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                parent = dest.parent
                boundary = stages[0] if row['component'] == 'public' else stages[1]
                while parent != boundary:
                    parent.chmod(0o755)
                    parent = parent.parent
                with dest.open('xb') as output, tf.extractfile(name) as source:
                    shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
                dest.chmod(0o644)
        with (stages[0] / 'release.json').open('xb') as output:
            output.write(canonical(m) + b'\n')
            output.flush()
            os.fsync(output.fileno())
        self.verify_installed(m, stages[0] / 'dist', stages[1])
        for stage in stages:
            for directory in sorted([stage] + [p for p in stage.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
                sync_directory(directory)
        os.rename(stages[0], public.parent)
        sync_directory(public.parent.parent)
        os.rename(stages[1], private)
        sync_directory(private.parent)
        return public, private

    def operate(self, header, archive):
        require(set(header) == {'action', 'source_sha', 'expected_current', 'archive_sha256', 'bytes'}, 'request_fields')
        require(header['action'] in {'promote', 'rollback'}, 'request_action')
        require(SHA.fullmatch(header['source_sha']) and SHA.fullmatch(header['expected_current']), 'request_SHA')
        require(HASH.fullmatch(header['archive_sha256']) and type(header['bytes']) is int and header['bytes'] == archive.stat().st_size, 'request_archive')
        require(digest(archive.read_bytes()) == header['archive_sha256'], 'transport_digest')
        m = verify_archive(archive, header['source_sha'])
        for base in [PUBLIC, PRIVATE, PUBLIC + '/releases', PRIVATE + '/releases', CONTROL]:
            self.secure_directory(self.p(base))
        with self.p(CONTROL + '/lock').open('a+b') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            current = self.current()
            require(current['source_sha'] == header['expected_current'], 'stale_current_SHA')
            shared = self.shared()
            target_public, target_private = self.paths(m['source_sha'])
            if header['action'] == 'promote' and current['source_sha'] == m['source_sha']:
                self.verify_installed(m, self.pointer(PUBLIC), self.pointer(PRIVATE))
                require(self.health(), 'existing_release_unhealthy')
                return {'status': 'already_current_verified', **self.status()}
            require(self.health() or header['action'] == 'rollback', 'initial_handler_unhealthy')
            journal = {'action': header['action'], 'source_sha': m['source_sha'], 'previous_sha': current['source_sha'], 'phase': 'staging_reserved', 'started_at': time.time()}
            journal_path = self.p(CONTROL + '/last-operation.json')
            atomic_json(journal_path, journal)
            if header['action'] == 'promote':
                target_public, target_private = self.stage(archive, m)
            else:
                if m['source_sha'] != self.config['baseline_manifest']['source_sha']:
                    activated = target_public.parent / 'activation.json'
                    require(activated.is_file() and not activated.is_symlink(), 'rollback_target_not_previously_activated')
                    marker = json.loads(activated.read_text())
                    require(marker['source_sha'] == m['source_sha'] and marker['payload_digest'] == m['payload_digest'], 'rollback_activation_identity')
                self.verify_installed(m, target_public, target_private)
            journal['phase'] = 'staged'
            atomic_json(journal_path, journal)
            previous_private = self.pointer(PRIVATE)
            self.secure_directory(previous_private)
            for path in previous_private.rglob('*'):
                require(not path.is_symlink(), 'previous_code_symlink')
            previous_private_hashes = {p.relative_to(previous_private).as_posix(): digest(p.read_bytes()) for p in previous_private.rglob('*') if p.is_file()}
            selected_private_hashes = {r['path']: r['sha256'] for r in m['files'] if r['component'] == 'private'}
            backend_changed = previous_private_hashes != selected_private_hashes
            journal.update(phase='backend_switch_reserved', backend_restart_needed=backend_changed)
            atomic_json(journal_path, journal)
            self.switch(PRIVATE, target_private)
            if backend_changed:
                self.runner(['/usr/bin/systemctl', 'restart', 'qs-forms.service'])
            require(self.health(), 'backend_unconfirmed_manual_reconcile')
            journal['phase'] = 'backend_ready_UI_switch_reserved'
            atomic_json(journal_path, journal)
            require(self.current()['source_sha'] == header['expected_current'], 'pointer_drift')
            self.switch(PUBLIC, target_public)
            self.verify_installed(m, self.pointer(PUBLIC), self.pointer(PRIVATE))
            require(self.shared() == shared, 'shared_state_drift_manual_reconcile')
            if m['source_sha'] != self.config['baseline_manifest']['source_sha']:
                atomic_json(target_public.parent / 'activation.json', {'source_sha': m['source_sha'], 'payload_digest': m['payload_digest'], 'local_activation_verified_at': time.time()})
            journal.update(phase='activated_local_verified', finished_at=time.time())
            atomic_json(journal_path, journal)
            return {'status': 'activated_local_verified', **self.status()}


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1, 'fixed_privileged_endpoint')
    os.umask(0o077)
    config_path = Path('/etc/qs-release/config.json')
    s = config_path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022, 'unsafe_configuration')
    manager = Manager(json.loads(config_path.read_text()))
    raw = sys.stdin.buffer.readline(8193)
    require(len(raw) <= 8192 and raw.endswith(b'\n'), 'header_size')
    header = json.loads(raw)
    if header == {'action': 'status'}:
        print(json.dumps(manager.status()))
        return
    require(type(header.get('bytes')) is int and 0 < header['bytes'] <= MAX_BYTES, 'bounded_input')
    with tempfile.TemporaryDirectory(prefix='incoming-', dir=CONTROL) as tmp:
        archive = Path(tmp) / 'website.tar'
        with archive.open('xb') as output:
            remaining = header['bytes']
            while remaining:
                data = sys.stdin.buffer.read(min(1024 * 1024, remaining))
                require(bool(data), 'truncated_input')
                output.write(data)
                remaining -= len(data)
        require(not sys.stdin.buffer.read(1), 'extra_input')
        print(json.dumps(manager.operate(header, archive)))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        code = str(error) if isinstance(error, ValueError) else type(error).__name__
        print(json.dumps({'status': 'stopped_or_unconfirmed', 'code': code, 'automatic_retry': False}))
        sys.exit(2)
