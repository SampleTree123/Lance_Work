"""History isolation, held-out selection and complete-chain alignment (CPU)."""
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_datamake_chain_review as prepare
import build_datamake_chain_review as review
import run_datamake_lora_visual_sanity as runner
import datamake_coinve_review_media as coinve_media


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ChainReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        row = {"chain_id": "new_chain", "sample_id": "sample3", "target_round": 3,
               "dataset_origin": "ue_synthetic", "prompts": ["edit <one>", "edit two", "edit three"],
               "edit_axes": ["camera_id", "action_id", "outfit_id"], "turn_ids": ["t1", "t2", "t3"],
               "video_paths": [f"gt{i}.mp4" for i in range(4)]}
        for name in row["video_paths"]:
            (self.root / name).write_bytes(name.encode())
        self.suite = {"media_root": str(self.root), "chains": [row], "inference": {
            "diffusion_steps": 30, "cfg_text_scale": 1., "noise_seed": 42, "timestep_shift": 3.5}}
        self.cases = prepare.make_cases(self.suite)

    def test_gt_prefixes_generate_every_round_without_generated_history(self):
        cases = [c for c in self.cases if c["mode"] == "teacher_forced"]
        self.assertEqual([c["outputs"][0]["round"] for c in cases], [1, 2, 3])
        for round_no, case in enumerate(cases, 1):
            turns = case["conversation"]["turns"]
            self.assertEqual(sum(t.get("action") == "edit_video" for t in turns), 1)
            history = [t["content"][0]["value"] for t in turns if t["role"] == "assistant"]
            self.assertEqual(history, [str(self.root / f"gt{i}.mp4") for i in range(1, round_no)])
            self.assertEqual(case["outputs"][0]["actual_source"], str(self.root / f"gt{round_no - 1}.mp4"))
            self.assertNotIn(str(self.root / f"gt{round_no}.mp4"), json.dumps(turns))

    def test_rollout_only_initial_source_and_all_prompts(self):
        case = self.cases[-1]
        turns = case["conversation"]["turns"]
        self.assertTrue(all(t["role"] == "user" and t["action"] == "edit_video" for t in turns))
        videos = [x["value"] for t in turns for x in t["content"] if x["type"] == "video"]
        self.assertEqual(videos, [str(self.root / "gt0.mp4")])
        for previous, current in zip(case["outputs"], case["outputs"][1:]):
            self.assertEqual(current["actual_source"], previous["output"])

    def test_selection_uses_max_prefix_and_excludes_prior_chains(self):
        rows = []
        for n in (3, 4, 5):
            for k in range(1, n + 1):
                rows.append({**self.suite["chains"][0], "chain_id": f"chain{n}", "target_round": k})
        rows.append({**rows[0], "chain_id": "old_chain", "target_round": 3})
        selected = prepare.select_chains(rows, {"old_chain"}, 42)
        self.assertEqual([r["chain_id"] for r in selected], ["chain3", "chain4", "chain5"])
        self.assertEqual(selected, prepare.select_chains(list(reversed(rows)), {"old_chain"}, 42))

    def test_page_has_four_aligned_rows_and_explicit_preview(self):
        run = self.root / "review"
        run.mkdir()
        manifest = {"status": "prepared", "chain_suite": self.suite, "cases": self.cases}
        with patch.object(review, "video_check", return_value={"decoded_frames": 57}):
            audit = review.build_page(run, manifest)
        html = (run / "index.html").read_text()
        tags = Tags(html).tags
        self.assertEqual([a["data-mode"] for t, a in tags if "data-mode" in a], ["teacher_forced", "autoregressive"])
        self.assertEqual([a["data-kind"] for t, a in tags if t == "tr"], ["inference", "ground_truth"] * 2)
        self.assertEqual(sum(a.get("class") == "video-cell" for t, a in tags), 16)
        self.assertIn("edit &lt;one&gt;", html)
        self.assertIn("尚未推理", html)
        self.assertEqual(audit["status"], "prepared")
        self.assertTrue(all(p.is_symlink() for p in (run / "references").iterdir()))
        with patch.object(review, "video_check", return_value={}):
            review.build_page(run, manifest, copy_media=True)
        self.assertTrue(all(not p.is_symlink() for p in (run / "references").iterdir()))

    def test_missing_or_mismatched_results_rejected(self):
        manifest = {"status": "generated", "completed_steps": 350, "chain_suite": self.suite, "cases": self.cases}
        broken = copy.deepcopy(manifest)
        broken["cases"][-1]["outputs"][1]["prompt"] = "different prompt"
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            review.grouped_outputs(broken)
        run = self.root / "generated"
        run.mkdir()
        with patch.object(review, "video_check", return_value={}):
            with self.assertRaises(FileNotFoundError):
                review.build_page(run, manifest)
        for case in self.cases:
            for item in case["outputs"]:
                path = run / item["output"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(item["output"].encode())
        with patch.object(review, "video_check", return_value={}):
            audit = review.build_page(run, manifest)
        self.assertEqual(len(audit["media"]), 10)  # four GT endpoints + six outputs
        self.assertNotIn("待推理", (run / "index.html").read_text())

    def test_mixed_training_preprocessing_and_hash_check(self):
        path = self.root / "dataset.yaml"
        path.write_text('D1:\n  datamake_mixed_v2v_local:\n    video_transform_args: {resolution: 480}\n    vit_video_transform_args: {resolution: 448}\n    video_frame_sampler_args: {type: multi_clips}\n')
        settings = runner.load_training_preprocessing({"dataset_config": str(path)})
        self.assertEqual(settings["video_transform_args"]["resolution"], 480)
        with self.assertRaisesRegex(ValueError, "changed"):
            runner.load_training_preprocessing({"dataset_config": str(path), "dataset_config_sha256": "bad"})

    def add_real_case(self):
        row = {**self.suite["chains"][0], "sample_id": "coinve-example", "chain_id": "coinve-example",
               "target_round": 1, "dataset_origin": "coinve", "prompts": ["1. Add an object.\n2. Replace the background."],
               "video_paths": [str(self.root / "gt0.mp4"), str(self.root / "gt1.mp4")],
               "crop_policy": "paired_absolute_5s_12fps_kn1_fixed_v1", "crop_start_seconds": 1.25,
               "crop_duration_seconds": 5.0}
        self.suite["real_cases"] = [row]
        self.suite["real_media_sha256"] = {p: "hash" for p in row["video_paths"]}
        return prepare.make_cases(self.suite)[-1]

    def test_real_case_is_once_and_target_is_not_input(self):
        case = self.add_real_case()
        self.assertEqual(case["mode"], "single_turn")
        self.assertEqual(len(case["outputs"]), 1)
        turns = case["conversation"]["turns"]
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["content"][1]["value"], self.suite["real_cases"][0]["prompts"][0])
        self.assertNotIn("gt1.mp4", json.dumps(turns))
        self.assertEqual(case["paired_crop"]["start_seconds"], 1.25)

    def test_scoped_real_preprocessing_61_62_and_restoration_on_failure(self):
        import torch
        case = self.add_real_case()
        original = lambda *args, **kwargs: "original"
        transform = lambda frames: torch.arange(61).view(1, 61, 1, 1).expand(3, -1, 2, 2)
        builder = SimpleNamespace(get_video_tensor_online=original, transform=transform, vit_transform=transform)
        with patch.object(coinve_media, "sampled_frames", return_value=([None] * 61, {"indices": [9] * 61})) as decode:
            with self.assertRaisesRegex(RuntimeError, "generation failed"):
                with coinve_media.paired_input(builder, case):
                    vae = builder.get_video_tensor_online(case["paired_crop"]["path"], "vae_video", element_dtype="video")
                    vit = builder.get_video_tensor_online(case["paired_crop"]["path"], "vit_video", element_dtype="video")
                    self.assertEqual(vae.shape[1], 61)
                    self.assertEqual(vit.shape[1], 62)
                    self.assertTrue(torch.equal(vit[:, -1], vit[:, -2]))
                    with self.assertRaisesRegex(ValueError, "only its source"):
                        builder.get_video_tensor_online(case["outputs"][0]["gt_target"], "vae_video", element_dtype="video")
                    raise RuntimeError("generation failed")
            self.assertEqual(decode.call_count, 1)
        self.assertIs(builder.get_video_tensor_online, original)

    def test_real_section_three_videos_one_placeholder_and_single_prompt(self):
        self.add_real_case()
        run = self.root / "real_review"
        run.mkdir()
        manifest = {"status": "prepared", "chain_suite": self.suite, "cases": prepare.make_cases(self.suite)}
        def proxy(path, crop, run, digest):
            dest = run / "references" / path.name
            dest.write_bytes(b"proxy")
            return dest, {"sampled_frames": 61}
        with patch.object(coinve_media, "sampled_preview", side_effect=proxy), patch.object(review, "video_check", return_value={}):
            review.build_page(run, manifest)
        html = (run / "index.html").read_text()
        real = html.split('<article data-origin="coinve">')[1].split('</article>')[0]
        self.assertEqual(real.count('<video '), 2)
        self.assertEqual(real.count('class="placeholder"'), 1)
        self.assertIn("我们的模型输出", real)
        self.assertIn("真值 · Target", real)
        self.assertEqual(real.count("Add an object"), 1)
        self.assertNotIn("teacher_forced", real)


if __name__ == "__main__":
    unittest.main()
