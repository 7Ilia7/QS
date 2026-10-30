"""One mutation at most; bounded GET-only DNS recovery and status-only verification."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from release_lib import SHA, HASH, MAX_BYTES, canonical, digest, require, verify_archive
from delivery_policy import validate_delivery, is_new_auto_run, selected_head_is_current, TERMINAL_PHASES

ORIGIN = 'https://quality-service-hair.165-245-223-138.sslip.io'
HOST = '165.245.223.138'
GET_TIMEOUT = 25
RESOURCE_BUDGET = 90
READBACK_BUDGET = 600
DNS_BACKOFF = (1, 3)  # three attempts total, only demonstrated EAI_AGAIN
MIME = {'.html': {'text/html'}, '.js': {'application/javascript', 'text/javascript'}, '.css': {'text/css'}, '.xml': {'application/xml', 'text/xml'}, '.txt': {'text/plain'}, '.webp': {'image/webp'}, '.mp4': {'video/mp4'}, '.webm': {'video/webm'}, '.png': {'image/png'}, '.jpg': {'image/jpeg'}, '.jpeg': {'image/jpeg'}, '.svg': {'image/svg+xml'}, '.avif': {'image/avif'}, '.woff2': {'font/woff2'}, '.pdf': {'application/pdf'}, '.ico': {'image/x-icon', 'image/vnd.microsoft.icon'}}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('unexpected_HTTPS_redirect')


def latest_main():
    from select_ci import api
    return api('repos/7Ilia7/QS/git/ref/heads/main')['object']['sha']


def is_ancestor(earlier, later):
    return subprocess.call(['git', 'merge-base', '--is-ancestor', earlier, later], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0


def temporary_dns(error):
    """Only an actual gaierror(EAI_AGAIN), including nested URLError.reason."""
    seen = set()
    while isinstance(error, urllib.error.URLError) and id(error) not in seen:
        seen.add(id(error))
        error = error.reason
    return isinstance(error, socket.gaierror) and error.errno == socket.EAI_AGAIN


def read_resource(row, origin, opener, timeout, deadline, clock):
    with opener.open(origin + '/' + row['path'], timeout=timeout) as response:
        require(response.status == 200, 'HTTPS_status')
        mime = response.headers.get_content_type()
        expected_mimes = MIME.get(Path(row['path']).suffix)
        require(expected_mimes is not None and mime in expected_mimes, 'HTTPS_MIME')
        hasher, size = hashlib.sha256(), 0
        while True:
            require(clock() < deadline, 'HTTPS_readback_budget_exhausted')
            block = response.read1(min(1024 * 1024, row['bytes'] + 1 - size))
            require(clock() < deadline, 'HTTPS_readback_budget_exhausted')
            if not block:
                break
            size += len(block)
            require(size <= row['bytes'], 'HTTPS_size')
            hasher.update(block)
        require(size == row['bytes'] and hasher.hexdigest() == row['sha256'], 'HTTPS_hash')
    return {'path': row['path'], 'status': 200, 'bytes': size, 'sha256': hasher.hexdigest(), 'MIME': mime, 'TLS': 'default_CA_hostname_verification'}


def resource_process(row, remaining):
    """Parent kills/reaps this GET-only child even if libc DNS never returns."""
    try:
        reply = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--readback-resource'], input=canonical({'row': row, 'budget': remaining}), capture_output=True, timeout=remaining)
    except subprocess.TimeoutExpired:
        raise ValueError('HTTPS_readback_budget_exhausted') from None
    require(reply.returncode == 0, 'HTTPS_readback_worker_unconfirmed')
    value = json.loads(reply.stdout)
    if 'error' in value:
        error = value['error']
        if error['temporary_DNS_EAI_AGAIN']:
            raise urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, 'Temporary failure in name resolution'))
        raise ValueError(error['code'])
    return value['resource']


def resource_worker():
    # Internal protocol: bounded nonsecret public row, no transport or mutation
    # handler reachable from this mode. Origin and TLS policy are fixed here.
    raw = sys.stdin.buffer.read(8193)
    require(len(raw) <= 8192, 'resource_input_size')
    request = json.loads(raw)
    row, budget = request['row'], request['budget']
    require(type(budget) in (int, float) and 0 < budget <= RESOURCE_BUDGET, 'resource_budget')
    require(row['component'] == 'public' and type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_BYTES and HASH.fullmatch(row['sha256']), 'resource_identity')
    path = row['path']
    require(isinstance(path, str) and 0 < len(path) <= 2048 and not PurePosixPath(path).is_absolute() and PurePosixPath(path).as_posix() == path and '..' not in PurePosixPath(path).parts and not any(c in path for c in '\\?#%\r\n'), 'resource_path')
    try:
        value = read_resource(row, ORIGIN, urllib.request.build_opener(NoRedirect()), min(GET_TIMEOUT, budget), time.monotonic() + budget, time.monotonic)
        print(json.dumps({'resource': value}))
    except Exception as error:
        code = str(error) if isinstance(error, ValueError) else 'HTTPS_' + type(error).__name__
        print(json.dumps({'error': {'code': code, 'temporary_DNS_EAI_AGAIN': temporary_dns(error)}}))


def public_readback(manifest, origin=ORIGIN, opener=None, *, clock=None, sleeper=None):
    require(origin == ORIGIN or opener is not None, 'fixed_origin')
    clock, sleeper = clock or time.monotonic, sleeper or time.sleep
    deadline = clock() + READBACK_BUDGET
    results = []
    for row in manifest['files']:
        if row['component'] != 'public':
            continue
        resource_deadline = min(deadline, clock() + RESOURCE_BUDGET)
        for attempt in range(len(DNS_BACKOFF) + 1):
            remaining = resource_deadline - clock()
            require(remaining > 0, 'HTTPS_readback_budget_exhausted')
            try:
                value = resource_process(row, remaining) if opener is None else read_resource(row, origin, opener, min(GET_TIMEOUT, remaining), resource_deadline, clock)
                require(clock() < resource_deadline, 'HTTPS_readback_budget_exhausted')
                results.append({**value, 'GET_attempts': attempt + 1})
                break
            except OSError as error:
                if not temporary_dns(error) or attempt == len(DNS_BACKOFF):
                    raise
                delay = DNS_BACKOFF[attempt]
                require(resource_deadline - clock() > delay, 'HTTPS_readback_budget_exhausted')
                sleeper(delay)
    return results


@contextmanager
def transport():
    key, hosts = os.environ['QS_DEPLOY_SSH_KEY'], os.environ['QS_KNOWN_HOSTS']
    require(bool(key.strip()) and bool(hosts.strip()), 'missing_deploy_transport')
    require(any(line.split()[0] == HOST for line in hosts.splitlines() if line.strip()), 'pinned_known_host_required')
    with tempfile.TemporaryDirectory(prefix='qs-deploy-') as tmp:
        key_path, hosts_path = Path(tmp) / 'key', Path(tmp) / 'known_hosts'
        for path, value in [(key_path, key), (hosts_path, hosts)]:
            path.write_text(value.rstrip() + '\n')
            path.chmod(0o600)
        yield ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(hosts_path), '-o', 'ConnectTimeout=10', '-i', str(key_path), 'qs-deploy@' + HOST, 'qs-release']


def read_public(result, manifest):
    try:
        result['public_files'] = public_readback(manifest)
    except Exception as error:
        result['readback_error'] = {'type': type(error).__name__, 'temporary_DNS_EAI_AGAIN': temporary_dns(error)}
        if isinstance(error, ValueError):
            result['readback_error']['code'] = str(error)
        raise


def verified_status(command, manifest, expected, selection):
    reply = subprocess.run(command, input=b'{"action":"status"}\n', capture_output=True, timeout=60)
    require(reply.returncode == 0, 'verification_status_unconfirmed')
    value = json.loads(reply.stdout)
    require(isinstance(value, dict), 'verification_status_object')
    require(value.get('source_sha') == expected and value.get('payload_digest') == manifest['payload_digest'], 'verification_current_SHA_or_payload')
    require(value.get('code_matches_current_manifest') is True and value.get('private_health') is True, 'verification_code_or_health')
    journal = value.get('last_operation')
    require(isinstance(journal, dict) and journal.get('phase') in TERMINAL_PHASES and journal.get('source_sha') == expected, 'verification_phase_unconfirmed')
    delivery = validate_delivery(journal.get('delivery'))
    validate_delivery(journal.get('max_automatic_run'))
    require(journal['max_automatic_run']['kind'] in {'automatic', 'bootstrap'}, 'verification_maximum')
    require(all(delivery[k] == selection[k] for k in ('workflow_id', 'run_number', 'run_id')) and journal['max_automatic_run']['workflow_id'] == selection['workflow_id'], 'verification_delivery_CI_binding')
    paths = (value.get('public_target'), value.get('private_target'))
    require(paths in {(f'/srv/hair-sites/qc/releases/{expected}/dist', f'/srv/hair-sites/qc-backend/releases/{expected}'), ('/srv/hair-sites/qc/releases/qc-20261030-existing-v1/dist', '/srv/hair-sites/qc-backend/releases/qc-20261030-existing-v1')}, 'verification_paths')
    return value


def verify_only(directory, expected, report):
    require(isinstance(expected, str) and SHA.fullmatch(expected), 'verification_explicit_expected_SHA')
    m = verify_archive(directory / 'website.tar', expected)
    selection = json.loads((directory / 'selection.json').read_text())
    require(selection.get('operation') == 'verify_only' and selection.get('eligible') is True and selection.get('source_sha') == expected == selection.get('expected_current'), 'verification_selection_binding')
    require(selection.get('trusted_event') == 'push' and selection.get('branch') == 'main' and selection.get('workflow') == '.github/workflows/ci.yml', 'verification_trusted_CI')
    require(selection.get('repository', '').lower() == '7ilia7/qs', 'verification_repository')
    require(all(type(selection.get(k)) is int and 0 < selection[k] < 10**19 for k in ('workflow_id', 'run_number', 'run_id', 'artifact_id', 'run_attempt')), 'verification_CI_identity')
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', selection.get('GitHub_ZIP_digest', '')), 'verification_CI_digest')
    report.mkdir(parents=True, exist_ok=False)
    result = {'action': 'verify_only', 'source_sha': expected, 'expected_current': expected, 'automatic_retry': False, 'mutations': 0, 'forms_POSTs': 0, 'status': 'verification_status_started_unknown_until_receipt'}
    try:
        (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        with transport() as command:
            before = verified_status(command, m, expected, selection)
            result.update(preflight_status=before, receiver=before, status='verification_receiver_confirmed_public_readback_pending')
            (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            read_error = None
            try:
                read_public(result, m)
            except Exception as error:
                read_error = error
            result['status'] = 'verification_readback_pending_current_recheck_pending' if read_error else 'verification_public_verified_current_recheck_pending'
            (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            after = verified_status(command, m, expected, selection)
            result['postflight_status'] = after
            require(before == after, 'verification_current_state_drift')
            if read_error is not None:
                result['status'] = 'verification_receiver_confirmed_public_readback_pending'
                raise read_error
        result['status'] = 'PASS_verification_only'
        return result
    finally:
        (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


def deploy(action, directory, expected_current, report):
    m = verify_archive(directory / 'website.tar')
    selection = json.loads((directory / 'selection.json').read_text())
    require(selection.get('operation') != 'verify_only', 'verification_cannot_mutate')
    require(selection['eligible'] and selection['source_sha'] == m['source_sha'], 'selection_binding')
    delivery = validate_delivery(selection['delivery'])
    require((action == 'rollback') == (delivery['kind'] == 'rollback'), 'delivery_action')
    if delivery['kind'] == 'rollback':
        require(isinstance(expected_current, str) and SHA.fullmatch(expected_current), 'expected_current_SHA')
    data = (directory / 'website.tar').read_bytes()
    report.mkdir(parents=True, exist_ok=False)
    result = {'action': action, 'source_sha': m['source_sha'], 'expected_current': expected_current, 'automatic_retry': False, 'forms_POSTs': 0, 'status': 'not_started'}
    try:
        with transport() as command:
            result['status'] = 'SSH_status_started_unknown_until_receipt'
            (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            before = subprocess.run(command, input=b'{"action":"status"}\n', capture_output=True, timeout=60)
            require(before.returncode == 0, 'SSH_status_unconfirmed_no_retry')
            observed = json.loads(before.stdout)
            result['preflight_status'] = observed
            if delivery['kind'] != 'rollback':
                require(observed['code_matches_current_manifest'], 'current_code_unconfirmed')
            if delivery['kind'] == 'automatic':
                maximum = (observed.get('last_operation') or {}).get('max_automatic_run')
                if not is_new_auto_run(delivery, maximum):
                    result['status'] = 'SKIPPED_stale_or_duplicate_CI_run'
                    return result
                require(is_ancestor(observed['source_sha'], m['source_sha']), 'automatic_downgrade_refused')
            if delivery['kind'] in {'automatic', 'bootstrap'}:
                if not selected_head_is_current(delivery['kind'], m['source_sha'], latest_main()):
                    result['status'] = 'SKIPPED_main_advanced_before_mutation'
                    return result
                expected_current = observed['source_sha']
            else:
                require(observed['source_sha'] == expected_current, 'stale_current_SHA')
            result['expected_current'] = expected_current
            header = {'action': action, 'source_sha': m['source_sha'], 'expected_current': expected_current, 'archive_sha256': digest(data), 'bytes': len(data), 'delivery': delivery}
            result['status'] = 'SSH_mutation_started_unknown_until_receipt'
            (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            reply = subprocess.run(command, input=canonical(header) + b'\n' + data, capture_output=True, timeout=180)
            require(reply.returncode == 0, 'SSH_stopped_or_unconfirmed_inspect_status_no_retry')
            status = json.loads(reply.stdout)
            result['receiver'] = status
            require(status['source_sha'] == m['source_sha'] and status['payload_digest'] == m['payload_digest'] and status['code_matches_current_manifest'] and status['private_health'], 'receiver_readback')
            result['status'] = 'activated_receiver_verified_public_readback_pending'
            (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        read_public(result, m)
        result['status'] = 'PASS_activated_and_read_back'
        return result
    finally:
        (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    if sys.argv[1:] == ['--readback-resource']:
        resource_worker()
        raise SystemExit(0)
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--expected-source-sha')
    args = parser.parse_args()
    if args.verify_only:
        value = verify_only(args.artifact, args.expected_source_sha, args.report)
    else:
        require(args.expected_source_sha is None, 'expected_SHA_requires_verification_mode')
        selection = json.loads((args.artifact / 'selection.json').read_text())
        action = 'rollback' if selection['delivery']['kind'] == 'rollback' else 'promote'
        value = deploy(action, args.artifact, selection.get('expected_current'), args.report)
    print(json.dumps({'status': value['status'], 'source_sha': value['source_sha'], 'public_files': len(value.get('public_files', [])), 'forms_POSTs': 0}))
