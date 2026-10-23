"""Portable fixed-suite comparison pages; no GPU or real video generation."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_datamake_visual_sanity_review as review


class VisualReviewTests(unittest.TestCase):
    def test_same_named_videos_from_different_runs_do_not_collide(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current = root / "current"
            refs = current / "references"
            refs.mkdir(parents=True)
            originals = []
            for name in ("step650", "step800"):
                path = root / name / "turn00.mp4"
                path.parent.mkdir()
                path.write_bytes(name.encode())
                originals.append(path)
            copies = [review.local_reference(current, refs, path) for path in originals]
            self.assertNotEqual(copies[0], copies[1])
            for original, copied in zip(originals, copies):
                self.assertEqual(original.read_bytes(), copied.read_bytes())

    def test_comparison_requires_finished_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_text(json.dumps({"status": "running"}))
            with self.assertRaisesRegex(ValueError, "not finished"):
                review.comparison_runs([f"A650={root}"])

    def test_page_copies_videos_and_manifests_with_explicit_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gt = root / "gt.mp4"
            gt.write_bytes(b"ground truth")
            runs = []
            for step in (650, 800):
                run = root / f"step{step}"
                result = run / "teacher_forced_outfit_r3" / "turn00.mp4"
                result.parent.mkdir(parents=True)
                result.write_bytes(f"generated {step}".encode())
                manifest = {
                    "status": "generated", "completed_steps": step,
                    "preprocessing": {"mode": "training_dataset_config"},
                    "cases": [{"name": "teacher_forced_outfit_r3", "mode": "teacher_forced",
                               "outputs": [{"round": 3, "edit_axis": "outfit", "prompt": "blue jacket",
                                            "gt_target": str(gt), "actual_source": str(gt),
                                            "output": "teacher_forced_outfit_r3/turn00.mp4"}]}],
                }
                (run / "manifest.json").write_text(json.dumps(manifest))
                runs.append(run)
            argv = ["review", "--run-dir", str(runs[1]), "--label", "A step800",
                    "--compare-run", f"A step650={runs[0]}"]
            with patch.object(sys, "argv", argv), patch.object(review, "video_check", return_value={"decoded_frames": 57}), patch.object(review, "preview_frame", return_value=Image.new("RGB", (320, 180))), patch("builtins.print"):
                review.main()
            html = (runs[1] / "index.html").read_text()
            self.assertIn("A step800", html)
            self.assertIn("A step650", html)
            self.assertNotIn("STAGE2", html)
            audit = json.loads((runs[1] / "media_audit.json").read_text())
            self.assertEqual(audit["comparisons"][0]["completed_steps"], 650)
            self.assertTrue((runs[1] / audit["comparisons"][0]["manifest"]).is_file())
            self.assertTrue(all((runs[1] / path).is_file() for path in audit["reference_media"]))
            with Image.open(runs[1] / "comparison_50pct.jpg") as sheet:
                self.assertEqual(sheet.size, (1280, 220))


if __name__ == "__main__":
    unittest.main()
