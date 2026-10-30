"""QC forms, stdlib only. Private technical state, never customer payloads."""
import argparse
import fcntl
import hashlib
import hmac
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 8192
TTL = 86400
TARGET = '-4907639564'


def valid_id(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value, version=4)) == value and uuid.UUID(value).version == 4
    except (ValueError, TypeError, AttributeError):
        return False


def validate(data):
    if not isinstance(data, dict) or set(data) - {'request_id', 'type', 'name', 'phone', 'review', 'consent', 'source'}:
        raise ValueError('fields')
    if not valid_id(data.get('request_id')) or data.get('type') not in ('callback', 'review') or data.get('consent') is not True or data.get('source') != 'qc-web':
        raise ValueError('schema')
    result = dict(data)
    for field in ('name', 'review', 'phone'):
        if field in data:
            if not isinstance(data[field], str) or any(ord(c) < 32 and c not in '\n\t' for c in data[field]):
                raise ValueError(field)
            result[field] = data[field].strip()
    if len(result.get('name', '')) > 80:
        raise ValueError('name')
    if result['type'] == 'callback':
        if 'review' in result:
            raise ValueError('review')
        phone = re.sub(r'[\s()\-]', '', result.get('phone', ''))
        if re.fullmatch(r'0\d{9}', phone):
            phone = '+38' + phone
        if not re.fullmatch(r'\+[1-9][0-9]{7,14}', phone):
            raise ValueError('phone')
        result['phone'] = phone
    elif 'phone' in result or not 10 <= len(result.get('review', '')) <= 2000:
        raise ValueError('review')
    return result


class Store:
    def __init__(self, directory, clock=time.time, synthetic_pairs=None, initialize=True):
        self.pairs = dict(synthetic_pairs or {})
        if self.pairs and (len(self.pairs) != 2 or sorted(self.pairs.values()) != ['callback', 'review'] or not all(valid_id(k) for k in self.pairs)):
            raise ValueError('exactly two predeclared UUID/type pairs required')
        self.root = Path(directory)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink() or self.root.stat().st_mode & 0o077:
            raise ValueError('state directory must be private')
        self.lockfile = open(self.root / 'writer.lock', 'a+b')
        os.chmod(self.root / 'writer.lock', 0o600)
        try:
            fcntl.flock(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.lockfile.close()
            raise
        self.lock = threading.RLock()
        self.clock = clock
        self.path = self.root / 'outcomes.json'
        self.unhealthy = False
        if not self.path.exists() and not initialize:
            self.close()
            raise ValueError('state missing: operator initialization required; never auto-reset')
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'key': secrets.token_hex(32), 'records': {}}
        if 'synthetic_pairs' in self.data and self.data['synthetic_pairs'] != self.pairs:
            self.close()
            raise ValueError('predeclaration changed')
        if 'synthetic_pairs' not in self.data and any(k in self.data['records'] for k in self.pairs):
            self.close()
            raise ValueError('cannot predeclare an already used UUID')
        self.data['synthetic_pairs'] = self.pairs
        self.data.setdefault('spent_synthetic', [])
        # A reservation recovered after process death may already have reached Telegram.
        for record in self.data['records'].values():
            if record['status'] == 'pending':
                record['status'] = 'unknown'
        self.save()

    def save(self):
        temporary = self.root / 'outcomes.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(self.data, stream, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        directory = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def digest(self, data):
        raw = json.dumps(data, sort_keys=True, ensure_ascii=True).encode()
        return hmac.new(bytes.fromhex(self.data['key']), raw, hashlib.sha256).hexdigest()

    def public(self, request_id):
        record = self.data['records'].get(request_id)
        if self.unhealthy:
            return {'request_id': request_id, 'type': record['type'] if record else self.pairs.get(request_id), 'status': 'unknown', 'retry_safe': False}
        if record is None:
            return {'request_id': request_id, 'type': None, 'status': 'not_found', 'retry_safe': False}
        status = record['status'] if self.clock() - record['created'] < TTL else 'unknown'
        if request_id in self.pairs and status == 'delivered' and not self.receipt_valid(request_id, record):
            status = 'unknown'
        result = {'request_id': request_id, 'type': record['type'], 'status': status, 'retry_safe': status == 'failed'}
        if status == 'delivered':
            result['receipt_id'] = record['receipt_id']
        return result

    def receipt_valid(self, rid, record):
        receipt = record.get('provider_receipt')
        return (isinstance(receipt, dict) and set(receipt) == {'request_id', 'type', 'ok', 'message_id', 'target', 'timestamp', 'receipt_id'}
                and receipt['request_id'] == rid and receipt['type'] == self.pairs[rid] == record['type']
                and receipt['ok'] is True and type(receipt['message_id']) is int and receipt['message_id'] > 0
                and receipt['target'] == TARGET and valid_id(receipt['receipt_id'])
                and receipt['receipt_id'] == record.get('receipt_id') and type(receipt['timestamp']) in (int, float))

    def close(self):
        self.lockfile.close()


