"""Owned local DNS/HTTP/SSH faults; no external network, credentials or state."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'automation'))
import deploy as client
from select_ci import verification_context
from release_lib import canonical
import test_release as fixtures

A, B, C = fixtures.A, fixtures.B, fixtures.C
ENV = {'QS_DEPLOY_SSH_KEY': 'owned-synthetic-key', 'QS_KNOWN_HOSTS': '165.245.223.138 ssh-ed25519 owned-public-fixture'}


def dns():
    return urllib.error.URLError(urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN, 'owned temporary DNS')))


def wire_status(manager):
    # Manager's owned filesystem API prefixes paths with a temporary host root.
    # Production wire paths remain fixed; project only this fixture representation.
    value = manager.status()
    for key in ('public_target', 'private_target'):
        value[key] = '/' + Path(value[key]).relative_to(manager.root).as_posix()
    return value


class Response(io.BytesIO):
    status = 200
    def __init__(self, body=b'next', mime='text/html'):
        super().__init__(body)
        self.headers = SimpleNamespace(get_content_type=lambda: mime)


class Clock:
    now = 0
    def __call__(self): return self.now
    def sleep(self, seconds): self.now += seconds


class Reads(unittest.TestCase):
    def setUp(self):
        self.manifest = {'files': [{'component': 'public', 'path': 'index.html', 'bytes': 4, 'sha256': hashlib.sha256(b'next').hexdigest()}]}
        self.calls, self.sleeps = [], []
        self.clock = Clock()

    def run_reads(self, values):
        values = iter(values)
        def open_get(url, timeout):
            self.calls.append((url, timeout))
            value = next(values)
            if isinstance(value, BaseException): raise value
            return value
        def sleep(seconds):
            self.sleeps.append(seconds); self.clock.sleep(seconds)
        return client.public_readback(self.manifest, opener=SimpleNamespace(open=open_get), clock=self.clock, sleeper=sleep)

    def test_nested_temporary_DNS_retries_GET_then_succeeds(self):
        result = self.run_reads([dns(), Response()])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.sleeps, [1])
        self.assertEqual(result[0]['GET_attempts'], 2)
        self.assertTrue(all(url == client.ORIGIN + '/index.html' and 0 < timeout <= 25 for url, timeout in self.calls))

    def test_exhaustion_is_three_GETs_and_finite_backoff(self):
        with self.assertRaises(urllib.error.URLError): self.run_reads([dns(), dns(), dns()])
        self.assertEqual((len(self.calls), self.sleeps, self.clock.now), (3, [1, 3], 4))

    def test_permanent_DNS_certificate_timeout_and_HTTP_do_not_retry(self):
        faults = [socket.gaierror(socket.EAI_NONAME, 'owned permanent DNS'), ssl.SSLCertVerificationError('owned untrusted issuer'), urllib.error.URLError(ssl.SSLCertVerificationError('owned issuer')), TimeoutError('owned timeout'), urllib.error.HTTPError(client.ORIGIN, 503, 'owned 503', {}, None)]
        for fault in faults:
            with self.subTest(fault=type(fault).__name__):
                self.calls.clear(); self.sleeps.clear()
                with self.assertRaises(OSError): self.run_reads([fault])
                self.assertEqual((len(self.calls), self.sleeps), (1, []))

    def test_wrong_body_MIME_status_and_size_are_never_PASS_or_retried(self):
        bad_status = Response(); bad_status.status = 302
        for response in [Response(b'evil'), Response(mime='application/json'), Response(b'too large'), bad_status]:
            with self.subTest(response=response):
                self.calls.clear(); self.sleeps.clear()
                with self.assertRaisesRegex(ValueError, 'HTTPS_'): self.run_reads([response])
                self.assertEqual((len(self.calls), self.sleeps), (1, []))

    def test_redirect_handler_fails_without_following(self):
        with self.assertRaisesRegex(ValueError, 'unexpected_HTTPS_redirect'):
            client.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid/')

    def test_resource_deadline_refuses_backoff_beyond_remaining_budget(self):
        with patch.object(client, 'RESOURCE_BUDGET', 1):
            with self.assertRaisesRegex(ValueError, 'budget_exhausted'): self.run_reads([dns()])
        self.assertEqual((len(self.calls), self.sleeps), (1, []))

    def test_global_deadline_covers_all_resources_and_no_late_PASS(self):
        self.manifest['files'] *= 2
        clock = self.clock
        class Slow(Response):
            def read1(self, count):
                clock.now += 0.6
                return super().read1(count)
        with patch.object(client, 'READBACK_BUDGET', 2):
            with self.assertRaisesRegex(ValueError, 'budget_exhausted'): self.run_reads([Slow(), Slow()])
        self.assertEqual(len(self.calls), 2)
        self.assertLess(self.calls[1][1], 1)

    def test_returned_IO_after_deadline_cannot_be_accepted(self):
        clock = self.clock
        class Late(Response):
            def read1(self, count):
                clock.now += 91
                return super().read1(count)
        with self.assertRaisesRegex(ValueError, 'budget_exhausted'): self.run_reads([Late()])

    def test_reason_cycle_and_error_strings_do_not_fake_transient_DNS(self):
        cycle = urllib.error.URLError('owned'); cycle.reason = cycle
        self.assertFalse(client.temporary_dns(cycle))
        self.assertFalse(client.temporary_dns(urllib.error.URLError('EAI_AGAIN')))


class Verify(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ReleaseTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.archive = self.f.artifact()
        self.m = self.f.manager
        self.calls = []

    def select_verify(self):
        selection = {'eligible': True, 'operation': 'verify_only', 'repository': '7Ilia7/QS', 'source_sha': B, 'expected_current': B, 'trusted_event': 'push', 'branch': 'main', 'workflow': '.github/workflows/ci.yml', 'workflow_id': 7, 'run_number': 2, 'run_id': 102, 'run_attempt': 1, 'artifact_id': 55, 'GitHub_ZIP_digest': 'sha256:' + 'f'*64}
        (self.archive.parent / 'selection.json').write_text(json.dumps(selection))

    def install_and_select(self):
        self.m.operate(self.f.header(self.archive), self.archive)
        self.select_verify()

    def ssh_status(self, command, input, **kwargs):
        self.calls.append(input)
        self.assertEqual(input, b'{"action":"status"}\n')
        return SimpleNamespace(returncode=0, stdout=canonical(wire_status(self.m)))

    def verify(self, report='verify-report', readback=None, ssh=None):
        with patch.dict(os.environ, ENV), patch('deploy.subprocess.run', side_effect=ssh or self.ssh_status), patch('deploy.public_readback', side_effect=readback or (lambda m: [{'path': 'index.html'}])):
            return client.verify_only(self.archive.parent, B, self.f.root / report)

    def test_pending_readback_resume_is_status_only_preserves_everything(self):
        # Simulate one actual owned mutation followed by the demonstrated GET failure.
        def ssh(command, input, **kwargs):
            self.calls.append(input)
            if input == b'{"action":"status"}\n': return SimpleNamespace(returncode=0, stdout=canonical(self.m.status()))
            header, body = input.split(b'\n', 1)
            incoming = self.f.root/'incoming.tar'; incoming.write_bytes(body)
            return SimpleNamespace(returncode=0, stdout=canonical(self.m.operate(json.loads(header), incoming)))
        pending = self.f.root/'pending'
        def fail_get(manifest):
            self.assertEqual(json.loads((pending/'result.json').read_text())['status'], 'activated_receiver_verified_public_readback_pending')
            raise dns()
        with patch.dict(os.environ, ENV), patch('deploy.subprocess.run', side_effect=ssh), patch('deploy.latest_main', return_value=B), patch('deploy.is_ancestor', return_value=True), patch('deploy.public_readback', side_effect=fail_get):
            with self.assertRaises(urllib.error.URLError): client.deploy('promote', self.archive.parent, A, pending)
        self.assertEqual(sum(c != b'{"action":"status"}\n' for c in self.calls), 1)
        old_receipt = (pending/'result.json').read_bytes()
        self.assertEqual(json.loads(old_receipt)['receiver']['source_sha'], B)
        self.select_verify(); self.calls.clear()
        status, protected = self.m.status(), self.f.protected_bytes()
        result = self.verify()
        self.assertEqual(result['status'], 'PASS_verification_only')
        self.assertEqual(result['mutations'], 0)
        self.assertEqual(self.calls, [b'{"action":"status"}\n']*2)
        self.assertEqual((self.m.status(), self.f.protected_bytes()), (status, protected))
        self.assertEqual((pending/'result.json').read_bytes(), old_receipt)

    def test_failure_still_rechecks_current_and_preserves_pending_receipt(self):
        self.install_and_select()
        with self.assertRaises(urllib.error.URLError): self.verify(readback=lambda m: (_ for _ in ()).throw(dns()))
        result = json.loads((self.f.root/'verify-report/result.json').read_text())
        self.assertEqual(self.calls, [b'{"action":"status"}\n']*2)
        self.assertEqual(result['status'], 'verification_receiver_confirmed_public_readback_pending')
        self.assertTrue(result['readback_error']['temporary_DNS_EAI_AGAIN'])
        self.assertEqual(result['preflight_status'], result['postflight_status'])

    def test_wrong_expected_SHA_or_untrusted_selection_refuses_before_SSH(self):
        self.install_and_select()
        with patch('deploy.subprocess.run') as ssh:
            for expected in [None, C]:
                with self.subTest(expected=expected), self.assertRaises(ValueError): client.verify_only(self.archive.parent, expected, self.f.root/'unused')
            value=json.loads((self.archive.parent/'selection.json').read_text()); value['branch']='feature'; (self.archive.parent/'selection.json').write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'trusted_CI'): client.verify_only(self.archive.parent, B, self.f.root/'unused')
            ssh.assert_not_called()

    def test_verification_artifact_cannot_enter_mutating_driver(self):
        self.install_and_select()
        with patch('deploy.subprocess.run') as ssh:
            with self.assertRaisesRegex(ValueError, 'cannot_mutate'): client.deploy('promote', self.archive.parent, B, self.f.root/'unused')
            ssh.assert_not_called()

    def test_status_must_match_selected_CI_run_not_only_source_SHA(self):
        self.install_and_select()
        f=self.archive.parent/'selection.json'; selection=json.loads(f.read_text()); selection['run_id']=103; f.write_text(json.dumps(selection))
        with patch('deploy.public_readback') as get:
            with patch.dict(os.environ,ENV),patch('deploy.subprocess.run',side_effect=self.ssh_status):
                with self.assertRaisesRegex(ValueError,'delivery_CI_binding'): client.verify_only(self.archive.parent,B,self.f.root/'wrong-CI')
            get.assert_not_called()

    def test_unknown_unhealthy_wrong_SHA_incomplete_phase_refuse_before_GET(self):
        self.install_and_select()
        mutations=[lambda v:v.update(source_sha=C), lambda v:v.update(private_health=False), lambda v:v.update(code_matches_current_manifest=False), lambda v:v['last_operation'].update(phase='staging_reserved'), lambda v:v.update(last_operation=None)]
        for i, change in enumerate(mutations):
            value=copy.deepcopy(wire_status(self.m)); change(value)
            with patch('deploy.public_readback') as get:
                with patch.dict(os.environ,ENV), patch('deploy.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=canonical(value))):
                    with self.assertRaises(ValueError): client.verify_only(self.archive.parent,B,self.f.root/f'bad-{i}')
                get.assert_not_called()

    def test_lost_status_fails_without_GET_or_mutation(self):
        self.install_and_select()
        with patch('deploy.public_readback') as get, patch.dict(os.environ,ENV), patch('deploy.subprocess.run',return_value=SimpleNamespace(returncode=255,stdout=b'')) as ssh:
            with self.assertRaisesRegex(ValueError,'status_unconfirmed'): client.verify_only(self.archive.parent,B,self.f.root/'bad-status')
            self.assertEqual(ssh.call_count,1); get.assert_not_called()

    def test_watermark_or_journal_drift_after_GET_is_not_PASS(self):
        self.install_and_select()
        def change_after_get(m):
            j=self.m.p('/var/lib/qs-release/last-operation.json'); value=json.loads(j.read_text()); value['max_automatic_run']['run_number']+=1; j.write_text(json.dumps(value)); return []
        with self.assertRaisesRegex(ValueError,'current_state_drift'): self.verify(readback=change_after_get)
        self.assertEqual(self.calls,[b'{"action":"status"}\n']*2)


class VerificationCLI(unittest.TestCase):
    # Run only these CLI scenarios here, not a second inherited fixture suite.
    setUp = Verify.setUp
    select_verify = Verify.select_verify
    install_and_select = Verify.install_and_select
    def test_actual_cli_two_readonly_status_calls_and_DNS_recovery(self):
        self.install_and_select()
        result, report, calls, gets = self.cli('success', 'once')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(report['status'],'PASS_verification_only')
        self.assertEqual(len(calls),2); self.assertEqual(len(gets),2)
        self.assertTrue(all(v['input']=='{"action":"status"}\n' for v in calls))
        self.assertTrue(all(not Path(v['key']).exists() for v in calls))

    def test_actual_cli_exhaustion_rechecks_status_and_returns_failure(self):
        self.install_and_select()
        result, report, calls, gets = self.cli('exhausted','always')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((len(calls),len(gets)),(2,3))
        self.assertEqual(report['mutations'],0)
        self.assertEqual(report['status'],'verification_receiver_confirmed_public_readback_pending')

    def cli(self, name, dns_mode):
        root=self.f.root/name; root.mkdir(); bin=root/'bin'; bin.mkdir()
        (root/'status.json').write_text(json.dumps(wire_status(self.m)))
        ssh=bin/'ssh'
        ssh.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
p=Path(os.environ['OWNED_CLI']); data=sys.stdin.buffer.read(); key=sys.argv[sys.argv.index('-i')+1]
with (p/'ssh.jsonl').open('a') as f:f.write(json.dumps(dict(input=data.decode(),key=key))+'\\n')
assert data==b'{"action":"status"}\\n'
assert Path(key).stat().st_mode&0o777==0o600
print((p/'status.json').read_text())
'''); ssh.chmod(0o755)
        (root/'sitecustomize.py').write_text('''import io,json,os,socket,time,urllib.request,urllib.error
from pathlib import Path
p=Path(os.environ['OWNED_CLI']); count=0
class Response(io.BytesIO):
 status=200
 class Headers:
  def get_content_type(self):return 'text/html'
 headers=Headers()
class Opener:
 def open(self,url,timeout):
  global count
  count+=1
  with (p/'get.jsonl').open('a') as f:f.write(json.dumps(dict(url=url,timeout=timeout))+'\\n')
  if os.environ['OWNED_DNS']=='always' or (os.environ['OWNED_DNS']=='once' and count==1):raise urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN,'owned'))
  return Response(b'next')
urllib.request.build_opener=lambda *args:Opener()
time.sleep=lambda seconds:None
''')
        env=dict(os.environ,**ENV,OWNED_CLI=str(root),OWNED_DNS=dns_mode,PYTHONPATH=str(root),PATH=str(bin)+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
        script=Path(__file__).resolve().parents[1]/'automation/deploy.py'
        result=subprocess.run([sys.executable,'-B',str(script),'--verify-only','--expected-source-sha',B,'--artifact',str(self.archive.parent),'--report',str(root/'report')],capture_output=True,text=True,env=env,timeout=15)
        report=json.loads((root/'report/result.json').read_text())
        rows=lambda n:[json.loads(s) for s in (root/n).read_text().splitlines()]
        return result,report,rows('ssh.jsonl'),rows('get.jsonl')


class Selection(unittest.TestCase):
    def test_verification_requires_explicit_same_SHA_trusted_main_dispatch(self):
        event={'inputs':{'action':'verify','source_sha':B,'expected_current':B,'ci_run_id':'102'}}
        value=verification_context('workflow_dispatch',event,'7Ilia7/QS','refs/heads/main')
        self.assertEqual(value,dict(source_sha=B,run_id=102,expected_current=B))
        self.assertIsNone(verification_context('workflow_dispatch',event,'7Ilia7/QS','refs/heads/feature'))
        for key,val in [('source_sha',C),('expected_current',''),('ci_run_id','0')]:
            bad=copy.deepcopy(event);bad['inputs'][key]=val
            with self.subTest(key=key),self.assertRaises(ValueError): verification_context('workflow_dispatch',bad,'7Ilia7/QS','refs/heads/main')
        with self.assertRaises(ValueError): verification_context('workflow_run',event,'7Ilia7/QS','refs/heads/main')
        with self.assertRaises(ValueError): verification_context('workflow_dispatch',event,'other/fork','refs/heads/main')


class SelectionCLI(unittest.TestCase):
    setUp = Verify.setUp

    def select(self, name, mode='verify', fault=None):
        root=self.f.root/name; root.mkdir(); bin=root/'bin'; bin.mkdir()
        archive=root/'artifact.zip'
        with zipfile.ZipFile(archive,'w') as output:
            for n in ('website.tar','release.json','SHA256SUMS'): output.write(self.archive.parent/n,n)
        repository={'full_name':'7Ilia7/QS'}
        run=dict(id=102,repository=repository,head_repository=repository,event='push',head_branch='main',head_sha=B,path='.github/workflows/ci.yml',status='completed',conclusion='success',workflow_id=7,run_number=2,run_attempt=1)
        if fault=='fork': run['head_repository']={'full_name':'other/fork'}
        artifact=dict(id=55,name='website-'+B,expired=False,size_in_bytes=archive.stat().st_size,digest='sha256:'+hashlib.sha256(archive.read_bytes()).hexdigest(),workflow_run=dict(id=102,head_sha=B))
        if fault=='ZIPdigest': artifact['digest']='sha256:'+'0'*64
        routes={'repos/7Ilia7/QS/actions/runs/102':run,'repos/7Ilia7/QS/actions/runs/102/artifacts?per_page=100':dict(total_count=1,artifacts=[artifact]),'repos/7Ilia7/QS/git/ref/heads/main':dict(object=dict(sha=B if mode=='automatic' else C))}
        (root/'routes.json').write_text(json.dumps(routes))
        gh=bin/'gh'; gh.write_text('#!'+sys.executable+'\n'+'''import sys,json,os
from pathlib import Path
p=Path(os.environ['OWNED_SELECTOR']); args=sys.argv[1:]
with (p/'calls.jsonl').open('a') as f:f.write(json.dumps(args)+'\\n')
assert args[:3]==['api','--method','GET']
if args[3]=='repos/7Ilia7/QS/actions/artifacts/55/zip':sys.stdout.buffer.write((p/'artifact.zip').read_bytes())
else:print(json.dumps(json.loads((p/'routes.json').read_text())[args[3]]))
''');gh.chmod(0o755)
        git=bin/'git';git.write_text('#!'+sys.executable+'\n'+f'import sys\nassert sys.argv[1:]==["merge-base","--is-ancestor","{B}","origin/main"]\n');git.chmod(0o755)
        event= {'action':'completed','workflow_run':dict(run,name='Website CI')} if mode=='automatic' else {'inputs':dict(action=mode,source_sha=B,ci_run_id='102',expected_current=B if mode=='verify' else C)}
        (root/'event.json').write_text(json.dumps(event))
        env=dict(os.environ,OWNED_SELECTOR=str(root),PATH=str(bin)+os.pathsep+os.environ['PATH'],GITHUB_REPOSITORY='7Ilia7/QS',GITHUB_REF='refs/heads/main',GITHUB_EVENT_NAME='workflow_run' if mode=='automatic' else 'workflow_dispatch',GITHUB_EVENT_PATH=str(root/'event.json'),GITHUB_OUTPUT=str(root/'outputs'),QS_AUTO_CD_READY='true',PYTHONDONTWRITEBYTECODE='1')
        script=Path(__file__).resolve().parents[1]/'automation/select_ci.py'
        result=subprocess.run([sys.executable,'-B',str(script),'--output',str(root/'selected')],env=env,capture_output=True,text=True,timeout=15)
        return root,result

    def test_actual_selectorCLI_verification_older_installed_SHA_uses_trusted_artifact(self):
        root,result=self.select('verify')
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads((root/'selected/selection.json').read_text())
        self.assertEqual((value['operation'],value['source_sha'],value['expected_current']),('verify_only',B,B))
        self.assertEqual(value['latest_main_at_selection'],C)
        self.assertNotIn('delivery',value)
        self.assertEqual((root/'selected/website.tar').read_bytes(),self.archive.read_bytes())
        self.assertTrue(all(json.loads(row)[:3]==['api','--method','GET'] for row in (root/'calls.jsonl').read_text().splitlines()))

    def test_actual_selectorCLI_rejects_foreign_run_and_corrupt_ZIP_binding(self):
        for fault in ('fork','ZIPdigest'):
            root,result=self.select(fault,fault=fault)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'selected/selection.json').exists())
            self.assertFalse((root/'selected/website.tar').exists())

    def test_actual_selectorCLI_retains_normal_auto_and_manualrollback_delivery(self):
        for mode in ('automatic','rollback'):
            root,result=self.select(mode,mode=mode)
            self.assertEqual(result.returncode,0,result.stderr)
            value=json.loads((root/'selected/selection.json').read_text())
            self.assertEqual(value['delivery']['kind'],mode)
            self.assertNotIn('operation',value)


if __name__ == '__main__': unittest.main()
