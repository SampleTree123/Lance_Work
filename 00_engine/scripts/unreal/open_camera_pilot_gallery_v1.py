"""Open or safely restart the local camera review.

Only serves the requested run on IPv4 loopback. Reuses only an existing camera
gallery at the exact endpoint. It never touches UE or kills other listeners.
"""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time,urllib.request,urllib.error,webbrowser
from pathlib import Path

DEFAULT_RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
PORT=8876
URL=f'http://127.0.0.1:{PORT}/gallery/index.html'

def is_gallery(expected_index=None):
    try:
        with urllib.request.urlopen(URL,timeout=2) as response:
            content=response.read();text=content.decode('utf-8')
            return (response.status==200 and 'id="gallery-data"' in text and '相机样片审查' in text
                    and (expected_index is None or content==Path(expected_index).read_bytes()))
    except (OSError,UnicodeError,urllib.error.URLError):
        return False

def open_gallery(run_root=DEFAULT_RUN,*,open_browser=True):
    root=Path(run_root).resolve();index=root/'gallery/index.html'
    if not index.is_file():raise FileNotFoundError(index)
    started=False;process=None
    if not is_gallery(index):
        log_dir=root/'gallery';flags=0
        if os.name=='nt':
            flags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW
        with (log_dir/'server_stdout_v2.log').open('ab') as out,(log_dir/'server_stderr_v2.log').open('ab') as err:
            process=subprocess.Popen([sys.executable,'-m','http.server',str(PORT),'--bind','127.0.0.1','--directory',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=flags,start_new_session=os.name!='nt',cwd=root)
        for _ in range(25):
            if is_gallery(index):started=True;break
            if process.poll() is not None:break
            time.sleep(.2)
    available=is_gallery(index)
    target=URL if available else None
    result={'schema':'camera_gallery_launch_v1','url':target,'http_available':available,'started_new_server':started,'server_pid':process.pid if started else None,'bind':'127.0.0.1','run_root':str(root),'open_browser_requested':open_browser}
    (root/'gallery/launcher_status_v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not available:
        raise RuntimeError('Local review server could not start. Port 8876 may be occupied; check gallery/server_stderr_v2.log.')
    if open_browser:webbrowser.open(target)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,default=DEFAULT_RUN);p.add_argument('--no-browser',action='store_true');a=p.parse_args()
    print(json.dumps(open_gallery(a.run_root,open_browser=not a.no_browser),ensure_ascii=False))

if __name__=='__main__':main()
