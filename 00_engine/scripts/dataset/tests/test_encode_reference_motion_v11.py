"""Safe reference IDs and one small actual 300-frame encoder integration."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / "encode_render_v11.py"
SPEC = importlib.util.spec_from_file_location("tested_encode_reference_motion", SCRIPT)
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class Tests(unittest.TestCase):
    def test_safe_reference_ids_keep_main_ids_and_reject_path_escape(self):
        for value in ("train_node_000000", "test_node_000001", "ref_f752597252c97a92e70bb469", "ref_motion_front-1"):
            self.assertTrue(M.valid_job_id(value), value)
        for value in ("../ref_a", "ref_../x", "ref_a/b", "ref_a\\b", "ref_a.mp4", "ref_", "ref_" + "a" * 100, "ref_a:secret"):
            self.assertFalse(M.valid_job_id(value), value)

    def test_reference_motion_encodes_and_reuses_receipt(self):
        try: M.find_ffmpeg()
        except (RuntimeError, ImportError): self.skipTest("FFmpeg unavailable")
        temp_root = SCRIPT.parents[2] / "temp/reference_motion_encoder_tests"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as value:
            root = Path(value); jid = "ref_motion_fixture"; frames = root / "jobs" / jid / "frames"
            frames.mkdir(parents=True)
            def chunk(kind, data): return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
            png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
            png += chunk(b"IDAT", zlib.compress((b"\0" + bytes((64, 128, 192)) * 64) * 64)) + chunk(b"IEND", b"")
            for i in range(300): (frames / f"frame_{i:04d}.png").write_bytes(png)
            (root / "reference_jobs.json").write_text(json.dumps({"jobs": [{"job_id": jid, "width": 64, "height": 64, "fps": 30, "frames": 300}]}), encoding="utf-8")
            arguments = ["--run-root", str(root), "--jobs", "reference_jobs.json", "--job-id", jid]
            with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(M.main(arguments), 0)
            receipt = json.loads((frames.parent / "media_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["media"]["decoded_frames"], 300)
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(M.main(arguments), 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "reused_verified_receipt")


if __name__ == "__main__": unittest.main()
