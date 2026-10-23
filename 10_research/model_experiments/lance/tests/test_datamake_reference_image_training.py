"""Reference conditions must not replace source/target or change null behavior."""
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lance"), str(Path(__file__).parent)]
from data.datamake_reference_image import normalize_reference_images, read_reference_tensor
from data.datasets_factory.datamake_online_rollout_turn import process_online_rollout_row
from data.datasets_factory.dataset_datamake_mixed_v2v_local import DataMakeMixedV2VLocalIterableDataset, CROP_POLICY
from train.datamake_pred_x0_prefix import make_history_row
from test_datamake_multiturn_dataset import make_dataset, write_videos


class ReferenceTrainingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_videos(self.root, 4)
        Image.new("RGB", (28, 28), "red").save(self.root / "ref.png")
        self.dataset = make_dataset(self.root)
        self.row = dict(sample_id="s", chain_id="c", target_round=3, context_length=3,
                        prompts=["red shirt", "rotate camera", "blue shirt"],
                        video_paths=[f"videos/{i}.mp4" for i in range(4)])

    def tearDown(self):
        self.tmp.cleanup()

    def process(self, row, online=False):
        random.seed(2026)
        torch.manual_seed(2026)
        args = (row, 0, 0, 0, 0, "fixture")
        result = process_online_rollout_row(self.dataset, *args) if online else self.dataset._process_row(*args)
        return result, random.getstate(), torch.get_rng_state()

    def assert_nested_equal(self, a, b):
        if isinstance(a, torch.Tensor):
            self.assertTrue(torch.equal(a, b))
        elif isinstance(a, dict):
            self.assertEqual(a.keys(), b.keys())
            for key in a: self.assert_nested_equal(a[key], b[key])
        elif isinstance(a, (list, tuple)):
            self.assertEqual(len(a), len(b))
            for x, y in zip(a, b): self.assert_nested_equal(x, y)
        else:
            self.assertEqual(a, b)

    def test_null_reference_is_exact_legacy_sample_and_rng(self):
        for online in (False, True):
            original = self.process(self.row, online)
            for value in (None, [None, None, None]):
                self.assert_nested_equal(original, self.process({**self.row, "reference_images": value}, online))

    def test_optional_references_attach_to_their_turn_and_only_vit(self):
        row = {**self.row, "reference_images": ["ref.png", None, "ref.png"]}
        for online in (False, True):
            sample, _, _ = self.process(row, online)
            plan = sample["sequence_plan"]
            types = [p["type"] for p in plan]
            self.assertEqual(types, ["vit_video", "vit_video", "vit_video", "vit_video",
                                     "vae_video", "vit_video", "vae_video", "text_template"])
            refs = [i for i, p in enumerate(plan) if p.get("datamake_edit_role") == "reference_image"]
            self.assertEqual(refs, [1, 5])
            self.assertEqual([p.get("datamake_edit_role") for p in plan if p["type"] == "vae_video"], ["source", "target"])
            self.assertEqual(sum(p["loss"] for p in plan), 1)
            for i in refs:
                t = sample["video_tensor_list"][i]
                self.assertEqual(t.shape[1], 2)
                self.assertTrue(torch.equal(t[:, 0], t[:, 1]))
            self.assertNotIn(1003, sample["text_ids_list"][0])  # no image_pad grid cursor

    def test_offline_and_online_path_samples_identical_with_references(self):
        row = {**self.row, "reference_images": ["ref.png", None, "ref.png"]}
        self.assert_nested_equal(self.process(row)[0], self.process(row, True)[0])

    def test_invalid_schema_is_not_silently_dropped(self):
        for refs in ([None], "ref.png", [["ref.png"], None, None], ["", None, None], [1, None, None], ["https://a/b", None, None]):
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                normalize_reference_images({**self.row, "reference_images": refs})
        with self.assertRaises(ValueError):
            normalize_reference_images({**self.row, "reference_image": "ref.png"})

    def test_missing_or_bad_image_fails_not_unconditioned_fallback(self):
        for path in ("missing.png", "videos/0.mp4", "../escape.png"):
            for online in (False, True):
                with self.subTest(path=path, online=online), self.assertRaises(RuntimeError):
                    self.process({**self.row, "reference_images": [path, None, None]}, online)

    def test_reference_cannot_silently_run_without_vit(self):
        self.dataset.vision_cond_type = ["vae_Nsplit"]
        with self.assertRaises(RuntimeError):
            self.process({**self.row, "reference_images": ["ref.png", None, None]})

    def test_reference_obeys_visual_dropout_and_leaves_no_marker(self):
        self.dataset.data_config["vit_cond_dropout_prob"] = 1.0
        row = {**self.row, "reference_images": ["ref.png", None, None]}
        for online in (False, True):
            sample, _, _ = self.process(row, online)
            self.assertFalse(any(p["type"] == "vit_video" for p in sample["sequence_plan"]))
            text = sample["text_ids_list"][0]
            marker = self.dataset.tokenizer("Reference image for this instruction")["input_ids"]
            self.assertFalse(any(text[i:i+len(marker)] == marker for i in range(len(text))))

    def test_legacy_chain_reader_refuses_reference_instead_of_losing_it(self):
        from train.datamake_online_rollout import _chain_from_row
        with self.assertRaisesRegex(ValueError, "Legacy chain-record"):
            _chain_from_row({**self.row, "reference_images": ["ref.png", None, None]})

    def test_inference_rejects_training_field_instead_of_ignoring_reference(self):
        from multiturn.conversation import Turn
        for field in ("reference_images", "reference_image_paths"):
            with self.assertRaisesRegex(ValueError, "singular reference_image"):
                Turn.from_dict({"role": "user", "action": "edit_video", field: ["ref.png"]})

    def test_images_use_pixels_and_rgb_not_video_reader(self):
        def transform(frames):
            return torch.from_numpy(np.asarray(frames[0]).copy()).permute(2, 0, 1).unsqueeze(1).float()
        a = read_reference_tensor(self.root / "ref.png", transform)
        Image.new("RGB", (28, 28), "blue").save(self.root / "blue.png")
        b = read_reference_tensor(self.root / "blue.png", transform)
        self.assertFalse(torch.equal(a, b))
        self.assertEqual(tuple(a.shape), (3, 2, 28, 28))
        self.assertTrue(torch.equal(a[:, 0], a[:, 1]))

    def test_animated_reference_is_rejected(self):
        frames = [Image.new("RGB", (28, 28), c) for c in ("red", "blue")]
        frames[0].save(self.root / "anim.gif", save_all=True, append_images=frames[1:])
        with self.assertRaisesRegex(ValueError, "single still"):
            read_reference_tensor(self.root / "anim.gif", self.dataset.vit_transform)

    def test_pred_x0_prefix_slices_references_without_mutating_input(self):
        row = {**self.row, "reference_images": ["ref.png", None, "ref.png"]}
        result = make_history_row(row, 2, [torch.zeros(3, 5, 16, 16)])
        self.assertEqual(result["reference_images"], ["ref.png", None])
        self.assertEqual(len(row["reference_images"]), 3)
        self.assertNotIn("reference_images", make_history_row(self.row, 1, []))

    def test_coinve_does_not_crop_reference_as_video(self):
        dataset = self.dataset
        del dataset.get_video_tensor
        dataset.__class__ = DataMakeMixedV2VLocalIterableDataset
        dataset.transform = lambda frames: torch.zeros(3, len(frames), 8, 8)
        dataset._read_decord = lambda reader, indices: list(indices)
        row = dict(sample_id="coinve-test", chain_id="coinve-test", target_round=1,
                   prompts=["change shirt"], video_paths=["videos/0.mp4", "videos/1.mp4"],
                   reference_images=["ref.png"], dataset_origin="coinve", crop_policy=CROP_POLICY,
                   crop_start_seconds=2.0, crop_duration_seconds=5.0)
        opened = []
        class Reader:
            def __init__(self, path, **kwargs): opened.append(path)
            def __len__(self): return 325
            def get_avg_fps(self): return 24.0
        with patch("data.datasets_factory.dataset_datamake_mixed_v2v_local.decord.VideoReader", Reader):
            sample, _, _ = self.process(row)
        self.assertEqual([t.shape[1] for t in sample["video_tensor_list"]], [62, 61, 2, 61])
        self.assertTrue(all(p.endswith(".mp4") for p in opened))
        self.assertFalse(hasattr(dataset, "_paired_window"))

    def test_real_packer_mixes_reference_and_plain_samples_without_cross_attention(self):
        from data.dataset_base_train import DataConfig, PackedDataset
        from data.data_utils import create_sparse_mask
        from train.datamake_packed_batch import trim_attention_padding

        # Only media decoding is replaced; role-aware assembly, patchification,
        # token indexing, packing and the attention predicate are production code.
        def decode(media, vision_stream, **kwargs):
            if vision_stream == "vit_video":
                return torch.zeros(3, 2, 28, 28), 1, None
            return torch.zeros(3, 5, 32, 32), 8, None
        self.dataset.get_video_tensor = decode
        self.dataset.vit_transform = lambda frames: torch.zeros(3, len(frames), 28, 28)
        self.dataset.vision_token_count = lambda tensor: 1
        row = dict(sample_id="one", chain_id="one", target_round=1,
                   prompts=["change shirt"], video_paths=["videos/0.mp4", "videos/1.mp4"])
        plain = self.process(row)[0]
        reference = self.process({**row, "sample_id": "two", "reference_images": ["ref.png"]})[0]
        config = DataConfig({}, text_cond_dropout_prob=0, vit_cond_dropout_prob=0,
                            vae_cond_dropout_prob=0, latent_patch_size=[1, 1, 1])
        packer = PackedDataset(
            config, self.dataset.tokenizer,
            {"bos_token_id": 1, "eos_token_id": 2, "start_of_image": 1001,
             "end_of_image": 1004, "image_token_id": 1002},
            local_rank=0, world_size=1, num_workers=1, use_flex=True,
            max_num_tokens=4096, image_token_id=1002)
        status = packer.pack_sequence(plain, packer.set_sequence_status())
        first_length = status["curr"]
        first_targets = list(status["mse_loss_indexes"])
        status = packer.pack_sequence(reference, status)
        packed = trim_attention_padding(packer.to_tensor(status))
        targets = packed["mse_loss_indexes"].tolist()
        self.assertEqual(len(first_targets), 8)
        self.assertEqual(len(targets), 16)
        self.assertEqual(packed["vae_edit_roles"], ["source", "target", "source", "target"])
        self.assertEqual(packed["packed_vae_token_indexes"].numel(), 32)
        self.assertEqual(packed["packed_vit_token_indexes"].numel(), 3)
        self.assertEqual(packed["sample_N_target"], [1, 1, 0])
        self.assertEqual(packed["sample_lens"][0], first_length)
        self.assertTrue(all(index < first_length for index in targets[:8]))
        self.assertTrue(all(index >= first_length for index in targets[8:]))
        self.assertFalse(set(targets) & set(packed["packed_vit_token_indexes"].tolist()))
        predicate = create_sparse_mask(
            packed["sample_lens"], packed["split_lens"],
            ["full" if mode == "full_noise" else mode for mode in packed["attn_modes"]], "cpu")
        left = torch.arange(first_length)
        right = torch.arange(first_length, packed["sequence_length"])
        zero = torch.tensor(0)
        self.assertFalse(predicate(zero, zero, left[:, None], right[None, :]).any())
        self.assertFalse(predicate(zero, zero, right[:, None], left[None, :]).any())


if __name__ == "__main__":
    unittest.main()
