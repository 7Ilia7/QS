"""Local source inventory and optional domain plan; never edits site or contacts providers."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import argparse, json, re

ROOT = Path(__file__).resolve().parents[1]

class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.links = {}
    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if tag == 'meta':
            self.meta[row.get('name') or row.get('property')] = row.get('content')
        if tag == 'link':
            self.links[row.get('rel')] = row.get('href')

def inspect(origin=None):
    html = (ROOT/'site/index.html').read_text()
    parsed = Meta(); parsed.feed(html)
    content_source = (ROOT/'site/content-data.js').read_text()
    content = json.loads(content_source.split('window.qsStudioContent = ',1)[1].strip().removesuffix(';'))
    allow = json.loads((ROOT/'release/allowlist.json').read_text())
    image_sizes = {str(f.relative_to(ROOT/'site')):f.stat().st_size for f in sorted((ROOT/'site/img/optimized').glob('*')) if f.is_file()}
    result = {
        'evidence_tier':'LOCAL SOURCE; no domain/provider/network verification',
        'preview_noindex':'noindex' in (parsed.meta.get('robots') or ''),
        'preview_robots':(ROOT/'site/robots.txt').read_text(),
        'baseline_canonical_retained':parsed.links.get('canonical'),
        'baseline_og_url':parsed.meta.get('og:url'),
        'baseline_og_image':parsed.meta.get('og:image'),
        'sitemap_retained':(ROOT/'site/sitemap.xml').read_text(),
        'favicon':{'path':parsed.links.get('icon'),'exists':(ROOT/'site'/str(parsed.links.get('icon'))).is_file()},
        'public_allowlist_files':len(allow['public']),
        'public_text_bytes':{f:(ROOT/'site'/f).stat().st_size for f in ['index.html','styles.css','forms.css','script.js','forms.js','content-data.js']},
        'optimized_image_bytes':image_sizes,
        'review_schema_present':bool(re.search(r'"(?:aggregateRating|reviewRating)"',html)),
        'analytics_activation':'NONE added; accounts/IDs/configuration NOT CHECKED',
        'content_mode':content.get('mode'),
        'chosen_public_origin':content.get('publication',{}).get('public_origin'),
        'domain_https_redirect_search_console':'NOT CHECKED; domain/account/release authority required',
        'publication_ready':False,
    }
    if origin:
        url = urlsplit(origin)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
            raise ValueError('origin must be HTTPS origin only, no credentials/path/query/fragment')
        canonical = origin.rstrip('/')
        result['domain_plan_only'] = {
            'requires_explicit_chosen_domain_and_approved_release':True,
            'canonical_and_og_url':canonical+'/',
            'og_image':canonical+'/img/optimized/hero-1120.webp',
            'sitemap_urls':[canonical+'/',canonical+'/privacy.html'],
            'future_robots_sitemap':canonical+'/sitemap.xml',
            'preview_noindex_removal':'ONLY after final content/domain/owner/release review',
            'external_validation':'NOT RUN',
        }
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin',help='optional approved future HTTPS origin; plan only')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.origin),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'site_modified':False,'network_calls':0}))
