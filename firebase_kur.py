"""Convert downloaded Firebase configs locally, never print private keys."""
import argparse
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser(description='İndirilen Firebase dosyalarını yerel projeye bağlar.')
    p.add_argument('--android-json',required=True,type=Path)
    p.add_argument('--service-account',required=True,type=Path)
    args=p.parse_args()
    android=json.loads(args.android_json.read_text(encoding='utf-8-sig'))
    account=json.loads(args.service_account.read_text(encoding='utf-8-sig'))
    project=android['project_info']
    client=next((c for c in android['client'] if c['client_info']['android_client_info']['package_name']=='com.ogunlab.app'),None)
    if not client: raise SystemExit('Android paket adı com.ogunlab.app olmalı.')
    if account.get('type')!='service_account' or account.get('project_id')!=project['project_id'] or not account.get('private_key'):
        raise SystemExit('Servis hesabı ve Android ayarı aynı Firebase projesine ait olmalı.')
    out=ROOT/'private';out.mkdir(exist_ok=True)
    client_config={'application_id':client['client_info']['mobilesdk_app_id'],
        'api_key':client['api_key'][0]['current_key'],'project_id':project['project_id'],'sender_id':project['project_number']}
    (out/'firebase-client.json').write_text(json.dumps(client_config,ensure_ascii=False,indent=2),encoding='utf-8')
    target=out/'firebase-service-account.json'
    if args.service_account.resolve()!=target.resolve():shutil.copyfile(args.service_account,target)
    print('Yerel Firebase dosyaları hazır. Sunucuyu yeniden başlatıp telefonda uygulamayı açın.')
    print('Bu dosyalar özel kalmalı; ZIP paketine veya kaynak kod deposuna eklemeyin.')
if __name__=='__main__':main()
