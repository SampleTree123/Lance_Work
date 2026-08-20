import importlib.util
import json
import pathlib
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_head_bodyfit_scale_review_matrix_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_head_bodyfit_scale_review_matrix_v1_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class HeadBodyFitScaleReviewMatrixTests(unittest.TestCase):
    def test_repository_config_builds_expected_review_matrix(self):
        config_path = SCRIPT_PATH.parent / (
            "cc_head_bodyfit_scale_review_matrix_v1_config.json"
        )
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        document = SUBJECT.build_document(
            config,
            SUBJECT.read_json(SUBJECT.resolve_path(config["body_library"])),
            SUBJECT.read_json(
                SUBJECT.resolve_path(config["face_baseline_library"])
            ),
            SUBJECT.read_json(
                SUBJECT.resolve_path(config["pipeline_library"])
            ),
        )

        self.assertEqual(
            "head_bodyfit_scale_review_matrix",
            document["diagnostic_mode"],
        )
        self.assertEqual(10, len(document["presets"]))
        self.assertEqual(
            {
                "F01_Lean",
                "F02_Average",
                "F03_Athletic",
                "F04_Heavy",
                "M01_Lean",
                "M02_Average",
                "M03_Athletic",
                "M04_Heavy",
            },
            {item["bodyfit_id"] for item in document["presets"]},
        )
        face_variants = [
            item
            for item in document["presets"]
            if "face_variation" in item["review_groups"]
        ]
        self.assertEqual(3, len(face_variants))
        self.assertEqual(
            {"average", "broad_round", "narrow_long"},
            {item["face_shape_role"] for item in face_variants},
        )
        expected_values = [
            -0.4,
            -0.3,
            -0.2,
            -0.1,
            0.0,
            0.1,
            0.2,
            0.3,
            0.35,
            0.4,
        ]
        for preset in document["presets"]:
            self.assertEqual(
                expected_values,
                preset["head_scale_review"]["values"],
            )
            self.assertNotIn("appearance_recipe", preset)
            self.assertNotIn("facial_assembly", preset)


if __name__ == "__main__":
    unittest.main()
