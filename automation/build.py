"""Build only explicit source members; identical source yields identical tar bytes."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
from release_lib import canonical, digest, require, safe_path, validate_manifest, verify_archive, TOKEN


def build(root, source_sha, output):
    allow = json.loads((root / 'release/allowlist.json').read_text())
    require(set(allow) == {'schema', 'public', 'private'} and allow['schema'] == 'website.source-allowlist.v1', 'allowlist_schema')
    rows, data_by_name = [], {}
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
    manifest = build(root, args.source_sha, args.output)
    print(json.dumps({'source_sha': manifest['source_sha'], 'payload_digest': manifest['payload_digest'], 'files': len(manifest['files'])}))
