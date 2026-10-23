"""Independent common-camera loopback server. Owner: SCENE_CAMERA_SEQUENCE §14."""
from pathlib import Path
from http.server import ThreadingHTTPServer
from functools import partial
import argparse,json,os,socket,subprocess,sys,time,urllib.request,webbrowser
from open_stable_camera_gallery_v1 import RangeHandler

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/camera_common_presets_20261014_v1')

def available(index,port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/gallery/index.html',timeout=2) as r:
            return r.headers.get('X-Camera-Range-Server')=='stable-v1' and r.read()==index.read_bytes()
    except OSError:return False

def launch(root,open_browser,port=8882):
    root=root.resolve();index=root/'gallery/index.html';process=None
    if not index.is_file():raise FileNotFoundError(index)
    saved=root/'gallery/launcher_status_v1.json'
    if saved.is_file():
        previous=json.loads(saved.read_text(encoding='utf-8'))
        if available(index,previous.get('port',port)):port=previous.get('port',port)
    if not available(index,port):
        for candidate in range(port,port+15):
            if candidate in (8880,8881,8893):continue
            with socket.socket() as probe:
                try:probe.bind(('127.0.0.1',candidate))
                except OSError:continue
            port=candidate;break
        else:raise RuntimeError('No free review port; existing servers preserved')
        flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with (root/'gallery/server_stdout_v1.log').open('ab') as out,(root/'gallery/server_stderr_v1.log').open('ab') as err:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve','--run-root',str(root),'--port',str(port)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=flags,start_new_session=os.name!='nt',cwd=root)
        for _ in range(25):
            if available(index,port) or process.poll() is not None:break
            time.sleep(.2)
    ready=available(index,port);url=f'http://127.0.0.1:{port}/gallery/index.html'
    result={'url':url if ready else None,'port':port,'http_available':ready,'server_pid':process.pid if ready and process else None,'run_root':str(root),'open_browser_requested':open_browser}
    saved.write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not ready:raise RuntimeError('New review server unavailable; existing listeners preserved')
    if open_browser:webbrowser.open(url)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,default=RUN)
    p.add_argument('--port',type=int,default=8882);p.add_argument('--no-browser',action='store_true');p.add_argument('--serve',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    if a.serve:ThreadingHTTPServer(('127.0.0.1',a.port),partial(RangeHandler,directory=str(a.run_root.resolve()))).serve_forever()
    else:print(json.dumps(launch(a.run_root,not a.no_browser,a.port),ensure_ascii=False))
