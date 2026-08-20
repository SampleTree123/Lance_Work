import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module(
    "cc_validate_headshot_face_prototype_registry",
    "cc_validate_headshot_face_prototype_registry.py",
)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def file_record(path):
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": VALIDATOR.sha256_file(str(path)),
    }


class HeadshotPrototypeRegistryTests(unittest.TestCase):
    def make_registry(
        self,
        root,
        visual_status="pending_user_review",
        shaping_morph_count=0,
        measurement_status=None,
    ):
        identity = root / "identity.ccProject"
        profile = root / "profile.ccFacialProfile"
        rollback = root / "rollback.ccFacialProfile"
        source = root / "source.ccProject"
        for path, payload in (
            (identity, b"identity"),
            (profile, b"profile"),
            (rollback, b"rollback"),
            (source, b"source"),
        ):
            path.write_bytes(payload)

        manifest_path = root / "prototype.json"
        manifest = {
            "schema_version": 1,
            "prototype_id": "F_HS_003",
            "sex": "female",
            "status": "candidate_source_reference_pending",
            "identity_representation": {
                "mode": "baked_geometry_project",
                "nonzero_shaping_morph_count": shaping_morph_count,
            },
            "canonical_assets": {
                "identity_project": file_record(identity),
                "facial_profile": file_record(profile),
                "rollback_facial_profile": file_record(rollback),
            },
            "source_reference_match": {
                "confirmation_status": "pending_user_mapping"
            },
            "frozen_source": {
                "project_path": str(source),
                "project_bytes": source.stat().st_size,
                "project_sha256": VALIDATOR.sha256_file(str(source)),
            },
            "profile_upgrade": {
                "derived_uid": "CC5 MetaHuman",
                "derived_expression_count": 379,
            },
            "validation": {
                "machine_status": "passed",
                "visual_status": visual_status,
                "static_morphs_unchanged": True,
                "material_assignments_unchanged": True,
                "eye_structure_unchanged": True,
                "neutral_eye_integrity": True,
                "profile_persisted_after_reload": True,
                "source_project_unchanged": True,
            },
            "assembly_contract": {
                "pipeline": "headshot_project_seed_then_bodyfit_v1",
                "implemented": False,
            },
        }
        if measurement_status is not None:
            manifest["identity_representation"][
                "measurement_status"
            ] = measurement_status
        write_json(manifest_path, manifest)
        registry_path = root / "registry.json"
        write_json(
            registry_path,
            {
                "schema_version": 1,
                "prototypes": [
                    {
                        "prototype_id": "F_HS_003",
                        "sex": "female",
                        "manifest": file_record(manifest_path),
                    }
                ],
            },
        )
        return registry_path

    def test_pending_source_mapping_is_valid_but_not_production_enabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry = self.make_registry(pathlib.Path(temporary))
            result = VALIDATOR.validate_registry(str(registry))
            self.assertTrue(result["success"])
            self.assertEqual(0, result["production_enabled_count"])
            self.assertFalse(result["prototypes"][0]["source_reference_mapped"])

    def test_visual_pass_is_blocked_until_source_reference_is_mapped(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry = self.make_registry(
                pathlib.Path(temporary), visual_status="passed"
            )
            with self.assertRaisesRegex(
                VALIDATOR.RegistryError, "before source mapping"
            ):
                VALIDATOR.validate_registry(str(registry))

    def test_unmeasured_candidate_is_valid_but_not_production_enabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry = self.make_registry(
                pathlib.Path(temporary),
                shaping_morph_count=None,
                measurement_status="not_recorded_in_rm05c_batch",
            )
            result = VALIDATOR.validate_registry(str(registry))
            self.assertTrue(result["success"])
            self.assertEqual(0, result["production_enabled_count"])
            self.assertFalse(
                result["prototypes"][0]["shaping_morph_count_verified"]
            )

    def test_unmeasured_candidate_requires_explicit_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry = self.make_registry(
                pathlib.Path(temporary), shaping_morph_count=None
            )
            with self.assertRaisesRegex(
                VALIDATOR.RegistryError, "no shaping Morph measurement status"
            ):
                VALIDATOR.validate_registry(str(registry))


if __name__ == "__main__":
    unittest.main()
