"""Loopback review server with byte ranges for reliable browser video seeking."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import webbrowser

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_complete_angles_20261010_v1')
PORT = 8879
URL = 'http://127.0.0.1:8879/gallery/index.html'


from open_stable_camera_gallery_v1 import RangeHandler


def available(index):
    try:
        with urllib.request.urlopen(URL, timeout=2) as response:
            return (response.headers.get('X-Camera-Range-Server') == 'stable-v1'
                    and response.read() == index.read_bytes())
    except OSError:
        return False


def launch(root, open_browser):
    root = root.resolve()
    index = root / 'gallery/index.html'
    if not index.is_file():
        raise FileNotFoundError(index)
    process = None
    if not available(index):
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with (root / 'gallery/server_stdout_complete_v1.log').open('ab') as out, (root / 'gallery/server_stderr_complete_v1.log').open('ab') as err:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', '--run-root', str(root)], stdin=subprocess.DEVNULL, stdout=out, stderr=err, creationflags=flags, start_new_session=os.name != 'nt', cwd=root)
        for _ in range(25):
            if available(index) or process.poll() is not None:
                break
            time.sleep(.2)
    ready = available(index)
    result = {'schema': 'complete_camera_gallery_launch_v1', 'url': URL if ready else None,
              'http_available': ready, 'byte_ranges_supported': ready,
              'server_pid': process.pid if ready and process else None,
              'run_root': str(root), 'bind': '127.0.0.1', 'open_browser_requested': open_browser}
    (root / 'gallery/launcher_status_v1.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if not ready:
        raise RuntimeError('Port 8879 is occupied or the range-enabled review server could not start. Existing listeners were not stopped.')
    if open_browser:
        webbrowser.open(URL)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        ThreadingHTTPServer(('127.0.0.1', PORT), partial(RangeHandler, directory=str(args.run_root.resolve()))).serve_forever()
    else:
        print(json.dumps(launch(args.run_root, not args.no_browser), ensure_ascii=False))
