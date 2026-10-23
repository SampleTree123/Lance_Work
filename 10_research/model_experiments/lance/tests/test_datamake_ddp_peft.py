"""Real PEFT tests: legacy equivalence, named Adam migration and exact resume."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime/peft_0_15_2"), str(ROOT / "lance"), str(ROOT / "scripts")]
import torch
from torch import nn
from torch.distributed.algorithms._checkpoint.checkpoint_wrapper import checkpoint_wrapper, CheckpointImpl
from train.datamake_branch_lora import apply_branch_lora
from train.datamake_peft import inject, adapter_state, load_adapter, canonical_name, legacy_name
from train.datamake_ddp_checkpoint import save, load, validate, named_optimizer, load_named_optimizer
from train.datamake_train_state import initialize_adam_state
from convert_datamake_fsdp_to_peft import convert_optimizer
from run_datamake_ddp_training import load_profile, verify_gate

spec = importlib.util.spec_from_file_location("branch_toy", ROOT / "tests/lora_toy.py")
toy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toy)


class Toy(toy.Toy):
    def forward(self, x):
        return sum(m(x).square().mean() for name, m in self.named_modules()
                   if hasattr(m, "lora_A") and not name.endswith("mlp.down_proj"))


def create(both=True):
    torch.manual_seed(12)
    model = Toy()
    inject(model, toy.config(both))
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=3e-4, weight_decay=0)
    initialize_adam_state(optimizer)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda step: min(step / 101, 1))
    return model, optimizer, scheduler


def update(model, optimizer, scheduler):
    optimizer.zero_grad(set_to_none=True)
    for _ in range(8):
        (model(torch.randn(2, 4)) / 8).backward()
    nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1)
    optimizer.step()
    scheduler.step()


class PeftTests(unittest.TestCase):
    def test_interrupted_save_retries_without_overwriting_completed_or_partial_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model, opt, sched = create()
            update(model, opt, sched); update(model, opt, sched)
            legacy = root / '.0000002.incomplete'
            legacy.mkdir()
            (legacy / 'partial').write_text('previous interrupted attempt')
            original_save = torch.save

            def interrupt_optimizer(value, path, *args, **kwargs):
                if Path(path).name == 'optimizer.pt':
                    raise OSError('injected interruption')
                return original_save(value, path, *args, **kwargs)

            with patch.object(torch, 'save', side_effect=interrupt_optimizer):
                with self.assertRaisesRegex(RuntimeError, 'injected interruption'):
                    save(root, 2, model, opt, sched, toy.config(), {'test': 1}, 16)
            incomplete = list(root.glob('.0000002.incomplete-*'))
            self.assertEqual(len(incomplete), 1)
            partial_adapter = (incomplete[0] / 'adapter.safetensors').read_bytes()
            self.assertFalse((root / '0000002').exists())
            point = save(root, 2, model, opt, sched, toy.config(), {'test': 1}, 16)
            self.assertEqual(validate(point, {'test': 1}, 1)['next_microstep'], 16)
            self.assertEqual((incomplete[0] / 'adapter.safetensors').read_bytes(), partial_adapter)
            self.assertEqual((legacy / 'partial').read_text(), 'previous interrupted attempt')
            complete = (point / 'checkpoint_complete.json').read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'Refusing to overwrite'):
                save(root, 2, model, opt, sched, toy.config(), {'test': 1}, 16)
            self.assertEqual((point / 'checkpoint_complete.json').read_bytes(), complete)

    def test_gate_requires_actual_generation_update_in_both_arms(self):
        from safetensors.torch import save_file
        from train.datamake_ddp_checkpoint import finalize, write_json
        suffixes = [f'self_attn.{n}_moe_gen' for n in ('q_proj', 'k_proj', 'v_proj', 'o_proj')]
        suffixes += [f'mlp_moe_gen.{n}' for n in ('gate_proj', 'up_proj', 'down_proj')]
        targets = [f'language_model.model.layers.{i}.{s}' for i in range(36) for s in suffixes]
        targets += ['vae2llm', 'llm2vae', 'time_embedder.mlp.0', 'time_embedder.mlp.2']
        baseline = {f'{n}.lora_B.weight': torch.full((2, 2), .01) for n in targets}
        # Exercise the complete gate with real files/manifests, keeping unrelated
        # optimizer/scheduler/RNG fixtures equal to isolate the update check.
        for first in (0, 800):
            for c_changed, r_changed in ((False, False), (True, False), (False, True), (True, True)):
                with self.subTest(first=first, continuous=c_changed, resumed=r_changed), tempfile.TemporaryDirectory() as directory:
                    runs = [Path(directory) / name for name in ('continuous', 'prefix', 'resumed')]
                    for run, offset, change in zip(runs, (3, 2, 3), (c_changed, False, r_changed)):
                        staging = run / 'checkpoints' / '.staging'
                        staging.mkdir(parents=True)
                        state = deepcopy(baseline)
                        if change:
                            # Smaller than equality tolerance, but a real FP32 update.
                            state[next(iter(state))].add_(1e-8)
                        save_file(state, str(staging / 'adapter.safetensors'))
                        for name in ('adapter_config.json', 'datamake_lora_config.json'):
                            write_json(staging / name, {})
                        for name in ('optimizer.pt', 'scheduler.pt', *[f'rng.rank-{r:05d}-of-00004.pt' for r in range(4)]):
                            torch.save({'fixture': torch.tensor(1)}, staging / name)
                        step = first + offset
                        finalize(staging, run / 'checkpoints' / f'{step:07d}', step, 4, {}, step * 8, 4)
                        for rank in range(4):
                            (run / f'trace.rank-{rank}.jsonl').write_text(json.dumps({'step': step, 'sample_ids': ['sample'], 'loss': .1}) + '\n')
                    if c_changed and r_changed:
                        report = verify_gate(*runs, first_step=first)
                        self.assertEqual(report['status'], 'passed')
                        self.assertEqual(report['generation_update']['changed_b_tensors'], {'continuous': 1, 'resumed': 1})
                        trace_path = runs[2] / 'trace.rank-0.jsonl'
                        trace = json.loads(trace_path.read_text())
                        trace.update(peak_allocated_gib=100.5, peak_reserved_gib=120.5)
                        trace_path.write_text(json.dumps(trace) + '\n')
                        self.assertEqual(verify_gate(*runs, first_step=first)['status'], 'passed')
                        for key, value in (('loss', .2), ('sample_ids', ['other']), ('new_semantic_field', True)):
                            with self.subTest(changed_trace_field=key):
                                trace_path.write_text(json.dumps({**trace, key: value}) + '\n')
                                with self.assertRaisesRegex(RuntimeError, 'trace_rank_0'):
                                    verify_gate(*runs, first_step=first)
                        trace_path.write_text(json.dumps(trace) + '\n')
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'did not update after prefix'):
                            verify_gate(*runs, first_step=first)

    def test_exact_legacy_initialization_forward_and_gradient(self):
        for both in (True, False):
            torch.manual_seed(11)
            a = Toy()
            b = deepcopy(a)
            apply_branch_lora(a, toy.config(both))
            before = torch.get_rng_state().clone()
            inject(b, toy.config(both))
            self.assertTrue(torch.equal(before, torch.get_rng_state()))
            pa = dict(a.named_parameters())
            for name, value in b.named_parameters():
                if value.requires_grad:
                    self.assertTrue(torch.equal(pa[legacy_name(name)], value), name)
            # Nonzero B exercises gradients through both low-rank matrices.
            for name, value in b.named_parameters():
                if ".lora_B." in name:
                    with torch.no_grad():
                        value.fill_(.01)
                        pa[legacy_name(name)].fill_(.01)
            x = torch.randn(2, 4)
            la, lb = a(x), b(x)
            self.assertTrue(torch.equal(la, lb))
            la.backward(); lb.backward()
            for name, value in b.named_parameters():
                if value.requires_grad:
                    old = pa[legacy_name(name)].grad
                    self.assertEqual(old is None, value.grad is None)
                    if old is not None:
                        self.assertTrue(torch.equal(old, value.grad), name)

    def test_branch_common_initialization(self):
        a, _, _ = create(True)
        b, _, _ = create(False)
        sa, sb = adapter_state(a), adapter_state(b)
        for name in sb:
            self.assertTrue(torch.equal(sa[name], sb[name]))

    def test_base_unchanged_after_real_update(self):
        model, opt, sched = create()
        base = {name: p.detach().clone() for name, p in model.named_parameters() if not p.requires_grad}
        update(model, opt, sched); update(model, opt, sched)
        for name, p in model.named_parameters():
            if name in base:
                self.assertTrue(torch.equal(base[name], p))
        self.assertTrue(any(v.count_nonzero() for n, v in adapter_state(model).items() if '.lora_B.' in n))

    def test_exact_save_resume_and_cursor(self):
        for both in (True, False):
            with tempfile.TemporaryDirectory() as directory:
                a, opt, sched = create(both)
                update(a, opt, sched); update(a, opt, sched)
                point = save(directory, 2, a, opt, sched, toy.config(both), {"test": 1}, 16)
                update(a, opt, sched)
                expected = adapter_state(a)
                expected_optim = named_optimizer(a, opt)
                b, opt2, sched2 = create(both)
                state = load(point, b, opt2, sched2, {"test": 1})
                self.assertEqual(state["next_microstep"], 16)
                update(b, opt2, sched2)
                for name, value in adapter_state(b).items():
                    self.assertTrue(torch.equal(value, expected[name]))
                actual_optim = named_optimizer(b, opt2)
                for key, st in expected_optim["state_dict"]["state"].items():
                    for name, value in st.items():
                        self.assertTrue(torch.equal(value, actual_optim["state_dict"]["state"][key][name]))
                self.assertEqual(sched.state_dict(), sched2.state_dict())

    def test_corrupt_checkpoint_and_contract_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            model, opt, sched = create()
            update(model, opt, sched)
            point = save(directory, 1, model, opt, sched, toy.config(), {"test": 1}, 8)
            with self.assertRaises(ValueError): validate(point, {"test": 2})
            marker_path = point / "checkpoint_complete.json"
            original = marker_path.read_text()
            marker = json.loads(original)
            del marker["artifacts"]["optimizer.pt"]
            marker_path.write_text(json.dumps(marker))
            with self.assertRaises(ValueError): validate(point)
            marker_path.write_text(original)
            with (point / "optimizer.pt").open("ab") as stream: stream.write(b"bad")
            with self.assertRaises(ValueError): validate(point)

    def test_adam_mapping_and_migration_keeps_moments(self):
        a, opt, sched = create()
        update(a, opt, sched); update(a, opt, sched)
        payload = named_optimizer(a, opt)
        values = adapter_state(a)
        reverse = payload["parameter_names"]
        legacy = {"state": {}, "param_groups": []}
        for i, st in payload["state_dict"]["state"].items():
            name = reverse[i]
            legacy["state"][legacy_name(name)] = {**st, "_datamake_parameter_value": values[name]}
        for group in payload["state_dict"]["param_groups"]:
            legacy["param_groups"].append({**group, "params": [legacy_name(reverse[i]) for i in group["params"]]})
        migrated = convert_optimizer(legacy, values)
        b, _, _ = create()
        load_adapter(b, values)
        # Reverse registration in the optimizer to prove name-based mapping.
        opt2 = torch.optim.AdamW(list(reversed([p for p in b.parameters() if p.requires_grad])))
        load_named_optimizer(b, opt2, migrated)
        params = dict(b.named_parameters())
        for name, p in a.named_parameters():
            if p.requires_grad:
                for key, value in opt.state[p].items():
                    self.assertTrue(torch.equal(value, opt2.state[params[name]][key]))
        broken = deepcopy(legacy)
        first = next(iter(broken["state"]))
        broken["state"][first]["_datamake_parameter_value"] = torch.zeros_like(broken["state"][first]["_datamake_parameter_value"])
        with self.assertRaises(ValueError): convert_optimizer(broken, values)

    def test_checkpoint_wrapper_names_roundtrip(self):
        a, opt, sched = create()
        update(a, opt, sched); update(a, opt, sched)
        original = adapter_state(a)
        a.language_model.model.layers[0] = checkpoint_wrapper(a.language_model.model.layers[0], checkpoint_impl=CheckpointImpl.NO_REENTRANT)
        wrapped = adapter_state(a)
        self.assertEqual(set(original), set(wrapped))
        self.assertTrue(all('_checkpoint_wrapped_module' not in n for n in named_optimizer(a, opt)['parameter_names'].values()))
        b, _, _ = create()
        load_adapter(b, wrapped)
        for name, value in adapter_state(b).items(): self.assertTrue(torch.equal(original[name], value))

    def test_reject_recipe_drift(self):
        path = ROOT / 'configs/datamake_stage6_ddp_peft_both_branches_v1.json'
        original = load_profile(path)
        for group, field, value in [('optimization', 'learning_rate', .01), ('run', 'gradient_accumulation_steps', 1)]:
            profile = deepcopy(original)
            profile[group][field] = value
            with tempfile.TemporaryDirectory() as directory:
                p = Path(directory) / 'profile.json';p.write_text(json.dumps(profile))
                with self.assertRaises(ValueError): load_profile(p)


if __name__ == '__main__':
    unittest.main()
