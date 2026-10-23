"""CPU binding checks prevent empty-reference runs and stale image supervision."""
from copy import deepcopy
from itertools import combinations
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "lance")]
from prepare_datamake_reference_training import audit_dataset, prepare_profile, validate_reference_profile
from run_datamake_ddp_training import load_profile

BASE = ROOT / "configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json"


def row(index, refs=None):
    value = dict(sample_id=f"sample-{index}", chain_id=f"chain-{index}", target_round=1,
                 prompts=["Change the shirt."], video_paths=["source.mp4", "target.mp4"])
    if refs is not None:
        value["reference_images"] = refs
    return value


def dataset(directory, rows, shards=1):
    directory.mkdir(parents=True)
    paths = []
    for index in range(shards):
        path = directory / f"part-{index}.parquet"
        pq.write_table(pa.Table.from_pylist(rows[index::shards]), path)
        paths.append(str(path))
    config = {"D1": {"datamake_mixed_v2v_local": {
        "media_root": str(directory.parent), "vision_cond_type": ["vit", "vae_Nsplit"],
        "dataset_names": {"example": {"data_dir": paths}},
    }}}
    config_path = directory / "dataset.yaml"
    config_path.write_text(yaml.safe_dump(config))
    return config_path


class ReferencePreflightTest(unittest.TestCase):
    def test_mixed_optional_rows_and_relative_image_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGB", (20, 24), "red").save(root / "shirt.png")
            config = dataset(root / "data", [row(0, ["shirt.png"]), row(1), row(2, [None]), row(3, [str(root / "shirt.png")])])
            audit = audit_dataset(config)
            self.assertEqual((audit["rows"], audit["rows_with_current_reference"], audit["rows_without_reference"]), (4, 2, 2))
            self.assertEqual(audit["unique_images"], 1)
            self.assertEqual(audit["reference_occurrences"], 2)
            self.assertEqual(len(audit["files_sha256"]), 3)

    def test_no_reference_and_history_only_cannot_pass_training_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty = dataset(root / "plain", [row(0)])
            with self.assertRaisesRegex(ValueError, "no current-turn reference"):
                audit_dataset(empty)
            self.assertEqual(audit_dataset(empty, require_reference=False)["rows"], 1)
            Image.new("RGB", (16, 16)).save(root / "shirt.png")
            historical = row(0, ["shirt.png", None])
            historical.update(target_round=2, prompts=["Change shirt.", "Move camera."], video_paths=["a.mp4", "b.mp4", "c.mp4"])
            config = dataset(root / "historical", [historical])
            with self.assertRaisesRegex(ValueError, "no current-turn reference"):
                audit_dataset(config)

    def test_invalid_lengths_and_missing_corrupt_animated_images_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = (["missing.png"], ["broken.png"], ["animated.gif"], ["a.png", "b.png"])
            (root / "broken.png").write_text("not an image")
            Image.new("RGB", (16, 16), "red").save(root / "animated.gif", save_all=True,
                append_images=[Image.new("RGB", (16, 16), "blue")], duration=100)
            for index, refs in enumerate(cases):
                with self.subTest(refs=refs):
                    config = dataset(root / str(index), [row(index, refs)])
                    with self.assertRaises((ValueError, OSError)):
                        audit_dataset(config)

    def test_media_root_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGB", (16, 16)).save(root / "outside.png")
            config = dataset(root / "inside" / "data", [row(0, ["../outside.png"])])
            with self.assertRaisesRegex(ValueError, "escapes media_root"):
                audit_dataset(config)

    def test_image_condition_requires_vit_and_consistent_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGB", (16, 16)).save(root / "shirt.png")
            config = dataset(root / "no_vit", [row(0, ["shirt.png"])])
            value = yaml.safe_load(config.read_text())
            value["D1"]["datamake_mixed_v2v_local"]["vision_cond_type"] = ["vae_Nsplit"]
            config.write_text(yaml.safe_dump(value))
            with self.assertRaisesRegex(ValueError, "requires the ViT"):
                audit_dataset(config)
            invalid = row(0, ["shirt.png"])
            invalid["target_round"] = 2
            config = dataset(root / "wrong_round", [invalid])
            with self.assertRaisesRegex(ValueError, "target_round"):
                audit_dataset(config)

    def test_partial_reference_contract_cannot_silently_use_legacy_path(self):
        validate_reference_profile({"data": {}})
        with self.assertRaisesRegex(ValueError, "path/hash together"):
            validate_reference_profile({"data": {"reference_image_mode": "optional_single_vit_v1"}})

    def test_actual_launcher_rejects_every_incomplete_reference_binding(self):
        fields = {
            "reference_image_mode": "optional_single_vit_v1",
            "reference_image_audit": "/tmp/not-created-reference-audit.json",
            "reference_image_audit_sha256": "0" * 64,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for size in (1, 2):
                for selected in combinations(fields, size):
                    with self.subTest(fields=selected):
                        profile = json.loads(BASE.read_text())
                        profile["data"].update({key: fields[key] for key in selected})
                        profile["ddp"]["source_profile"] = str(root / "recipe.json")
                        recipe = deepcopy(profile)
                        recipe["run"]["run_name"] += "_recipe"
                        recipe["wandb"]["run_id"] += "-recipe"
                        (root / "recipe.json").write_text(json.dumps(recipe))
                        path = root / "profile.json"
                        path.write_text(json.dumps(profile))
                        with self.assertRaisesRegex(ValueError, "path/hash together"):
                            load_profile(path)

    def test_new_directory_name_cannot_reuse_base_wandb_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            collision = json.loads(BASE.read_text())["wandb"]["run_id"].replace("-", "_")
            with self.assertRaisesRegex(ValueError, "distinct W&B"):
                prepare_profile(BASE, {}, collision, Path(tmp) / "profile")

    def test_prepare_isolated_disabled_profile_and_detect_post_audit_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "shirt.png"
            Image.new("RGB", (16, 16), "red").save(image)
            image_link = root / "reference.png"
            image_link.symlink_to(image)
            media_alias = root / "media_alias"
            media_alias.symlink_to(root, target_is_directory=True)
            binding = deepcopy(json.loads(BASE.read_text())["data"])
            for split, count in (("train", 8), ("validation", 1), ("test", 1)):
                config = dataset(root / split, [row(i, [str(image_link)]) for i in range(count)], shards=count)
                payload = yaml.safe_load(config.read_text())
                payload["D1"]["datamake_mixed_v2v_local"]["media_root"] = str(media_alias)
                config.write_text(yaml.safe_dump(payload))
                binding[split + "_config"] = str(config)
                binding[split + "_prefixes"] = binding[split + "_chains"] = count
            binding["train_parquet_shards"] = 8
            binding["source_train_prefixes"] = 8
            for name in ("train_sampling_manifest", "split_manifest"):
                path = root / (name + ".json")
                path.write_text("{}")
                binding[name] = str(path)
            original = BASE.read_bytes()
            output = prepare_profile(BASE, binding, "unit_reference_test", root / "prepared")
            profile = load_profile(output)
            self.assertEqual(BASE.read_bytes(), original)
            self.assertFalse(profile["training_authorized"])
            self.assertEqual(profile["ddp"]["checkpoint_disabled_layers"], list(range(26, 36)))
            self.assertEqual(profile["checkpoint"]["completed_step_interval"], 50)
            self.assertEqual(profile["data"]["train_prefixes"], 8)
            validate_reference_profile(profile)
            other_root = root / "other_media"
            other_root.mkdir()
            media_alias.unlink()
            media_alias.symlink_to(other_root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "path changed since audit"):
                load_profile(output)
            media_alias.unlink()
            media_alias.symlink_to(root, target_is_directory=True)
            other = root / "other.png"
            Image.new("RGB", (16, 16), "blue").save(other)
            image_link.unlink()
            image_link.symlink_to(other)
            with self.assertRaisesRegex(ValueError, "path changed since audit"):
                load_profile(output)
            image_link.unlink()
            image_link.symlink_to(image)
            Image.new("RGB", (16, 16), "blue").save(image)
            with self.assertRaisesRegex(ValueError, "changed since audit"):
                load_profile(output)
            with self.assertRaises(FileExistsError):
                prepare_profile(BASE, binding, "unit_reference_test", root / "prepared")


if __name__ == "__main__":
    unittest.main()
