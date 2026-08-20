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


SUBJECT = load_module(
    "cc_attach_headshot_source_references",
    "cc_attach_headshot_source_references.py",
)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record(path):
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": SUBJECT.sha256_file(path),
    }


class HeadshotSourceReferenceTests(unittest.TestCase):
    def make_case(self, root):
        package = root / "F_HS_003"
        package.mkdir()
        manifest_path = package / "prototype.json"
        write_json(
            manifest_path,
            {
                "schema_version": 1,
                "prototype_id": "F_HS_003",
                "status": "pending",
                "canonical_assets": {},
                "source_reference_match": {
                    "confirmation_status": "pending_user_mapping"
                },
                "assembly_contract": {
                    "production_blockers": [
                        "source_reference_mapping_pending",
                        "rm05c_identity_pool_scale_comparison_pending",
                    ]
                },
            },
        )
        source = root / "source.jpg"
        source.write_bytes(b"source-photo")
        registry_path = root / "registry.json"
        write_json(
            registry_path,
            {
                "schema_version": 1,
                "selection_policy": {
                    "enabled_for_production": False,
                    "production_activation_blocked_by": [
                        "rm05c_identity_pool_scale_comparison"
                    ],
                },
                "prototypes": [
                    {
                        "prototype_id": "F_HS_003",
                        "status": "pending",
                        "manifest": record(manifest_path),
                    }
                ],
            },
        )
        mapping_path = root / "mapping.json"
        write_json(
            mapping_path,
            {
                "schema_version": 1,
                "mapping_id": "test_mapping",
                "mapped_at": "2026-08-10",
                "expected_count": 1,
                "status_after": "mapped_visual_pending",
                "confirmation_status": "mapped_pending_user_acceptance",
                "entries": [
                    {
                        "prototype_id": "F_HS_003",
                        "source_path": str(source),
                        "source_sha256": SUBJECT.sha256_file(source),
                    }
                ],
            },
        )
        return mapping_path, registry_path, manifest_path

    def test_mapping_is_hash_locked_and_keeps_production_disabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            mapping, registry, manifest = self.make_case(root)
            output = root / "result.json"
            result = SUBJECT.attach_sources(mapping, registry, output)
            self.assertEqual(1, result["mapped_count"])
            self.assertFalse(result["production_enabled"])
            updated = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(
                "mapped_pending_user_acceptance",
                updated["source_reference_match"]["confirmation_status"],
            )
            self.assertNotIn(
                "source_reference_mapping_pending",
                updated["assembly_contract"]["production_blockers"],
            )
            self.assertTrue((manifest.parent / "source_reference.jpg").is_file())

    def test_mapping_is_idempotent_when_source_hash_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            mapping, registry, _ = self.make_case(root)
            SUBJECT.attach_sources(mapping, registry, root / "result1.json")
            result = SUBJECT.attach_sources(mapping, registry, root / "result2.json")
            self.assertEqual("already_present", result["results"][0]["copy_status"])


if __name__ == "__main__":
    unittest.main()
