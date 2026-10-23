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

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_stable_follow_20261010_v1')
PORT = 8878
URL = 'http://127.0.0.1:8878/gallery/index.html'


class RangeHandler(SimpleHTTPRequestHandler):
    """Serve one byte range; reject malformed or unsatisfiable ranges."""
    def end_headers(self):
        self.send_header('X-Camera-Range-Server', 'stable-v1')
        super().end_headers()

    def send_head(self):
        self.byte_range = None
        path = Path(self.translate_path(self.path))
        header = self.headers.get('Range')
        if not header or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
        valid = bool(match and any(match.groups()) and size)
        start, end = 0, size - 1
        if valid:
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            else:
                valid = int(last) > 0
                start = max(0, size - int(last))
            valid = valid and 0 <= start <= end < size
        if not valid:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        file = path.open('rb')
        self.byte_range = (start, end)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        file.seek(start)
        return file

    def copyfile(self, source, outputfile):
        if self.byte_range is None:
            return super().copyfile(source, outputfile)
        remaining = self.byte_range[1] - self.byte_range[0] + 1
        while remaining:
            block = source.read(min(65536, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


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
        with (root / 'gallery/server_stdout_stable_v1.log').open('ab') as out, (root / 'gallery/server_stderr_stable_v1.log').open('ab') as err:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', '--run-root', str(root)], stdin=subprocess.DEVNULL, stdout=out, stderr=err, creationflags=flags, start_new_session=os.name != 'nt', cwd=root)
        for _ in range(25):
            if available(index) or process.poll() is not None:
                break
            time.sleep(.2)
    ready = available(index)
    result = {'schema': 'stable_camera_gallery_launch_v1', 'url': URL if ready else None,
              'http_available': ready, 'byte_ranges_supported': ready,
              'server_pid': process.pid if ready and process else None,
              'run_root': str(root), 'bind': '127.0.0.1', 'open_browser_requested': open_browser}
    (root / 'gallery/launcher_status_v1.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    if not ready:
        raise RuntimeError('Port 8878 is occupied or the range-enabled review server could not start. Existing listeners were not stopped.')
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
