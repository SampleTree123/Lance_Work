"""Actual HTTP behavior required for browser seeking; no fixed app port used."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_stable_camera_gallery_v1 import RangeHandler


def test_actual_video_byte_range_http(tmp_path):
    payload = bytes(range(256)) * 4
    (tmp_path / 'video.mp4').write_bytes(payload)
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(RangeHandler, directory=str(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/video.mp4'
    try:
        for header, start, end in [('bytes=0-9', 0, 9), ('bytes=20-99', 20, 99), ('bytes=1000-', 1000, 1023), ('bytes=-10', 1014, 1023)]:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'Range': header})) as response:
                assert response.status == 206
                assert response.headers['Content-Range'] == f'bytes {start}-{end}/1024'
                assert response.read() == payload[start:end + 1]
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=1024-'}))
        assert error.value.code == 416
        with urllib.request.urlopen(url) as response:
            assert response.status == 200 and response.read() == payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
