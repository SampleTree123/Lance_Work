from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch


LANCE_ROOT = Path(__file__).parents[1] / "lance"
sys.path.insert(0, str(LANCE_ROOT))

from train.train_utils import (  # noqa: E402
    build_edit_region_mse_weights,
    compute_training_loss,
)


class EditRegionWeightingTest(unittest.TestCase):
    def test_local_change_receives_larger_soft_weight(self):
        source = torch.zeros(1, 2, 3, 2)
        target = source.clone()
        target[0, 1, 2] = 4.0

        weights = build_edit_region_mse_weights(
            [source, target],
            [(1, 2, 3), (1, 2, 3)],
            ["source", "target"],
            (1, 1, 1),
            boost=1.0,
        )

        self.assertEqual(tuple(weights.shape), (6,))
        self.assertTrue(torch.all(weights >= 1.0))
        self.assertTrue(torch.all(weights <= 2.0))
        self.assertEqual(weights.argmax().item(), 5)
        self.assertAlmostEqual(weights.max().item(), 2.0, places=6)

    def test_identical_pair_reduces_to_uniform_baseline(self):
        source = torch.randn(2, 2, 2, 4)
        target = source.clone()

        weights = build_edit_region_mse_weights(
            [source, target],
            [(2, 2, 2), (2, 2, 2)],
            ["source", "target"],
            (1, 1, 1),
        )

        torch.testing.assert_close(weights, torch.ones(8))

    def test_patchification_averages_pixel_importance_per_token(self):
        source = torch.zeros(1, 2, 2, 1)
        target = source.clone()
        target[0, 0, 0, 0] = 3.0

        weights = build_edit_region_mse_weights(
            [source, target],
            [(1, 1, 1), (1, 1, 1)],
            ["source", "target"],
            (1, 2, 2),
        )

        self.assertEqual(tuple(weights.shape), (1,))
        self.assertGreater(weights.item(), 1.0)
        self.assertLess(weights.item(), 2.0)

    def test_rejects_target_without_direct_source(self):
        target = torch.zeros(1, 1, 1, 1)
        with self.assertRaisesRegex(ValueError, "no preceding direct source"):
            build_edit_region_mse_weights(
                [target],
                [(1, 1, 1)],
                ["target"],
                (1, 1, 1),
            )

    def test_weighted_loss_uses_global_weight_normalization(self):
        loss_dict = {
            "ce": None,
            "mse": torch.tensor([[1.0, 1.0], [9.0, 9.0]]),
            "frame_mse": None,
            "total_mse_tokens": 2,
        }
        args = SimpleNamespace(
            visual_gen=True,
            mse_weight=1.0,
            ce_weight=0.25,
            ce_loss_reweighting=False,
        )
        with patch("train.train_utils.dist.all_reduce"):
            loss, logged, _, total_tokens = compute_training_loss(
                loss_dict=loss_dict,
                data={},
                ce_loss_weights=None,
                training_args=args,
                device=torch.device("cpu"),
                world_size=1,
                mse_token_weights=torch.tensor([1.0, 2.0]),
            )

        self.assertAlmostEqual(logged["mse_unweighted"].item(), 5.0, places=6)
        self.assertAlmostEqual(logged["mse"].item(), 19.0 / 3.0, places=6)
        self.assertAlmostEqual(loss.item(), 19.0 / 3.0, places=6)
        self.assertEqual(total_tokens.item(), 2)


if __name__ == "__main__":
    unittest.main()
