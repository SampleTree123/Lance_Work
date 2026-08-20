from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import build_outfit_compatibility_gate_progress_run as progress  # noqa: E402


class OutfitProgressDiscoveryTests(unittest.TestCase):
    def test_resume_checkpoints_and_new_chunks_are_discovered_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "cheer_fix" / "validation_result.json"
            checkpoint.parent.mkdir()
            checkpoint.write_text("{}", encoding="utf-8")

            chunk_result = root / "chunks" / "chunk_01" / "validation_result.json"
            chunk_result.parent.mkdir(parents=True)
            chunk_result.write_text("{}", encoding="utf-8")

            resume_plan = root / "resume_plan.json"
            resume_plan.write_text(
                json.dumps(
                    {
                        "checkpoint_validations": [
                            str(checkpoint),
                            str(chunk_result),
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(progress, "DEFAULT_RESUME_PLAN", resume_plan):
                discovered = progress.discover_validations([root / "chunks"])

            self.assertEqual(discovered, [checkpoint.resolve(), chunk_result.resolve()])

    def test_stale_summary_sheets_are_removed_after_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sheets_root = Path(temporary)
            current = sheets_root / "g01-current.png"
            stale = sheets_root / "g01-old-sequence.png"
            unrelated = sheets_root / "notes.png"
            for path in (current, stale, unrelated):
                path.write_bytes(b"image")

            progress.remove_stale_sheets(sheets_root, {current})

            self.assertTrue(current.is_file())
            self.assertFalse(stale.exists())
            self.assertTrue(unrelated.is_file())


if __name__ == "__main__":
    unittest.main()
