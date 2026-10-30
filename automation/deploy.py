"""One forced-command SSH operation, followed by anonymous HTTPS readback. No retry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
from release_lib import SHA, canonical, digest, require, verify_archive

ORIGIN = 'https://quality-service-hair.165-245-223-138.sslip.io'
HOST = '165.245.223.138'
MIME = {'.html': {'text/html'}, '.js': {'application/javascript', 'text/javascript'}, '.css': {'text/css'}, '.xml': {'application/xml', 'text/xml'}, '.txt': {'text/plain'}, '.webp': {'image/webp'}, '.mp4': {'video/mp4'}, '.webm': {'video/webm'}, '.png': {'image/png'}, '.jpg': {'image/jpeg'}, '.jpeg': {'image/jpeg'}, '.svg': {'image/svg+xml'}, '.avif': {'image/avif'}, '.woff2': {'font/woff2'}, '.pdf': {'application/pdf'}, '.ico': {'image/x-icon', 'image/vnd.microsoft.icon'}}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('unexpected_HTTPS_redirect')


def public_readback(manifest, origin=ORIGIN, opener=None):
    require(origin == ORIGIN or opener is not None, 'fixed_origin')
    opener = opener or urllib.request.build_opener(NoRedirect())
    results = []
    for row in manifest['files']:
        if row['component'] != 'public':
            continue
        url = origin + '/' + row['path']
        with opener.open(url, timeout=25) as response:
            require(response.status == 200, 'HTTPS_status')
            mime = response.headers.get_content_type()
            expected_mimes = MIME.get(Path(row['path']).suffix)
            require(expected_mimes is not None and mime in expected_mimes, 'HTTPS_MIME')
            hasher, size = hashlib.sha256(), 0
            while True:
                block = response.read(min(1024 * 1024, row['bytes'] + 1 - size))
                if not block:
                    break
                size += len(block)
                require(size <= row['bytes'], 'HTTPS_size')
                hasher.update(block)
            require(size == row['bytes'] and hasher.hexdigest() == row['sha256'], 'HTTPS_hash')
            results.append({'path': row['path'], 'status': 200, 'bytes': size, 'sha256': hasher.hexdigest(), 'MIME': mime, 'TLS': 'default_CA_hostname_verification'})
    return results


def deploy(action, directory, expected_current, report):
    m = verify_archive(directory / 'website.tar')
    require(SHA.fullmatch(expected_current), 'expected_current_SHA')
    data = (directory / 'website.tar').read_bytes()
    header = {'action': action, 'source_sha': m['source_sha'], 'expected_current': expected_current, 'archive_sha256': digest(data), 'bytes': len(data)}
    report.mkdir(parents=True, exist_ok=False)
    result = {'action': action, 'source_sha': m['source_sha'], 'expected_current': expected_current, 'automatic_retry': False, 'forms_POSTs': 0, 'status': 'not_started'}
    try:
        key = os.environ['QS_DEPLOY_SSH_KEY']
        hosts = os.environ['QS_KNOWN_HOSTS']
        require(bool(key.strip()) and bool(hosts.strip()), 'missing_deploy_transport')
        require(any(line.split()[0] == HOST for line in hosts.splitlines() if line.strip()), 'pinned_known_host_required')
        with tempfile.TemporaryDirectory(prefix='qs-deploy-') as tmp:
            key_path, hosts_path = Path(tmp) / 'key', Path(tmp) / 'known_hosts'
            for path, value in [(key_path, key), (hosts_path, hosts)]:
                path.write_text(value.rstrip() + '\n')
                path.chmod(0o600)
            command = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(hosts_path), '-o', 'ConnectTimeout=10', '-i', str(key_path), 'qs-deploy@' + HOST, 'qs-release']
            result['status'] = 'SSH_invocation_started_unknown_until_receipt'
            (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            reply = subprocess.run(command, input=canonical(header) + b'\n' + data, capture_output=True, timeout=180)
            require(reply.returncode == 0, 'SSH_stopped_or_unconfirmed_inspect_status_no_retry')
            status = json.loads(reply.stdout)
            result['receiver'] = status
            require(status['source_sha'] == m['source_sha'] and status['payload_digest'] == m['payload_digest'] and status['code_matches_current_manifest'] and status['private_health'], 'receiver_readback')
        result['status'] = 'activated_receiver_verified_public_readback_pending'
        result['public_files'] = public_readback(m)
        result['status'] = 'PASS_activated_and_read_back'
        return result
    finally:
        (report / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', choices=['promote', 'rollback'], required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--expected-current', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    value = deploy(args.action, args.artifact, args.expected_current, args.report)
    print(json.dumps({'status': value['status'], 'source_sha': value['source_sha'], 'public_files': len(value['public_files']), 'forms_POSTs': 0}))
