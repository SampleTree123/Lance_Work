from __future__ import annotations

import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve Lance Visual Review locally.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Document root; defaults to Lance_Work.",
    )
    return parser.parse_args()


class ReviewHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._byte_range: tuple[int, int] | None = None
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: object) -> None:
        # The portal can run unattended for hours; per-request console output
        # must not depend on a parent shell keeping its output pipe open.
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        range_header = self.headers.get("Range")
        if not range_header:
            self._byte_range = None
            return super().send_head()

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            self._byte_range = None
            return super().send_head()
        try:
            source = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        try:
            size = os.fstat(source.fileno()).st_size
            start, end = self._parse_byte_range(range_header, size)
        except ValueError:
            source.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{os.path.getsize(path)}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        self._byte_range = (start, end)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(path)))
        self.end_headers()
        return source

    @staticmethod
    def _parse_byte_range(header: str, size: int) -> tuple[int, int]:
        if not header.startswith("bytes=") or "," in header or size <= 0:
            raise ValueError("unsupported range")
        value = header[6:].strip()
        if "-" not in value:
            raise ValueError("invalid range")
        start_text, end_text = value.split("-", 1)
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else size - 1
        else:
            suffix = int(end_text)
            if suffix <= 0:
                raise ValueError("invalid suffix")
            start = max(0, size - suffix)
            end = size - 1
        if start < 0 or start >= size or end < start:
            raise ValueError("range outside file")
        return start, min(end, size - 1)

    def copyfile(self, source, outputfile) -> None:
        if self._byte_range is None:
            super().copyfile(source, outputfile)
            return
        start, end = self._byte_range
        source.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            block = source.read(min(64 * 1024, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    handler = functools.partial(ReviewHandler, directory=str(root))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving {root} at http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
