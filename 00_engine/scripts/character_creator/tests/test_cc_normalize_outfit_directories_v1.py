from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "cc_normalize_outfit_directories_v1.py"
SPEC = importlib.util.spec_from_file_location("cc_outfit_normalizer", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class OutfitDirectoryNormalizationTests(unittest.TestCase):
    def test_core_slot_classification(self) -> None:
        cases = {
            "Winter Jacket.ccCloth": "Coats",
            "Top 01.ccCloth": "Shirts",
            "Shorts 01.ccCloth": "Pants",
            "Kilt.ccCloth": "Skirts",
            "Summer Dress.ccCloth": "Full-body",
            "Boots.ccShoes": "Shoes",
            "Scarf.ccCloth": "_Accessories-Pending",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                actual = MODULE.classify_asset("male", "Example", Path(name))
                self.assertEqual(expected, actual)

    def test_locked_bundle_components_are_nested_but_shoes_are_not(self) -> None:
        family = "Elise"
        self.assertEqual(
            "Full-body/Locked-Bundle",
            MODULE.classify_asset("female", family, Path("1.ccCloth")),
        )
        self.assertEqual(
            "Shoes",
            MODULE.classify_asset("female", family, Path("1.ccShoes")),
        )

    def test_plan_ignores_assets_already_inside_slot_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for sex in ("female", "male"):
                (root / sex).mkdir()
            family = root / "female" / "Example"
            family.mkdir()
            (family / "Top.ccCloth").write_bytes(b"top")
            (family / "Pants").mkdir()
            (family / "Pants" / "Pants.ccCloth").write_bytes(b"pants")

            moves, unclassified = MODULE.build_plan(root)

            self.assertEqual([], unclassified)
            self.assertEqual(1, len(moves))
            self.assertEqual(
                ("Shirts", "Top.ccCloth"),
                Path(str(moves[0]["destination"])).parts[-2:],
            )

    def test_execute_preserves_file_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for sex in ("female", "male"):
                (root / sex).mkdir()
            family = root / "male" / "Example"
            family.mkdir()
            source = family / "Jacket.ccCloth"
            source.write_bytes(b"stable garment payload")

            moves, unclassified = MODULE.build_plan(root)
            self.assertEqual([], unclassified)
            expected_hash = moves[0]["sha256"]
            MODULE.execute_plan(moves)

            destination = family / "Coats" / "Jacket.ccCloth"
            self.assertFalse(source.exists())
            self.assertTrue(destination.is_file())
            self.assertEqual(expected_hash, MODULE.sha256(destination))


if __name__ == "__main__":
    unittest.main()
