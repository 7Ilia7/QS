"""Estimate contract semantics; notification transport is always mocked."""
import http.client
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/backend'))
from server import App, Store, Server, Telegram, TARGET, validate, estimate_summary


def request(grams=100,master='master',removal=False):
    return {'request_id':str(uuid.uuid4()),'type':'callback','phone':'+380000000001','consent':True,'source':'qc-web',
            'estimate':{'version':1,'master':master,'grams':grams,'removal':removal}}


class EstimateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(self.tmp.name)
        self.sent=[]
        def send(data):
            self.sent.append(data)
            return {'ok':True,'result':{'message_id':1,'chat':{'id':int(TARGET)}}}
        self.send=send
        self.app=App(self.store,send,'http://127.0.0.1',per_ip=100,total=100)
        self.block=patch('socket.create_connection',side_effect=AssertionError('external network forbidden'))
        self.block.start()

    def tearDown(self):
        self.block.stop()
        self.store.close()
        self.tmp.cleanup()

    def post(self,data):
        return self.app.request('POST','/api/forms',{'Origin':self.app.origin,'Content-Type':'application/json','Idempotency-Key':data['request_id']},json.dumps(data).encode())

    def test_exact_half_open_tiers_both_masters_and_removal(self):
        cases=[(0.001,0),(49.99999999999999,0),(50,1),(99.99999999999999,1),(100,2),(199.99999999999997,2),(200,3),(1e308,3)]
        for master,prices in [('master',[3100,5300,7500,9700]),('olena',[4400,6600,8800,11000])]:
            for grams,tier in cases:
                for removal in (False,True):
                    data=request(grams,master,removal)
                    self.assertEqual(self.post(data)[0],200)
                    summary=dict(estimate_summary(self.sent[-1]['estimate']))
                    self.assertEqual(summary['РОБОТА'],f'{prices[tier]} грн')
                    self.assertEqual(summary['ЗНЯТТЯ'],f'{1300 if removal else 0} грн')
                    self.assertEqual(summary['РАЗОМ ЗА РОБОТУ'],f'{prices[tier]+(1300 if removal else 0)} грн')
                    self.assertIn('окремо',summary['ВОЛОССЯ'])

    def test_schema_rejects_client_amounts_wrong_types_nonfinite_and_review(self):
        original=request()['estimate']
        bad=[None,{},[],{**original,'price':1},{k:v for k,v in original.items() if k!='removal'}]
        for key,values in {'version':[True,1.0,2,'1'],'master':['Master','Олена',{},None],
                           'grams':[True,False,0,-1,'100',None,float('nan'),float('inf'),-float('inf'),10**309],
                           'removal':[0,1,'false',None]}.items():
            bad.extend({**original,key:value} for value in values)
        for value in bad:
            data=request();data['estimate']=value
            self.assertEqual(self.post(data)[0],422,value)
        data=request();data.update(type='review',review='LOCAL MOCK review');data.pop('phone')
        self.assertEqual(self.post(data)[0],422)
        self.assertEqual(self.sent,[])

    def test_fingerprint_normalization_conflict_status_privacy_and_restart(self):
        data=request(100.0)
        first=self.post(data)
        data['estimate']['grams']=100
        self.assertEqual(self.post(data),first)
        for field,value in [('grams',100.1),('master','olena'),('removal',True)]:
            changed={**data,'estimate':{**data['estimate'],field:value}}
            self.assertEqual(self.post(changed)[0],409)
        rid=data['request_id']
        self.assertEqual(self.store.data['records'][rid]['estimate'],data['estimate'])
        self.assertNotIn('estimate',self.store.public(rid))
        self.assertNotIn('phone',self.store.path.read_text())
        self.store.close();self.store=Store(self.tmp.name,initialize=False)
        self.app=App(self.store,lambda _:self.fail('duplicate resend'),self.app.origin)
        self.assertEqual(self.post(data),first)
        self.assertEqual(len(self.sent),1)

    def test_plain_callback_and_capability_are_backward_compatible(self):
        data=request();data.pop('estimate')
        self.assertEqual(self.post(data)[0],200)
        before=len(self.store.data['records'])
        self.assertEqual(self.app.request('GET','/api/forms/capabilities',{}),(200,{'estimate':{'version':1}}))
        self.assertEqual(len(self.store.data['records']),before)
        self.assertEqual(self.app.request('GET','/api/forms/capabilities',{'Origin':'https://other.example'})[0],403)
        self.assertEqual(self.app.request('POST','/api/forms/capabilities',{'Origin':self.app.origin})[0],404)

    def test_telegram_text_server_amounts_escaping_and_no_body_storage(self):
        data=validate({**request(50,'olena',True),'name':'<LOCAL MOCK &>'})
        class Reply:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return b'{"ok":true}'
        transport=Telegram('DUMMY_LOCAL_ONLY',TARGET)
        with patch.object(transport.opener,'open',return_value=Reply()) as call:
            transport(data)
            text=json.loads(call.call_args.args[0].data)['text']
        self.assertIn('РОБОТА: 6600 грн',text)
        self.assertIn('РАЗОМ ЗА РОБОТУ: 7900 грн',text)
        self.assertIn('&lt;LOCAL MOCK &amp;&gt;',text)
        self.assertNotIn('<LOCAL MOCK',text)

    def test_limits_failure_unknown_preserve_context_without_resend(self):
        data=request()
        self.app.send=lambda _:(_ for _ in ()).throw(TimeoutError())
        code,body=self.post(data)
        self.assertEqual((code,body['status'],body['retry_safe']),(503,'unknown',False))
        self.assertEqual(self.post(data)[0],202)
        data['estimate']['grams']=50
        self.assertEqual(self.post(data)[0],409)
        fresh=request();fresh['name']='x'*9000
        self.assertEqual(self.post(fresh)[0],413)


if __name__=='__main__':unittest.main(verbosity=2)
