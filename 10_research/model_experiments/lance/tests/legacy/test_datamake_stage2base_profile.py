"""Base-only ablation: same v3 recipe, separate Stage 2 base/run identity."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest

from test_datamake_online_rollout_profile import (
    MODULE,
    ROOT,
    DataArguments,
    HfArgumentParser,
    ModelArguments,
    OnlineRolloutArguments,
    TrainingArguments,
    _run_profile_contract_check,
    validate_frozen_training_arguments,
)


PROFILE = ROOT / "configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json"


class Stage2BaseProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = MODULE.read_json(MODULE.DEFAULT_PROFILE)
        cls.profile = MODULE.validate_profile(PROFILE, verify_base_hash=False)

    def test_only_base_and_run_metadata_change(self):
        for section in (
            "data", "lora", "freeze", "rollout", "loss", "condition_dropout",
            "optimization", "distributed", "checkpoint",
        ):
            self.assertEqual(self.profile[section], self.control[section], section)
        for section, excluded in (
            ("run", {"run_name"}),
            ("model", {"model_path", "model_safetensors_sha256"}),
            ("wandb", {"run_id", "tags"}),
            ("slurm", {"job_script"}),
        ):
            self.assertEqual(
                {k: v for k, v in self.profile[section].items() if k not in excluded},
                {k: v for k, v in self.control[section].items() if k not in excluded},
                section,
            )
        for path, digest in self.control["source"]["implementation_files"].items():
            self.assertEqual(self.profile["source"]["implementation_files"][path], digest)
        self.assertEqual(
            MODULE.sha256_file(MODULE.DEFAULT_PROFILE),
            self.profile["ablation"]["control_profile_sha256"],
        )

    def test_formal_command_uses_fresh_stage2_base_and_passes_trainer_contract(self):
        command = MODULE.build_torchrun_command(self.profile, PROFILE, None, 29543)
        self.assertNotIn("--resume_from", command)
        arguments = command[command.index("train/datamake_online_rollout_lora_train.py") + 1:]
        model, data, training, online = HfArgumentParser(
            (ModelArguments, DataArguments, TrainingArguments, OnlineRolloutArguments)
        ).parse_args_into_dataclasses(args=arguments)
        self.assertEqual(
            model.model_path,
            str(MODULE.workspace_path(self.profile["model"]["model_path"])),
        )
        self.assertIn("model_bases/datamake_dialogue_stage2_step3669", model.model_path)
        self.assertFalse(training.auto_resume)
        self.assertFalse(training.load_data_status)
        self.assertIsNone(training.resume_from)
        self.assertEqual(training.total_steps, 1800)
        _run_profile_contract_check(PROFILE, model, data, online, training)
        validate_frozen_training_arguments(model, data, training, online, world_size=4)

    def test_run_storage_and_wandb_are_separate(self):
        self.assertNotEqual(self.profile["run"]["run_name"], self.control["run"]["run_name"])
        self.assertNotEqual(self.profile["wandb"]["run_id"], self.control["wandb"]["run_id"])
        environment = MODULE.build_environment(self.profile)
        self.assertEqual(environment["WANDB_RUN_GROUP"], self.control["wandb"]["group"])
        self.assertIn("ablation-base-01-b", environment["WANDB_TAGS"])
        self.assertEqual(environment["WANDB_MODE"], "online")

    def test_stage2_checkpoint_has_same_lora_target_topology(self):
        spec = importlib.util.spec_from_file_location(
            "stage2_base_lora_inspector", ROOT / "scripts/inspect_datamake_generation_lora.py"
        )
        inspector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inspector)
        audit = inspector.inspect(
            MODULE.workspace_path(self.profile["model"]["model_path"]), 64, True
        )
        self.assertEqual(audit["target_module_count"], 256)
        self.assertEqual(audit["trainable_parameter_count"], 120412160)
        targets = [
            {k: v for k, v in target.items() if k != "lora_parameters"}
            for target in audit["targets"]
        ]
        signature = hashlib.sha256(
            json.dumps(targets, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertEqual(signature, self.profile["lora"]["target_signature_sha256"])

    def test_slurm_entry_selects_this_profile_and_cluster_limits(self):
        script = MODULE.workspace_path(self.profile["slurm"]["job_script"]).read_text()
        self.assertIn(PROFILE.name, script)
        self.assertNotIn("DATAMAKE_FORMAL_PROFILE", script)
        self.assertIn("#SBATCH --partition=testqueue", script)
        self.assertIn("#SBATCH --time=18:00:00", script)
        self.assertIn("#SBATCH --gres=gpu:h200:4", script)
        self.assertIn("outputs/slurm_logs/dm_lance_x0_s2base_%j.out", script)
        self.assertIn("outputs/slurm_logs/dm_lance_x0_s2base_%j.err", script)
        self.assertIn('RESUME_VALUE=${RESUME_FROM:-none}', script)


if __name__ == "__main__":
    unittest.main()
