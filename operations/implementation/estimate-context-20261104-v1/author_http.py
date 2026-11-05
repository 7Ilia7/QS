"""Owned loopback mock-preview checks, never forwards to external destinations."""
import hashlib
import http.client
import json
from pathlib import Path
import uuid

ROOT=Path(__file__).resolve().parents[3]
PORT=8046
def call(method,path,data=None):
    assert path.startswith('/')
    connection=http.client.HTTPConnection('127.0.0.1',PORT,timeout=5)
    headers={'Origin':f'http://127.0.0.1:{PORT}'}
    body=None
    if data is not None:
        headers.update({'Content-Type':'application/json','Idempotency-Key':data['request_id']})
        body=json.dumps(data)
    connection.request(method,path,body,headers)
    response=connection.getresponse()
    result=response.status,dict(response.headers),response.read()
    connection.close()
    assert result[1]['X-QS-Preview-Mode']=='LOCAL-MOCK-NO-DELIVERY'
    return result

def main():
    rows=[]
    names=json.loads((ROOT/'release/allowlist.json').read_text())['public']
    for name in names:
        code,_,body=call('GET','/'+name)
        assert code==200 and body==(ROOT/'site'/name).read_bytes(),name
        rows.append({'public':name,'sha256':hashlib.sha256(body).hexdigest()})
    assert b'Telegram' in call('GET','/__local_demo')[2]
    assert json.loads(call('GET','/api/forms/capabilities')[2])=={'estimate':{'version':1}}
    for private in ('/app/backend/server.py','/backend/server.py','/release.json','/outcomes.json','/.git/config','/operations/implementation/estimate-context-20261104-v1/preview.py','/%2e%2e/app/backend/server.py'):
        assert call('GET',private)[0]==404,private
    data={'request_id':str(uuid.uuid4()),'type':'callback','phone':'+380000000001','name':'LOCAL MOCK ONLY','source':'qc-web','consent':True,'estimate':{'version':1,'master':'olena','grams':99.99999999999999,'removal':True}}
    code,_,raw=call('POST','/api/forms',data)
    response=json.loads(raw)
    assert code==200 and response['status']=='delivered' and response['request_id']==data['request_id']
    assert 'estimate' not in response and 'message_id' not in response
    assert call('POST','/api/forms',data)[2]==raw
    assert call('GET','/api/forms/status?request_id='+data['request_id'])[2]==raw
    data['estimate']['grams']=100
    assert call('POST','/api/forms',data)[0]==409
    data['request_id']=str(uuid.uuid4());data['estimate']['total']=1
    assert call('POST','/api/forms',data)[0]==422
    data['request_id']=str(uuid.uuid4());data.pop('estimate')
    assert call('POST','/api/forms',data)[0]==200
    result={'tier':'REAL LOCAL HTTP; MOCK NOTIFICATION ONLY','public_bytes_verified':len(names),'public':rows,
            'private_paths_404':7,'capabilities':200,'estimate_callback':200,'duplicate':200,'status':200,
            'changed_context':409,'client_amount':422,'plain_callback':200,'real_external_sends':0}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
