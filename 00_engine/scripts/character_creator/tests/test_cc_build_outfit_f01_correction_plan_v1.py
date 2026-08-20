import json
import tempfile
import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from cc_build_outfit_f01_correction_plan_v1 import build_plan


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class CorrectionPlanTests(unittest.TestCase):
    def test_builds_smoke_and_restart_bounded_f01_chunks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            presets = []
            subjects = []
            families = []
            results = []
            for index in range(4):
                subject_id = "F01" if index < 3 else "F04"
                family_id = f"family.{index}"
                preset_id = f"preset_{index}"
                presets.append(
                    {
                        "preset_id": preset_id,
                        "look_id": f"{family_id}::default",
                        "family_id": family_id,
                        "subject_id": subject_id,
                        "bodyfit_id": "F01_Lean" if index < 3 else "F04_Heavy",
                        "sex": "female",
                    }
                )
                families.append({"family_id": family_id})
                case_dir = root / "cases" / preset_id
                captures = []
                for view in range(5):
                    image = case_dir / f"{view}.png"
                    image.parent.mkdir(parents=True, exist_ok=True)
                    image.write_bytes(b"image")
                    captures.append({"image": {"path": str(image)}})
                result_path = case_dir / "result.json"
                write_json(result_path, {"success": True, "captures": captures})
                results.append(
                    {
                        "success": True,
                        "preset_id": preset_id,
                        "result_path": str(result_path),
                    }
                )
            subjects.extend(
                [
                    {"subject_id": "F01"},
                    {"subject_id": "F04"},
                ]
            )
            gate_path = root / "gate.json"
            validation_path = root / "validation.json"
            output_path = root / "plan.json"
            manifests_dir = root / "manifests"
            run_root = root / "runs"
            write_json(
                gate_path,
                {
                    "library_id": "gate",
                    "subjects": subjects,
                    "families": families,
                    "presets": presets,
                    "execution_policy": {"remove_source_accessories": False},
                },
            )
            write_json(validation_path, {"results": results})

            plan = build_plan(
                gate_path,
                [validation_path],
                output_path,
                manifests_dir,
                run_root,
                cases_per_chunk=2,
                job_prefix="fix",
            )

            self.assertEqual(plan["affected_case_count"], 3)
            self.assertEqual(len(plan["correction_chunks"]), 2)
            self.assertEqual(plan["smoke"]["preset_id"], "preset_0")
            smoke = json.loads(
                (manifests_dir / "smoke.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(smoke["presets"]), 1)
            self.assertTrue(smoke["execution_policy"]["remove_source_accessories"])
            chunk = json.loads(
                (manifests_dir / "chunk_01.json").read_text(encoding="utf-8")
            )
            self.assertEqual(len(chunk["presets"]), 2)
            self.assertTrue(chunk["execution_policy"]["remove_source_accessories"])
            self.assertNotIn("preset_3", plan["affected_preset_ids"])


if __name__ == "__main__":
    unittest.main()
