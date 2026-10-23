from __future__ import annotations

import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).parents[1]
LANCE_ROOT = ROOT / "lance"
sys.path.insert(0, str(LANCE_ROOT))

from train.datamake_online_rollout import (  # noqa: E402
    build_epoch_groups,
    load_chain_records,
    make_turn_row,
    optimizer_windows,
    rank_compensated_lance_seed,
    reject_duplicate_cli_options,
    stable_turn_seed,
    validate_dataset_binding,
    window_target_count,
)


CHAIN_ROOT = (
    ROOT
    / "outputs/training_data/"
    "datamake_dialogue_first_batch_v002_chain_seed2026_20260904"
)


class OnlineRolloutContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.manifest = load_chain_records(
            CHAIN_ROOT / "train/manifest.json"
        )

    def test_chain_dataset_preserves_every_target(self):
        self.assertEqual(len(self.records), 3600)
        self.assertEqual(sum(row.round_count for row in self.records), 13483)
        self.assertEqual(
            {length: sum(row.round_count == length for row in self.records) for length in (3, 4, 5)},
            {3: 1513, 4: 1491, 5: 596},
        )

    def test_dataset_yaml_is_bound_to_online_chain_manifest(self):
        validate_dataset_binding(
            CHAIN_ROOT / "train/lance_dataset.yaml",
            CHAIN_ROOT / "train/manifest.json",
        )

    def test_four_rank_schedule_has_450_accumulated_steps_and_no_repeats(self):
        groups = build_epoch_groups(self.records, world_size=4, seed=2042, epoch=0)
        windows = optimizer_windows(groups, accumulation_steps=2)
        self.assertEqual(len(groups), 900)
        self.assertEqual(len(windows), 450)
        ids = [
            item.record.chain_id
            for group in groups
            for item in group
            if item.contributes_loss
        ]
        self.assertEqual(len(ids), 3600)
        self.assertEqual(len(set(ids)), 3600)
        self.assertEqual(sum(map(window_target_count, windows)), 13483)

    def test_online_turn_replaces_both_history_roles_but_keeps_gt_target(self):
        record = next(row for row in self.records if row.round_count == 5)
        generated = [torch.zeros(3, 5, 16, 16), torch.ones(3, 5, 16, 16)]
        row = make_turn_row(record, 3, generated)
        self.assertEqual(row["prompts"], list(record.prompts[:3]))
        self.assertEqual(
            row["video_paths"],
            list(record.video_paths[:4]),
        )
        self.assertEqual(row["video_inputs"][0], record.video_paths[0])
        self.assertIs(row["video_inputs"][1], generated[0])
        self.assertIs(row["video_inputs"][2], generated[1])
        self.assertEqual(row["video_inputs"][3], record.video_paths[3])

    def test_turn_seed_is_epoch_chain_and_round_specific(self):
        values = {
            stable_turn_seed(2026, epoch, chain, round_number)
            for epoch, chain, round_number in (
                (0, "c1", 1),
                (1, "c1", 1),
                (0, "c2", 1),
                (0, "c1", 2),
            )
        }
        self.assertEqual(len(values), 4)
        self.assertEqual(stable_turn_seed(2026, 0, "c1", 1), stable_turn_seed(2026, 0, "c1", 1))

    def test_lance_internal_rank_offset_is_exactly_cancelled(self):
        stable = stable_turn_seed(2026, 3, "chain-x", 4)
        self.assertGreaterEqual(stable, 1024)
        effective = {
            rank_compensated_lance_seed(stable, rank) + rank
            for rank in range(4)
        }
        self.assertEqual(effective, {stable})
        with self.assertRaisesRegex(ValueError, "max_samples=1"):
            rank_compensated_lance_seed(stable, 0, max_samples=2)

    def test_duplicate_cli_options_are_rejected(self):
        reject_duplicate_cli_options(["--lr", "1e-4", "--total_steps=1800"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            reject_duplicate_cli_options(["--lr", "1e-4", "--lr=1e-5"])


if __name__ == "__main__":
    unittest.main()
