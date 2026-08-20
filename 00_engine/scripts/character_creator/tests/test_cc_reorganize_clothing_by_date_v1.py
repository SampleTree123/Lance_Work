from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "cc_reorganize_clothing_by_date_v1.py"
SPEC = importlib.util.spec_from_file_location("cc_clothing_reorg", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def make_zip(path: Path, member: str, payload: bytes, year: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo(member, (year, 1, 2, 3, 4, 6))
        archive.writestr(info, payload)


class ClothingDateReorganizationTests(unittest.TestCase):
    def test_archive_date_gate_and_cross_sex_deduplication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for sex in ("female", "male"):
                (root / sex).mkdir()
            make_zip(
                root / "female" / "shared.zip",
                "Pack/Character Creator 3 Template/Cloth/Shirts/Top.ccCloth",
                b"same payload",
                2023,
            )
            make_zip(
                root / "male" / "shared-repacked.zip",
                "Other/Character Creator 3 Template/Cloth/Shirts/Top.ccCloth",
                b"same payload",
                2023,
            )
            make_zip(
                root / "male" / "old.zip",
                "Pack/Character Creator 3 Template/Cloth/Pants/Old.ccCloth",
                b"old",
                2020,
            )
            packages = MODULE.scan_sources(root)
            logical = MODULE.merge_duplicate_packages(packages)
            shared = next(item for item in logical if item["logical_sex"] == "both")
            old = next(item for item in logical if item["label"] == "old")
            self.assertEqual("accepted", shared["classification"])
            self.assertEqual(2, shared["duplicate_source_count"])
            self.assertEqual("outdated", old["classification"])

    def test_default_zip_date_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for sex in ("female", "male"):
                (root / sex).mkdir()
            make_zip(root / "female" / "unknown.zip", "Top.ccCloth", b"x", 1980)
            package = MODULE.scan_sources(root)[0]
            self.assertEqual("date_unknown", package["classification"])

    def test_current_year_loose_timestamp_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for sex in ("female", "male"):
                (root / sex).mkdir()
            asset = root / "male" / "Pack" / "Top.ccCloth"
            asset.parent.mkdir()
            asset.write_bytes(b"payload")
            package = MODULE.scan_sources(root)[0]
            self.assertEqual("date_unknown", package["classification"])

    def test_loose_package_uses_product_root_and_copies_without_nested_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for sex in ("female", "male"):
                (root / sex).mkdir()
            product = root / "female" / "\u670d\u88c5" / "Office Pack"
            asset = (
                product
                / "Character Creator 3 Template"
                / "Cloth"
                / "Shirts"
                / "Office"
                / "Top.ccCloth"
            )
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"payload")
            stamp = datetime(2024, 2, 3).timestamp()
            os.utime(asset, (stamp, stamp))
            (product / "nested.zip").write_bytes(b"not copied")
            packages = MODULE.scan_sources(root)
            loose = next(item for item in packages if item["source_type"] == "loose_directory")
            self.assertEqual(product.resolve(), Path(loose["source_path"]))
            self.assertEqual("accepted", loose["classification"])

    def test_newest_half_policy_is_separate_per_sex_and_keeps_boundary_ties(self) -> None:
        logical = []
        for sex, years in (("female", [2019, 2020, 2021, 2021]), ("male", [2018, 2024])):
            for index, year in enumerate(years):
                logical.append(
                    {
                        "logical_sex": sex,
                        "label": f"{sex}-{index}",
                        "earliest_asset_date": f"{year}-01-01T00:00:00",
                        "unknown_date_count": 0,
                        "classification": "outdated",
                    }
                )
        boundaries = MODULE.apply_policy(logical, MODULE.POLICY_NEWEST_HALF)
        female = [x for x in logical if x["logical_sex"] == "female"]
        male = [x for x in logical if x["logical_sex"] == "male"]
        self.assertEqual(2, boundaries["female"]["target_count_before_boundary_ties"])
        self.assertEqual(2, sum(x["classification"] == "accepted" for x in female))
        self.assertEqual(1, sum(x["classification"] == "accepted" for x in male))
        self.assertEqual("2021-01-01T00:00:00", boundaries["female"]["boundary_earliest_asset_date"])


if __name__ == "__main__":
    unittest.main()
