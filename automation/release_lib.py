"""Portable artifact validation. No provider, credential or runtime-state access."""
import hashlib
import json
import re
import tarfile
from pathlib import PurePosixPath

MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 512
SHA = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
TOKEN = re.compile(rb"\b[0-9]{6,12}:[A-Za-z0-9_-]{30,50}\b")
PUBLIC_EXT = {'.html', '.css', '.js', '.xml', '.txt', '.webp', '.png', '.jpg', '.jpeg', '.svg', '.avif', '.woff2', '.mp4', '.webm', '.pdf', '.ico'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(value, component):
    require(isinstance(value, str) and len(value) <= 180, 'invalid_path')
    p = PurePosixPath(value)
    require(not p.is_absolute() and str(p) == value, 'noncanonical_path')
    require(all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', x) and x not in {'.', '..'} for x in p.parts), 'unsafe_path')
    require(p.parts and not any(x.lower() in {'env', 'state', 'secrets', 'node_modules', '__pycache__'} or x.lower().endswith(('.env', '.pem', '.key')) for x in p.parts), 'private_material_path')
    if component == 'public':
        require(p.suffix.lower() in PUBLIC_EXT and p.parts[0] not in {'backend', 'tests', 'automation'}, 'public_type')
    return value


def validate_manifest(m, expected_sha=None):
    require(isinstance(m, dict) and set(m) == {'schema', 'source_sha', 'files', 'payload_digest'}, 'manifest_fields')
    require(m['schema'] == 'website.release.v1' and bool(SHA.fullmatch(m['source_sha'])), 'source_identity')
    require(expected_sha is None or m['source_sha'] == expected_sha, 'source_mismatch')
    rows = m['files']
    require(isinstance(rows, list) and 2 <= len(rows) <= MAX_FILES, 'file_count')
    names = set()
    total = 0
    for r in rows:
        require(isinstance(r, dict) and set(r) == {'component', 'path', 'bytes', 'sha256'}, 'row_fields')
        require(r['component'] in {'public', 'private'}, 'component')
        safe_path(r['path'], r['component'])
        name = r['component'] + '/' + r['path']
        require(name not in names, 'duplicate_path')
        names.add(name)
        require(type(r['bytes']) is int and 0 <= r['bytes'] <= MAX_BYTES, 'file_size')
        require(isinstance(r['sha256'], str) and bool(HASH.fullmatch(r['sha256'])), 'file_hash')
        total += r['bytes']
    require(total <= MAX_BYTES - 1024 * 1024, 'payload_size')
    require('public/index.html' in names and 'private/backend/server.py' in names, 'required_entrypoints')
    require(rows == sorted(rows, key=lambda r: (r['component'], r['path'])), 'row_order')
    require(m['payload_digest'] == digest(canonical(rows)), 'payload_digest')
    return m


def verify_archive(path, expected_sha=None):
    require(path.stat().st_size <= MAX_BYTES, 'archive_size')
    with tarfile.open(path, 'r:') as tf:
        members = tf.getmembers()
        require(1 <= len(members) <= MAX_FILES + 1, 'archive_count')
        require(members[0].name == 'release.json' and members[0].size <= 128 * 1024, 'manifest_first')
        require(members[0].isfile(), 'manifest_type')
        m = validate_manifest(json.load(tf.extractfile(members[0])), expected_sha)
        expected = {r['component'] + '/' + r['path']: r for r in m['files']}
        require(len(members) == len(expected) + 1, 'archive_allowlist')
        seen = {'release.json'}
        for member in members:
            require(member.isfile() and not member.pax_headers and member.mode == 0o644, 'archive_member_type')
        for member in members[1:]:
            require(member.name in expected and member.name not in seen, 'archive_path')
            seen.add(member.name)
            row = expected[member.name]
            require(member.size == row['bytes'], 'archive_member_size')
            data = tf.extractfile(member).read(MAX_BYTES + 1)
            require(len(data) == row['bytes'] and digest(data) == row['sha256'], 'archive_member_hash')
            require(not TOKEN.search(data), 'credential_pattern')
        return m
