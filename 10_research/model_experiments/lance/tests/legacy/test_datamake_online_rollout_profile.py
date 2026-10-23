from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import torch
from transformers import HfArgumentParser


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/run_datamake_online_rollout_lora_training.py"
SPEC = importlib.util.spec_from_file_location("online_rollout_launcher", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

LANCE_ROOT = ROOT / "lance"
sys.path.insert(0, str(LANCE_ROOT))
from config.config_factory import DataArguments, ModelArguments, TrainingArguments  # noqa: E402
from modeling.lance.lance import _build_forward_outputs  # noqa: E402
from train.datamake_online_rollout import OnlineRolloutArguments  # noqa: E402
from train.datamake_online_rollout_lora_train import (  # noqa: E402
    _run_profile_contract_check,
    predict_clean_latent_patches,
    validate_frozen_training_arguments,
)


def argument_value(command, name):
    index = command.index(name)
    return command[index + 1]


class OnlineRolloutProfileTest(unittest.TestCase):
    def write_profile_variant(self, *, status=None, training_authorized=None, mutate=None):
        profile = json.loads(MODULE.DEFAULT_PROFILE.read_text(encoding="utf-8"))
        if status is not None:
            profile["status"] = status
        if training_authorized is not None:
            profile["training_authorized"] = training_authorized
        if mutate is not None:
            mutate(profile)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            dir=MODULE.DEFAULT_PROFILE.parent,
            delete=False,
        ) as stream:
            json.dump(profile, stream)
            path = Path(stream.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def parse_training_arguments(self, command):
        arguments = command[
            command.index("train/datamake_online_rollout_lora_train.py") + 1 :
        ]
        return HfArgumentParser(
            (ModelArguments, DataArguments, TrainingArguments, OnlineRolloutArguments)
        ).parse_args_into_dataclasses(args=arguments)

    def test_default_forward_output_keeps_legacy_key_set(self):
        loss = torch.tensor(1.0)
        default = _build_forward_outputs(loss, None, None, 1)
        self.assertEqual(
            set(default), {"mse", "ce", "frame_mse", "total_mse_tokens"}
        )
        extended = _build_forward_outputs(
            loss,
            None,
            None,
            1,
            return_flow_intermediates=True,
            flow_noisy_target=loss,
            flow_pred_velocity=loss,
            flow_timesteps=loss,
        )
        self.assertEqual(
            set(extended) - set(default),
            {"flow_noisy_target", "flow_pred_velocity", "flow_timesteps"},
        )

    def test_one_step_x0_formula_reuses_flow_intermediates(self):
        clean = torch.tensor([[1.0, -2.0], [0.5, 3.0]])
        noise = torch.tensor([[4.0, 2.0], [-1.0, 5.0]])
        timesteps = torch.tensor([0.25, 0.8])
        noisy = (1 - timesteps[:, None]) * clean + timesteps[:, None] * noise
        predicted = predict_clean_latent_patches(
            {
                "flow_noisy_target": noisy,
                "flow_pred_velocity": noise - clean,
                "flow_timesteps": timesteps,
            }
        )
        torch.testing.assert_close(predicted, clean)
        self.assertFalse(predicted.requires_grad)

    def test_frozen_profile_and_executable_command_match_decisions(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE, verify_base_hash=False)
        command = MODULE.build_torchrun_command(
            profile, MODULE.DEFAULT_PROFILE, None, 29543
        )
        self.assertEqual(argument_value(command, "--nproc-per-node"), "4")
        self.assertEqual(argument_value(command, "--total_steps"), "1800")
        self.assertEqual(argument_value(command, "--warmup_steps"), "20")
        self.assertEqual(argument_value(command, "--lr"), "0.0001")
        self.assertEqual(argument_value(command, "--min_lr"), "1e-05")
        self.assertEqual(argument_value(command, "--ce_weight"), "0.0")
        self.assertEqual(argument_value(command, "--edit_region_weighting"), "False")
        self.assertEqual(argument_value(command, "--save_every"), "50")
        self.assertEqual(argument_value(command, "--keep_last_checkpoints"), "4")
        self.assertEqual(argument_value(command, "--datamake_gradient_accumulation_steps"), "2")
        self.assertEqual(argument_value(command, "--datamake_history_mode"), "one_step_x0_history")
        self.assertEqual(argument_value(command, "--datamake_rollout_diffusion_steps"), "0")
        self.assertEqual(argument_value(command, "--datamake_rollout_cfg_text_scale"), "1.0")
        self.assertEqual(argument_value(command, "--datamake_rollout_use_kv_cache"), "False")
        self.assertEqual(argument_value(command, "--datamake_lora_rank"), "64")
        self.assertEqual(argument_value(command, "--vit_type"), "qwen_2_5_vl_original")
        self.assertEqual(argument_value(command, "--max_num_frames"), "121")
        self.assertEqual(argument_value(command, "--max_latent_size"), "64")
        self.assertEqual(argument_value(command, "--freeze_vit_connector"), "False")
        latent_index = command.index("--latent_patch_size")
        self.assertEqual(command[latent_index + 1 : latent_index + 4], ["1", "1", "1"])
        self.assertEqual(argument_value(command, "--sharding_strategy"), "HYBRID_SHARD")
        self.assertEqual(argument_value(command, "--text_cond_dropout_prob"), "0.0")
        self.assertEqual(argument_value(command, "--vit_cond_dropout_prob"), "0.0")
        self.assertEqual(argument_value(command, "--vae_cond_dropout_prob"), "0.0")
        self.assertNotIn(
            "datamake_dialogue_stage2_r5x3_region_fullparam", " ".join(command)
        )

    def test_command_parses_without_unknown_or_duplicate_arguments(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE, verify_base_hash=False)
        command = MODULE.build_torchrun_command(
            profile, MODULE.DEFAULT_PROFILE, None, 29543
        )
        arguments = command[
            command.index("train/datamake_online_rollout_lora_train.py") + 1 :
        ]
        parsed = HfArgumentParser(
            (
                ModelArguments,
                DataArguments,
                TrainingArguments,
                OnlineRolloutArguments,
            )
        ).parse_args_into_dataclasses(args=arguments)
        self.assertEqual(parsed[1].data_seed, 2042)
        self.assertEqual(parsed[2].total_steps, 1800)
        self.assertFalse(parsed[3].datamake_smoke_mode)

    def test_smoke_uses_same_recipe_but_two_steps_and_offline_logging(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE, verify_base_hash=False)
        command = MODULE.build_torchrun_command(
            profile, MODULE.DEFAULT_PROFILE, None, 29543, smoke_steps=2
        )
        self.assertEqual(argument_value(command, "--total_steps"), "2")
        self.assertEqual(argument_value(command, "--datamake_smoke_mode"), "True")
        self.assertEqual(argument_value(command, "--wandb_offline"), "True")
        self.assertEqual(
            argument_value(command, "--wandb_name"),
            "datamake_dialogue_one_step_x0_lora_r64_4xh200_v3_smoke",
        )
        self.assertEqual(
            argument_value(command, "--wandb_runid"),
            "datamake-dialogue-one-step-x0-lora-r64-v3-smoke",
        )
        self.assertEqual(argument_value(command, "--save_every"), "0")
        self.assertEqual(argument_value(command, "--save_final_checkpoint"), "True")

    def test_resumed_smoke_keeps_run_identity_and_advances_target_step(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE, verify_base_hash=False)
        checkpoint = Path("/tmp/datamake-smoke/checkpoints/0000002")
        command = MODULE.build_torchrun_command(
            profile,
            MODULE.DEFAULT_PROFILE,
            checkpoint,
            29543,
            smoke_steps=3,
            smoke_label="resume3",
        )
        self.assertEqual(argument_value(command, "--total_steps"), "3")
        self.assertEqual(argument_value(command, "--resume_from"), str(checkpoint))
        self.assertEqual(
            argument_value(command, "--wandb_name"),
            "datamake_dialogue_one_step_x0_lora_r64_4xh200_v3_smoke_resume3",
        )
        self.assertEqual(
            argument_value(command, "--wandb_runid"),
            "datamake-dialogue-one-step-x0-lora-r64-v3-smoke-resume3",
        )
        self.assertEqual(argument_value(command, "--datamake_smoke_label"), "resume3")

    def test_training_entry_handles_pending_and_authorized_profile_states(self):
        pending_path = self.write_profile_variant(
            status="gpu_smoke_passed_formal_launch_pending_user_authorization",
            training_authorized=False,
        )
        pending_profile = MODULE.validate_profile(pending_path, verify_base_hash=False)
        formal = MODULE.build_torchrun_command(
            pending_profile, pending_path, None, 29543
        )
        model_args, data_args, training_args, online_args = self.parse_training_arguments(
            formal
        )
        with self.assertRaisesRegex(ValueError, "formal profile status"):
            _run_profile_contract_check(
                pending_path,
                model_args,
                data_args,
                online_args,
                training_args,
            )

        smoke = MODULE.build_torchrun_command(
            pending_profile,
            pending_path,
            None,
            29543,
            smoke_steps=3,
            smoke_label="continuous3",
        )
        model_args, data_args, training_args, online_args = self.parse_training_arguments(
            smoke
        )
        _run_profile_contract_check(
            pending_path,
            model_args,
            data_args,
            online_args,
            training_args,
        )

        authorized_path = self.write_profile_variant(
            status="training_authorized", training_authorized=True
        )
        authorized_profile = MODULE.validate_profile(
            authorized_path, verify_base_hash=False
        )
        formal = MODULE.build_torchrun_command(
            authorized_profile, authorized_path, None, 29543
        )
        model_args, data_args, training_args, online_args = self.parse_training_arguments(
            formal
        )
        _run_profile_contract_check(
            authorized_path,
            model_args,
            data_args,
            online_args,
            training_args,
        )

    def test_profile_rejects_timestep_shift_drift(self):
        profile_path = self.write_profile_variant(
            mutate=lambda profile: profile["rollout"].update(timestep_shift=1.0)
        )
        with self.assertRaisesRegex(ValueError, "rollout timestep shift"):
            MODULE.validate_profile(profile_path, verify_base_hash=False)

    def test_training_entry_rejects_direct_structural_drift(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE, verify_base_hash=False)
        command = MODULE.build_torchrun_command(
            profile, MODULE.DEFAULT_PROFILE, None, 29543, smoke_steps=2
        )
        arguments = command[
            command.index("train/datamake_online_rollout_lora_train.py") + 1 :
        ]
        model_args, data_args, training_args, online_args = HfArgumentParser(
            (ModelArguments, DataArguments, TrainingArguments, OnlineRolloutArguments)
        ).parse_args_into_dataclasses(args=arguments)
        model_args.max_num_frames = 57
        with self.assertRaisesRegex(ValueError, "maximum frames"):
            validate_frozen_training_arguments(
                model_args, data_args, training_args, online_args, world_size=4
            )
        model_args.max_num_frames = 121
        training_args.sharding_strategy = "FULL_SHARD"
        with self.assertRaisesRegex(ValueError, "FSDP sharding strategy"):
            validate_frozen_training_arguments(
                model_args, data_args, training_args, online_args, world_size=4
            )
        training_args.sharding_strategy = "HYBRID_SHARD"
        training_args.timestep_shift = 1.0
        with self.assertRaisesRegex(ValueError, "training timestep shift"):
            validate_frozen_training_arguments(
                model_args, data_args, training_args, online_args, world_size=4
            )


if __name__ == "__main__":
    unittest.main()
