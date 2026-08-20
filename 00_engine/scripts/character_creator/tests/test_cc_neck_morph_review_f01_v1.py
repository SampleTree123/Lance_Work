import importlib.util
import json
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
BUILDER_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_neck_morph_review_f01_v1.py",
)
CONFIG_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_neck_morph_review_f01_v1_config.json",
)


def load_builder():
    spec = importlib.util.spec_from_file_location("neck_review_builder", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NeckMorphReviewTests(unittest.TestCase):
    def test_full_and_smoke_libraries_keep_selected_f01_head_scale(self):
        builder = load_builder()
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            config = json.load(handle)

        full = builder.build_library(config, smoke=False)
        smoke = builder.build_library(config, smoke=True)
        headshot_smoke = builder.build_library(
            config,
            smoke=True,
            smoke_morph_index=1,
        )
        headshot_focus = builder.build_library(config, focus=True)
        full_preset = full["presets"][0]
        smoke_preset = smoke["presets"][0]

        self.assertEqual(full["diagnostic_mode"], "neck_morph_review_matrix")
        self.assertEqual(full_preset["bodyfit_id"], "F01_Lean")
        self.assertEqual(
            full_preset["neck_morph_review"]["head_scale"]["target"],
            -0.2,
        )
        self.assertEqual(len(full_preset["neck_morph_review"]["morphs"]), 2)
        self.assertEqual(
            sum(
                len(item["values"])
                for item in full_preset["neck_morph_review"]["morphs"]
            ),
            12,
        )
        self.assertNotIn("head_scale_review", full_preset)
        self.assertTrue(full_preset["skip_post_diagnostic_face_validation"])
        self.assertEqual(len(smoke_preset["neck_morph_review"]["morphs"]), 1)
        self.assertEqual(
            smoke_preset["neck_morph_review"]["morphs"][0]["values"],
            [0.0, 1.0],
        )
        self.assertEqual(
            headshot_smoke["presets"][0]["neck_morph_review"]["morphs"][0][
                "review_id"
            ],
            "headshot_neck_height",
        )
        self.assertEqual(
            headshot_smoke["presets"][0]["neck_morph_review"]["morphs"][0][
                "values"
            ],
            [-1.0, 0.0, 0.5],
        )
        self.assertEqual(
            headshot_focus["library_id"],
            "adult_f01_neck_height_focus_v1",
        )
        self.assertEqual(
            headshot_focus["presets"][0]["neck_morph_review"]["morphs"][0][
                "values"
            ],
            [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0],
        )
        self.assertEqual(
            full_preset["neck_morph_review"]["views"],
            [
                {"view_id": "yaw_000", "yaw_degrees": 0.0},
                {"view_id": "yaw_045", "yaw_degrees": 45.0},
                {"view_id": "yaw_090", "yaw_degrees": 90.0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
