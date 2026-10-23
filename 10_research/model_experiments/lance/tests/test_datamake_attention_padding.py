"""Removing dummy attention tokens must preserve real-token masks and gradients."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'lance'), str(ROOT / 'scripts')]
from data.data_utils import create_sparse_mask
from train.datamake_packed_batch import trim_attention_padding
from run_datamake_ddp_training import load_profile


def example(lengths, budget=512):
    real = sum(lengths)
    splits, modes = [], []
    for length in lengths:
        splits.extend([2, length - 2])
        modes.extend(['causal', 'full'])
    return dict(sequence_length=real, sample_lens=[*lengths, budget-real],
                split_lens=[*splits, budget-real], attn_modes=[*modes, 'causal'],
                sample_type=['gen']*len(lengths)+['pad'],
                sample_N_target=[1]*len(lengths)+[0],
                packed_position_ids=torch.arange(real), mse_loss_indexes=torch.arange(2, real))


def mask(data):
    length = sum(data['sample_lens'])
    fn = create_sparse_mask(data['sample_lens'], data['split_lens'], data['attn_modes'], 'cpu')
    return fn(torch.tensor(0), torch.tensor(0), torch.arange(length)[:, None], torch.arange(length)[None, :])


class AttentionPaddingTests(unittest.TestCase):
    def test_unequal_samples_keep_all_real_masks_and_metadata(self):
        for lengths in ([7], [7, 11], [7, 11, 23, 35], [64, 64], [127], [129]):
            with self.subTest(lengths=lengths):
                original = example(lengths)
                result = trim_attention_padding(original)
                real = sum(lengths)
                self.assertEqual(sum(result['sample_lens']), ((real+127)//128)*128)
                self.assertEqual(result['sample_lens'][:-1], lengths)
                self.assertEqual(result['sample_type'][-1], 'pad')
                self.assertEqual(original['sample_lens'][-1], 512-real)
                for key in original.keys()-{'sample_lens', 'split_lens'}:
                    self.assertIs(result[key], original[key])
                before, after = mask(original), mask(result)
                self.assertTrue(torch.equal(before[:real, :real], after[:real, :real]))
                self.assertFalse(after[:real, real:].any())
                self.assertFalse(after[real:, :real].any())
                self.assertEqual(trim_attention_padding(result)['sample_lens'], result['sample_lens'])

    def test_outputs_and_qkv_gradients_equal_dense_reference(self):
        torch.manual_seed(10)
        original = example([7, 11])
        real = original['sequence_length']
        inputs = [torch.randn(real, 8, dtype=torch.float64) for _ in range(3)]
        results = []
        for data in (original, trim_attention_padding(original)):
            q, k, v = [x.clone().requires_grad_() for x in inputs]
            padded = [torch.nn.functional.pad(x, (0, 0, 0, sum(data['sample_lens'])-real)) for x in (q, k, v)]
            scores = (padded[0] @ padded[1].T / 8**.5).masked_fill(~mask(data), -float('inf'))
            output = (scores.softmax(-1) @ padded[2])[:real]
            gradients = torch.autograd.grad(output.square().sum(), (q, k, v))
            results.append((output, gradients))
        torch.testing.assert_close(results[0][0], results[1][0], rtol=1e-12, atol=1e-12)
        for a, b in zip(results[0][1], results[1][1]):
            torch.testing.assert_close(a, b, rtol=1e-12, atol=1e-12)

    def test_real_document_is_never_trimmed(self):
        data = example([7, 11])
        data['sample_type'][-1] = 'gen'
        with self.assertRaisesRegex(ValueError, 'isolated trailing'):
            trim_attention_padding(data)

    def test_profile_policy_validation_and_legacy_default(self):
        data = json.loads((ROOT / 'configs/datamake_stage6_ddp_peft_both_branches_v1.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.json'
            path.write_text(json.dumps(data))
            self.assertEqual(load_profile(path)['ddp'].get('attention_padding', 'fixed'), 'fixed')
            for policy in ('fixed', 'minimal', 'invalid'):
                data['ddp']['attention_padding'] = policy
                path.write_text(json.dumps(data))
                if policy == 'invalid':
                    with self.assertRaisesRegex(ValueError, 'Attention padding'):
                        load_profile(path)
                else:
                    self.assertEqual(load_profile(path)['ddp']['attention_padding'], policy)


if __name__ == '__main__':
    unittest.main()
