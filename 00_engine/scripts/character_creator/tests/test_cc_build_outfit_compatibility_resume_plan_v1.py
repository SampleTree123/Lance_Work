from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "cc_build_outfit_compatibility_resume_plan_v1.py"
)
SPEC = importlib.util.spec_from_file_location("cc_outfit_resume_plan_test", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class OutfitCompatibilityResumePlanTests(unittest.TestCase):
    def test_completed_looks_are_skipped_and_partial_looks_are_replayed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            subjects = [
                {"subject_id": f"subject_{index}"} for index in range(1, 4)
            ]
            families = [
                {"family_id": f"family_{index}"} for index in range(1, 4)
            ]
            presets = []
            for look_index in range(1, 4):
                for subject_index in range(1, 4):
                    presets.append(
                        {
                            "preset_id": f"look_{look_index}_body_{subject_index}",
                            "look_id": f"family_{look_index}::default",
                            "subject_id": f"subject_{subject_index}",
                            "sex": "female",
                            "bodyfit_id": f"F0{subject_index}",
                        }
                    )
            gate = {
                "library_id": "test_gate",
                "presets": presets,
                "subjects": subjects,
                "families": families,
            }
            gate_path = root / "gate.json"
            write_json(gate_path, gate)

            results = []
            for preset_id in [
                "look_1_body_1",
                "look_1_body_2",
                "look_1_body_3",
                "look_2_body_1",
                "legacy_look_removed_from_current_gate",
            ]:
                case_root = root / "cases" / preset_id
                captures = []
                for index in range(5):
                    image_path = case_root / f"view_{index}.png"
                    image_path.parent.mkdir(parents=True, exist_ok=True)
                    image_path.write_bytes(b"image")
                    captures.append({"image": {"path": str(image_path)}})
                result_path = case_root / "result.json"
                write_json(result_path, {"success": True, "captures": captures})
                results.append(
                    {
                        "preset_id": preset_id,
                        "success": True,
                        "result_path": str(result_path),
                    }
                )
            validation_path_a = root / "validation_a.json"
            validation_path_b = root / "validation_b.json"
            write_json(validation_path_a, {"results": results[:3]})
            write_json(validation_path_b, {"results": results[3:]})

            output_path = root / "resume_plan.json"
            plan = MODULE.build_resume_plan(
                gate_path=gate_path,
                validation_path=[validation_path_a, validation_path_b],
                output_path=output_path,
                chunks_dir=root / "chunks",
                run_root=root / "runs",
                looks_per_chunk=1,
                job_prefix="test_resume_r2",
            )

            self.assertEqual(plan["counts"]["verified_completed_cases"], 4)
            self.assertEqual(
                plan["counts"]["ignored_checkpoint_cases_outside_gate"], 1
            )
            self.assertEqual(plan["counts"]["incomplete_cases"], 5)
            self.assertEqual(plan["counts"]["scheduled_cases"], 6)
            self.assertEqual(plan["counts"]["completed_looks"], 1)
            self.assertEqual(plan["counts"]["remaining_looks"], 2)
            self.assertEqual(plan["counts"]["chunk_count"], 2)
            self.assertEqual(plan["counts"]["replayed_cases_due_to_partial_look"], 1)
            self.assertTrue(plan["safety_policy"]["restart_not_per_case"])
            self.assertEqual(
                plan["safety_policy"]["target_cases_per_submitted_job"], [3, 6]
            )
            self.assertEqual(
                plan["safety_policy"]["target_cases_per_cc_process"], [6, 12]
            )
            self.assertEqual(
                plan["safety_policy"]["private_memory_soft_limit_gib"], 24
            )
            self.assertEqual(
                plan["safety_policy"]["evaluation_boundary"],
                "after_each_complete_look",
            )
            self.assertTrue(
                plan["safety_policy"]["run_resource_release_probe_at_soft_limit"]
            )
            self.assertTrue(
                plan["safety_policy"]
                ["continue_only_if_resources_recover_above_soft_limits"]
            )
            self.assertFalse(
                plan["chunks"][0]["requires_offline_cc_restart_before_run"]
            )
            self.assertEqual(
                plan["chunks"][0]["restart_policy"],
                "resource_gate_at_complete_look_boundary",
            )
            self.assertEqual(plan["chunks"][0]["case_count"], 3)
            self.assertEqual(
                plan["chunks"][0]["look_ids"], ["family_2::default"]
            )
            self.assertTrue(Path(plan["chunks"][0]["manifest_path"]).is_file())
            self.assertEqual(len(plan["checkpoint_validations"]), 2)
            self.assertEqual(
                plan["ignored_checkpoint_preset_ids"],
                ["legacy_look_removed_from_current_gate"],
            )
            self.assertEqual(plan["chunks"][0]["job_id"], "test_resume_r2_chunk_01")


if __name__ == "__main__":
    unittest.main()
