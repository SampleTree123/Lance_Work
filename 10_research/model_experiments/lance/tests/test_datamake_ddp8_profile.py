"""Eight-rank launch, data coverage, loss switch and complete resume gate."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "lance"), str(ROOT / "runtime/peft_0_15_2")]
import torch
from safetensors.torch import save_file
from run_datamake_ddp_training import command, load_profile, verify_gate
from train.datamake_ddp_train import recipe_arguments
from train.datamake_ddp_checkpoint import finalize, write_json
from train.datamake_stage2_lora_data import IndexedPrefixDataset, locate_prefix
from data.datasets_factory.dataset_datamake_mixed_v2v_local import DataMakeMixedV2VLocalIterableDataset

PROFILE = ROOT / "configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json"


class EightRankTests(unittest.TestCase):
    def test_profile_actual_arguments_and_job(self):
        p = load_profile(PROFILE)
        self.assertEqual(p["distributed"]["gpus_per_node"], 8)
        self.assertEqual(p["run"]["global_batch_size"], 32)
        self.assertEqual(p["run"]["gradient_accumulation_steps"], 4)
        self.assertEqual(p["run"]["num_workers_per_rank"], 1)
        self.assertFalse(p["freeze"]["understanding_adapters"])
        self.assertTrue(p["freeze"]["all_base_parameters"])
        self.assertEqual(p["checkpoint"]["completed_step_interval"], 50)
        self.assertEqual(p["checkpoint"]["keep_last_complete"], 4)
        _, _, t = recipe_arguments(p)
        self.assertFalse(t.edit_region_weighting)
        cmd = command(PROFILE, Path("/tmp/not-launched"), world_size=8)
        self.assertIn("--nproc-per-node=8", cmd)
        job = (ROOT / "jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch").read_text()
        self.assertIn("--gres=gpu:h200:8", job)
        self.assertIn("${DDP_MODE:-validate}", job)

    def test_eight_actual_rank_shards_cover_all_instances(self):
        p = load_profile(PROFILE)
        sampling = json.loads(Path(p["data"]["train_sampling_manifest"]).read_text())
        split = json.loads(Path(p["data"]["split_manifest"]).read_text())
        data_root = Path(p["data"]["split_manifest"]).parent
        paths = [str(data_root / r["path"]) for r in split["splits"]["train"]["parquet_files"]]
        all_ids, attempts = set(), 0
        for rank in range(8):
            source = DataMakeMixedV2VLocalIterableDataset(dataset_name="datamake_mixed_v2v_local",
                tokenizer=None, data_dir_list=paths, all_data_paths=paths,
                local_rank=rank, world_size=8, num_workers=1)
            source.set_epoch(seed=p["run"]["data_seed"])
            data = IndexedPrefixDataset(SimpleNamespace(grouped_datasets=[source]), 12000, p["run"]["data_seed"])
            self.assertEqual(len(data.rows), 1)
            for i in range(2285):
                worker, row, cycle = locate_prefix(i, [len(data.rows[0])])
                all_ids.add(data.rows[worker][row]["sampling_instance_id"])
                attempts += 1
            self.assertEqual(len(data.rows[0]), sampling["distributed_allocation"]["rank_rows"][rank])
        self.assertEqual(len(all_ids), 18276)
        self.assertEqual(attempts - len(all_ids), 4)

    def test_gate_checks_rng_and_trace_for_rank_seven(self):
        suffixes = [f"self_attn.{n}_moe_gen" for n in ("q_proj", "k_proj", "v_proj", "o_proj")]
        suffixes += [f"mlp_moe_gen.{n}" for n in ("gate_proj", "up_proj", "down_proj")]
        targets = [f"language_model.model.layers.{i}.{s}" for i in range(36) for s in suffixes]
        targets += ["vae2llm", "llm2vae", "time_embedder.mlp.0", "time_embedder.mlp.2"]
        baseline = {f"{n}.lora_B.weight": torch.full((1, 1), .01) for n in targets}
        with tempfile.TemporaryDirectory() as tmp:
            runs = [Path(tmp) / n for n in ("continuous", "prefix", "resumed")]
            for run, step in zip(runs, (3, 2, 3)):
                staging = run / "checkpoints/.staging"
                staging.mkdir(parents=True)
                state = deepcopy(baseline)
                if step == 3: state[next(iter(state))].add_(.001)
                save_file(state, str(staging / "adapter.safetensors"))
                for name in ("adapter_config.json", "datamake_lora_config.json"):
                    write_json(staging / name, {})
                for name in ("optimizer.pt", "scheduler.pt", *[f"rng.rank-{r:05d}-of-00008.pt" for r in range(8)]):
                    torch.save({"fixture": torch.tensor(1)}, staging / name)
                finalize(staging, run / f"checkpoints/{step:07d}", step, 8, {}, step*4, 4)
                for rank in range(8):
                    (run / f"trace.rank-{rank}.jsonl").write_text(json.dumps({"loss": .1, "sample_ids": [f"rank{rank}"]}) + "\n")
            report = verify_gate(*runs, world_size=8)
            self.assertEqual(report["status"], "passed")
            self.assertIn("rng.rank-00007-of-00008.pt", report)
            self.assertIn("trace_rank_7", report)
            (runs[2] / "trace.rank-7.jsonl").write_text(json.dumps({"loss": .2, "sample_ids": ["rank7"]}) + "\n")
            with self.assertRaisesRegex(RuntimeError, "trace_rank_7"):
                verify_gate(*runs, world_size=8)


if __name__ == "__main__":
    unittest.main()
