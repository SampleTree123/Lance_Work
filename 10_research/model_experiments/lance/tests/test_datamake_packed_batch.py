"""Packed loss must preserve the original globally normalized microsteps."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lance'))
import torch
from train.datamake_packed_batch import compute_packed_training_loss
from data.data_utils import create_sparse_mask


class PackedLossTests(unittest.TestCase):
    def test_unequal_rank_slot_lengths_match_separate_microstep_gradients(self):
        for batch_size in (2, 4, 8):
            for dtype in (torch.float64, torch.float32):
                counts = [[1 + (rank * 3 + slot * 5) % 9 for slot in range(batch_size)] for rank in range(4)]
                values, weights = [], []
                for rank, sizes in enumerate(counts):
                    values.append([torch.arange(n*3,dtype=dtype).reshape(n,3)/10 + rank + slot for slot,n in enumerate(sizes)])
                    weights.append([torch.linspace(1,2,n,dtype=dtype) for n in sizes])
                denoms=torch.stack([sum(weights[r][slot].sum() for r in range(4)) for slot in range(batch_size)])
                tokens=torch.tensor(counts).sum(0)
                for rank in range(4):
                    parameter=torch.tensor(.7,dtype=dtype,requires_grad=True)
                    losses=[(parameter*x-.2).square() for x in values[rank]]
                    original=sum((loss.mean(-1)*w).sum()*4/denoms[slot]/8 for slot,(loss,w) in enumerate(zip(losses,weights[rank])))
                    expected=torch.autograd.grad(original,parameter)[0]
                    parameter=torch.tensor(.7,dtype=dtype,requires_grad=True)
                    loss_dict={'mse':torch.cat([(parameter*x-.2).square() for x in values[rank]]), 'ce':None,'frame_mse':None}
                    destinations=iter((denoms,tokens))
                    def reduce(tensor): tensor.copy_(next(destinations))
                    with patch('train.datamake_packed_batch.dist.is_initialized',return_value=True),patch('train.datamake_packed_batch.dist.get_world_size',return_value=4),patch('train.datamake_packed_batch.dist.all_reduce',side_effect=reduce):
                        actual,_,_,_=compute_packed_training_loss(loss_dict,counts[rank],SimpleNamespace(mse_weight=1),torch.cat(weights[rank]))
                    actual_grad=torch.autograd.grad(actual/(8//batch_size),parameter)[0]
                    torch.testing.assert_close(actual_grad,expected,rtol=1e-6,atol=1e-8)

    def test_native_attention_mask_isolates_unequal_samples_and_padding(self):
        fn=create_sparse_mask([7,11,2],[3,4,5,6,2],['full','noise','full','noise','causal'],'cpu')
        q=torch.arange(20)[:,None];k=torch.arange(20)[None,:]
        mask=fn(torch.tensor(0),torch.tensor(0),q,k)
        self.assertFalse(mask[:7,7:].any())
        self.assertFalse(mask[7:18,:7].any())
        self.assertFalse(mask[7:18,18:].any())
        self.assertFalse(mask[18:,:18].any())
        self.assertTrue(mask[6,0])
        self.assertTrue(mask[17,7])

    def test_mismatched_target_partition_is_rejected(self):
        losses={'mse':torch.ones(5,3),'ce':None,'frame_mse':None}
        with self.assertRaisesRegex(ValueError,'counts'):
            compute_packed_training_loss(losses,[2,2],SimpleNamespace(mse_weight=1))


if __name__=='__main__': unittest.main()
