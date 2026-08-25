from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cc_ingest_first_batch_action_window_selection_v1.py"
SPEC = importlib.util.spec_from_file_location("action_window_ingest", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


def file_record(path: Path, size_key: str = "bytes") -> dict:
    return {
        "path": str(path),
        size_key: path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class ActionWindowSelectionTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> dict[str, Path]:
        cases = []
        actions = []
        selections = []
        for sex in ("female", "male"):
            for index in range(1, 7):
                action_id = f"ACT_{sex[0].upper()}{index:02d}_FIXTURE"
                case_id = action_id.lower()
                motion = root / f"{index:02d}_{case_id}.rlMotion"
                video = root / f"{case_id}.mp4"
                motion.write_bytes(action_id.encode("ascii"))
                video.write_bytes((action_id + "-video").encode("ascii"))
                source_duration = 4.0 if index == 1 else 9.0
                source_window = min(5.0, source_duration)
                padding = 5.0 - source_window
                start = 0.0 if padding else 2.0
                video_info = {
                    **file_record(video),
                    "duration_seconds": source_duration,
                }
                cases.append(
                    {
                        "action_id": action_id,
                        "case_id": case_id,
                        "sex": sex,
                        "source_filename": motion.name,
                        "video": video_info,
                        "source_window_duration_seconds": source_window,
                        "padding_policy": "blend_to_subtle_idle_at_both_ends" if padding else "none",
                    }
                )
                actions.append(
                    {
                        "action_id": action_id,
                        "sex": sex,
                        "semantic_family": "fixture",
                        "runtime_file": file_record(motion, "size_bytes"),
                    }
                )
                selections.append(
                    {
                        "action_id": action_id,
                        "case_id": case_id,
                        "sex": sex,
                        "source_filename": motion.name,
                        "source_video_sha256": video_info["sha256"],
                        "source_duration_seconds": source_duration,
                        "window_start_seconds": start,
                        "window_end_seconds": start + source_window,
                        "source_window_duration_seconds": source_window,
                        "production_duration_seconds": 5.0,
                        "padding_required_seconds": padding,
                        "padding_policy": cases[-1]["padding_policy"],
                        "confirmed": True,
                    }
                )

        manifest = root / "manifest.json"
        selection = root / "selection.json"
        registry = root / "registry.json"
        output = root / "frozen.json"
        manifest.write_text(
            json.dumps(
                {
                    "review_id": "fixture-review",
                    "window_duration_seconds": 5.0,
                    "cases": cases,
                }
            ),
            encoding="utf-8",
        )
        selection.write_text(
            json.dumps(
                {
                    "review_id": "fixture-review",
                    "complete": True,
                    "production_window_duration_seconds": 5.0,
                    "selections": selections,
                }
            ),
            encoding="utf-8",
        )
        registry.write_text(
            json.dumps(
                {
                    "status": "frozen_pending_cc_and_ue_validation",
                    "actions": actions,
                }
            ),
            encoding="utf-8",
        )
        return {
            "manifest": manifest,
            "selection": selection,
            "registry": registry,
            "output": output,
        }

    def freeze(self, fixture: dict[str, Path]) -> dict:
        return SUBJECT.freeze_action_windows(
            selection_path=fixture["selection"],
            manifest_path=fixture["manifest"],
            registry_path=fixture["registry"],
            output_path=fixture["output"],
        )

    def test_freezes_twelve_valid_windows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            summary = self.freeze(fixture)
            frozen = json.loads(fixture["output"].read_text(encoding="utf-8"))
            self.assertEqual(summary["action_count"], 12)
            self.assertEqual(summary["idle_padded_action_count"], 2)
            self.assertEqual(frozen["status"], "frozen_ready_for_cc_export")
            self.assertEqual(len(frozen["actions"]), 12)

    def test_accepts_replacement_window_registry_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            registry = json.loads(fixture["registry"].read_text(encoding="utf-8"))
            registry["status"] = (
                "frozen_pending_replacement_window_and_ue_validation"
            )
            fixture["registry"].write_text(json.dumps(registry), encoding="utf-8")

            summary = self.freeze(fixture)

            self.assertEqual(summary["action_count"], 12)

    def test_rejects_unfrozen_registry_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            registry = json.loads(fixture["registry"].read_text(encoding="utf-8"))
            registry["status"] = "draft"
            fixture["registry"].write_text(json.dumps(registry), encoding="utf-8")

            with self.assertRaises(SUBJECT.ActionWindowSelectionError):
                self.freeze(fixture)

    def test_rejects_unconfirmed_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            selection = json.loads(fixture["selection"].read_text(encoding="utf-8"))
            selection["selections"][0]["confirmed"] = False
            fixture["selection"].write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaises(SUBJECT.ActionWindowSelectionError):
                self.freeze(fixture)

    def test_rejects_out_of_range_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            selection = json.loads(fixture["selection"].read_text(encoding="utf-8"))
            selection["selections"][1]["window_start_seconds"] = 8.0
            selection["selections"][1]["window_end_seconds"] = 13.0
            fixture["selection"].write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaises(SUBJECT.ActionWindowSelectionError):
                self.freeze(fixture)

    def test_rejects_preview_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self.make_fixture(Path(temporary))
            manifest = json.loads(fixture["manifest"].read_text(encoding="utf-8"))
            Path(manifest["cases"][0]["video"]["path"]).write_bytes(b"drift")
            with self.assertRaises(SUBJECT.ActionWindowSelectionError):
                self.freeze(fixture)


if __name__ == "__main__":
    unittest.main()
