import importlib.util
import json
import os
import tempfile
import unittest

from PIL import Image


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_summarize_dynamic_wrinkle_age_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_summarize_dynamic_wrinkle_age_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def application(strength):
    return {
        "morph_deltas": {
            "body": [],
            "face": [],
            "junction": [],
            "other": [],
        },
        "strength": strength,
        "strength_results": [
            {
                "face_part": "part_{}".format(index),
                "status": {"is_error": False},
            }
            for index in range(13)
        ],
    }


class DynamicWrinkleAgeSummaryTests(unittest.TestCase):
    def test_complete_case_proves_image_and_strength_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            batch_path = os.path.join(directory, "batch.json")
            artifact_root = os.path.join(directory, "artifacts")
            chunk_dir = os.path.join(artifact_root, "chunk_01")
            case_dir = os.path.join(chunk_dir, "WRINKLE_M_YOUNG")
            os.makedirs(case_dir)
            pairs = []
            for index, pose_id in enumerate(MODULE.EXPECTED_POSE_IDS):
                baseline = os.path.join(
                    case_dir, "{}_baseline.png".format(index)
                )
                target = os.path.join(
                    case_dir, "{}_target.png".format(index)
                )
                Image.new("RGB", (16, 16), (0, 0, 0)).save(baseline)
                Image.new("RGB", (16, 16), (index + 1, 0, 0)).save(
                    target
                )
                pairs.append(
                    {
                        "baseline_image": baseline,
                        "pose_id": pose_id,
                        "target_image": target,
                    }
                )
            batch = {
                "presets": [
                    {
                        "age_label": "young",
                        "dynamic_wrinkle_age_validation": {
                            "profile_id": "PROFILE_M",
                            "skin_asset_id": "SKIN_M",
                        },
                        "preset_id": "WRINKLE_M_YOUNG",
                        "sex": "male",
                    }
                ]
            }
            batch["presets"].extend(
                {
                    "age_label": age,
                    "dynamic_wrinkle_age_validation": {
                        "profile_id": "P",
                        "skin_asset_id": "S",
                    },
                    "preset_id": "P_{}".format(index),
                    "sex": sex,
                }
                for index, (sex, age) in enumerate(
                    (
                        ("male", "middle"),
                        ("male", "older"),
                        ("female", "young"),
                        ("female", "middle"),
                        ("female", "older"),
                    )
                )
            )
            validation = {
                "results": [
                    {
                        "dynamic_wrinkle_validation": {
                            "baseline": {
                                "application": application(0.0)
                            },
                            "pairs": pairs,
                            "target": {
                                "application": application(1.0)
                            },
                            "target_restore": application(1.0),
                        },
                        "facial_assembly": {
                            "age_morph": {"actual": 0.0}
                        },
                        "preset_id": "WRINKLE_M_YOUNG",
                        "success": True,
                    }
                ]
            }
            with open(batch_path, "w", encoding="utf-8") as handle:
                json.dump(batch, handle)
            with open(
                os.path.join(chunk_dir, "validation_result.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(validation, handle)

            summary = MODULE.build_summary(artifact_root, batch_path)

        self.assertEqual(1, summary["completed_case_count"])
        self.assertEqual(5, summary["pending_case_count"])
        case = summary["cases"][0]
        self.assertTrue(case["structural_pass"])
        self.assertTrue(
            all(
                item["difference"]["maximum_channel_difference"] > 0
                for item in case["pairs"]
            )
        )


if __name__ == "__main__":
    unittest.main()
