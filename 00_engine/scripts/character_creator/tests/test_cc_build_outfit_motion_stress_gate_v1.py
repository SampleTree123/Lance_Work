import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "cc_build_outfit_motion_stress_gate_v1.py"
)
SPEC = importlib.util.spec_from_file_location("outfit_motion_stress_builder", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


class OutfitMotionStressBuilderTests(unittest.TestCase):
    def test_loads_frozen_static_application_order(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = root / "result.json"
            result.write_text(
                json.dumps(
                    {
                        "success": True,
                        "case_id": "female.demo::F04_Heavy",
                        "asset_applications": [
                            {
                                "asset_id": "asset_b",
                                "slot": "full_body",
                                "inventory_changes": {
                                    "added": [
                                        {
                                            "id": "1",
                                            "collection": "GetClothes",
                                            "name": "DemoTop",
                                            "python_type": "RICloth",
                                        }
                                    ],
                                    "removed": [],
                                },
                            },
                            {
                                "asset_id": "asset_a",
                                "slot": "full_body",
                                "inventory_changes": {
                                    "added": [
                                        {
                                            "id": "2",
                                            "collection": "GetClothes",
                                            "name": "DemoTop",
                                            "python_type": "RICloth",
                                        }
                                    ],
                                    "removed": [
                                        {
                                            "id": "1",
                                            "collection": "GetClothes",
                                            "name": "DemoTop",
                                            "python_type": "RICloth",
                                        }
                                    ],
                                },
                            },
                        ],
                        "assembled_inventory": {
                            "objects": [
                                {
                                    "id": "2",
                                    "collection": "GetClothes",
                                    "name": "DemoTop",
                                    "python_type": "RICloth",
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            review = root / "review.json"
            review.write_text(
                json.dumps(
                    {
                        "groups": [
                            {
                                "cases": [
                                    {
                                        "sex": "female",
                                        "bodyfit_id": "F04_Heavy",
                                        "look_id": "female.demo::default",
                                        "result_path": str(result),
                                    }
                                ]
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            orders = SUBJECT.load_static_application_orders(review)
            self.assertEqual(
                orders["female.demo::default"]["ordered_asset_ids"],
                ["asset_b", "asset_a"],
            )
            self.assertEqual(
                orders["female.demo::default"][
                    "allowed_required_asset_replacements"
                ],
                [
                    {
                        "removing_asset_id": "asset_a",
                        "removed_owner_asset_id": "asset_b",
                        "removed_owner_slot": "full_body",
                        "object_collection": "GetClothes",
                        "object_name": "DemoTop",
                    }
                ],
            )
            reordered = SUBJECT.reorder_assets_from_static_evidence(
                [{"asset_id": "asset_a"}, {"asset_id": "asset_b"}],
                orders["female.demo::default"],
                "female.demo::default",
            )
            self.assertEqual(
                [item["asset_id"] for item in reordered],
                ["asset_b", "asset_a"],
            )

    def test_selects_one_heavy_bodyfit_per_look_and_writes_chunks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            motions = {}
            for sex in ("female", "male"):
                motions[sex] = []
                for profile in ("locomotion_walk", "full_body_calibration"):
                    path = root / f"{sex}_{profile}.iMotionPlus"
                    path.write_bytes((sex + profile).encode("ascii"))
                    motions[sex].append((profile, path))
            old_motions = SUBJECT.MOTIONS
            SUBJECT.MOTIONS = motions
            try:
                static_gate = {
                    "schema_version": 1,
                    "library_id": "static",
                    "diagnostic_mode": "outfit_compatibility_gate",
                    "preview_capture_mode": "render_image",
                    "preview_resolution": [1024, 1024],
                    "preview_lightroom": "lightroom",
                    "full_body_camera": "camera",
                    "execution_policy": {
                        "stop_on_blocking_dialog": True,
                        "checkpoint_after_each_case": True,
                    },
                    "representative_looks": [
                        {"look_id": "female.family::default"},
                        {"look_id": "male.family::default"},
                    ],
                    "presets": [
                        self._preset("female", "F01_Lean", "female.family::default"),
                        self._preset("female", "F04_Heavy", "female.family::default"),
                        self._preset("female", "F05_Short_Average", "female.family::default"),
                        self._preset("male", "M01_Lean", "male.family::default"),
                        self._preset("male", "M04_Heavy", "male.family::default"),
                        self._preset("male", "M05_Short_Average", "male.family::default"),
                    ],
                }
                gate_path = root / "static.json"
                gate_path.write_text(json.dumps(static_gate), encoding="utf-8")
                document = SUBJECT.build_gate(gate_path, root / "run", "dynamic")
                self.assertEqual(document["diagnostic_mode"], "outfit_motion_stress_gate")
                self.assertEqual(document["counts"]["test_case_count"], 2)
                self.assertEqual(document["counts"]["expected_image_count"], 22)
                self.assertEqual(
                    {item["bodyfit_id"] for item in document["presets"]},
                    {"F04_Heavy", "M04_Heavy"},
                )
                self.assertTrue(
                    document["scope_policy"][
                        "motions_are_diagnostic_not_production_pool"
                    ]
                )
                for preset in document["presets"]:
                    self.assertLessEqual(len(preset["output_directory_name"]), 14)
                    self.assertTrue(preset["output_directory_name"].startswith("d"))
                    self.assertEqual(len(preset["motion_stress_profiles"]), 2)
                    for profile in preset["motion_stress_profiles"]:
                        self.assertEqual(
                            profile["sample_normalized_positions"],
                            [0.0, 0.2, 0.4, 0.6, 0.8],
                        )
                        self.assertEqual(len(profile["motion"]["sha256"]), 64)
                count = SUBJECT.write_chunks(document, root / "chunks", 1)
                self.assertEqual(count, 2)
                self.assertEqual(len(list((root / "chunks").glob("chunk_*.json"))), 2)
            finally:
                SUBJECT.MOTIONS = old_motions

    @staticmethod
    def _preset(sex, bodyfit_id, look_id):
        preset_id = f"{sex}_{bodyfit_id}"
        return {
            "preset_id": preset_id,
            "case_id": preset_id,
            "output_directory_name": preset_id,
            "look_id": look_id,
            "subject_id": bodyfit_id,
            "sex": sex,
            "bodyfit_id": bodyfit_id,
            "source_project": {"path": "project", "size_bytes": 1, "sha256": "0" * 64},
            "selected_assets": [
                {
                    "asset_id": "asset",
                    "slot": "full_body",
                    "path": "asset",
                    "size_bytes": 1,
                    "sha256": "1" * 64,
                    "cloth_options_policy": "fit_body_shape",
                }
            ],
            "capture_views": [],
            "expected_image_count": 0,
        }


if __name__ == "__main__":
    unittest.main()
