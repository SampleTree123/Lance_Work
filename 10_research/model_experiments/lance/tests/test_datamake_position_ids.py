"""Exact position-ID equivalence against the pinned upstream implementation."""
import ast
import hashlib
from pathlib import Path
import subprocess
import sys
from typing import List
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = '9717d9160ed16fedfdad5ce39ccbc6c9d69695e0'
SOURCE = ROOT / 'lance/data/common.py'


def extract_shift(source):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'shift_position_ids')
    namespace = {'torch': torch, 'List': List}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<shift_position_ids>', 'exec'), namespace)
    return namespace['shift_position_ids']


def upstream_shift():
    source = subprocess.check_output(['git', '-C', str(ROOT / 'lance'), 'show', f'{UPSTREAM}:data/common.py'], text=True)
    return extract_shift(source)


def equivalence_checks(device='cpu'):
    reference, optimized = upstream_shift(), extract_shift(SOURCE.read_text())
    generator = torch.Generator().manual_seed(2081)
    patterns = [[0,1,2,3,4]*4, [0,1,1,2,3,4]*3, [0,1,3,4]*4,
                [0,2,3,4]*4, [0]*20, [1,2]*10, [3,4]*10, []]
    count = 0
    for labels in patterns:
        for dtype in (torch.int32, torch.int64):
            modality = torch.tensor(labels, dtype=torch.long, device=device)
            original_modality = modality.clone()
            n = len(labels)
            for values in ('random', 'zeros', 'cancel'):
                positions = torch.randint(1, 100, (3, 1, n * 2), generator=generator, dtype=dtype).to(device)[..., ::2]
                if values == 'zeros': positions.zero_()
                if values == 'cancel':
                    # The original condition tests the sum, not merely token presence.
                    positions[..., modality == 2] = 0
                    if (modality == 2).sum() >= 2:
                        idx = torch.where(modality == 2)[0]
                        positions[0, 0, idx[0]] = 7
                        positions[0, 0, idx[1]] = -7
                for modes in (['causal'], ['full'], ['full', 'full_noise', 'causal', 'full']):
                    a, b = positions.clone(), positions.clone()
                    kwargs = dict(pos_shift=1000, attn_modes=modes, split_lens=[n]+[0]*(len(modes)-1),
                                  pro_type=10, i_sample_modality=modality)
                    expected, actual = reference(a, **kwargs), optimized(b, **kwargs)
                    assert expected is a and actual is b
                    assert torch.equal(expected, actual), (labels, dtype, values, modes)
                    assert torch.equal(modality, original_modality)
                    count += 1
    # Inactive modes must still accept the optional modality argument as None.
    for modes, pro_type in ((['causal'],10), (['full'],None), ([],10)):
        x = torch.arange(12).reshape(3,1,4).to(device)
        kwargs = dict(pos_shift=1000,attn_modes=modes,split_lens=[4]*len(modes),pro_type=pro_type)
        assert torch.equal(reference(x.clone(),**kwargs),optimized(x.clone(),**kwargs))
        count += 1
    return count


class PositionIdTests(unittest.TestCase):
    def test_exact_upstream_equivalence(self):
        self.assertEqual(equivalence_checks(), 147)

    def test_ddp_contract_binds_position_helper(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from run_datamake_ddp_training import load_profile, make_contract, WORKSPACE_ROOT
        profile = load_profile(ROOT/'configs/datamake_stage6_ddp_peft_both_branches_v1.json')
        hashes = make_contract(profile)['implementation_sha256']
        self.assertEqual(hashes[str(SOURCE.relative_to(WORKSPACE_ROOT))], hashlib.sha256(SOURCE.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
