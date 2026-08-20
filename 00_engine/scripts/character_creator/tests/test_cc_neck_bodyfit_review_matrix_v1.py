import importlib.util
import json
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
BUILDER_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_neck_bodyfit_review_matrix_v1.py",
)
CONFIG_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_neck_bodyfit_review_matrix_v1_config.json",
)


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "neck_bodyfit_review_builder",
        BUILDER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NeckBodyfitReviewMatrixTests(unittest.TestCase):
    def test_repository_config_builds_m01_and_m03_matrix(self):
        builder = load_builder()
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        library = builder.build_library(config)

        self.assertEqual(
            library["diagnostic_mode"],
            "neck_morph_review_matrix",
        )
        self.assertEqual(library["matrix"]["bodyfit_count"], 2)
        self.assertEqual(len(library["presets"]), 2)
        expected = {
            "M01_Lean": -0.1,
            "M03_Athletic": 0.1,
        }
        for preset in library["presets"]:
            bodyfit_id = preset["bodyfit_id"]
            review = preset["neck_morph_review"]
            self.assertIn(bodyfit_id, expected)
            self.assertEqual(
                review["head_scale"]["target"],
                expected[bodyfit_id],
            )
            self.assertEqual(
                review["morphs"][0]["values"],
                [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0],
            )
            self.assertTrue(
                preset["skip_post_diagnostic_face_validation"]
            )
            self.assertNotIn("head_scale_review", preset)


if __name__ == "__main__":
    unittest.main()
