"""Cache policy must preserve native online/offline/mixed VAE outputs."""
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run_datamake_ddp_training import load_profile

source = ROOT / 'lance/common/val/utils.py'
tree = ast.parse(source.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'make_padded_latent')
namespace = {'torch': torch}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
make_padded_latent = namespace['make_padded_latent']

class FakeVAE:
    def vae_encode(self, videos):
        return [video * 2 for video in videos]

class VAECacheTests(unittest.TestCase):
    def test_native_outputs_and_default_behavior(self):
        videos = [torch.tensor([1.0], requires_grad=True), torch.tensor([3.0], requires_grad=True)]
        for modes in (['online', 'online'], ['offline', 'offline'], ['offline', 'online']):
            with self.subTest(modes=modes):
                with patch('torch.cuda.empty_cache') as clear:
                    default = make_padded_latent(videos, modes, FakeVAE())
                    clear.assert_called_once_with()
                with patch('torch.cuda.empty_cache') as clear:
                    retained = make_padded_latent(videos, modes, FakeVAE(), empty_cache=False)
                    clear.assert_not_called()
                for i, (a, b) in enumerate(zip(default, retained)):
                    self.assertTrue(torch.equal(a, b))
                    self.assertEqual(a.requires_grad, b.requires_grad)
                    if modes[i] == 'online':
                        self.assertTrue(torch.equal(a, videos[i] * 2))
                        self.assertFalse(a.requires_grad)
                    else:
                        self.assertIs(a, videos[i])
                        self.assertIs(b, videos[i])

    def test_profile_cache_policy(self):
        original = json.loads((ROOT / 'configs/datamake_stage6_ddp_peft_both_branches_v1.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'profile.json'
            for policy in ('release', 'retain', 'invalid', False):
                original['ddp']['vae_cache_policy'] = policy
                path.write_text(json.dumps(original))
                if policy in ('release', 'retain'):
                    self.assertEqual(load_profile(path)['ddp']['vae_cache_policy'], policy)
                else:
                    with self.assertRaisesRegex(ValueError, 'VAE cache policy'):
                        load_profile(path)

if __name__ == '__main__':
    unittest.main()
