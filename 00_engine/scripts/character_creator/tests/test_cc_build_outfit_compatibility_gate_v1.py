from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "cc_build_outfit_compatibility_gate_v1.py"
)
SPEC = importlib.util.spec_from_file_location("cc_outfit_gate_test", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class OutfitCompatibilityGateTests(unittest.TestCase):
    def test_locked_bundle_preserves_confirmed_application_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            family_path = Path(temp_dir) / "outfit_family.json"
            relative_paths = [
                "Full-body/suit.ccCloth",
                "Shoes/boots.ccShoes",
                "_Accessories-Pending/gloves.ccGloves",
                "_Accessories-Pending/harness.ccCloth",
            ]
            records = []
            required_assets = []
            for index, relative_path in enumerate(relative_paths):
                path = family_path.parent / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative_path.encode("utf-8"))
                asset_id = f"asset.{index}"
                required_assets.append(asset_id)
                records.append(
                    {
                        "asset_id": asset_id,
                        "display_name": path.stem,
                        "path": relative_path,
                        "slot": (
                            "full_body"
                            if index == 0
                            else "shoes"
                            if index == 1
                            else "family_accessory"
                        ),
                        "size_bytes": path.stat().st_size,
                        "sha256": MODULE.sha256_file(path),
                    }
                )

            document = {
                "family_id": "male.order_sensitive_bundle",
                "display_name": "Order Sensitive Bundle",
                "sex": "male",
                "assembly_mode": "locked_bundle",
                "assets": records,
                "assembly": {
                    "bundle": {
                        "bundle_id": "default",
                        "required_assets": required_assets,
                    }
                },
                "footwear_policy": {
                    "mode": "native_pool",
                    "allow_barefoot": False,
                },
            }

            looks = MODULE.representative_looks(
                family_path=family_path,
                document=document,
                inventory={},
                shoes_by_id={},
                seed=1,
            )

            self.assertEqual(
                required_assets,
                [asset["asset_id"] for asset in looks[0]["selected_assets"]],
            )

    def test_ccgloves_uses_byte_identical_registered_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "gloves.ccGloves"
            alias = root / "gloves.ccCloth"
            source.write_bytes(b"byte-identical-glove-payload")
            alias.write_bytes(source.read_bytes())
            digest = MODULE.sha256_file(source)
            registry_path = root / "registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "registry_id": "test_registry",
                        "policy": {
                            "byte_identity_required": True,
                            "source_assets_remain_immutable": True,
                            "allowed_transform": (
                                "extension_dispatch_alias_only"
                            ),
                        },
                        "aliases": [
                            {
                                "alias_id": "test_glove_alias",
                                "source": {
                                    "path": str(source),
                                    "size_bytes": source.stat().st_size,
                                    "sha256": digest,
                                },
                                "alias": {
                                    "path": str(alias),
                                    "size_bytes": alias.stat().st_size,
                                    "sha256": digest,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            aliases, registry = MODULE.load_compatibility_alias_registry(
                registry_path
            )
            resolved, transform = MODULE.resolve_compatibility_alias(
                source,
                {
                    "size_bytes": source.stat().st_size,
                    "sha256": digest,
                },
                aliases,
            )

            self.assertEqual(alias.resolve(), resolved)
            self.assertEqual("test_registry", registry["registry_id"])
            self.assertEqual("test_glove_alias", transform["alias_id"])
            self.assertTrue(transform["byte_identity_verified"])

    def test_ccgloves_without_registered_alias_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "gloves.ccGloves"
            source.write_bytes(b"unsupported-loader-extension")
            with self.assertRaises(MODULE.OutfitGateError):
                MODULE.resolve_compatibility_alias(
                    source,
                    {
                        "size_bytes": source.stat().st_size,
                        "sha256": MODULE.sha256_file(source),
                    },
                    {},
                )


if __name__ == "__main__":
    unittest.main()
