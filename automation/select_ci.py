"""Select one successful trusted main push run and verify its downloaded ZIP digest."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile
from release_lib import SHA, MAX_BYTES, digest, require, validate_manifest, verify_archive
from delivery_policy import delivery_context, selected_head_is_current, validate_delivery


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
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repository = os.environ['GITHUB_REPOSITORY']
    context = delivery_context(os.environ['GITHUB_EVENT_NAME'], json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()), repository, os.environ['GITHUB_REF'], os.environ.get('QS_AUTO_CD_READY') == 'true')
    def skipped(reason):
        args.output.mkdir(exist_ok=False)
        (args.output / 'selection.json').write_text(json.dumps({'eligible': False, 'reason': reason}) + '\n')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('eligible=false\n')
        print(json.dumps({'eligible': False, 'reason': reason}))
    if context is None:
        skipped('event_not_eligible_or_bootstrap_not_enabled')
        raise SystemExit(0)
    sha, run_id = context['source_sha'], str(context['run_id'])
    run = api('repos/' + repository + '/actions/runs/' + run_id)
    artifacts = api('repos/' + repository + '/actions/runs/' + run_id + '/artifacts?per_page=100')
    require(artifacts['total_count'] <= 100, 'unexpected_artifact_count')
    chosen = select_metadata(run, artifacts['artifacts'], repository, sha)
    require(run['id'] == context['run_id'], 'event_run_binding')
    delivery = validate_delivery({'kind': context['kind'], 'workflow_id': run['workflow_id'], 'run_number': run['run_number'], 'run_id': run['id']})
    latest = api('repos/' + repository + '/git/ref/heads/main')['object']['sha']
    if not selected_head_is_current(delivery['kind'], sha, latest):
        skipped('stale_main_SHA')
        raise SystemExit(0)
    subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'origin/main'], check=True)
    zip_path = args.output.with_suffix('.zip')
    with zip_path.open('xb') as dest:
        subprocess.run(['gh', 'api', '--method', 'GET', 'repos/' + repository + '/actions/artifacts/' + str(chosen['id']) + '/zip'], stdout=dest, check=True)
    unpack(zip_path, args.output, chosen, sha)
    receipt = {'eligible': True, 'run_id': run['id'], 'run_attempt': run['run_attempt'], 'source_sha': sha, 'artifact_id': chosen['id'], 'GitHub_ZIP_digest': chosen['digest'], 'trusted_event': 'push', 'branch': 'main', 'workflow': run['path'], 'delivery': delivery, 'expected_current': context['expected_current'], 'latest_main_at_selection': latest}
    (args.output / 'selection.json').write_text(json.dumps(receipt, indent=2) + '\n')
    zip_path.unlink()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('eligible=true\n')
    print(json.dumps(receipt))
