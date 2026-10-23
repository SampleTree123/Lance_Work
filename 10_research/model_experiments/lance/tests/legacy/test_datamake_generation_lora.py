from __future__ import annotations

import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path

import torch
from torch import nn
from safetensors.torch import save_file


LANCE_ROOT = Path(__file__).parents[1] / "lance"
sys.path.insert(0, str(LANCE_ROOT))

from train.datamake_generation_lora import (  # noqa: E402
    GenerationLoRAConfig,
    LoRALinear,
    apply_generation_lora,
    install_lora_adapter_inference_loader,
    load_adapter_state_dict,
    read_lora_config,
    write_lora_config,
)
from train.datamake_lora_generation_train import (  # noqa: E402
    parse_lora_arguments,
    validate_upstream_contract,
)


REQUIRED_UPSTREAM_ARGUMENTS_FOR_TEST = {
    "--freeze_und_params": "True",
    "--freeze_und": "True",
    "--freeze_vit": "True",
    "--freeze_vae": "True",
    "--freeze_llm": "False",
    "--use_ema": "False",
}


class Attention(nn.Module):
    def __init__(self):
        super().__init__()
        self.q_proj = nn.Linear(4, 4)
        self.q_proj_moe_gen = nn.Linear(4, 4)
        self.k_proj_moe_gen = nn.Linear(4, 2)
        self.v_proj_moe_gen = nn.Linear(4, 2)
        self.o_proj_moe_gen = nn.Linear(4, 4)


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.gate_proj = nn.Linear(4, 8, bias=False)
        self.up_proj = nn.Linear(4, 8, bias=False)
        self.down_proj = nn.Linear(8, 4, bias=False)


class Layer(nn.Module):
    def __init__(self):
        super().__init__()
        self.self_attn = Attention()
        self.mlp = MLP()
        self.mlp_moe_gen = MLP()


class DummyLance(nn.Module):
    def __init__(self):
        super().__init__()
        self.language_model = nn.Module()
        self.language_model.model = nn.Module()
        self.language_model.model.layers = nn.ModuleList([Layer()])
        self.time_embedder = nn.Module()
        self.time_embedder.mlp = nn.Sequential(nn.Linear(2, 4), nn.SiLU(), nn.Linear(4, 4))
        self.vae2llm = nn.Linear(3, 4)
        self.llm2vae = nn.Linear(4, 3)
        self.connector = nn.Linear(4, 4)


def config() -> GenerationLoRAConfig:
    return GenerationLoRAConfig(
        rank=2,
        alpha=2,
        dropout=0,
        target_scope="generation_experts_and_io",
        expected_target_modules=11,
    )


