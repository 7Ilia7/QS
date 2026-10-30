import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from server import App, Store, Server, TARGET, Telegram
from test_server import payload, ok
from inspect_receipts import inspect


class Receipts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.pairs = {str(uuid.uuid4()): 'callback', str(uuid.uuid4()): 'review'}
        self.store = Store(self.temp.name, synthetic_pairs=self.pairs)
        self.calls = []
        def send(data):
            self.calls.append(data)
            return ok(data)
        self.app = App(self.store, send, 'https://qc.example')
        self.network = patch('socket.create_connection', side_effect=AssertionError('external network forbidden'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.store.close()
        self.temp.cleanup()

    def data(self, kind):
        data = payload(kind)
        data['request_id'] = next(k for k,v in self.pairs.items() if v == kind)
        return data

    def post(self, data):
        return self.app.request('POST', '/api/forms', {'Origin': 'https://qc.example', 'Content-Type': 'application/json', 'Idempotency-Key': data['request_id']}, json.dumps(data).encode())

    def reopen(self):
        self.store.close()
        self.store = Store(self.temp.name, synthetic_pairs=self.pairs, initialize=False)
        self.app = App(self.store, lambda _: self.fail('no resends'), 'https://qc.example')

    def test_two_receipts_only_public_opaque_and_restart(self):
        for kind in ('callback', 'review'):
            data = self.data(kind)
            code, public = self.post(data)
            self.assertEqual(code, 200)
            receipt = self.store.data['records'][data['request_id']]['provider_receipt']
            self.assertEqual(set(receipt), {'request_id','type','ok','message_id','target','timestamp','receipt_id'})
            self.assertEqual((receipt['target'], receipt['message_id'], receipt['ok']), (TARGET,123,True))
            self.assertEqual(public['receipt_id'], receipt['receipt_id'])
            self.assertNotIn('message_id', public)
            self.assertNotIn('target', public)
            self.assertNotIn('provider_receipt', public)
        customer = payload('review')
        self.assertEqual(self.post(customer)[0], 200)
        self.assertNotIn('provider_receipt', self.store.data['records'][customer['request_id']])
        self.assertEqual(sum('provider_receipt' in r for r in self.store.data['records'].values()), 2)
        serialized = self.store.path.read_text()
        for value in ('Private test review', '<Test', '+380000000001', 'DUMMY_TOKEN'):
            self.assertNotIn(value, serialized)
        self.reopen()
        for kind in ('callback','review'):
            self.assertEqual(self.post(self.data(kind))[0], 200)

    def test_predeclared_type_mismatch_and_immutable_config(self):
        data = self.data('callback')
        data.pop('phone')
        data.update(type='review', review='long valid review')
        self.assertEqual(self.post(data)[0], 422)
        self.assertEqual(self.calls, [])
        self.store.close()
        with self.assertRaises(ValueError):
            Store(self.temp.name, synthetic_pairs={})
        with self.assertRaises(ValueError):
            Store(self.temp.name, synthetic_pairs={str(uuid.uuid4()): 'callback'})
        self.store = Store(self.temp.name, synthetic_pairs=self.pairs)

    def test_receipt_loss_corruption_and_record_loss_never_resend(self):
        for kind in ('callback','review'):
            data = self.data(kind)
            self.post(data)
            record = self.store.data['records'][data['request_id']]
            record['provider_receipt']['message_id'] = True
            self.assertEqual(self.post(data)[1]['status'], 'unknown')
            record.pop('provider_receipt')
            self.store.save()
        self.reopen()
        for kind in ('callback','review'):
            data = self.data(kind)
            self.assertEqual(self.post(data)[1]['status'], 'unknown')
            del self.store.data['records'][data['request_id']]
            self.assertEqual(self.post(data)[1]['status'], 'unknown')

    def test_receipt_commit_failure_crash_recovery_both(self):
        for kind in ('callback','review'):
            data = self.data(kind)
            save = self.store.save
            count = 0
            def crash():
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError('mock disk failure after acceptance')
                save()
            with patch.object(self.store, 'save', side_effect=crash):
                code, public = self.post(data)
            self.assertEqual((code,public['status'],public['retry_safe']), (503,'unknown',False))
            self.assertNotIn('provider_receipt', self.store.data['records'][data['request_id']])
            self.assertEqual(self.post(data)[0],503)
            self.reopen()
            self.assertEqual(self.post(data)[1]['status'], 'unknown')
            self.app.send = lambda data: ok(data)

    def test_deadline_discards_late_receipt_and_no_retry(self):
        self.app.deadline = 0.01
        release = threading.Event()
        def slow(data):
            release.wait(1)
            return ok(data)
        self.app.send = slow
        data = self.data('review')
        self.assertEqual(self.post(data)[1]['status'], 'unknown')
        release.set()
        time.sleep(0.02)
        self.assertNotIn('provider_receipt', self.store.data['records'][data['request_id']])
        self.reopen()
        self.assertEqual(self.post(data)[1]['status'], 'unknown')

    def test_missing_ledger_startup_fails_closed(self):
        self.store.close()
        self.store.path.unlink()
        with self.assertRaises(ValueError):
            Store(self.temp.name, synthetic_pairs=self.pairs, initialize=False)

    def test_expired_admission_never_calls_provider(self):
        data = self.data('callback')
        code, result = self.app.request('POST','/api/forms',{'Origin':'https://qc.example','Content-Type':'application/json','Idempotency-Key':data['request_id']},json.dumps(data).encode(),remaining=0)
        self.assertEqual(code,408)
        self.assertEqual(self.calls, [])

    def test_transport_synthetic_label(self):
        client = Telegram('DUMMY_ONLY', TARGET, self.pairs)
        class Reply:
            def __enter__(self): return self
            def __exit__(self,*_): pass
            def read(self,_): return json.dumps(ok({})).encode()
        with patch.object(client.opener,'open',return_value=Reply()) as send:
            client(self.data('callback'))
            self.assertIn('TEST_CALLBACK', json.loads(send.call_args.args[0].data)['text'])

    def test_private_inspector_allowlist_and_missing_receipt(self):
        for kind in ('callback','review'):
            self.post(self.data(kind))
        rows = inspect(self.store.path)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['message_id'] == 123 for r in rows))
        raw = json.dumps(rows)
        for forbidden in ('records','key','name','phone','review text','digest','DUMMY'):
            self.assertNotIn(forbidden,raw)
        rid = self.data('callback')['request_id']
        self.store.data['records'][rid].pop('provider_receipt')
        self.store.save()
        self.assertEqual(next(r for r in inspect(self.store.path) if r['request_id']==rid)['status'],'unknown')

    def test_admission_expires_during_reservation_no_send(self):
        data = self.data('callback')
        save = self.store.save
        def slow_disk():
            time.sleep(0.02)
            save()
        with patch.object(self.store,'save',side_effect=slow_disk):
            _, result = self.app.request('POST','/api/forms',{'Origin':'https://qc.example','Content-Type':'application/json','Idempotency-Key':data['request_id']},json.dumps(data).encode(),remaining=0.001)
        self.assertEqual(result['status'],'unknown')
        self.assertEqual(self.calls,[])

    def test_process_crash_after_possible_acceptance(self):
        script = '''
import json,os,socket,sys
from server import Store,App,TARGET
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError("external network forbidden"))
data=json.loads(sys.argv[2]); pairs=json.loads(sys.argv[3])
s=Store(sys.argv[1],synthetic_pairs=pairs,initialize=False)
save=s.save; count=0
def crash():
 global count
 count+=1
 if count==2: os._exit(77)
 save()
s.save=crash
a=App(s,lambda d:{"ok":True,"result":{"message_id":123,"chat":{"id":int(TARGET)}}},"https://qc.example")
a.request("POST","/api/forms",{"Origin":"https://qc.example","Content-Type":"application/json","Idempotency-Key":data["request_id"]},json.dumps(data).encode())
'''
        for kind in ('callback','review'):
            data=self.data(kind)
            self.store.close()
            result=subprocess.run([sys.executable,'-B','-c',script,self.temp.name,json.dumps(data),json.dumps(self.pairs)],capture_output=True,timeout=3)
            self.assertEqual(result.returncode,77,result.stderr)
            self.assertEqual(result.stdout,b'')
            self.store=Store(self.temp.name,synthetic_pairs=self.pairs,initialize=False)
            self.app=App(self.store,lambda _:self.fail('crash replay send'),'https://qc.example')
            self.assertEqual(self.post(data)[1]['status'],'unknown')


