"""CPU coverage for branch selection, averaging, cursor and checkpoint-v5."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import random
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from safetensors.torch import load_file, save_file
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lance"))
sys.path.insert(0, str(ROOT / "scripts"))
from train.datamake_branch_lora import (
    BranchLoRAConfig, LoRALinear, apply_branch_lora, is_generation_target,
    is_understanding_target, install_branch_adapter_inference_loader,
)
from train.datamake_stage2_lora_checkpoint import (
    initialize_adam_state, save_lora_checkpoint, load_lora_checkpoint,
    save_and_stop_requested,
)
from train.datamake_stage2_lora_data import locate_prefix, preprocessing_rng
from run_datamake_stage2_lora_training import load_profile, torchrun_command, make_contract


class Toy(nn.Module):
    def __init__(self):
        super().__init__()
        self.language_model = nn.Module()
        self.language_model.model = nn.Module()
        layer = nn.Module()
        layer.self_attn = nn.Module()
        for name in ("q_proj", "k_proj", "v_proj", "o_proj"):
            setattr(layer.self_attn, name, nn.Linear(4, 4))
            setattr(layer.self_attn, name + "_moe_gen", nn.Linear(4, 4))
        for name in ("mlp", "mlp_moe_gen"):
            module = nn.Module()
            for child in ("gate_proj", "up_proj", "down_proj"):
                setattr(module, child, nn.Linear(4, 4))
            setattr(layer, name, module)
        self.language_model.model.layers = nn.ModuleList([layer])
        self.time_embedder = nn.Module()
        self.time_embedder.mlp = nn.Sequential(nn.Linear(4, 4), nn.SiLU(), nn.Linear(4, 4))
        self.vae2llm, self.llm2vae, self.connector = [nn.Linear(4, 4) for _ in range(3)]

    def forward(self, value):
        # An intentionally unused UND module exercises lazy/zero Adam state.
        return sum(module(value).square().mean() for name, module in self.named_modules()
                   if isinstance(module, LoRALinear) and not name.endswith(".mlp.down_proj"))


def config(both=True):
    return BranchLoRAConfig(rank=2, alpha=2, target_scope="both_branches" if both else "generation_experts_and_io",
                            expected_target_modules=18 if both else 11)


def create_model(both=True):
    torch.manual_seed(12)
    model = Toy()
    apply_branch_lora(model, config(both))
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=3e-4, weight_decay=0)
    initialize_adam_state(optimizer)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: min(step / 101, 1))
    return model, optimizer, scheduler


def update(model, optimizer, scheduler):
    optimizer.zero_grad(set_to_none=True)
    for _ in range(8):
        (model(torch.randn(2, 4)) / 8).backward()
    optimizer.step()
    scheduler.step()


class RuntimeTests(unittest.TestCase):
    def test_save_and_stop_uses_rank_zero_decision_and_preserves_request(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "SAVE_AND_STOP"
            with patch("torch.distributed.get_rank", return_value=0), patch("torch.distributed.broadcast") as broadcast:
                self.assertFalse(save_and_stop_requested(directory, "cpu"))
                request.touch()
                self.assertTrue(save_and_stop_requested(directory, "cpu"))
                self.assertTrue(request.is_file())  # consumed only after successful save
                self.assertEqual(broadcast.call_count, 2)
                self.assertEqual(broadcast.call_args.kwargs, {"src": 0})
            for decision in (0, 1):
                with patch("torch.distributed.get_rank", return_value=1), patch("pathlib.Path.is_file", side_effect=AssertionError("nonzero rank must not poll")), patch("torch.distributed.broadcast", side_effect=lambda flag, src: flag.fill_(decision)):
                    self.assertEqual(save_and_stop_requested(directory, "cpu"), bool(decision))

    def test_scope_and_identical_generation_initialization(self):
        a, b = Toy(), Toy()
        state = torch.get_rng_state()
        apply_branch_lora(a, config(True))
        self.assertTrue(torch.equal(state, torch.get_rng_state()))
        apply_branch_lora(b, config(False))
        aparams, bparams = dict(a.named_parameters()), dict(b.named_parameters())
        self.assertEqual(sum(p.requires_grad for p in aparams.values()), 36)
        self.assertEqual(sum(p.requires_grad for p in bparams.values()), 22)
        for name, value in bparams.items():
            if value.requires_grad:
                self.assertTrue(torch.equal(value, aparams[name]), name)
        for name, value in aparams.items():
            self.assertEqual(value.requires_grad, name.endswith(("lora_A", "lora_B")))
        self.assertFalse(is_understanding_target("vit_model.blocks.0.mlp.up_proj"))

    def test_branch_gradients_and_unchanged_base(self):
        for both in (True, False):
            model, optimizer, scheduler = create_model(both)
            base = {k: p.clone() for k, p in model.named_parameters() if not p.requires_grad}
            update(model, optimizer, scheduler)  # warmup LR=0
            update(model, optimizer, scheduler)  # first nonzero update
            for name, p in model.named_parameters():
                if name in base:
                    self.assertTrue(torch.equal(base[name], p))
                elif name.endswith("lora_B") and is_generation_target(name[:-7]):
                    self.assertGreater(p.count_nonzero().item(), 0, name)
            if both:
                unused = model.language_model.model.layers[0].mlp.down_proj.lora_B
                self.assertEqual(optimizer.state[unused]["step"].item(), 0)

    def test_save_after_nonzero_update_then_resume_third(self):
        for both in (True, False):
            with tempfile.TemporaryDirectory() as directory:
                model, opt, sched = create_model(both)
                update(model, opt, sched)
                update(model, opt, sched)
                checkpoint = save_lora_checkpoint(Path(directory), 2, model, opt, sched, config(both),
                                                 {"test": "stage6"}, {"next_microstep": 16}, 1,
                                                 SimpleNamespace(info=lambda *_: None))
                saved = load_file(str(checkpoint / "adapter.safetensors"))
                for name, value in model.named_parameters():
                    if value.requires_grad:
                        self.assertTrue(torch.equal(saved[name], value), name)
                update(model, opt, sched)
                expected = {n: p.detach().clone() for n, p in model.named_parameters()}
                expected_opt = deepcopy(opt.state_dict())
                expected_rng = torch.get_rng_state()
                restored, ropt, rsched = create_model(both)
                state = load_lora_checkpoint(checkpoint, restored, ropt, rsched, config(both), {"test": "stage6"})
                self.assertEqual(state["next_microstep"], 16)
                update(restored, ropt, rsched)
                for name, value in restored.named_parameters():
                    self.assertTrue(torch.equal(expected[name], value), name)
                for key, fields in expected_opt["state"].items():
                    for field, value in fields.items():
                        self.assertTrue(torch.equal(value, ropt.state_dict()["state"][key][field]))
                self.assertEqual(sched.state_dict(), rsched.state_dict())
                self.assertTrue(torch.equal(expected_rng, torch.get_rng_state()))

    def test_keep_four_prunes_oldest_only_after_fifth_complete_save(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model, opt, sched = create_model(False)
            for step in range(1, 6):
                update(model, opt, sched)
                save_lora_checkpoint(root, step, model, opt, sched, config(False),
                                     {"test": "keep-four"}, {"next_microstep": step * 8}, 4,
                                     SimpleNamespace(info=lambda *_: None))
                actual = sorted(p.parent.name for p in root.glob("*/checkpoint_complete.json"))
                expected = [f"{s:07d}" for s in range(max(1, step - 3), step + 1)]
                self.assertEqual(actual, expected)
            self.assertFalse((root / "0000001").exists())

    def test_indexed_resume_and_preprocessing_rng(self):
        schedule = [locate_prefix(i, [3, 2]) for i in range(32)]
        self.assertEqual(schedule[:4], [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)])
        self.assertEqual(schedule[16:], [locate_prefix(i, [3, 2]) for i in range(16, 32)])
        state, py, npstate = torch.get_rng_state(), random.getstate(), np.random.get_state()
        draws = []
        for _ in range(2):
            with preprocessing_rng(2026):
                draws.append((torch.rand(1), random.random(), np.random.rand()))
        self.assertTrue(torch.equal(draws[0][0], draws[1][0]))
        self.assertEqual(draws[0][1:], draws[1][1:])
        self.assertTrue(torch.equal(state, torch.get_rng_state()))
        self.assertEqual(py, random.getstate())
        self.assertTrue(np.array_equal(npstate[1], np.random.get_state()[1]))

    def test_accumulation_mean(self):
        full, micro = nn.Linear(4, 2), nn.Linear(4, 2)
        micro.load_state_dict(full.state_dict())
        values = torch.randn(8, 4)
        full(values).square().mean().backward()
        for value in values:
            (micro(value).square().mean() / 8).backward()
        for a, b in zip(full.parameters(), micro.parameters()):
            torch.testing.assert_close(a.grad, b.grad)

    def test_inference_base_loaded_before_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            reference = Toy()
            apply_branch_lora(reference, config())
            state = {n: p.detach().clone() for n, p in reference.named_parameters() if p.requires_grad}
            state["vae2llm.lora_B"].fill_(.1)
            save_file(state, str(path / "adapter.safetensors"))
            (path / "datamake_lora_config.json").write_text(json.dumps(config().to_dict()))
            fake = ModuleType("inference_lance")
            def base_loader(model, _):
                self.assertFalse(any(isinstance(m, LoRALinear) for m in model.modules()))
                for p in model.parameters():
                    p.data.fill_(.25)
            fake.init_from_model_path_if_needed = base_loader
            with patch.dict(sys.modules, {"inference_lance": fake}):
                install_branch_adapter_inference_loader(path)
                model = Toy()
                fake.init_from_model_path_if_needed(model, None)
            for name, value in model.named_parameters():
                expected = state[name] if name in state else torch.full_like(value, .25)
                self.assertTrue(torch.equal(expected, value), name)

    def test_short_launcher_and_slurm_limits(self):
        for arm in ("both_branches",):
            path = ROOT / f"configs/datamake_dialogue_stage2_recipe_lora_r64_{arm}_v1.json"
            profile = load_profile(path)
            command = torchrun_command(path, Path("/tmp/run"))
            self.assertIn("--nproc-per-node=4", command)
            self.assertNotIn("--lr", command)
            contract = make_contract(profile, path)
            self.assertEqual(contract["schedule"], "rank_shards_alternating_workers_indexed_prefix_v1")
            job = (ROOT / f"jobs/datamake_stage6_lora_{arm}.sbatch").read_text()
            for entry in ("--partition=testqueue", "--time=18:00:00", "--gres=gpu:h200:4", "outputs/slurm_logs"):
                self.assertIn(entry, job)


if __name__ == "__main__":
    unittest.main()