class GenerationLoRATest(unittest.TestCase):
    def test_only_generation_lora_parameters_are_trainable(self):
        model = DummyLance()
        report = apply_generation_lora(model, config())
        self.assertEqual(report["target_module_count"], 11)
        self.assertIsInstance(
            model.language_model.model.layers[0].self_attn.q_proj_moe_gen,
            LoRALinear,
        )
        self.assertIsInstance(model.vae2llm, LoRALinear)
        self.assertIsInstance(model.time_embedder.mlp[0], LoRALinear)
        self.assertIsInstance(model.connector, nn.Linear)
        trainable = [name for name, p in model.named_parameters() if p.requires_grad]
        self.assertTrue(trainable)
        self.assertTrue(
            all(name.endswith("lora_A") or name.endswith("lora_B") for name in trainable)
        )

    def test_zero_initialized_adapter_preserves_base_output_and_roundtrips(self):
        torch.manual_seed(7)
        model = DummyLance()
        layer = model.language_model.model.layers[0].self_attn.q_proj_moe_gen
        inputs = torch.randn(3, 4)
        expected = layer(inputs)
        apply_generation_lora(model, config())
        wrapped = model.language_model.model.layers[0].self_attn.q_proj_moe_gen
        self.assertTrue(torch.equal(expected, wrapped(inputs)))
        with torch.no_grad():
            wrapped.lora_B.fill_(0.25)
        adapted = wrapped(inputs)

        clone = DummyLance()
        apply_generation_lora(clone, config())
        clone.load_state_dict(model.state_dict(), strict=True)
        actual = clone.language_model.model.layers[0].self_attn.q_proj_moe_gen(inputs)
        self.assertTrue(torch.allclose(actual, adapted))

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "datamake_lora_config.json"
            write_lora_config(str(path), config())
            self.assertEqual(read_lora_config(str(path)), config())

    def test_exact_target_name_and_shape_signature_is_enforced(self):
        model = DummyLance()
        baseline = apply_generation_lora(model, config())
        wrong = GenerationLoRAConfig(
            rank=2,
            alpha=2,
            dropout=0,
            target_scope="generation_experts_and_io",
            expected_target_modules=11,
            expected_target_signature_sha256="0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "names/shapes"):
            apply_generation_lora(DummyLance(), wrong)
        self.assertEqual(len(baseline["target_signature_sha256"]), 64)

    def test_partial_adapter_loader_rejects_missing_unexpected_and_wrong_shape(self):
        model = DummyLance()
        apply_generation_lora(model, config())
        state = {
            name: parameter.detach().clone()
            for name, parameter in model.named_parameters()
            if name.endswith("lora_A") or name.endswith("lora_B")
        }
        load_adapter_state_dict(model, state)
        missing = dict(state)
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(RuntimeError, "topology mismatch"):
            load_adapter_state_dict(model, missing)
        unexpected = dict(state)
        unexpected["not.a.lora"] = torch.zeros(1)
        with self.assertRaisesRegex(RuntimeError, "topology mismatch"):
            load_adapter_state_dict(model, unexpected)
        wrong_shape = dict(state)
        key = next(iter(wrong_shape))
        wrong_shape[key] = torch.zeros(1)
        with self.assertRaisesRegex(RuntimeError, "shape_mismatches"):
            load_adapter_state_dict(model, wrong_shape)

    def test_separate_adapter_inference_loads_official_base_before_lora(self):
        with tempfile.TemporaryDirectory() as directory:
            source = DummyLance()
            apply_generation_lora(source, config())
            with torch.no_grad():
                for name, parameter in source.named_parameters():
                    if name.endswith("lora_A"):
                        parameter.fill_(0.125)
                    elif name.endswith("lora_B"):
                        parameter.fill_(0.25)
            adapter_state = {
                name: parameter.detach().cpu().contiguous()
                for name, parameter in source.named_parameters()
                if name.endswith("lora_A") or name.endswith("lora_B")
            }
            write_lora_config(
                str(Path(directory) / "datamake_lora_config.json"), config()
            )
            save_file(adapter_state, str(Path(directory) / "adapter.safetensors"))

            fake_inference = ModuleType("inference_lance")
            calls = []

            def original_loader(model, model_args):
                target = model.language_model.model.layers[0].self_attn.q_proj_moe_gen
                self.assertIsInstance(target, nn.Linear)
                self.assertEqual(model_args.model_path, "/official/base")
                with torch.no_grad():
                    target.weight.fill_(3.0)
                calls.append("base")

            fake_inference.init_from_model_path_if_needed = original_loader
            with patch.dict(sys.modules, {"inference_lance": fake_inference}):
                self.assertTrue(install_lora_adapter_inference_loader(directory))
                target_model = DummyLance()
                fake_inference.init_from_model_path_if_needed(
                    target_model, SimpleNamespace(model_path="/official/base")
                )

            self.assertEqual(calls, ["base"])
            wrapped = target_model.language_model.model.layers[0].self_attn.q_proj_moe_gen
            self.assertIsInstance(wrapped, LoRALinear)
            self.assertTrue(torch.all(wrapped.base_layer.weight == 3.0))
            restored = {
                name: parameter.detach().cpu()
                for name, parameter in target_model.named_parameters()
                if name.endswith("lora_A") or name.endswith("lora_B")
            }
            self.assertEqual(set(restored), set(adapter_state))
            for name in restored:
                self.assertTrue(torch.equal(restored[name], adapter_state[name]))

    def test_guarded_entry_requires_r64_generation_freeze_and_1e4(self):
        arguments = []
        required = {
            **REQUIRED_UPSTREAM_ARGUMENTS_FOR_TEST,
            "--lr": "1e-4",
            "--edit_region_weighting": "False",
        }
        for name, value in required.items():
            arguments.extend([name, value])
        lora_arguments = [
            "--datamake_lora_rank",
            "64",
            "--datamake_lora_alpha",
            "64",
            "--datamake_lora_dropout",
            "0.0",
            "--datamake_lora_target_scope",
            "generation_experts_and_io",
            "--datamake_lora_expected_target_modules",
            "256",
        ]
        lora_arguments.extend(["--datamake_history_mode", "teacher_forced"])
        parsed, history_mode, remaining = parse_lora_arguments(
            [*lora_arguments, *arguments]
        )
        self.assertEqual(parsed.rank, 64)
        self.assertEqual(history_mode, "teacher_forced")
        validate_upstream_contract(remaining, history_mode)
        lora_arguments[1] = "32"
        with self.assertRaisesRegex(ValueError, "rank"):
            parse_lora_arguments([*lora_arguments, *arguments])

    def test_rollout_full_rejects_region_weighting(self):
        arguments = []
        for name, value in {
            **REQUIRED_UPSTREAM_ARGUMENTS_FOR_TEST,
            "--lr": "1e-4",
            "--edit_region_weighting": "True",
        }.items():
            arguments.extend([name, value])
        with self.assertRaisesRegex(ValueError, "rollout_full"):
            validate_upstream_contract(arguments, "rollout_full")


if __name__ == "__main__":
    unittest.main()