class Telegram:
    def __init__(self, token, target, synthetic_pairs=None):
        if not token or target != TARGET:
            raise ValueError('missing token or unapproved target')
        self.token = token
        self.target = target
        self.pairs = synthetic_pairs or {}
        # No ambient proxies; redirects must never carry a credential to another host.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def __call__(self, data):
        label = ('TEST_' if self.pairs.get(data['request_id']) == data['type'] else '') + data['type'].upper()
        fields = [('TYPE', label), ('ID', data['request_id']), ('SOURCE', 'qc-web'),
                  ('UTC', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))]
        fields += [(key.upper(), data[key]) for key in ('name', 'phone', 'review') if data.get(key)]
        text = '\n'.join(html.escape(key + ': ' + value) for key, value in fields)
        body = json.dumps({'chat_id': self.target, 'text': text, 'parse_mode': 'HTML'}).encode()
        request = urllib.request.Request('https://api.telegram.org/bot' + self.token + '/sendMessage', data=body,
                                         headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with self.opener.open(request, timeout=8) as response:
                return json.loads(response.read(65537))
        except urllib.error.HTTPError as error:
            # Only a parsed explicit Bot API rejection is definite. No raw error logging.
            return json.loads(error.read(65537))


class App:
    def __init__(self, store, send, origin, trusted_proxy=False, per_ip=5, total=60, deadline=8):
        parsed = urllib.parse.urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or origin != parsed.scheme + '://' + parsed.netloc:
            raise ValueError('exact origin required')
        self.store, self.send, self.origin = store, send, origin
        self.trusted_proxy, self.per_ip, self.total = trusted_proxy, per_ip, total
        self.buckets = {}
        self.global_times = []
        self.deadline = deadline
        self.provider_slots = threading.BoundedSemaphore(16)

    def request(self, method, path, headers, body=b'', peer='127.0.0.1', remaining=None):
        end = time.monotonic() + remaining if remaining is not None else None
        headers = {k.lower(): v for k, v in headers.items()}
        def fail(code, name, safe=True):
            return code, {'error': name, 'retry_safe': safe}
        url = urllib.parse.urlsplit(path)
        if method == 'GET' and path == '/health':
            return 200, {'status': 'ok', 'service': 'qs-forms', 'version': 1}
        if headers.get('origin') not in (None, self.origin) or (method == 'POST' and headers.get('origin') != self.origin):
            return fail(403, 'origin')
        if method == 'GET' and url.path == '/api/forms/status':
            query = urllib.parse.parse_qs(url.query)
            rid = query.get('request_id', [None])[0]
            if set(query) != {'request_id'} or len(query['request_id']) != 1 or not valid_id(rid):
                return fail(400, 'request_id')
            with self.store.lock:
                return 200, self.store.public(rid)
        if method != 'POST' or path != '/api/forms':
            return fail(404, 'not_found')
        if headers.get('content-type', '').lower() not in ('application/json', 'application/json; charset=utf-8'):
            return fail(415, 'content_type')
        if len(body) > MAX_BODY:
            return fail(413, 'size')
        try:
            def unique_pairs(pairs):
                out = {}
                for key, value in pairs:
                    if key in out:
                        raise ValueError('duplicate field')
                    out[key] = value
                return out
            data = validate(json.loads(body.decode('utf-8'), object_pairs_hook=unique_pairs))
        except (ValueError, UnicodeError, RecursionError):
            return fail(422, 'validation')
        rid = data['request_id']
        if rid in self.store.pairs and self.store.pairs[rid] != data['type']:
            return fail(422, 'predeclared_type', False)
        if headers.get('idempotency-key') != rid:
            return fail(400, 'idempotency_key')
        if self.trusted_proxy:
            try:
                if not ipaddress.ip_address(peer).is_loopback:
                    return fail(403, 'proxy')
                peer = str(ipaddress.ip_address(headers.get('x-forwarded-for', '')))
            except ValueError:
                return fail(400, 'proxy_client')
        with self.store.lock:
            if self.store.unhealthy:
                return fail(503, 'state_unavailable', False)
            digest = self.store.digest(data)
            prior = self.store.data['records'].get(rid)
            if prior:
                if not hmac.compare_digest(prior['digest'], digest):
                    return fail(409, 'idempotency_conflict', False)
                outcome = self.store.public(rid)
                return (200 if outcome['status'] == 'delivered' else 502 if outcome['status'] == 'failed' else 202), outcome
            if rid in self.store.data['spent_synthetic']:
                return 202, {'request_id': rid, 'type': self.store.pairs[rid], 'status': 'unknown', 'retry_safe': False}
            if end is not None and time.monotonic() >= end:
                return fail(408, 'admission_deadline', False)
            now = self.store.clock()
            self.buckets = {key: [v for v in values if now-v < 60] for key, values in self.buckets.items() if values and now-values[-1] < 60}
            self.global_times = [v for v in self.global_times if now-v < 60]
            values = self.buckets.get(peer, [])
            if len(values) >= self.per_ip or len(self.global_times) >= self.total or (peer not in self.buckets and len(self.buckets) >= 4096):
                return fail(429, 'rate_limited')
            if len(self.store.data['records']) >= 10000:
                return fail(503, 'capacity')
            if not self.provider_slots.acquire(False):
                return fail(503, 'provider_capacity')
            self.buckets[peer] = values + [now]
            self.global_times.append(now)
            self.store.data['records'][rid] = {'type': data['type'], 'digest': digest, 'created': now, 'status': 'pending'}
            if rid in self.store.pairs:
                self.store.data['spent_synthetic'].append(rid)
            try:
                self.store.save()  # MUST be durable before any network effect.
            except BaseException:
                self.provider_slots.release()
                self.store.unhealthy = True
                raise
        status, code = 'unknown', 503
        done, replies = threading.Event(), []
        def invoke():
            try:
                if end is None or time.monotonic() < end:
                    replies.append(self.send(data))
            except Exception:
                pass
            finally:
                self.provider_slots.release()
                done.set()
        # Absolute application deadline; slow network cannot extend browser wait.
        # Late replies never mutate outcome or trigger retries; slots stay bounded.
        threading.Thread(target=invoke, daemon=True).start()
        try:
            wait = min(self.deadline, max(0, end-time.monotonic())) if end is not None else self.deadline
            response = replies[0] if done.wait(wait) and replies else None
            if isinstance(response, dict) and response.get('ok') is False and type(response.get('error_code')) is int and response['error_code'] in (400, 401, 403, 404, 429):
                status, code = 'failed', 502
            elif isinstance(response, dict) and response.get('ok') is True:
                result = response.get('result', {})
                if isinstance(result, dict) and type(result.get('message_id')) is int and result['message_id'] > 0 and str(result.get('chat', {}).get('id')) == TARGET:
                    status, code = 'delivered', 200
        except Exception:
            pass  # Uncertain; never leak token-bearing exception/URL or resend.
        with self.store.lock:
            record = self.store.data['records'][rid]
            record['status'] = status
            if status == 'delivered':
                record['receipt_id'] = str(uuid.uuid4())
                if rid in self.store.pairs:
                    record['provider_receipt'] = {'request_id': rid, 'type': data['type'], 'ok': True,
                        'message_id': result['message_id'], 'target': TARGET, 'timestamp': self.store.clock(), 'receipt_id': record['receipt_id']}
            try:
                self.store.save()
            except Exception:
                record['status'] = 'unknown'
                record.pop('provider_receipt', None)
                record.pop('receipt_id', None)
                self.store.unhealthy = True
                return 503, self.store.public(rid)
            return code, self.store.public(rid)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, address, app, admission_seconds=10, max_handlers=16):
        if not ipaddress.ip_address(address[0]).is_loopback:
            raise ValueError('loopback bind required')
        self.app = app
        self.admission_seconds = admission_seconds
        self.slots = threading.BoundedSemaphore(max_handlers)
        self.admitted = {}
        self.admitted_lock = threading.Lock()
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not ipaddress.ip_address(address[0]).is_loopback or not self.slots.acquire(False):
            request.close()
            return
        def expire():
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            request.close()
        timer = threading.Timer(self.admission_seconds, expire)
        timer.daemon = True
        with self.admitted_lock:
            self.admitted[id(request)] = (time.monotonic()+self.admission_seconds, timer)
        timer.start()
        try:
            super().process_request(request, address)
        except BaseException:
            timer.cancel()
            with self.admitted_lock:
                self.admitted.pop(id(request), None)
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            with self.admitted_lock:
                _, timer = self.admitted.pop(id(request))
            timer.cancel()
            self.slots.release()

    def handle_error(self, request, address):
        pass  # No request body, query, provider exception or customer metadata logs.


