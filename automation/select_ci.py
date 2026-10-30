"""Select one successful trusted main push run and verify its downloaded ZIP digest."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile
from release_lib import SHA, MAX_BYTES, digest, require, validate_manifest, verify_archive


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', '--method', 'GET', path], text=True))


def select_metadata(run, artifacts, repository, sha):
    require(SHA.fullmatch(sha), 'selected_SHA')
    require(run['repository']['full_name'].lower() == repository.lower() and run['head_repository']['full_name'].lower() == repository.lower(), 'foreign_repository')
    require(run['event'] == 'push' and run['head_branch'] == 'main' and run['head_sha'] == sha, 'untrusted_run_source')
    require(run['path'] == '.github/workflows/ci.yml', 'wrong_workflow')
    require(run['status'] == 'completed' and run['conclusion'] == 'success', 'CI_not_successful')
    found = [a for a in artifacts if a['name'] == 'website-' + sha]
    require(len(found) == 1 and not found[0]['expired'], 'missing_or_ambiguous_artifact')
    artifact = found[0]
    require(0 < artifact['size_in_bytes'] <= MAX_BYTES + 1024 * 1024, 'artifact_size')
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', artifact.get('digest', '')), 'artifact_digest_required')
    require(artifact['workflow_run']['head_sha'] == sha and artifact['workflow_run']['id'] == run['id'], 'artifact_run_binding')
    return artifact


def unpack(zip_path, output, artifact, sha):
    require(zip_path.stat().st_size <= MAX_BYTES + 1024 * 1024, 'download_size')
    require('sha256:' + digest(zip_path.read_bytes()) == artifact['digest'], 'GitHub_artifact_digest_mismatch')
    output.mkdir(exist_ok=False)
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        require(len(names) == 3 and set(names) == {'website.tar', 'release.json', 'SHA256SUMS'}, 'ZIP_allowlist')
        for item in archive.infolist():
            require(item.file_size <= MAX_BYTES and item.compress_size <= MAX_BYTES and not item.is_dir(), 'ZIP_entry')
            require((item.external_attr >> 16) & 0o170000 != 0o120000, 'ZIP_symlink')
            with (output / item.filename).open('xb') as dest, archive.open(item) as source:
                remaining = item.file_size
                while remaining:
                    block = source.read(min(1024 * 1024, remaining))
                    require(bool(block), 'ZIP_truncated')
                    dest.write(block)
                    remaining -= len(block)
    m = verify_archive(output / 'website.tar', sha)
    require(validate_manifest(json.loads((output / 'release.json').read_text()), sha) == m, 'external_manifest_mismatch')
    require((output / 'SHA256SUMS').read_text() == digest((output / 'website.tar').read_bytes()) + '  website.tar\n', 'archive_checksum')
    return m


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'[1-9][0-9]{0,18}', args.run_id), 'run_id')
    require(SHA.fullmatch(args.source_sha), 'selected_SHA')
    repository = os.environ['GITHUB_REPOSITORY']
    require(repository.lower() == '7ilia7/qs', 'repository')
    require(os.environ['GITHUB_REF'] == 'refs/heads/main', 'dispatch_from_main_only')
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.source_sha, 'origin/main'], check=True)
    run = api('repos/' + repository + '/actions/runs/' + args.run_id)
    artifacts = api('repos/' + repository + '/actions/runs/' + args.run_id + '/artifacts?per_page=100')
    require(artifacts['total_count'] <= 100, 'unexpected_artifact_count')
    chosen = select_metadata(run, artifacts['artifacts'], repository, args.source_sha)
    zip_path = args.output.with_suffix('.zip')
    with zip_path.open('xb') as dest:
        subprocess.run(['gh', 'api', '--method', 'GET', 'repos/' + repository + '/actions/artifacts/' + str(chosen['id']) + '/zip'], stdout=dest, check=True)
    unpack(zip_path, args.output, chosen, args.source_sha)
    receipt = {'run_id': run['id'], 'run_attempt': run['run_attempt'], 'source_sha': args.source_sha, 'artifact_id': chosen['id'], 'GitHub_ZIP_digest': chosen['digest'], 'trusted_event': 'push', 'branch': 'main', 'workflow': run['path']}
    (args.output / 'selection.json').write_text(json.dumps(receipt, indent=2) + '\n')
    zip_path.unlink()
    print(json.dumps(receipt))
