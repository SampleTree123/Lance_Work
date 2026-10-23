"""CPU checks for inference cases and train-matched visual preprocessing."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lance"))
import run_datamake_lora_visual_sanity as sanity


def fake_row(parquet, sample_id, chain_id, target_round):
    return {
        "sample_id": f"{chain_id}_r{target_round}",
        "video_paths": [f"videos/{i}.mp4" for i in range(target_round + 1)],
        "prompts": [f"edit {i}" for i in range(1, target_round + 1)],
        "edit_axes": ["outfit_id"] * target_round,
    }


def fake_conversation(row, media):
    turns = []
    for index, prompt in enumerate(row["prompts"]):
        turns.append({"role": "user", "content": [{"type": "text", "value": prompt}]})
        if index < len(row["prompts"]) - 1:
            turns.append({"role": "assistant", "content": [{"type": "video", "value": f"gt{index + 1}"}]})
    turns[0]["content"].insert(0, {"type": "video", "value": "initial_source"})
    turns[-1]["action"] = "edit_video"
    return {"turns": turns, "system_prompt": None}


class VisualSanityTests(unittest.TestCase):
    def setUp(self):
        with patch.object(sanity, "select_row", side_effect=fake_row), patch.object(sanity, "build_conversation", side_effect=fake_conversation):
            self.cases = sanity.make_cases(Path("validation.parquet"))

    def test_rollout_has_only_initial_video_and_generates_all_turns(self):
        turns = self.cases[0]["conversation"]["turns"]
        self.assertEqual(len(turns), 3)
        self.assertTrue(all(t["role"] == "user" and t["action"] == "edit_video" for t in turns))
        videos = [item["value"] for turn in turns for item in turn["content"] if item["type"] == "video"]
        self.assertEqual(videos, ["initial_source"])

    def test_teacher_forced_generates_only_final_target(self):
        for case, expected_history in zip(self.cases[1:], (1, 2, 4)):
            turns = case["conversation"]["turns"]
            self.assertEqual(sum(t["role"] == "assistant" for t in turns), expected_history)
            self.assertEqual(sum(t.get("action") == "edit_video" for t in turns), 1)
            self.assertEqual(len(case["outputs"]), 1)

    def test_manifest_sources_follow_generated_outputs(self):
        outputs = self.cases[0]["outputs"]
        self.assertEqual(outputs[1]["actual_source"], outputs[0]["output"])
        self.assertEqual(outputs[2]["actual_source"], outputs[1]["output"])
        self.assertEqual(sum(len(c["outputs"]) for c in self.cases), 6)
        for case in self.cases[1:]:
            item = case["outputs"][0]
            self.assertEqual(item["actual_source"], item["gt_source"])


class TrainingPreprocessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = [
            json.loads((ROOT / "configs" / name).read_text())
            for name in (
                "datamake_dialogue_one_step_x0_lora_r64_v3.json",
                "datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json",
            )
        ]
        cls.settings = sanity.load_training_preprocessing({
            "dataset_config": str(sanity.ROOT / cls.profiles[0]["data"]["train_config"])
        })

    def make_builder(self):
        from multiturn.sequence_builder import MultiTurnSequenceBuilder

        # Real inference builder, but no model, tokenizer or CUDA is needed
        # to exercise its preprocessing. Begin with the old high-res preset.
        return MultiTurnSequenceBuilder(
            tokenizer=None, data_args=None, model_args=None, training_args=None,
            new_token_ids={
                "bos_token_id": 1, "eos_token_id": 2,
                "start_of_image": 3, "end_of_image": 4, "image_token_id": 5,
            },
            dataset_config=SimpleNamespace(resolution="video_480p", max_duration=6),
        )

    def test_both_bases_use_the_same_training_yaml_settings(self):
        for profile in self.profiles:
            settings = sanity.load_training_preprocessing({
                "dataset_config": str(sanity.ROOT / profile["data"]["train_config"])
            })
            self.assertEqual(settings, self.settings)
            self.assertEqual(settings["video_transform_args"]["resolution"], 480)
            self.assertEqual(settings["vit_video_transform_args"]["resolution"], 448)
            self.assertEqual(settings["dataset_config_sha256"], profile["data"]["train_config_sha256"])

    def test_real_builder_replaces_both_resolution_presets(self):
        builder = self.make_builder()
        image = Image.new("RGB", (2560, 1440), color=(37, 113, 211))
        self.assertEqual(tuple(builder.transform([image]).shape), (3, 1, 480, 848))
        self.assertEqual(tuple(builder.vit_transform([image]).shape), (3, 1, 448, 812))
        sanity.apply_training_preprocessing(builder, self.settings)
        for input_size in ((2560, 1440), (624, 352)):
            frame = Image.new("RGB", input_size, color=(37, 113, 211))
            with self.subTest(input_size=input_size):
                self.assertEqual(tuple(builder.transform([frame]).shape), (3, 1, 352, 624))
                self.assertEqual(tuple(builder.vit_transform([frame]).shape), (3, 1, 336, 588))

    def test_pixels_and_normalization_match_training_transforms(self):
        from data.transforms import VideoTransform

        builder = self.make_builder()
        sanity.apply_training_preprocessing(builder, self.settings)
        # A non-uniform image catches crop/resize differences, not only shape.
        pixels = torch.arange(144 * 256 * 3).remainder(256).to(torch.uint8)
        frame = Image.fromarray(pixels.reshape(144, 256, 3).numpy())
        for name, field in (("transform", "video_transform_args"), ("vit_transform", "vit_video_transform_args")):
            expected = VideoTransform(**self.settings[field])([frame])
            actual = getattr(builder, name)([frame])
            torch.testing.assert_close(actual, expected, rtol=0, atol=0)

    def test_sampling_matches_gt_and_generated_history_frame_counts(self):
        builder = self.make_builder()
        sanity.apply_training_preprocessing(builder, self.settings)
        gt = builder.frame_sampler({"clip_indices": [(0, 150)], "fps": 30})
        history = builder.frame_sampler({"clip_indices": [(0, 57)], "fps": 12})
        self.assertEqual(len(gt.indices), 57)
        self.assertEqual(history.indices, list(range(57)))
        self.assertEqual(builder.frame_sampler.sample_fps, 12)
        self.assertEqual(builder.frame_sampler.max_duration, 6)


if __name__ == "__main__":
    unittest.main()
