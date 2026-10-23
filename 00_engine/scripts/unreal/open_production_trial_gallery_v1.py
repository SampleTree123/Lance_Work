"""Current-run-only loopback video gallery; never replaces an existing server.

Root may start `--serve` with Windows Start-Process -WindowStyle Hidden.
The server binds its actual free port and records URL/PID before serving.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from functools import partial
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser
from open_stable_camera_gallery_v1 import RangeHandler
from encode_production_trial_v1 import pin,read,write

RUN=Path(__file__).resolve().parents[2]/'outputs/production_workflow_20261017_v1'
PROTECTED_PORTS={8880,8881,8882,8883,8884,8885,8893}


def candidate_ports(start=8886,count=30):
    if type(start) is not int or type(count) is not int or not 1024<=start<=65535 or not 1<=count<=100:
        raise ValueError('Require a valid starting port and bounded search')
    return [port for port in range(start,min(65536,start+count)) if port not in PROTECTED_PORTS]


def paths(run=RUN):
    run=Path(run).resolve()
    if run!=RUN.resolve():raise ValueError('This launcher serves only the current production workflow run')
    index=run/'trial_gallery/index.html'
    if not index.is_file():raise FileNotFoundError(index)
    return run,index,run/'trial_gallery/launcher_status_v1.json'


def gallery_url(port):
    if type(port) is not int or not 1024<=port<=65535 or port in PROTECTED_PORTS:raise ValueError('Invalid/protected production gallery port')
    return f'http://127.0.0.1:{port}/trial_gallery/index.html'


def available(index,port):
    url=gallery_url(port)
    try:
        with urllib.request.urlopen(url,timeout=1) as response:
            return response.headers.get('X-Camera-Range-Server')=='stable-v1' and response.read()==Path(index).read_bytes()
    except OSError:return False


def serve(run=RUN,start_port=8886):
    run,index,receipt=paths(run);server=None
    for port in candidate_ports(start_port):
        try:
            server=ThreadingHTTPServer(('127.0.0.1',port),partial(RangeHandler,directory=str(run)))
        except OSError:
            # Binding failure means another listener stays untouched.
            continue
        break
    if server is None:raise RuntimeError('No free production gallery port; existing listeners preserved')
    actual_port=server.server_address[1]
    result={'schema':'production_trial_gallery_launch_v1','status':'ready','http_available':True,
        'url':gallery_url(actual_port),'port':actual_port,'server_pid':os.getpid(),'bind':'127.0.0.1',
        'run_root':str(run),'directory_scope':'current_production_run_only','index':pin(index),'byte_ranges_supported':True,
        'started_at':datetime.now(timezone.utc).isoformat(),'existing_servers_terminated':False}
    write(receipt,result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    try:server.serve_forever()
    finally:
        server.server_close()
        if receipt.is_file() and read(receipt).get('server_pid')==os.getpid():
            write(receipt,dict(result,status='stopped',http_available=False,stopped_at=datetime.now(timezone.utc).isoformat()))


def launch(run=RUN,open_browser=True,start_port=8886):
    run,index,receipt=paths(run);record=None;process=None
    if receipt.is_file():
        saved=read(receipt)
        if (saved.get('schema')=='production_trial_gallery_launch_v1' and saved.get('run_root')==str(run)
                and saved.get('status')=='ready' and saved.get('port') in candidate_ports(saved.get('port',start_port),1)
                and available(index,saved['port'])):
            record=saved
    if record is None:
        gallery=run/'trial_gallery'
        flags=(subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP) if os.name=='nt' else 0
        with (gallery/'server_stdout_v1.log').open('ab') as out,(gallery/'server_stderr_v1.log').open('ab') as err:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve','--port',str(start_port)],
                stdin=subprocess.DEVNULL,stdout=out,stderr=err,cwd=run,creationflags=flags,start_new_session=os.name!='nt')
        for _ in range(35):
            if receipt.is_file():
                saved=read(receipt)
                if saved.get('server_pid')==process.pid and saved.get('status')=='ready' and available(index,saved['port']):
                    record=saved;break
            if process.poll() is not None:break
            time.sleep(.2)
        if record is None:raise RuntimeError('Production gallery launch not confirmed; inspect its logs. Existing servers preserved.')
    record=dict(record,open_browser_requested=bool(open_browser),reused_existing_server=process is None)
    write(receipt,record)
    if open_browser:webbrowser.open(record['url'])
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serve',action='store_true')
    parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int,default=8886)
    args=parser.parse_args()
    if args.serve:serve(start_port=args.port)
    else:print(json.dumps(launch(open_browser=not args.no_browser,start_port=args.port),ensure_ascii=False))