class Admission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.calls = []
        self.app = App(self.store, lambda d: self.calls.append(d) or ok(d), 'https://qc.example')
        self.server = Server(('127.0.0.1',0),self.app,admission_seconds=0.25,max_handlers=2)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.sockets = []
        original = socket.create_connection
        def local_only(address,*args,**kwargs):
            if address[0] != '127.0.0.1': raise AssertionError('external network forbidden')
            return original(address,*args,**kwargs)
        self.network = patch('socket.create_connection',side_effect=local_only)
        self.network.start()

    def tearDown(self):
        for sock in self.sockets: sock.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.network.stop()
        self.store.close()
        self.temp.cleanup()

    def connect(self):
        sock = socket.create_connection(('127.0.0.1',self.server.server_port),timeout=1)
        self.sockets.append(sock)
        return sock

    def test_slow_header_absolute_deadline_despite_drip(self):
        sock = self.connect()
        started = time.monotonic()
        sock.sendall(b'POST /api/forms HTTP/1.1\r\nX-Slow: ')
        for _ in range(12):
            try: sock.sendall(b'x')
            except OSError: break
            time.sleep(0.04)
        try: response = sock.recv(4096)
        except ConnectionResetError: response = b''
        self.assertEqual(response,b'')
        self.assertLess(time.monotonic()-started,0.8)
        self.assertEqual(self.calls,[])

    def test_slow_body_deadline_no_send_and_concurrency_recovery(self):
        held = [self.connect(),self.connect()]
        for sock in held:
            sock.sendall(b'POST /api/forms HTTP/1.1\r\nHost: qc.example\r\nContent-Length: 100\r\n\r\n{')
        time.sleep(0.04)
        rejected = self.connect()
        rejected.sendall(b'GET /health HTTP/1.0\r\n\r\n')
        try: result = rejected.recv(100)
        except ConnectionResetError: result = b''
        self.assertEqual(result,b'')
        for _ in range(8):
            for sock in held:
                try: sock.sendall(b'x')
                except OSError: pass
            time.sleep(0.04)
        self.assertEqual(self.calls,[])
        time.sleep(0.05)
        connection = http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=1)
        connection.request('GET','/health')
        response = connection.getresponse()
        self.assertEqual(response.status,200)
        response.read()
        connection.close()

    def test_header_byte_cap(self):
        sock = self.connect()
        sock.sendall(b'GET /health HTTP/1.1\r\nX: '+b'x'*17000+b'\r\n\r\n')
        try: result = sock.recv(100)
        except ConnectionResetError: result = b''
        self.assertEqual(result,b'')
        self.assertEqual(self.calls,[])

    def test_provider_wait_cannot_extend_admitted_socket(self):
        data = payload('review')
        release = threading.Event()
        def slow(data):
            release.wait(1)
            return ok(data)
        self.app.send = slow
        connection = http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=1)
        start = time.monotonic()
        try:
            connection.request('POST','/api/forms',json.dumps(data),{'Origin':'https://qc.example','Content-Type':'application/json','Idempotency-Key':data['request_id']})
            try:
                response = connection.getresponse()
                self.assertNotEqual(json.loads(response.read()).get('status'),'delivered')
            except (http.client.RemoteDisconnected,ConnectionResetError):
                pass
            self.assertLess(time.monotonic()-start,0.8)
            time.sleep(0.03)
            release.set()
            time.sleep(0.03)
            self.assertEqual(self.store.public(data['request_id'])['status'],'unknown')
        finally:
            release.set()
            connection.close()

    def test_public_bind_refused(self):
        with self.assertRaises(ValueError):
            Server(('0.0.0.0',0),self.app)


if __name__ == '__main__': unittest.main(verbosity=2)
