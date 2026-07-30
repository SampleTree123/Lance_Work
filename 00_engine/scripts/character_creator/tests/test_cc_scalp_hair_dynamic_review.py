import importlib.util
import pathlib
import tempfile
import unittest


SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SCRIPT_DIR / "cc_build_scalp_hair_dynamic_review_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "cc_build_scalp_hair_dynamic_review_v1_under_test",
    SCRIPT_PATH,
)
SUBJECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUBJECT)


class ScalpHairDynamicReviewTests(unittest.TestCase):
    def test_default_evidence_builds_complete_review(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "review.json"
            document = SUBJECT.build(output_path=str(output))

        self.assertEqual(58, len(document["assets"]))
        self.assertEqual(
            {
                "dynamic_approved": 52,
                "rigid_short_approved": 6,
            },
            document["summary"]["production_status_counts"],
        )
        self.assertEqual(
            74,
            document["summary"]["dynamic_base_case_count"]
            + document["summary"]["cross_presentation_case_count"],
        )
        self.assertEqual(
            64,
            document["summary"]["static_pressure_case_count"],
        )
        self.assertEqual(
            16,
            document["summary"]["static_pressure_asset_count"],
        )

    def test_documented_asset_risks_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "review.json"
            document = SUBJECT.build(output_path=str(output))
        assets = {
            item["asset_id"]: item for item in document["assets"]
        }

        self.assertIn(
            "nape_component_color_mismatch_pending_pigmentation",
            assets["CCAPP_SCALP_HAIR_b76abfcd9bdb"]["risk_tags"],
        )
        self.assertIn(
            "accessory_visibility_head_shape_sensitive",
            assets["CCAPP_SCALP_HAIR_c8078bdda14a"]["risk_tags"],
        )
        self.assertEqual(
            "accepted_with_documented_risk",
            assets["CCAPP_SCALP_HAIR_c8078bdda14a"][
                "static_pressure"
            ]["status"],
        )


if __name__ == "__main__":
    unittest.main()
