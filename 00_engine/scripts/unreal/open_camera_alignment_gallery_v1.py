"""Independent port 8881 review launcher. Does not stop old review servers."""
from pathlib import Path
from http.server import ThreadingHTTPServer
from functools import partial
import argparse,json,os,subprocess,sys,time,urllib.request,webbrowser
from open_stable_camera_gallery_v1 import RangeHandler

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/camera_motion_scene_alignment_20261012_v1')
PORT=8881
URL='http://127.0.0.1:8881/gallery/index.html'

def available(index):
    try:
        with urllib.request.urlopen(URL,timeout=2) as response:
            return response.headers.get('X-Camera-Range-Server')=='stable-v1' and response.read()==index.read_bytes()
    except OSError:return False

def launch(root,open_browser):
    root=root.resolve();index=root/'gallery/index.html';process=None
    if not index.is_file():raise FileNotFoundError(index)
    if not available(index):
        flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        with (root/'gallery/server_stdout_v1.log').open('ab') as out,(root/'gallery/server_stderr_v1.log').open('ab') as err:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve','--run-root',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=flags,start_new_session=os.name!='nt',cwd=root)
        for _ in range(25):
            if available(index) or process.poll() is not None:break
            time.sleep(.2)
    ready=available(index)
    result={'url':URL if ready else None,'http_available':ready,'server_pid':process.pid if ready and process else None,'run_root':str(root),'open_browser_requested':open_browser}
    (root/'gallery/launcher_status_v1.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not ready:raise RuntimeError('Port 8881 occupied or new review server unavailable; existing listeners preserved')
    if open_browser:webbrowser.open(URL)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-root',type=Path,default=RUN)
    parser.add_argument('--no-browser',action='store_true');parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.serve:ThreadingHTTPServer(('127.0.0.1',PORT),partial(RangeHandler,directory=str(args.run_root.resolve()))).serve_forever()
    else:print(json.dumps(launch(args.run_root,not args.no_browser),ensure_ascii=False))
