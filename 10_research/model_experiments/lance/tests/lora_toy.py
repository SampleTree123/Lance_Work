"""Small branch-topology fixture shared by current adapter tests."""
from torch import nn
from train.datamake_branch_lora import BranchLoRAConfig, LoRALinear

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
