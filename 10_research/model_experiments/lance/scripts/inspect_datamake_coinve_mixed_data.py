#!/usr/bin/env python3
"""Audit every mixed reference and sample real videos through the CPU packer."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pyarrow.parquet as pq
import yaml

from build_datamake_coinve_mixed_data import (
    LANCE_ROOT, SPLIT_ROOT, WEIGHTED_ROOT, fixed_crop_start, sha256_file, write_json,
)


def canonical(row, keys):
    return json.dumps({k: row[k] for k in keys}, sort_keys=True, ensure_ascii=False)


def audit(root, real_pack=False):
    manifest = json.loads((root / "split_manifest.json").read_text())
    for path, digest in manifest["source_files_sha256"].items():
        assert sha256_file(Path(path)) == digest, path
    assert sha256_file(root / "coinve_provenance.jsonl") == manifest["coinve_provenance_sha256"]
    original_split = json.loads((SPLIT_ROOT / "split_manifest.json").read_text())
    original_weighted = json.loads((WEIGHTED_ROOT / "sampling_manifest.json").read_text())
    sys.path.insert(0, str(LANCE_ROOT / "lance"))
    from data.datasets_factory.dataset_datamake_mixed_v2v_local import crop_frame_indices
    rows_by_split, paths, sizes, max_time_difference = {}, set(), [], 0.0
    for name, record in manifest["splits"].items():
        rows = []
        for f in record["parquet_files"]:
            path = root / f["path"]
            assert sha256_file(path) == f["sha256"]
            shard = pq.read_table(path).to_pylist()
            assert len(shard) == f["rows"]
            rows.extend(shard)
            if name == "train": sizes.append(len(shard))
        assert len(rows) == record["sample_count"]
        assert dict(Counter(r["dataset_origin"] for r in rows)) == record["origin_counts"]
        config_path = root / record["dataset_config"]
        assert sha256_file(config_path) == record["dataset_config_sha256"]
        args = yaml.safe_load(config_path.read_text())["D1"]["datamake_mixed_v2v_local"]
        assert args["dataset_names"]["datamake_coinve_mixed"]["data_dir"] == [str(root / f["path"]) for f in record["parquet_files"]]
        source_root = WEIGHTED_ROOT if name == "train" else SPLIT_ROOT
        source_files = original_weighted["parquet_files"] if name == "train" else original_split["splits"][name]["parquet_files"]
        old = pq.read_table([source_root / f["path"] for f in source_files])
        assert Counter(canonical(r, old.schema.names) for r in old.to_pylist()) == Counter(
            canonical(r, old.schema.names) for r in rows if r["dataset_origin"] == "ue_synthetic")
        for row in rows:
            assert len(row["prompts"]) + 1 == len(row["video_paths"])
            assert row["video_paths"][-2:] == [row["input_video_path"], row["output_video_path"]]
            for value in row["video_paths"]:
                paths.add(Path(value) if Path(value).is_absolute() else Path(manifest["media_root"]) / value)
            if row["dataset_origin"] != "coinve": continue
            probe = json.loads(row["media_metadata_json"])
            common = min(probe[s]["frames"] / probe[s]["fps"] for s in ("source", "target"))
            assert row["crop_start_seconds"] == fixed_crop_start(row["sample_id"], common, manifest["seed"])
            times = []
            for side in ("source", "target"):
                metadata = probe[side]
                indices = crop_frame_indices(metadata["frames"], metadata["fps"], row["crop_start_seconds"])
                times.append([i / metadata["fps"] for i in indices])
                p = row["video_paths"][0 if side == "source" else 1]
                assert Path(p).stat().st_size == metadata["bytes"]
            delta = max(abs(a-b) for a,b in zip(*times))
            # Independent integer-frame quantization at each end can differ
            # by two native frames; total clip duration must not drive timing.
            assert delta <= 2 / min(probe[s]["fps"] for s in ("source", "target")) + 1e-6
            max_time_difference = max(max_time_difference, delta)
        rows_by_split[name] = rows
    for p in paths: assert p.is_file() and p.stat().st_size > 0, p
    assert len(paths) == manifest["media_files"]
    assert not list(root.rglob("*.mp4"))
    # Verify the actual indexed rank/worker schedule covers every train row.
    import random
    from train.datamake_stage2_lora_data import locate_prefix
    shard_order = list(range(8))
    seed = manifest["distributed_allocation"]["data_seed"]
    random.Random(seed).shuffle(shard_order)
    visited = set()
    steps = (sum(sizes) + 3) // 4
    for rank in range(4):
        assigned = shard_order[rank*2:rank*2+2]
        for i in range(steps):
            worker, row, _ = locate_prefix(i, [sizes[j] for j in assigned])
            visited.add((assigned[worker], row))
    assert len(visited) == sum(sizes)
    report = {"status": "passed", "scope": "full_manifest_reference_crop_math_and_cpu_pack",
              "all_synthetic_rows_unchanged": True, "all_coinve_windows_valid": True,
              "all_media_references_present": len(paths), "video_files_copied": 0,
              "max_source_target_sample_time_difference_seconds": max_time_difference,
              "indexed_first_pass_rows_covered": len(visited), "data_seed": seed,
              "gpu_loss_backward": "not_run", "real_media_packs": []}
    if real_pack:
        report["real_media_packs"] = pack_samples(root, rows_by_split)
    write_json(root / "validation_report.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


def pack_samples(root, rows_by_split):
    import gc
    import torch
    from train.datamake_ddp_train import recipe_arguments
    from train.datamake_stage2_lora_data import IndexedPrefixDataset
    from train.datamake_packed_batch import trim_attention_padding
    from train.train_utils import build_train_dataset_config
    from data.dataset_base_train import PackedDataset
    from data.data_utils import add_special_tokens
    from modeling.qwen2 import Qwen2Tokenizer
    torch.set_num_threads(1)
    profile = json.loads((LANCE_ROOT / "configs/datamake_stage6_padding_both_20260910.json").read_text())
    binding = json.loads((root / "profile_data_binding.json").read_text())
    profile["data"].update(binding["data"])
    profile["run"].update(binding["run"])
    m, d, t = recipe_arguments(profile)
    from datamake_runtime import workspace_path
    base = workspace_path(profile["model"]["model_path"])
    tokenizer, specials, _ = add_special_tokens(Qwen2Tokenizer.from_pretrained(str(base)))
    config = build_train_dataset_config(d, m, t, SimpleNamespace(downsample_temporal=4, downsample_spatial=16))
    packer = PackedDataset(config, tokenizer=tokenizer, special_tokens=specials, local_rank=0, world_size=4,
        interpolate_pos=m.interpolate_pos, use_flex=t.use_flex, data_status=None, apply_chat_template=False,
        image_token_id=json.loads((base / "llm_config.json").read_text())["video_token_id"],
        cfg_type=t.cfg_type, cfg_uncond_token_id=t.cfg_uncond_token_id, **asdict(d))
    packer.set_epoch(d.data_seed)
    dataset = IndexedPrefixDataset(packer, 24000, d.data_seed)
    cases = [next(r for r in rows_by_split["train"] if r["sample_id"] == sid)
             for sid in ("coinve-000000", "coinve-155212")]
    cases += [next(r for r in rows_by_split[s] if r["dataset_origin"] == "coinve") for s in ("validation", "test")]
    cases += [next(r for r in rows_by_split["train"] if r["dataset_origin"] == "ue_synthetic" and r["target_round"] == n)
              for n in (1, 5)]
    results = []
    for row in cases:
        # Use the production indexed preprocessing + pack path with this exact
        # record in a local slot, without modifying any parquet or scheduler.
        dataset.rows[0][0] = row
        packed = trim_attention_padding(dataset[0])
        assert packed["vae_edit_roles"] == ["source", "target"]
        shapes = [list(v.shape) for v in packed["padded_videos"]]
        assert shapes[0] == shapes[1], shapes
        if row["dataset_origin"] == "coinve": assert shapes[0][1] == 61, shapes
        record = {"sample_id": row["sample_id"], "origin": row["dataset_origin"], "split": row["split"],
                  "target_round": row["target_round"], "video_shapes": shapes,
                  "sample_lens": packed["sample_lens"], "crop_start_seconds": row["crop_start_seconds"]}
        if not results:
            text = packed["packed_text_ids"].clone()
            # Hash all tensors that contain preprocessed visual inputs without
            # retaining another full set of 480p videos in CPU memory.
            def digest(v): return hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()
            video_hashes = [digest(v) for v in packed["padded_videos"]]
            del packed
            again = trim_attention_padding(dataset[0])
            assert torch.equal(text, again["packed_text_ids"])
            assert video_hashes == [digest(v) for v in again["padded_videos"]]
            del again
            record["same_index_replay_exact"] = True
        else:
            del packed
        results.append(record)
        print(json.dumps(record), flush=True)
        gc.collect()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--real-pack", action="store_true")
    args = parser.parse_args()
    audit(args.dataset_root.absolute(), args.real_pack)
