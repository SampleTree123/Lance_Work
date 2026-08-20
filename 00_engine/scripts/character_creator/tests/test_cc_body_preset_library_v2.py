import importlib.util
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_body_preset_library_v2.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_body_preset_library_v2",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BodyPresetLibraryV2Tests(unittest.TestCase):
    def test_builds_accepted_hash_locked_10_bodyfit_library(self):
        document = MODULE.build()

        self.assertEqual(document["library_id"], "adult_body_fits_v2")
        self.assertEqual(document["status"], "accepted")
        self.assertEqual(document["bodyfit_count"], 10)
        self.assertEqual(
            [item["preset_id"] for item in document["presets"]],
            list(MODULE.PRODUCTION_ORDER),
        )
        self.assertTrue(
            all(
                item["review_status"] == "accepted"
                for item in document["presets"]
            )
        )
        self.assertEqual(
            document["technical_validation"]["male_count"],
            5,
        )
        self.assertEqual(
            document["technical_validation"]["female_count"],
            5,
        )
        self.assertEqual(
            document["technical_validation"][
                "runtime_height_matrix_success_count"
            ],
            10,
        )

        by_id = {
            item["preset_id"]: item for item in document["presets"]
        }
        self.assertTrue(
            by_id["M05_Short_Average"]["source_project"]["path"].endswith(
                "M05_Short_Average.ccProject"
            )
        )
        self.assertTrue(
            by_id["F05_Short_Average"]["source_project"]["path"].endswith(
                "F05_Short_Average.ccProject"
            )
        )
        self.assertNotIn(
            "candidate.ccProject",
            by_id["M05_Short_Average"]["source_project"]["path"],
        )
        self.assertNotIn(
            "candidate.ccProject",
            by_id["F05_Short_Average"]["source_project"]["path"],
        )


if __name__ == "__main__":
    unittest.main()
