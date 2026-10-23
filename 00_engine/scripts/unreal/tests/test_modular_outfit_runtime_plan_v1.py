from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1] / "modular_outfit_runtime_plan_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "modular_outfit_runtime_plan_v1_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def module(module_key: str, scene_name: str, slot: str = "shirts") -> dict:
    return {
        "module_key": module_key,
        "asset_id": module_key,
        "display_name": scene_name,
        "slot": slot,
        "source": "family",
        "source_path": f"C:/{scene_name}.ccCloth",
        "cc_scene_objects": [
            {
                "collection": "GetClothes",
                "name": scene_name,
                "python_type": "RLPy.RICloth",
            }
        ],
    }


def mesh(name: str, path: str | None = None) -> dict:
    return {
        "class": "SkeletalMesh",
        "name": name,
        "path": path or f"/Game/Test/{name}",
        "skeleton": "/Game/Test/Skeleton",
    }


class NameNormalizationTests(unittest.TestCase):
    def test_normalizes_cc_and_unreal_generated_names(self) -> None:
        self.assertEqual(
            MODULE.normalize_object_name("/Game/Test/Tux_Shirt.Tux_Shirt"),
            "tuxshirt",
        )
        self.assertEqual(
            MODULE.normalize_object_name("Tux_Shirt_SkeletalMesh"),
            "tuxshirt",
        )

    def test_exact_match_beats_prefixed_match(self) -> None:
        self.assertGreater(
            MODULE._mesh_match_score("Tux Shirt", "Tux_Shirt"),
            MODULE._mesh_match_score("Tux Shirt", "CC_CASE_Tux_Shirt"),
        )


class ClassificationTests(unittest.TestCase):
    def test_maps_modules_and_ignores_non_apparel_split_meshes(self) -> None:
        case = {
            "case_id": "M_LAYERED",
            "modules": [
                module("Shirts/Tux.ccCloth", "Tux_Shirt"),
                module("Coats/Jacket.ccCloth", "Jacket", "coats"),
            ],
        }
        report = {
            "success": True,
            "meshes": [
                mesh("CC_Base_Body"),
                mesh("Tux_Shirt_SkeletalMesh"),
                mesh("CC_CASE_Jacket"),
            ],
        }

        result = MODULE.classify_case_meshes(case, report)

        self.assertEqual(result["classified_mesh_count"], 2)
        self.assertEqual(result["ignored_split_mesh_count"], 1)
        self.assertEqual(
            result["modules"][0]["mesh_paths"],
            ["/Game/Test/Tux_Shirt_SkeletalMesh"],
        )

    def test_rejects_ambiguous_split_mesh_match(self) -> None:
        case = {
            "case_id": "F_LOCKED",
            "modules": [module("Full-body/1.ccCloth", "Part_One")],
        }
        report = {
            "success": True,
            "meshes": [mesh("A_Part_One"), mesh("B_Part_One")],
        }

        with self.assertRaisesRegex(MODULE.RuntimePlanError, "Expected one"):
            MODULE.classify_case_meshes(case, report)

    def test_rejects_unfinalized_scene_evidence(self) -> None:
        case = {
            "case_id": "M_CASE",
            "modules": [{"module_key": "Shirts/Test.ccCloth"}],
        }

        with self.assertRaisesRegex(MODULE.RuntimePlanError, "scene evidence"):
            MODULE.classify_case_meshes(
                case, {"success": True, "meshes": [mesh("Test")]}
            )


class RuntimePlanTests(unittest.TestCase):
    def _manifest(self) -> dict:
        cases = []
        for sex, prefix, bodyfit in (
            ("male", "M", "M02_Average"),
            ("female", "F", "F02_Average"),
        ):
            cases.append(
                {
                    "case_id": f"{prefix}_BASE",
                    "case_role": "base_body",
                    "sex": sex,
                    "bodyfit_id": bodyfit,
                    "modules": [],
                }
            )
            cases.append(
                {
                    "case_id": f"{prefix}_CASE",
                    "case_role": "outfit_modules",
                    "sex": sex,
                    "bodyfit_id": bodyfit,
                    "family": {"family_id": f"{sex}.test"},
                    "coverage_tags": ["standard_separates"],
                    "modules": [
                        module("Shirts/Top.ccCloth", f"{prefix}_Top"),
                        module("Pants/Bottom.ccCloth", f"{prefix}_Bottom", "pants"),
                    ],
                    "runtime_variants": [
                        {
                            "variant_id": "full",
                            "enabled_modules": [
                                "Shirts/Top.ccCloth",
                                "Pants/Bottom.ccCloth",
                            ],
                            "disabled_modules": [],
                        },
                        {
                            "variant_id": "top_only",
                            "enabled_modules": ["Shirts/Top.ccCloth"],
                            "disabled_modules": ["Pants/Bottom.ccCloth"],
                        },
                    ],
                }
            )
        return {
            "status": "cc_export_passed",
            "pilot_id": "test_pilot",
            "cases": cases,
        }

    def _write_reports(self, root: Path) -> None:
        for sex, prefix in (("male", "M"), ("female", "F")):
            del sex
            MODULE.write_json(
                root / f"{prefix}_BASE_import_reference.json",
                {
                    "mode": "import_reference",
                    "case_id": f"{prefix}_BASE",
                    "success": True,
                    "requires_auto_setup": False,
                    "material_quality_passed": True,
                    "rig_assets_passed": True,
                    "assets": [
                        {
                            **mesh(f"{prefix}_Body"),
                            "skeleton": f"/Game/Test/{prefix}_Skeleton",
                        }
                    ],
                },
            )
            MODULE.write_json(
                root / f"{prefix}_CASE_import_split.json",
                {
                    "mode": "import_split",
                    "case_id": f"{prefix}_CASE",
                    "success": True,
                    "meshes": [mesh(f"{prefix}_Top"), mesh(f"{prefix}_Bottom")],
                },
            )
            MODULE.write_json(
                root / f"{prefix}_CASE_validate_case.json",
                {
                    "mode": "validate_case",
                    "case_id": f"{prefix}_CASE",
                    "success": True,
                },
            )

    def test_builds_two_bodyfits_with_hard_reference_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_reports(root)

            plan = MODULE.build_runtime_plan(self._manifest(), root)

        self.assertEqual(plan["bodyfit_count"], 2)
        self.assertEqual(plan["runtime_variant_count"], 6)
        self.assertEqual(
            [item["component_count"] for item in plan["bodyfits"]], [2, 2]
        )
        male = plan["bodyfits"][0]
        self.assertEqual(male["runtime_variants"][0]["qualified_variant_id"], "M_BASE::base")
        male_variant = male["cases"][0]["runtime_variants"][0]
        self.assertEqual(
            male_variant["enabled_component_names"],
            ["Outfit_M_CASE_01", "Outfit_M_CASE_02"],
        )

    def test_rejects_manifest_before_cc_export_finalization(self) -> None:
        manifest = self._manifest()
        manifest["status"] = "source_export_pending"
        with self.assertRaisesRegex(MODULE.RuntimePlanError, "finalized CC export"):
            MODULE.build_runtime_plan(manifest, Path("missing"))


if __name__ == "__main__":
    unittest.main()