class HeaderBudget:
    """Bound bytes read for request line+headers even with slow streaming."""
    def __init__(self, stream):
        self.stream, self.left = stream, 16384

    def readline(self, limit=-1):
        if self.left <= 0:
            raise ValueError('header budget')
        value = self.stream.readline(min(self.left+1, limit) if limit >= 0 else self.left+1)
        self.left -= len(value)
        if self.left < 0:
            raise ValueError('header budget')
        return value

    def __getattr__(self, name):
        return getattr(self.stream, name)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)
        super().setup()
        self.rfile = HeaderBudget(self.rfile)
        with self.server.admitted_lock:
            self.admission_end = self.server.admitted[id(self.request)][0]

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.handle_api()

    def do_POST(self):
        self.handle_api()

    def handle_api(self):
        try:
            # Reject ambiguous HTTP framing, including duplicate critical headers.
            for key in ('Content-Length', 'Content-Type', 'Origin', 'Idempotency-Key', 'X-Forwarded-For'):
                if len(self.headers.get_all(key, [])) > 1:
                    raise ValueError('framing')
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('framing')
            size = int(self.headers.get('Content-Length', '0'))
            if size < 0:
                raise ValueError('size')
            if size > MAX_BODY:
                code, data = 413, {'error': 'size', 'retry_safe': True}
            else:
                body = bytearray()
                while len(body) < size:
                    remaining = self.admission_end - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError()
                    self.connection.settimeout(remaining)
                    chunk = self.rfile.read1(min(8192, size - len(body)))
                    if not chunk:
                        raise ValueError('truncated')
                    body.extend(chunk)
                self.connection.settimeout(10)
                code, data = self.server.app.request(self.command, self.path, dict(self.headers), bytes(body), self.client_address[0], remaining=max(0, self.admission_end-time.monotonic()))
        except (ValueError, TimeoutError, socket.timeout):
            code, data = 400, {'error': 'request', 'retry_safe': True}
        except Exception:
            code, data = 503, {'error': 'unavailable', 'retry_safe': False}
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        if code == 429:
            self.send_header('Retry-After', '60')
        self.end_headers()
        self.wfile.write(raw)
        self.close_connection = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8787)
    parser.add_argument('--initialize-state', action='store_true', help='operator-only fresh ledger initialization; never reset existing state')
    args = parser.parse_args()
    # No dotenv loading/secret discovery. Deployment injects an approved environment.
    pairs = json.loads(os.environ.get('QS_SYNTHETIC_PAIRS', '{}'))
    if args.initialize_state and (Path(os.environ['QS_STATE_DIR'])/'outcomes.json').exists():
        raise ValueError('refuse existing ledger reinitialization')
    store = Store(os.environ['QS_STATE_DIR'], synthetic_pairs=pairs, initialize=args.initialize_state)
    if args.initialize_state:
        store.close()
        return
    app = App(store, Telegram(os.environ['QS_TELEGRAM_TOKEN'], os.environ['QS_TELEGRAM_CHAT_ID'], pairs),
              os.environ['QS_ORIGIN'], trusted_proxy=os.environ.get('QS_TRUST_LOOPBACK_PROXY') == '1')
    server = Server(('127.0.0.1', args.port), app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == '__main__':
    main()
