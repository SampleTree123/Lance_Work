from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch
from transformers import HfArgumentParser


SCRIPT = (
    Path(__file__).parents[1]
    / "scripts"
    / "run_datamake_formal_training.py"
)
SPEC = importlib.util.spec_from_file_location("datamake_formal_training", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

STAGE2_PROFILE = (
    Path(__file__).parents[1]
    / "configs"
    / "datamake_dialogue_stage2_r5x3_region_v1.json"
)

LANCE_ROOT = Path(__file__).parents[1] / "lance"
sys.path.insert(0, str(LANCE_ROOT))
from train.train_utils import build_lr_scheduler  # noqa: E402
from config.config_factory import (  # noqa: E402
    DataArguments,
    ModelArguments,
    TrainingArguments,
)


def argument_value(command, name):
    index = command.index(name)
    return command[index + 1]


def write_dummy_checkpoint(root: Path, step: int, shards: int = 4) -> Path:
    checkpoint = root / f"{step:07d}"
    checkpoint.mkdir(parents=True)
    required = [
        "model.safetensors",
        "scheduler.pt",
        "data_status.pt",
        *[f"optimizer.{index:05d}-of-{shards:05d}.pt" for index in range(shards)],
    ]
    for filename in required:
        (checkpoint / filename).write_bytes(filename.encode("ascii"))
    state = {
        "checkpoint_format_version": 1,
        "checkpoint_name": f"{step:07d}",
        "completed_steps": step,
        "next_step": step,
        "optimizer_shards": shards,
        "world_size": 4,
    }
    (checkpoint / "trainer_state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    marker = {
        **state,
        "status": "complete",
        "required_artifact_sizes": {
            filename: (checkpoint / filename).stat().st_size for filename in required
        },
    }
    (checkpoint / "checkpoint_complete.json").write_text(
        json.dumps(marker), encoding="utf-8"
    )
    return checkpoint


@contextmanager
def validated_archived_stage2_profile():
    """Validate the frozen Stage 2 recipe without requiring retired weights."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        model_dir = root / "historical_stage1_model"
        model_dir.mkdir()
        profile_path = root / STAGE2_PROFILE.name
        profile_payload = json.loads(STAGE2_PROFILE.read_text(encoding="utf-8"))
        profile_payload["model"]["model_path"] = str(model_dir)
        profile_path.write_text(json.dumps(profile_payload), encoding="utf-8")
        yield MODULE.validate_profile(profile_path)


class FormalTrainingProfileTest(unittest.TestCase):
    def test_slurm_script_matches_profile_and_has_no_termination_save(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE)
        slurm_path = (
            Path(__file__).parents[1]
            / "jobs"
            / "datamake_dialogue_first_batch_v1.sbatch"
        )
        text = slurm_path.read_text(encoding="utf-8")

        self.assertIn(
            f"#SBATCH --partition={profile['slurm']['partition']}", text
        )
        self.assertIn(f"#SBATCH -A {profile['slurm']['account']}", text)
        self.assertIn(f"#SBATCH --qos={profile['slurm']['qos']}", text)
        self.assertIn(
            f"#SBATCH --gres=gpu:h200:{profile['distributed']['gpus_per_node']}",
            text,
        )
        self.assertIn(f"#SBATCH --time={profile['slurm']['time_limit']}", text)
        self.assertIn("#SBATCH --output=/home/users/astar/cfar/stuchengyou/", text)
        self.assertIn("#SBATCH --error=/home/users/astar/cfar/stuchengyou/", text)
        self.assertEqual(text.count("outputs/slurm_logs/"), 4)
        self.assertIn("source ~/.init.sh", text)
        self.assertIn("conda activate \"$LANCE_ENV\"", text)
        self.assertIn(
            "unset HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY", text
        )
        self.assertIn(
            "unset http_proxy https_proxy all_proxy no_proxy", text
        )
        self.assertNotIn("#SBATCH --signal", text)
        self.assertNotIn("USR1", text)
        self.assertNotIn("CUDA_VISIBLE_DEVICES=", text)

    def test_wandb_preflight_removes_proxies_and_returns_identity(self):
        profile = {
            "wandb": {
                "entity": "expected-entity",
                "project": "datamake_lance",
            }
        }
        completed = SimpleNamespace(
            returncode=0,
            stdout='{"username": "xingkeshuo", "entity": "expected-entity"}\n',
            stderr="",
        )
        proxy_env = {
            "HTTP_PROXY": "http://127.0.0.1:27890",
            "https_proxy": "http://127.0.0.1:27890",
        }
        with patch.dict(MODULE.os.environ, proxy_env, clear=True), patch.object(
            MODULE.subprocess, "run", return_value=completed
        ) as run_mock:
            identity = MODULE.wandb_online_preflight(profile, timeout_seconds=7)

        child_env = run_mock.call_args.kwargs["env"]
        self.assertNotIn("HTTP_PROXY", child_env)
        self.assertNotIn("https_proxy", child_env)
        self.assertEqual(run_mock.call_args.kwargs["timeout"], 7)
        self.assertEqual(identity["username"], "xingkeshuo")
        self.assertEqual(identity["entity"], "expected-entity")

    def test_wandb_preflight_timeout_is_a_hard_failure(self):
        profile = {
            "wandb": {
                "entity": "expected-entity",
                "project": "datamake_lance",
            }
        }
        timeout = MODULE.subprocess.TimeoutExpired(["python"], 5)
        with patch.object(MODULE.subprocess, "run", side_effect=timeout):
            with self.assertRaisesRegex(RuntimeError, "timed out after 5 seconds"):
                MODULE.wandb_online_preflight(profile, timeout_seconds=5)

    def test_training_environment_does_not_restore_proxies(self):
        profile = {
            "wandb": {
                "entity": "expected-entity",
                "project": "datamake_lance",
                "run_id": "run-id",
                "group": "group",
                "job_type": "formal-train",
                "tags": ["dialogue"],
            }
        }
        with patch.dict(
            MODULE.os.environ,
            {"ALL_PROXY": "socks5://127.0.0.1:27890"},
            clear=True,
        ):
            env = MODULE.build_environment(profile)

        self.assertNotIn("ALL_PROXY", env)
        self.assertEqual(env["WANDB_INIT_TIMEOUT"], "60")

    def test_frozen_profile_and_command_match_confirmed_contract(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE)
        command = MODULE.build_torchrun_command(
            profile,
            resume_from=None,
            master_port=29531,
        )

        self.assertEqual(argument_value(command, "--nproc-per-node"), "4")
        self.assertEqual(argument_value(command, "--total_steps"), "3371")
        self.assertEqual(argument_value(command, "--warmup_steps"), "101")
        self.assertEqual(argument_value(command, "--lr_scheduler"), "cosine")
        self.assertEqual(argument_value(command, "--lr_num_cycles"), "0.5")
        self.assertEqual(argument_value(command, "--save_every"), "600")
        self.assertEqual(
            argument_value(command, "--checkpoint_completed_steps"), "True"
        )
        self.assertEqual(argument_value(command, "--save_final_checkpoint"), "True")
        self.assertEqual(argument_value(command, "--keep_last_checkpoints"), "2")
        self.assertEqual(argument_value(command, "--num_shard"), "4")
        self.assertEqual(argument_value(command, "--num_replicate"), "1")
        self.assertEqual(argument_value(command, "--use_ema"), "False")
        self.assertEqual(profile["data"]["train_parquet_shards"], 8)
        self.assertEqual(profile["run"]["num_workers_per_rank"], 2)
        self.assertEqual(profile["run"]["data_seed"], 2040)
        self.assertEqual(
            profile["_data_allocation"]["rank_rows"],
            [3371, 3371, 3371, 3370],
        )
        self.assertEqual(profile["_data_allocation"]["padding_repeats"], 1)
        self.assertNotIn("lora", " ".join(command).lower())

    def test_single_cosine_cycle_is_monotonic_after_warmup(self):
        parameter = torch.nn.Parameter(torch.tensor(1.0))
        optimizer = torch.optim.AdamW([parameter], lr=1e-5)
        args = SimpleNamespace(
            lr_scheduler="cosine",
            warmup_steps=101,
            total_steps=3371,
            min_lr=1e-6,
            lr_num_cycles=0.5,
        )
        scheduler = build_lr_scheduler(optimizer, args)
        learning_rates = []
        for _ in range(args.total_steps):
            optimizer.step()
            scheduler.step()
            learning_rates.append(optimizer.param_groups[0]["lr"])

        self.assertAlmostEqual(learning_rates[100], 1e-5, places=12)
        self.assertTrue(
            all(
                left >= right
                for left, right in zip(learning_rates[100:], learning_rates[101:])
            )
        )
        self.assertAlmostEqual(learning_rates[-1], 1e-6, places=12)

    def test_generated_command_parses_with_upstream_argument_classes(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE)
        command = MODULE.build_torchrun_command(profile, None, 29531)
        training_argv = command[command.index("train/unified_train.py") + 1 :]
        _, data_args, training_args = HfArgumentParser(
            (ModelArguments, DataArguments, TrainingArguments)
        ).parse_args_into_dataclasses(args=training_argv)

        self.assertEqual(data_args.num_workers, 2)
        self.assertEqual(training_args.total_steps, 3371)
        self.assertEqual(training_args.save_every, 600)
        self.assertTrue(training_args.save_final_checkpoint)
        self.assertTrue(training_args.checkpoint_completed_steps)
        self.assertEqual(training_args.keep_last_checkpoints, 2)
        self.assertEqual(training_args.lr_num_cycles, 0.5)

    def test_archived_stage2_profile_has_confirmed_sampling_loss_and_retention(self):
        with validated_archived_stage2_profile() as profile:
            command = MODULE.build_torchrun_command(profile, None, 29531)

        self.assertEqual(profile["data"]["source_train_prefixes"], 13483)
        self.assertEqual(profile["data"]["train_prefixes"], 14675)
        self.assertEqual(profile["data"]["round_repeats"]["5"], 3)
        self.assertEqual(profile["run"]["total_steps"], 3669)
        self.assertEqual(profile["run"]["data_seed"], 2081)
        self.assertEqual(profile["_data_allocation"]["padding_repeats"], 1)
        self.assertEqual(argument_value(command, "--edit_region_weighting"), "True")
        self.assertEqual(argument_value(command, "--edit_region_weight_boost"), "1.0")
        self.assertEqual(argument_value(command, "--text_cond_dropout_prob"), "0.0")
        self.assertEqual(argument_value(command, "--vit_cond_dropout_prob"), "0.0")
        self.assertEqual(argument_value(command, "--keep_last_checkpoints"), "1")
        self.assertEqual(argument_value(command, "--use_ema"), "False")

    def test_archived_stage2_smoke_recipe_disables_checkpoint_writes(self):
        with validated_archived_stage2_profile() as profile:
            smoke = MODULE.make_smoke_profile(profile, 2, "unit")
            command = MODULE.build_torchrun_command(smoke, None, 29531)

        self.assertEqual(argument_value(command, "--total_steps"), "2")
        self.assertEqual(argument_value(command, "--save_every"), "0")
        self.assertEqual(argument_value(command, "--save_final_checkpoint"), "False")
        self.assertEqual(argument_value(command, "--wandb_offline"), "True")
        self.assertEqual(argument_value(command, "--edit_region_weighting"), "True")

    def test_complete_checkpoint_requires_marker_and_all_shards(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint = write_dummy_checkpoint(root, 600)
            marker = MODULE.validate_complete_checkpoint(checkpoint, 4, 3371)
            self.assertEqual(marker["completed_steps"], 600)

            (checkpoint / "optimizer.00003-of-00004.pt").unlink()
            with self.assertRaisesRegex(ValueError, "missing/empty"):
                MODULE.validate_complete_checkpoint(checkpoint, 4, 3371)

    def test_latest_checkpoint_ignores_incomplete_staging_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = write_dummy_checkpoint(root, 600)
            second = write_dummy_checkpoint(root, 1200)
            (root / ".0001800.incomplete").mkdir()

            complete = MODULE.list_complete_checkpoints(root, 4, 3371)
            self.assertEqual(complete, [first.resolve(), second.resolve()])

    def test_resume_command_restores_full_state(self):
        profile = MODULE.validate_profile(MODULE.DEFAULT_PROFILE)
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint = write_dummy_checkpoint(Path(temp_dir), 600)
            command = MODULE.build_torchrun_command(profile, checkpoint, 29531)

        self.assertEqual(argument_value(command, "--resume_from"), str(checkpoint))
        self.assertEqual(argument_value(command, "--resume_model_only"), "False")
        self.assertEqual(argument_value(command, "--load_data_status"), "True")
        self.assertEqual(argument_value(command, "--total_steps"), "3371")


if __name__ == "__main__":
    unittest.main()
