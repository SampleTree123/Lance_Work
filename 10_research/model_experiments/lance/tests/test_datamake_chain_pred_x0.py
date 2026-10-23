"""Whole-chain coverage, fixed target windows and detached reuse contracts."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

import torch

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "lance"), str(ROOT / "runtime/peft_0_15_2")]
from run_datamake_chain_pred_x0_ddp_training import load_profile, make_contract, BASELINE
from train.datamake_chain_window_schedule import read_chains, make_windows, schedule_digest, turn_seed
from train.datamake_chain_window_data import ChainRuntime
import run_datamake_ddp_training as control

PROFILE = ROOT / "configs/datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.json"


class ChainPredX0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load_profile(PROFILE)
        cls.chains = read_chains(cls.profile)
        cls.windows = make_windows(cls.chains, 3000, cls.profile["run"]["data_seed"])

    def test_fixed_batch_nonempty_ranks_and_no_split_chain(self):
        seen = set()
        for ranks in self.windows:
            self.assertEqual(len(ranks), 8)
            self.assertTrue(all(ranks))
            self.assertEqual(sum(self.chains[i]["targets"] for units in ranks for _, i in units), 32)
            for units in ranks:
                for identity in units:
                    self.assertNotIn(identity, seen)
                    seen.add(identity)

    def test_full_epoch_preserves_all_weighted_instances_and_real_proportion(self):
        instances, rounds, origins = [], Counter(), Counter()
        for ranks in self.windows:
            for units in ranks:
                for epoch, index in units:
                    if epoch != 0:
                        continue
                    for record in self.chains[index]["records"]:
                        row = record["row"]
                        instances.append(row["sampling_instance_id"])
                        rounds[int(row["target_round"])] += 1
                        origins[row["dataset_origin"]] += 1
        self.assertEqual(len(instances), len(set(instances)))
        self.assertEqual(len(instances), 18276)
        self.assertEqual(rounds, {1: 7201, 2: 3600, 3: 3600, 4: 2087, 5: 1788})
        self.assertEqual(origins, {"ue_synthetic": 14675, "coinve": 3601})

    def test_resume_reconstructs_identical_windows_and_noise_seeds(self):
        again = make_windows(self.chains, 3000, self.profile["run"]["data_seed"])
        self.assertEqual(self.windows[77:80], again[77:80])
        self.assertEqual(schedule_digest(self.chains, self.windows), schedule_digest(self.chains, again))
        seeds = [turn_seed(2220, 0, "chain", 5, repeat) for repeat in range(3)]
        self.assertEqual(len(set(seeds)), 3)
        self.assertNotEqual(seeds[0], turn_seed(2220, 1, "chain", 5, 0))

    def test_r5_three_forwards_but_no_repeated_history_generation(self):
        chain = next(c for c in self.chains if c["length"] == 5)
        rounds = [r["row"]["target_round"] for r in chain["records"]]
        self.assertEqual(rounds, [1, 2, 3, 4, 5, 5, 5])
        self.assertEqual(sum(k < chain["length"] for k in rounds), 4)
        self.assertEqual(sum(c["length"] - 1 for c in self.chains), 9883)

    def test_detached_history_and_no_original_source_hash_changes(self):
        runtime = ChainRuntime(None, None, {}, {}, 0)
        with self.assertRaises(ValueError):
            runtime.append_history(torch.ones(3, 1, 2, 2, requires_grad=True))
        value = torch.ones(3, 1, 2, 2).detach()
        runtime.append_history(value)
        self.assertIs(runtime.histories[0], value)
        baseline = control.make_contract(control.load_profile(control.workspace_path(BASELINE)))
        variant = make_contract(self.profile)
        for path, digest in baseline["implementation_sha256"].items():
            self.assertEqual(variant["implementation_sha256"][path], digest)
        self.assertEqual(self.profile["chain_schedule"]["extra_round_loss_weights"], [1]*5)


if __name__ == "__main__":
    unittest.main()
