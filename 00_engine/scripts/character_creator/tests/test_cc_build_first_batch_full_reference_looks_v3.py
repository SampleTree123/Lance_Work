import json
import os
import sys
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import cc_build_first_batch_full_reference_looks_v2 as v2
import cc_build_first_batch_full_reference_looks_v3 as v3


class FirstBatchFullReferenceMatrixV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = v2.build(
            v2.DEFAULT_IDENTITY_LIBRARY,
            v2.DEFAULT_OUTFIT_GATE,
            v2.DEFAULT_IDENTITY_ROOT,
            v2.DEFAULT_EXPORT_ROOT,
            verify_identity_projects=False,
            identity_outfit_map=v3.FULL_MATRIX,
            document_id="test_full_matrix",
        )
        cls.existing = v2.build(
            v2.DEFAULT_IDENTITY_LIBRARY,
            v2.DEFAULT_OUTFIT_GATE,
            v2.DEFAULT_IDENTITY_ROOT,
            v2.DEFAULT_EXPORT_ROOT,
            verify_identity_projects=False,
        )

    def test_complete_matrix_has_four_outfits_per_identity(self):
        rows = self.full["look_rows"]
        self.assertEqual(32, len(rows))
        self.assertEqual(32, len({item["look_id"] for item in rows}))
        by_identity = {}
        for row in rows:
            by_identity.setdefault(row["identity_id"], set()).add(row["outfit_id"])
        self.assertEqual(8, len(by_identity))
        self.assertTrue(
            all(outfits == {"O01", "O02", "O03", "O04"} for outfits in by_identity.values())
        )

    def test_delta_is_exact_complement_of_existing_ring(self):
        with tempfile.TemporaryDirectory() as temporary:
            existing_path = os.path.join(temporary, "existing.json")
            with open(existing_path, "w", encoding="utf-8") as handle:
                json.dump(self.existing, handle)
            delta, existing_ids, missing_ids = v3.build_delta(
                self.full, existing_path
            )

        full_ids = {item["look_id"] for item in self.full["presets"]}
        self.assertEqual(16, len(existing_ids))
        self.assertEqual(16, len(missing_ids))
        self.assertFalse(set(existing_ids) & set(missing_ids))
        self.assertEqual(full_ids, set(existing_ids) | set(missing_ids))
        self.assertEqual(missing_ids, [item["look_id"] for item in delta["presets"]])

    def test_all_four_female_o04_looks_use_frozen_override(self):
        rows = [
            item
            for item in self.full["presets"]
            if item["sex"] == "female"
            and item["first_batch_outfit_id"] == "O04"
        ]
        self.assertEqual(4, len(rows))
        for preset in rows:
            coats = [
                item
                for item in preset["selected_assets"]
                if item["slot"] == "coats"
            ]
            self.assertEqual(["CasualJacket_C"], [item["display_name"] for item in coats])


if __name__ == "__main__":
    unittest.main()
