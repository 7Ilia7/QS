"""Local source checks, without network or form submissions."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote
from release_lib import require


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'src', 'poster'} or (tag == 'link' and key == 'href'):
                self.refs.append(value)
            if key == 'srcset':
                self.refs.extend(x.strip().split()[0] for x in value.split(','))


def check(root):
    names = set(json.loads((root / 'release/allowlist.json').read_text())['public'])
    for html in (root / 'site').glob('*.html'):
        parser = Assets()
        parser.feed(html.read_text())
        for ref in parser.refs:
            url = urlsplit(ref or '')
            if url.scheme or url.netloc or not url.path:
                continue
            local = unquote(url.path).lstrip('/')
            require(local in names, 'missing_local_asset:' + local)
    for css in (root / 'site').glob('*.css'):
        for ref in re.findall(r'url\([\"\']?([^\)\"\']+)', css.read_text()):
            if not urlsplit(ref).scheme and not ref.startswith('#'):
                require(ref.lstrip('/') in names, 'missing_CSS_asset:' + ref)
    return {'local_asset_references': 'PASS', 'public_files': len(names), 'network_calls': 0}


if __name__ == '__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[1])))
