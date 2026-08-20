import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PATCHER = load_module(
    "cc_animation_fbx_patcher",
    ROOT / "cc_patch_unreal_animation_fbx_ascii.py",
)
FINALIZER = load_module(
    "cc_p0_export_finalizer",
    ROOT / "cc_finalize_p0_animation_ue_export_v1.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_record(path: Path) -> dict:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


class P0AnimationUEExportTests(unittest.TestCase):
    def test_ascii_patcher_replaces_exact_47_bone_tokens(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.fbx"
            destination = root / "patched.fbx"
            report = root / "patch.json"
            source.write_text(
                "; FBX 7.4.0 project file\n"
                + "\n".join(PATCHER.SOURCE_TO_TARGET),
                encoding="utf-8",
            )
            result = PATCHER.patch_fbx(source, destination, report)
            self.assertEqual(47, result["mapping_count"])
            text = destination.read_text(encoding="utf-8")
            for target in PATCHER.SOURCE_TO_TARGET.values():
                self.assertIn(target, text)

    def make_export_fixture(self, root: Path):
        work_order = root / "work_order.json"
        work_order.write_text(
            json.dumps(
                {
                    "work_order_id": "work-order",
                    "unreal": {
                        "vendor_root": "/Game/Vendor",
                        "datamake_root": "/Game/DataMake",
                        "required_runtime_checks": ["skeleton_binding"],
                    },
                }
            ),
            encoding="utf-8",
        )
        actors = []
        motions = []
        for sex in ("female", "male"):
            actor_root = root / "actors" / sex
            reference_root = actor_root / "reference"
            motion_root = actor_root / "motions"
            fbm = reference_root / f"{sex}.fbm"
            textures = reference_root / "textures"
            motion_root.mkdir(parents=True)
            fbm.mkdir(parents=True)
            textures.mkdir(parents=True)
            (fbm / "texture.png").write_bytes(b"fbm")
            (textures / "texture.png").write_bytes(b"texture")
            fbx = reference_root / f"{sex}.fbx"
            sidecar = reference_root / f"{sex}.json"
            fbx.write_bytes(b"reference")
            sidecar.write_text("{}", encoding="utf-8")
            actors.append(
                {
                    "actor_binding_id": sex,
                    "character_id": sex,
                    "sex": sex,
                    "bodyfit_id": sex,
                    "appearance_recipe_id": sex,
                    "reference": {
                        "fbx": file_record(fbx),
                        "json": file_record(sidecar),
                        "fbm": {"path": str(fbm), "file_count": 1},
                        "textures": {
                            "path": str(textures),
                            "file_count": 1,
                        },
                    },
                }
            )
            for index in range(2):
                case_id = f"{sex}_{index}"
                motion = motion_root / f"{case_id}_UE5_ASCII.fbx"
                motion.write_text(
                    "; FBX 7.4.0 project file\n"
                    + "\n".join(PATCHER.SOURCE_TO_TARGET),
                    encoding="utf-8",
                )
                motions.append(
                    {
                        "actor_binding_id": sex,
                        "case_id": case_id,
                        "clip": {"length_frame": 10},
                        "fbx": file_record(motion),
                        "options": {"root_motion_policy": "in_place"},
                        "source_motion": {"path": f"{case_id}.rlmotion"},
                    }
                )
        report = {
            "status": "cc_export_complete_patch_pending",
            "success": True,
            "work_order": {
                "id": "work-order",
                "sha256": digest(work_order),
            },
            "actors": actors,
            "motions": motions,
        }
        (root / "p0_ue_runtime_cc_export.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        return work_order

    def test_finalizer_builds_two_actor_four_motion_manifest(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            work_order = self.make_export_fixture(root)
            result = FINALIZER.finalize_export(root, work_order)
            self.assertEqual("ready_for_ue_import", result["status"])
            self.assertEqual(2, len(result["actors"]))
            self.assertEqual(4, len(result["motions"]))
            self.assertTrue((root / "export_bundle_manifest.json").is_file())

    def test_finalizer_rejects_raw_animation_hash_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            work_order = self.make_export_fixture(root)
            motion = next((root / "actors").rglob("*_UE5_ASCII.fbx"))
            motion.write_text("drift", encoding="utf-8")
            with self.assertRaises(FINALIZER.P0ExportFinalizeError):
                FINALIZER.finalize_export(root, work_order)

    def test_frozen_config_matches_work_order_hash(self):
        config = json.loads(
            (ROOT / "cc_p0_animation_ue_export_20260818_v1.json").read_text(
                encoding="utf-8"
            )
        )
        payload = config["animation_p0_ue_export"]
        work_order = Path(payload["work_order_path"])
        self.assertEqual(payload["work_order_sha256"], digest(work_order))
        self.assertEqual(2, len(config["presets"]))


if __name__ == "__main__":
    unittest.main()
