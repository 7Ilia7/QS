import concurrent.futures
import contextlib
import http.client
import io
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from server import App, Store, Server, TARGET, Telegram, TTL


def payload(kind='callback'):
    data = dict(request_id=str(uuid.uuid4()), type=kind, consent=True, source='qc-web', name='<Test & name>')
    data.update(phone='+380000000001') if kind == 'callback' else data.update(review='<b>Private test review & text</b>')
    return data


def ok(data):
    return {'ok': True, 'result': {'message_id': 123, 'chat': {'id': int(TARGET)}}}


class FormsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.calls = []
        def send(data):
            self.calls.append(data)
            return ok(data)
        self.app = App(self.store, send, 'https://qc.example', per_ip=100, total=200)
        # Any accidental real external connection fails. Transport is injected/mock only.
        self.network = patch('socket.create_connection', side_effect=AssertionError('external network forbidden'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.store.close()
        self.temp.cleanup()

    def post(self, data, app=None, raw=None, headers=None):
        base = {'Content-Type': 'application/json', 'Origin': 'https://qc.example', 'Idempotency-Key': data.get('request_id', '')}
        base.update(headers or {})
        return (app or self.app).request('POST', '/api/forms', base, json.dumps(data).encode() if raw is None else raw)

    def status(self, data):
        return self.app.request('GET', '/api/forms/status?request_id=' + data['request_id'], {})[1]

    def test_positive_both_and_replay(self):
        for kind in ('callback', 'review'):
            data = payload(kind)
            code, body = self.post(data)
            self.assertEqual(code, 200)
            self.assertEqual((body['request_id'], body['type'], body['status']), (data['request_id'], kind, 'delivered'))
            self.assertTrue(uuid.UUID(body['receipt_id']))
            self.assertEqual(self.status(data), body)
            self.assertEqual(self.post(data), (code, body))
        self.assertEqual(len(self.calls), 2)

    def test_invalid_both_empty_type_lengths_and_keys(self):
        for kind in ('callback', 'review'):
            base = payload(kind)
            variants = [{}, {**base, 'consent': False}, {**base, 'name': 'x'*81}, {**base, 'other': True},
                        {**base, 'type': 'CALLBACK'}, {**base, 'name': []}, {**base, 'source': 'other'},
                        {**base, 'request_id': str(uuid.uuid1())}, {**base, 'name': '\x00bad'}]
            variants += [{**base, 'phone': ''}, {**base, 'phone': 'bad'}, {**base, 'review': 'not allowed'}] if kind == 'callback' else [{**base, 'review': ''}, {**base, 'review': 'x'*2001}, {**base, 'phone': '+380000000001'}]
            for data in variants:
                self.assertEqual(self.post(data)[0], 422)
            for raw in (b'', b'{', b'null', b'[]', b'\xff', b'{"type":"callback","type":"review"}'):
                self.assertEqual(self.post(base, raw=raw)[0], 422)
            self.assertEqual(self.post(base, raw=b' '*8193)[0], 413)
            self.assertEqual(self.post(base, headers={'Content-Type': 'text/plain'})[0], 415)
            self.assertEqual(self.post(base, headers={'Origin': 'https://evil.example'})[0], 403)
            self.assertEqual(self.post(base, headers={'Idempotency-Key': str(uuid.uuid4())})[0], 400)
        self.assertEqual(self.calls, [])

    def test_normalization_and_conflicting_payload(self):
        data = payload()
        data['phone'] = '(000) 000-00-01'
        self.assertEqual(self.post(data)[0], 200)
        self.assertEqual(self.calls[0]['phone'], '+380000000001')
        self.assertEqual(self.post({**data, 'name': 'different'})[0], 409)
        self.assertEqual(len(self.calls), 1)

    def test_concurrent_duplicates_both_types(self):
        for kind in ('callback', 'review'):
            entered, release = threading.Event(), threading.Event()
            def send(data):
                self.calls.append(data)
                entered.set()
                release.wait(2)
                return ok(data)
            self.app.send = send
            data = payload(kind)
            with concurrent.futures.ThreadPoolExecutor(8) as pool:
                first = pool.submit(self.post, data)
                self.assertTrue(entered.wait(1))
                others = list(pool.map(lambda _: self.post(data), range(7)))
                self.assertTrue(all(code == 202 and body['status'] == 'pending' for code, body in others))
                release.set()
                self.assertEqual(first.result()[0], 200)
        self.assertEqual(len(self.calls), 2)

    def test_provider_errors_and_ambiguous_both(self):
        for kind in ('callback', 'review'):
            for response in ({'ok': False, 'error_code': 400, 'description': 'PRIVATE RAW ERROR'},
                             {'ok': True}, {'ok': True, 'result': {'message_id': True, 'chat': {'id': TARGET}}},
                             {'ok': True, 'result': {'message_id': 123, 'chat': {'id': '-100wrong'}}}, None):
                self.app.send = lambda data: response
                data = payload(kind)
                code, result = self.post(data)
                definite = isinstance(response, dict) and response.get('ok') is False
                self.assertEqual(code, 502 if definite else 503)
                self.assertEqual(result['retry_safe'], definite)
                self.assertNotIn('receipt_id', result)
                self.assertNotIn('PRIVATE', json.dumps(result))
            def timeout(data):
                raise TimeoutError('SECRET URL')
            self.app.send = timeout
            code, result = self.post(payload(kind))
            self.assertEqual((code, result['status'], result['retry_safe']), (503, 'unknown', False))

    def test_absolute_deadline_and_late_acceptance(self):
        release = threading.Event()
        self.app.deadline = 0.02
        def send(data):
            release.wait(1)
            return ok(data)
        self.app.send = send
        data = payload('review')
        started = time.monotonic()
        self.assertEqual(self.post(data)[1]['status'], 'unknown')
        self.assertLess(time.monotonic()-started, 0.5)
        release.set()
        time.sleep(0.03)
        self.assertEqual(self.status(data)['status'], 'unknown')
        self.assertEqual(self.post(data)[0], 202)

    def test_crash_after_possible_accept_and_refresh(self):
        for kind in ('callback', 'review'):
            data = payload(kind)
            original = self.store.save
            count = 0
            def crash():
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError('simulated crash after Telegram acceptance before outcome persist')
                original()
            self.store.save = crash
            self.assertEqual(self.post(data)[0], 503)
            self.store.close()
            self.store = Store(self.temp.name)
            self.app = App(self.store, lambda _: self.fail('must never resend after crash'), 'https://qc.example')
            self.assertEqual(self.status(data)['status'], 'unknown')
            self.assertEqual(self.post(data)[0], 202)
            self.app.send = lambda data: ok(data)

    def test_refresh_delivered_failed_ttl_and_missing(self):
        for kind in ('callback', 'review'):
            data = payload(kind)
            first = self.post(data)[1]
            self.store.close()
            self.store = Store(self.temp.name)
            self.app = App(self.store, lambda _: self.fail('resend forbidden'), 'https://qc.example')
            self.assertEqual(self.status(data), first)
            self.store.clock = lambda: time.time() + TTL + 1
            self.assertEqual(self.status(data)['status'], 'unknown')
            self.assertEqual(self.post(data)[0], 202)
            self.assertEqual(self.status(payload(kind))['retry_safe'], False)
            self.store.clock = time.time
            self.app.send = ok

    def test_rate_limits_and_replay_even_at_limit(self):
        self.app.per_ip = 1
        data = payload()
        self.assertEqual(self.post(data)[0], 200)
        self.assertEqual(self.post(payload('review'))[0], 429)
        self.assertEqual(self.post(data)[0], 200)
        self.assertEqual(len(self.calls), 1)
        self.app.per_ip = 10
        self.app.total = 1
        self.assertEqual(self.post(payload())[0], 429)

    def test_private_disk_and_no_customer_logging(self):
        log = io.StringIO()
        data = payload('review')
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            self.post(data)
        disk = (Path(self.temp.name) / 'outcomes.json').read_text()
        for private in ('Private test', '<Test', 'phone', 'review" :', 'TELEGRAM_TOKEN'):
            self.assertNotIn(private, disk)
        self.assertEqual(log.getvalue(), '')
        self.assertEqual((Path(self.temp.name) / 'outcomes.json').stat().st_mode & 0o777, 0o600)
        with self.assertRaises(BlockingIOError):
            Store(self.temp.name)

    def test_trusted_proxy_rejects_untrusted_or_appended_ip(self):
        self.app.trusted_proxy = True
        self.assertEqual(self.post(payload())[0], 400)
        self.assertEqual(self.post(payload(), headers={'X-Forwarded-For': '1.2.3.4, 1.2.3.5'})[0], 400)
        self.assertEqual(self.post(payload(), headers={'X-Forwarded-For': '192.0.2.1'})[0], 200)

    def test_server_error_is_ambiguous_and_failed_refresh_is_stable(self):
        self.app.send = lambda _: {'ok': False, 'error_code': 500}
        self.assertEqual(self.post(payload())[1]['retry_safe'], False)
        self.app.send = lambda _: {'ok': False, 'error_code': 403}
        data = payload('review')
        result = self.post(data)[1]
        self.store.close()
        self.store = Store(self.temp.name)
        self.app = App(self.store, lambda _: self.fail('no failed replay'), 'https://qc.example')
        self.assertEqual(self.status(data), result)
        self.assertEqual(self.post(data)[0], 502)

    def test_disk_failure_before_reservation_never_sends(self):
        with patch.object(self.store, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.post(payload())
        self.assertEqual(len(self.calls), 0)

    def test_capacity_fail_closed_and_maximum_review(self):
        data = payload('review')
        data['review'] = '&'*2000
        self.assertEqual(self.post(data)[0], 200)
        # Only technical records; test capacity without 10000 disk writes.
        record = next(iter(self.store.data['records'].values()))
        self.store.data['records'].update({str(uuid.uuid4()): dict(record) for _ in range(9999)})
        self.assertEqual(self.post(payload())[0], 503)
        self.assertEqual(len(self.calls), 1)

    def test_telegram_transport_escaping_and_no_retry(self):
        client = Telegram('DUMMY_TEST_ONLY', TARGET)
        class Reply:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, _): return json.dumps(ok({})).encode()
        with patch.object(client.opener, 'open', return_value=Reply()) as send:
            client(payload('review'))
            body = json.loads(send.call_args.args[0].data)
            self.assertEqual(body['chat_id'], TARGET)
            self.assertIn('&lt;b&gt;Private', body['text'])
            self.assertNotIn('<b>', body['text'])
            self.assertEqual(send.call_count, 1)
        with self.assertRaises(ValueError):
            Telegram('DUMMY', '-100wrong')

    def test_loopback_http_framing_health_and_headers(self):
        # Permit only the explicitly local test connection; provider stays injected.
        self.network.stop()
        original = socket.create_connection
        def local_only(address, *args, **kwargs):
            if address[0] != '127.0.0.1':
                raise AssertionError('nonlocal network forbidden')
            return original(address, *args, **kwargs)
        with patch('socket.create_connection', side_effect=local_only):
            server = Server(('127.0.0.1', 0), self.app)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def request(method, path, body=None, headers=None):
                    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=2)
                    connection.request(method, path, body, headers or {})
                    response = connection.getresponse()
                    result = response.status, dict(response.headers), json.loads(response.read())
                    connection.close()
                    return result
                code, headers, body = request('GET', '/health')
                self.assertEqual(code, 200)
                self.assertEqual(headers['Cache-Control'], 'no-store')
                data = payload('review')
                self.assertEqual(request('POST', '/api/forms', json.dumps(data), {'Origin': 'https://qc.example', 'Content-Type': 'application/json', 'Idempotency-Key': data['request_id']})[0], 200)
                self.assertEqual(request('POST', '/api/forms', '', {'Content-Length': '9999'})[0], 413)
                self.assertEqual(request('POST', '/api/forms', '', {'Transfer-Encoding': 'chunked'})[0], 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
        self.network.start()


if __name__ == '__main__':
    unittest.main(verbosity=2)
