import importlib.util
import os
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR, "cc_build_first_batch_full_reference_looks_v2.py"
)
SPEC = importlib.util.spec_from_file_location(
    "first_batch_look_builder_v2", MODULE_PATH
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class FirstBatchFullReferenceLookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = builder.build(
            builder.DEFAULT_IDENTITY_LIBRARY,
            builder.DEFAULT_OUTFIT_GATE,
            builder.DEFAULT_IDENTITY_ROOT,
            builder.DEFAULT_EXPORT_ROOT,
            verify_identity_projects=False,
        )

    def test_ring_counts(self):
        rows = self.document["look_rows"]
        self.assertEqual(16, len(rows))
        self.assertEqual(8, sum(item["sex"] == "female" for item in rows))
        self.assertEqual(8, sum(item["sex"] == "male" for item in rows))
        by_identity = {}
        for row in rows:
            by_identity.setdefault(row["identity_id"], []).append(row)
        self.assertEqual(8, len(by_identity))
        self.assertTrue(all(len(items) == 2 for items in by_identity.values()))

    def test_production_outputs_are_unique_and_frozen(self):
        presets = self.document["presets"]
        outputs = [item["production_output"] for item in presets]
        self.assertEqual(16, len({item["project_path"] for item in outputs}))
        self.assertEqual(16, len({item["export_root"] for item in outputs}))
        self.assertTrue(all(item["skip_preview_capture"] for item in outputs))
        self.assertTrue(all(item["selected_assets"] for item in presets))
        self.assertTrue(
            all(len(item["capture_views"]) == 1 for item in presets)
        )
        self.assertFalse(
            self.document["execution_policy"]["record_asset_load_undo"]
        )

    def test_female_o04_uses_casual_jacket_c(self):
        female_o04 = [
            item
            for item in self.document["presets"]
            if item["sex"] == "female"
            and item["first_batch_outfit_id"] == "O04"
        ]
        self.assertEqual(2, len(female_o04))
        for preset in female_o04:
            coats = [
                item
                for item in preset["selected_assets"]
                if item["slot"] == "coats"
            ]
            self.assertEqual(1, len(coats))
            self.assertEqual("CasualJacket_C", coats[0]["display_name"])
            self.assertEqual(
                "female_o04_casual_jacket_c_20260820",
                preset["outfit_asset_override_id"],
            )


if __name__ == "__main__":
    unittest.main()
