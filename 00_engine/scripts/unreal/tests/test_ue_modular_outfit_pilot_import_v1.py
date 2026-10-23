from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "ue_modular_outfit_pilot_import_v1.py"
)
MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "ue_modular_outfit_pilot_manifest_20260829_v1.json"
)

sys.modules.setdefault("unreal", types.ModuleType("unreal"))
SPEC = importlib.util.spec_from_file_location(
    "ue_modular_outfit_pilot_import_v1_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ManifestValidationTests(unittest.TestCase):
    def test_gc_only_runs_after_wardrobe_import_phases(self):
        library = types.SimpleNamespace(collect_garbage=Mock())
        with patch.object(MODULE.unreal, "SystemLibrary", library, create=True):
            with patch.object(MODULE.gc, "collect") as python_gc:
                self.assertFalse(MODULE.collect_after_wardrobe_import({}, "import_split"))
                manifest = {"import_scope": "wardrobe_average_v1"}
                self.assertFalse(MODULE.collect_after_wardrobe_import(manifest, "validate_case"))
                self.assertTrue(MODULE.collect_after_wardrobe_import(manifest, "import_split"))
                self.assertTrue(MODULE.collect_after_wardrobe_import(manifest, "import_reference"))
                self.assertEqual(python_gc.call_count, 2)
        self.assertEqual(library.collect_garbage.call_count, 2)

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = MODULE.read_json(MANIFEST)

    def test_real_manifest_has_frozen_case_and_base_shape(self) -> None:
        summary = MODULE.validate_manifest(self.manifest)

        self.assertEqual(summary["case_count"], 14)
        self.assertEqual(
            summary["base_case_ids"],
            {"male": "M_BASE", "female": "F_BASE"},
        )
        self.assertEqual(len(summary["case_ids"]), len(set(summary["case_ids"])))

    def test_export_pending_status_does_not_invalidate_manifest(self) -> None:
        pending = copy.deepcopy(self.manifest)
        pending["status"] = "source_export_pending"

        self.assertEqual(MODULE.validate_manifest(pending)["case_count"], 14)

    def test_wardrobe_batch_reuses_bases_and_limits_destination_by_sex(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["import_scope"] = "wardrobe_average_v1"
        manifest["cases"] = [MODULE.case_for_id(manifest, cid)
                             for cid in ("M_BASE", "F_BASE", "M_1920_LAYERED")]
        manifest["counts"]["case_count"] = 3
        for case in manifest["cases"][:2]:
            case["reuse_existing_base"] = True
            case["ue_case_root"] = MODULE.case_destinations(case["bodyfit_id"], case["case_id"])["case_root"]
        garment = manifest["cases"][2]
        garment["ue_case_root"] = "/Game/Vendor/Reallusion/CC5/Wardrobe/Male/Average/Casual/Coats/M_A"
        self.assertEqual(MODULE.validate_manifest(manifest)["case_count"], 3)
        garment["ue_case_root"] = garment["ue_case_root"].replace("/Male/", "/Female/")
        with self.assertRaisesRegex(ValueError, "outside its sex/Average scope"):
            MODULE.validate_manifest(manifest)

    def test_explicit_path_cannot_escape_vendor(self):
        for root in ("/Game/DataMake/Scenes", "/Game/Vendor/Reallusion/CC5/Wardrobe/Male/../Bad"):
            with self.assertRaises(ValueError):
                MODULE.destinations_for_case({"ue_case_root": root})

    def test_rejects_any_case_count_other_than_fourteen(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid["cases"].pop()

        with self.assertRaisesRegex(ValueError, "expected 14 cases"):
            MODULE.validate_manifest(invalid)

    def test_rejects_changed_base_case_contract(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        MODULE.case_for_id(invalid, "M_BASE")["case_role"] = "outfit_modules"

        with self.assertRaisesRegex(
            ValueError, "base cases must be exactly M_BASE and F_BASE"
        ):
            MODULE.validate_manifest(invalid)

    def test_rejects_missing_planned_project(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        del MODULE.case_for_id(invalid, "F_BASE")["planned_export"]["project"]

        with self.assertRaisesRegex(
            ValueError, "planned_export.project is required"
        ):
            MODULE.validate_manifest(invalid)

    def test_base_case_lookup_is_sex_bounded(self) -> None:
        self.assertEqual(
            MODULE.base_case_for_sex(self.manifest, "male")["case_id"],
            "M_BASE",
        )
        self.assertEqual(
            MODULE.base_case_for_sex(self.manifest, "female")["case_id"],
            "F_BASE",
        )
        with self.assertRaisesRegex(ValueError, "Unsupported sex"):
            MODULE.base_case_for_sex(self.manifest, "unknown")


class PathConstructionTests(unittest.TestCase):
    def test_case_destinations_stay_under_required_project_root(self) -> None:
        paths = MODULE.case_destinations("M02_Average", "M_1920_LAYERED")
        case_root = (
            "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/"
            "M02_Average/Cases/M_1920_LAYERED"
        )

        self.assertEqual(paths["case_root"], case_root)
        self.assertEqual(paths["full_reference"], case_root + "/FullReference")
        self.assertEqual(paths["modules"], case_root + "/Modules")
        self.assertEqual(
            paths["pipeline"],
            case_root + "/Modules/DM_Interchange_Split_Pipeline_v1",
        )

    def test_case_destinations_reject_path_injection(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsafe case_id"):
            MODULE.case_destinations("M02_Average", "../M_BASE")

    def test_planned_export_paths_include_all_three_artifacts(self) -> None:
        manifest = MODULE.read_json(MANIFEST)
        case = MODULE.case_for_id(manifest, "F_DRESS_FULLBODY")
        paths = MODULE.planned_export_paths(case)

        self.assertEqual(set(paths), {"fbx", "json", "project"})
        self.assertEqual(paths["fbx"].suffix.lower(), ".fbx")
        self.assertEqual(paths["json"].suffix.lower(), ".json")
        self.assertEqual(paths["project"].suffix.lower(), ".ccproject")


class HashCaptureTests(unittest.TestCase):
    def test_inspect_file_captures_actual_hash_without_expected_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.fbx"
            path.write_bytes(b"modular-outfit")

            record = MODULE.inspect_file(path, "CASE.fbx")

        self.assertTrue(record["passed"])
        self.assertEqual(record["size_bytes"], 14)
        self.assertEqual(len(record["sha256"]), 64)
        self.assertIsNone(record["expected_sha256"])


class FactoryProbeContractTests(unittest.TestCase):
    def test_reallusion_false_can_import_probe_is_advisory(self) -> None:
        probe = {
            "available": True,
            "class": "/Script/RLPlugin.CCFbxFactory",
            "formats": ["fbx;FBX meshes and animations"],
            "can_import": {r"D:\character.fbx": False},
        }

        self.assertTrue(MODULE.factory_probe_ready(probe))

    def test_wrong_factory_or_missing_fbx_format_is_rejected(self) -> None:
        self.assertFalse(
            MODULE.factory_probe_ready(
                {
                    "available": True,
                    "class": "/Script/UnrealEd.FbxFactory",
                    "formats": ["fbx;FBX meshes and animations"],
                }
            )
        )
        self.assertFalse(
            MODULE.factory_probe_ready(
                {
                    "available": True,
                    "class": "/Script/RLPlugin.CCFbxFactory",
                    "formats": ["obj;OBJ Static meshes"],
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
