"""CPU recipe checks; GPU runtime validation is a separate startup gate."""
import hashlib
import json
from pathlib import Path
import unittest

LANCE = Path(__file__).resolve().parents[1]
ROOT = LANCE.parents[2]


def profile(name):
    return json.loads((LANCE / "configs" / name).read_text())


class Stage2LoRAPairProfilesTest(unittest.TestCase):
    def setUp(self):
        self.stage2 = profile("datamake_dialogue_stage2_r5x3_region_v1.json")
        self.both = profile("datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1.json")
        self.optimized = profile("datamake_stage6_padding_both_20260910.json")

    def test_optimized_joint_template_preserves_recipe_and_checkpoint_policy(self):
        for key in ("data", "model", "optimization", "history", "lora", "freeze", "checkpoint"):
            self.assertEqual(self.optimized[key], self.both[key], key)
        self.assertEqual(self.optimized["distributed"]["backend"], "ddp")
        self.assertFalse(self.optimized["freeze"]["understanding_adapters"])
        self.assertEqual(self.optimized["checkpoint"]["completed_step_interval"], 100)
        self.assertEqual(self.optimized["ddp"]["checkpoint_disabled_layers"], list(range(26, 36)))
        self.assertEqual(self.optimized["ddp"]["vae_cache_policy"], "retain")
        self.assertEqual(self.optimized["ddp"]["attention_padding"], "minimal")
        self.assertNotEqual(self.optimized["run"]["run_name"], self.both["run"]["run_name"])

    def test_stage2_recipe_preserved_except_explicit_user_overrides(self):
        for arm in (self.both,):
            for key in ("data", "distributed"):
                self.assertEqual(arm[key], self.stage2[key])
            optimization = dict(self.stage2["optimization"])
            optimization["learning_rate"] = 3e-4
            optimization["minimum_learning_rate"] = 3e-5
            self.assertEqual(arm["optimization"], optimization)
            actual, expected = dict(arm["run"]), dict(self.stage2["run"])
            actual.pop("run_name")
            expected.pop("run_name")
            expected.update(total_steps=3000, global_batch_size=32,
                            gradient_accumulation_steps=8)
            self.assertEqual(actual, expected)
            for key, value in self.stage2["model"].items():
                if key not in {"model_path", "use_lora", "train_lance_core"}:
                    self.assertEqual(arm["model"][key], value, key)

    def test_accumulation_and_optimizer_step_budget(self):
        for arm in (self.both,):
            run, distributed = arm["run"], arm["distributed"]
            micro_batch = (distributed["nodes"] * distributed["gpus_per_node"]
                           * run["per_rank_batch_size"])
            self.assertEqual(micro_batch, 4)
            self.assertEqual(run["gradient_accumulation_steps"], 8)
            self.assertEqual(run["global_batch_size"],
                             micro_batch * run["gradient_accumulation_steps"])
            self.assertEqual(run["total_steps"], 3000)
            self.assertEqual(run["global_batch_size"] * run["total_steps"], 96000)

    def test_both_arms_start_from_official_base_with_fresh_adapters(self):
        base = "10_research/model_experiments/lance/models/Lance/Lance_3B_Video"
        for arm in (self.both,):
            self.assertEqual(arm["model"]["model_path"], base)
            self.assertEqual(arm["initialization"]["base_model_path"], base)
            self.assertEqual(arm["initialization"]["status"],
                             "confirmed_official_pretrained")
            self.assertTrue(arm["initialization"]["fresh_lora"])
            self.assertFalse(arm["initialization"]["load_previous_adapter"])
            self.assertFalse(arm["initialization"]["load_previous_optimizer"])
        self.assertTrue((ROOT / base / "model.safetensors").is_file())

    def test_teacher_forced_history_and_parameter_only_freezing(self):
        for arm in (self.both,):
            self.assertEqual(arm["history"]["mode"], "teacher_forced")
            self.assertFalse(arm["history"]["online_rollout"])
            self.assertFalse(arm["history"]["one_step_x0_history"])
            self.assertTrue(arm["freeze"]["all_base_parameters"])
            self.assertFalse(arm["freeze"]["understanding_activation_detach"])
            self.assertEqual(arm["lora"]["rank"], 64)
            self.assertEqual(arm["lora"]["alpha"], 64.0)

    def test_checkpoint_every_100_updates_keeps_latest_four(self):
        for arm in (self.both,):
            for key, value in self.stage2["checkpoint"].items():
                if key not in ("require_full_state", "completed_step_interval", "keep_last_complete"):
                    self.assertEqual(arm["checkpoint"][key], value, key)
            self.assertEqual(arm["checkpoint"]["completed_step_interval"], 100)
            self.assertEqual(arm["checkpoint"]["keep_last_complete"], 4)
            self.assertTrue(arm["checkpoint"]["require_complete_resume_state"])
            self.assertEqual(
                arm["checkpoint"]["weight_storage"],
                "adapter_only_with_one_shared_immutable_base",
            )

    def test_fresh_restart_uses_separate_output_and_wandb_identity(self):
        for arm in (self.both,):
            self.assertTrue(arm["run"]["run_name"].endswith("_restart1"))
            self.assertTrue(arm["wandb"]["run_id"].endswith("-restart1"))
            self.assertFalse(arm["initialization"]["load_previous_adapter"])
            self.assertFalse(arm["initialization"]["load_previous_optimizer"])

    def test_retained_input_files_match_frozen_hashes(self):
        data = self.both["data"]
        for key in (
            "split_manifest", "train_sampling_manifest",
            "train_config", "validation_config", "test_config",
        ):
            path = ROOT / data[key]
            self.assertTrue(path.is_file(), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), data[key + "_sha256"])

    def test_common_base_and_topology_arithmetic(self):
        self.assertEqual(self.both["initialization"], self.optimized["initialization"])
        for arm in (self.both,):
            audit = arm["lora"]["architecture_audit"]
            self.assertEqual(audit["all_branch_modules"],
                             audit["generation_modules"] + audit["understanding_modules"])
            self.assertEqual(audit["all_branch_r64_parameters"],
                             audit["generation_r64_parameters"] + audit["understanding_r64_parameters"])


if __name__ == "__main__":
    unittest.main()
