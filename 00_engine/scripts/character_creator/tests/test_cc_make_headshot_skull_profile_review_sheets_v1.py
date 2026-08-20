import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

from PIL import Image


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_make_headshot_skull_profile_review_sheets_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "cc_make_headshot_skull_profile_review_sheets_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class HeadshotSkullProfileReviewSheetTests(unittest.TestCase):
    def test_creates_overview_and_view_strips(self):
        with tempfile.TemporaryDirectory() as directory:
            views = {}
            for index, (view_id, unused_label) in enumerate(MODULE.VIEW_ORDER):
                path = os.path.join(directory, "{}.png".format(view_id))
                Image.new("RGB", (64, 64), (index * 30, 20, 40)).save(path)
                views[view_id] = path
            preset_id = "F_HS_002_P00_BASELINE"
            manifest_path = os.path.join(directory, "manifest.json")
            result_path = os.path.join(directory, "result.json")
            profile = {
                "id": "P00_BASELINE",
                "label": "Baseline",
                "head_width": 0.0,
                "head_depth": 0.0,
                "skull_height": 0.0,
                "skull_width": 0.0,
                "skull_depth": 0.0,
                "skull_back_depth": 0.0,
                "skull_peak": 0.0,
            }
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "presets": [
                            {
                                "preset_id": preset_id,
                                "head_shape_profile": profile,
                            }
                        ]
                    },
                    handle,
                )
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "diagnostic_mode": "targeted_morph_visual_matrix",
                        "results": [
                            {
                                "preset_id": preset_id,
                                "sex": "female",
                                "success": True,
                                "neck_morph_review": {
                                    "morphs": [
                                        {"candidates": [{"views": views}]}
                                    ]
                                },
                            }
                        ],
                    },
                    handle,
                )
            output_dir = os.path.join(directory, "review")

            index = MODULE.create_review_sheets(
                manifest_path,
                [result_path],
                output_dir,
            )

            self.assertEqual(1, index["case_count"])
            self.assertTrue(
                os.path.isfile(os.path.join(output_dir, "female", "overview.png"))
            )
            self.assertTrue(os.path.isfile(os.path.join(output_dir, "README.md")))
            for view_id, unused_label in MODULE.VIEW_ORDER:
                self.assertTrue(
                    os.path.isfile(
                        os.path.join(
                            output_dir,
                            "female",
                            "{}_comparison.png".format(view_id),
                        )
                    )
                )


if __name__ == "__main__":
    unittest.main()
