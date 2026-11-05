"""LOCAL ONLY combined preview. Real modified App, mock sender, no credentials."""
import argparse
import json
import mimetypes
import os
import re
from pathlib import Path
import signal
import socket
import sys
import tempfile
import urllib.parse

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/backend'))
from server import App, Store, Server, Handler, TARGET

CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; frame-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
DEMO='''<!doctype html><html lang="uk"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>QS LOCAL DEMO — без надсилання</title><style>body{margin:0;background:#17120c;color:#ffe3a0;font:16px system-ui}header{padding:12px}iframe{display:block;border:0;width:100%;height:calc(100dvh - 100px)}</style><header><strong>LOCAL DEMO: Telegram вимкнено. Справжні заявки НЕ надсилаються.</strong><br>HTTP/API використовує змінений handler і mock sender. Успіх форми тут означає лише локальну імітацію. Вводьте лише synthetic дані.</header><iframe title="QS локальний перегляд" src="/index.html" sandbox="allow-scripts allow-same-origin allow-forms"></iframe></html>'''.encode()


def make_handler(public):
    class PreviewHandler(Handler):
        def end_headers(self):
            self.send_header('X-QS-Preview-Mode','LOCAL-MOCK-NO-DELIVERY')
            self.send_header('Content-Security-Policy',CSP)
            super().end_headers()

        def do_GET(self):
            path=urllib.parse.urlsplit(self.path).path
            if path.startswith('/api/'):
                return super().do_GET()
            name=urllib.parse.unquote(path).lstrip('/')
            if name in public and Path(name).suffix == '.mp4' and self.headers.get('Range'):
                file = ROOT/'site'/name
                if file.is_symlink():
                    self.send_error(404); return
                size = file.stat().st_size
                match = re.fullmatch(r'bytes=(\d*)-(\d*)',self.headers['Range'])
                start = end = None
                if match and (match[1] or match[2]):
                    if match[1]:
                        start = int(match[1])
                        end = min(int(match[2]) if match[2] else size-1,size-1)
                    else:
                        start = max(0,size-int(match[2]))
                        end = size-1
                if start is None or start>=size or end<start:
                    self.send_response(416)
                    self.send_header('Content-Range',f'bytes */{size}')
                    self.send_header('Content-Length','0')
                    self.end_headers(); return
                # Bound each metadata/seek response; later ranges remain available.
                end = min(end,start+512*1024-1)
                with file.open('rb') as stream:
                    stream.seek(start); body=stream.read(end-start+1)
                self.send_response(206)
                self.send_header('Content-Type','video/mp4')
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Cache-Control','no-store')
                self.send_header('Connection','close')
                self.end_headers()
                try:self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError):pass
                self.close_connection=True
                return
            if path in ('/','/__local_demo'):
                body,kind,code=DEMO,'text/html; charset=utf-8',200
            elif name in public and not (ROOT/'site'/name).is_symlink():
                body=(ROOT/'site'/name).read_bytes()
                kind=mimetypes.guess_type(name)[0] or 'application/octet-stream'
                code=200
            else:
                body,kind,code=b'Not found','text/plain',404
            self.send_response(code)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('Connection','close')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection=True
    return PreviewHandler


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8045)
    args=parser.parse_args()
    public=set(json.loads((ROOT/'release/allowlist.json').read_text())['public'])
    # A sender is defined here; production Telegram transport is never constructed.
    def mock_send(data):
        return {'ok':True,'result':{'message_id':1,'chat':{'id':int(TARGET)}}}
    socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('preview external network forbidden'))
    with tempfile.TemporaryDirectory(prefix='qs-estimate-demo-') as state:
        store=Store(state)
        app=App(store,mock_send,f'http://127.0.0.1:{args.port}')
        server=Server(('127.0.0.1',args.port),app)
        server.RequestHandlerClass=make_handler(public)
        signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        print(json.dumps({'pid':os.getpid(),'port':args.port,'mode':'LOCAL-MOCK-NO-DELIVERY','url':f'http://127.0.0.1:{args.port}/__local_demo'}),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:
            server.server_close()
            store.close()


if __name__=='__main__':main()
