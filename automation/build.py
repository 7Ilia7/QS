"""Build only explicit source members; identical source yields identical tar bytes."""
import argparse
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
from release_lib import canonical, digest, require, safe_path, validate_manifest, verify_archive, TOKEN, SHA


def verify_git_sources(root, source_sha, source_bytes):
    top = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=root, text=True).strip()).resolve()
    require(top == root, 'source_repository_root')
    tree = subprocess.check_output(['git', 'ls-tree', '-rz', '--full-tree', source_sha, '--', 'site', 'app', 'release/allowlist.json'], cwd=root)
    tracked = {}
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        require(mode in {'100644', '100755'} and kind == 'blob', 'source_not_HEAD_blob')
        tracked[name.decode()] = oid
    require(set(tracked) == set(source_bytes), 'source_not_HEAD_allowlist')
    for name, data in source_bytes.items():
        oid = subprocess.check_output(['git', 'hash-object', '--stdin'], cwd=root, input=data).decode().strip()
        require(oid == tracked[name], 'source_bytes_not_HEAD')


def build(root, source_sha, output, *, git_provenance=False):
    root = root.resolve(strict=True)
    require(bool(SHA.fullmatch(source_sha)), 'source_identity')
    for folder in ['site', 'app']:
        base = root / folder
        mode = base.lstat().st_mode
        require(not stat.S_ISLNK(mode), 'source_root_symlink')
        require(stat.S_ISDIR(mode), 'source_root_directory')
        require(base.resolve(strict=True) == root / folder, 'source_root_escape')
    allow_bytes = (root / 'release/allowlist.json').read_bytes()
    allow = json.loads(allow_bytes)
    require(set(allow) == {'schema', 'public', 'private'} and allow['schema'] == 'website.source-allowlist.v1', 'allowlist_schema')
    rows, data_by_name = [], {}
    source_bytes = {'release/allowlist.json': allow_bytes}
    for component, folder in [('public', 'site'), ('private', 'app')]:
        names = allow[component]
        require(isinstance(names, list) and len(names) == len(set(names)) and names == sorted(names), 'allowlist_order')
        base = root / folder
        actual = set()
        for f in base.rglob('*'):
            require(not f.is_symlink(), 'source_symlink')
            if f.is_file():
                actual.add(f.relative_to(base).as_posix())
        require(actual == set(names), 'source_allowlist_mismatch')
        for name in names:
            safe_path(name, component)
            data = (base / name).read_bytes()
            require(not TOKEN.search(data), 'credential_pattern')
            rows.append({'component': component, 'path': name, 'bytes': len(data), 'sha256': digest(data)})
            data_by_name[component + '/' + name] = data
            source_bytes[folder + '/' + name] = data
    if git_provenance:
        verify_git_sources(root, source_sha, source_bytes)
    rows.sort(key=lambda r: (r['component'], r['path']))
    m = validate_manifest({'schema': 'website.release.v1', 'source_sha': source_sha, 'files': rows, 'payload_digest': digest(canonical(rows))})
    output.mkdir(parents=True, exist_ok=False)
    metadata = canonical(m) + b'\n'
    with tarfile.open(output / 'website.tar', 'w', format=tarfile.USTAR_FORMAT) as tf:
        for name, data in [('release.json', metadata)] + sorted(data_by_name.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime, info.uid, info.gid = len(data), 0o644, 0, 0, 0
            tf.addfile(info, io.BytesIO(data))
    verify_archive(output / 'website.tar', source_sha)
    (output / 'release.json').write_bytes(metadata)
    (output / 'SHA256SUMS').write_text(digest((output / 'website.tar').read_bytes()) + '  website.tar\n')
    return m


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == args.source_sha, 'HEAD_mismatch')
    require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root, text=True).strip(), 'tracked_source_dirty')
    manifest = build(root, args.source_sha, args.output, git_provenance=True)
    print(json.dumps({'source_sha': manifest['source_sha'], 'payload_digest': manifest['payload_digest'], 'files': len(manifest['files'])}))
