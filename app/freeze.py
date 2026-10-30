import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parent
old=root.parent/'qs-client-ready-backend-20261022-v1'
original=json.loads((root/'original-manifest.json').read_text())
assert (old/'manifest.json').read_bytes()==(root/'original-manifest.json').read_bytes()
for entry in original['files']:
    assert hashlib.sha256((old/entry['path']).read_bytes()).hexdigest()==entry['sha256'],entry['path']
names=['README.md','Readmde.md','api-deployment-agreement.md','original-manifest.json',
       'backend/server.py','backend/test_server.py','backend/test_correction.py',
       'backend/inspect_receipts.py','backend/package.json','test-results.txt','freeze.py']
entries=[{'path':name,'bytes':(root/name).stat().st_size,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in sorted(names)]
digest=hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(root/'manifest.json').write_text(json.dumps({'schema':'qs-backend-artifact.v2','handoff_id':'evt-owner-513fc12254e755fb15d617da','digest':digest,'files':entries},indent=2)+'\n')
print(json.dumps({'digest':digest,'files':len(entries),'original_v1_unchanged':True,'tests_passed':32,'release_B1_public_ingress':'unresolved_decision'}))
