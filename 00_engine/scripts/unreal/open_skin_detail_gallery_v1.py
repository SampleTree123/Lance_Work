"""Local skin experiment review server. Owner: CHARACTER_RUNTIME.md section 3.20."""
import argparse,json,os,subprocess,sys,time,urllib.request,webbrowser
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from open_stable_camera_gallery_v1 import RangeHandler

ROOT=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/skin_detail_optimization_20261012_v1')
PORT=8893
URL=f'http://127.0.0.1:{PORT}/gallery/index.html'
def ready():
    try:
        with urllib.request.urlopen(URL,timeout=2) as r:
            return r.headers.get('X-Camera-Range-Server')=='stable-v1' and r.read()==(ROOT/'gallery/index.html').read_bytes()
    except OSError:return False
def main():
    p=argparse.ArgumentParser();p.add_argument('--serve',action='store_true');p.add_argument('--no-browser',action='store_true');a=p.parse_args()
    if a.serve:
        ThreadingHTTPServer(('127.0.0.1',PORT),partial(RangeHandler,directory=str(ROOT))).serve_forever()
        return
    if not (ROOT/'gallery/index.html').is_file():raise FileNotFoundError('Build gallery first')
    child=None
    if not ready():
        with (ROOT/'gallery/server.log').open('ab') as stream:
            child=subprocess.Popen([sys.executable,__file__,'--serve'],stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,
                creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
        for _ in range(25):
            if ready() or child.poll() is not None:break
            time.sleep(.2)
    if not ready():raise RuntimeError('Review port unavailable; existing listener was not stopped')
    report={'url':URL,'http_available':True,'server_pid':child.pid if child else None,'bind':'127.0.0.1','run_root':str(ROOT)}
    (ROOT/'gallery/launcher_status_v1.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not a.no_browser:webbrowser.open(URL)
    print(json.dumps(report))
if __name__=='__main__':main()
