#!/usr/bin/env python3
"""Build reference-only UE R5x3 + CoinVE mixed prefix data; never copy media."""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from build_datamake_round_weighted_train import choose_data_seed, sha256_file, write_json

LANCE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = LANCE_ROOT / "outputs/training_data"
SPLIT_ROOT = DATA_ROOT / "datamake_dialogue_first_batch_v002_split_seed2026_sharded8_20260831"
WEIGHTED_ROOT = DATA_ROOT / "datamake_dialogue_first_batch_v002_stage2_r5x3_seed2041_sharded8_20260901"
COINVE_ROOT = Path("/scratch/prj0000000275/jcy/ljy/video_collection/lance_general_edit_finetune/3_lance_lora_finetuning/artifacts/coinve_ablation_v1")
CROP_POLICY = "paired_absolute_5s_12fps_kn1_fixed_v1"


def load_json(path):
    return json.loads(path.read_text())


def fixed_crop_start(sample_id, common_duration, seed):
    if not math.isfinite(common_duration) or common_duration < 5:
        raise ValueError(f"video pair shorter than five seconds: {sample_id}")
    digest = hashlib.sha256(f"{seed}\0{sample_id}\0paired_crop".encode()).digest()
    fraction = int.from_bytes(digest[:8], "big") / 2**64
    # Floor to nanoseconds, so rounding cannot exceed the common interval.
    return math.floor(fraction * (common_duration - 5) * 1e9) / 1e9


def verified_rows(root, records):
    rows = []
    schema = None
    for record in records:
        path = root / record["path"]
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"source parquet changed: {path}")
        table = pq.read_table(path)
        if len(table) != record["rows"]:
            raise ValueError(f"source row count changed: {path}")
        rows.extend(table.to_pylist())
        schema = table.schema
    return rows, schema


def build(output, coinve_root=COINVE_ROOT, seed=20260911):
    output = output.absolute()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite dataset: {output}")
    split = load_json(SPLIT_ROOT / "split_manifest.json")
    weighted = load_json(WEIGHTED_ROOT / "sampling_manifest.json")
    template = yaml.safe_load((WEIGHTED_ROOT / "train/lance_dataset.yaml").read_text())
    media_root = Path(template["D1"]["datamake_multiturn_v2v_local"]["media_root"])
    input_paths = [SPLIT_ROOT / "split_manifest.json", WEIGHTED_ROOT / "sampling_manifest.json",
                   WEIGHTED_ROOT / "train/lance_dataset.yaml", coinve_root / "coinve_4k_pool.csv",
                   coinve_root / "technical_probe.jsonl"]
    inputs = {str(p): sha256_file(p) for p in input_paths}
    records = list(csv.DictReader((coinve_root / "coinve_4k_pool.csv").open(encoding="utf-8-sig")))
    if len(records) != 4000 or len({r["sample_id"] for r in records}) != 4000:
        raise ValueError("expected the frozen, unique CoinVE 4K pool")
    probes = {}
    with (coinve_root / "technical_probe.jsonl").open() as stream:
        for line in stream:
            item = json.loads(line)
            probes[item["sample_id"]] = item
    by_split = {}
    schema = None
    for name in ("train", "validation", "test"):
        root = WEIGHTED_ROOT if name == "train" else SPLIT_ROOT
        files = weighted["parquet_files"] if name == "train" else split["splits"][name]["parquet_files"]
        rows, source_schema = verified_rows(root, files)
        if name == "train":
            schema = source_schema
        for row in rows:
            row.update(dataset_origin="ue_synthetic", source_sample_id=row["sample_id"], split=name,
                       crop_policy=None, crop_start_seconds=None, crop_duration_seconds=None,
                       media_metadata_json=None)
            row.setdefault("sampling_repeat_index", 0)
            row.setdefault("sampling_instance_id", row["sample_id"] + "::repeat0")
        by_split[name] = rows
    schema = schema.append(pa.field("dataset_origin", pa.string())).append(pa.field("source_sample_id", pa.string()))
    for name, dtype in [("split", pa.string()), ("crop_policy", pa.string()),
                        ("crop_start_seconds", pa.float64()), ("crop_duration_seconds", pa.float64()),
                        ("media_metadata_json", pa.string())]:
        schema = schema.append(pa.field(name, dtype))
    provenance = []
    for record in records:
        sid, name = record["sample_id"], record["split"]
        if name not in by_split or record["technical_status"] != "pass" or not record["instruction"].strip():
            raise ValueError(f"invalid CoinVE record: {sid}")
        probe = probes[sid]
        if probe["status"] != "pass":
            raise ValueError(f"failed technical probe: {sid}")
        for side in ("source", "target"):
            path = Path(record[f"{side}_local"])
            if not path.is_absolute() or not path.is_file() or path.stat().st_size != probe[side]["bytes"]:
                raise ValueError(f"missing/changed media: {path}")
        duration = min(float(probe[s]["frames"]) / float(probe[s]["fps"]) for s in ("source", "target"))
        start = fixed_crop_start(sid, duration, seed)
        row = dict.fromkeys(schema.names)
        row.update(schema_version="datamake_lance_mixed_prefix_v1", sample_id=sid, chain_id=sid,
                   target_round=1, context_length=1, language="en", prompt_view="dialogue",
                   prompts=[record["instruction"]], video_paths=[record["source_local"], record["target_local"]],
                   turn_ids=[sid + "::turn1"], edit_axes=json.loads(record["operations_json"]),
                   input_video_path=record["source_local"], output_video_path=record["target_local"],
                   chain_policy="single_turn_compound_edit", semantic_facts_json="{}",
                   sampling_repeat_index=0, sampling_instance_id=sid + "::repeat0",
                   dataset_origin="coinve", source_sample_id=sid, split=name,
                   crop_policy=CROP_POLICY, crop_start_seconds=start, crop_duration_seconds=5.0,
                   media_metadata_json=json.dumps(probe, sort_keys=True))
        by_split[name].append(row)
        provenance.append({**record, "crop_start_seconds": start, "crop_duration_seconds": 5.0,
                           "crop_policy": CROP_POLICY})
    # Verify all referenced files, including the retained UE release after cleanup.
    paths = {str(Path(p) if Path(p).is_absolute() else media_root / p)
             for rows in by_split.values() for row in rows for p in row["video_paths"]}
    for path in paths:
        if not Path(path).is_file() or Path(path).stat().st_size == 0:
            raise FileNotFoundError(path)
    groups = {name: {r["chain_id"] for r in rows} for name, rows in by_split.items()}
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if groups[a] & groups[b]:
            raise ValueError("chain/sample identity overlaps splits")
    output.mkdir(parents=True)
    manifest = {"schema_version": "datamake_coinve_mixed_dataset_v1", "builder_sha256": sha256_file(Path(__file__)),
                "source_files_sha256": inputs, "seed": seed, "media_root": str(media_root),
                "media_storage": "references_only_no_video_copy", "media_files": len(paths),
                "crop_policy": CROP_POLICY, "crop_refresh": "fixed_per_sample_across_epochs",
                "synthetic_round_repeats": weighted["round_repeats"], "coinve_repeats": 1,
                "split_policy": "preserve_both_existing_splits; no new parent-video regrouping",
                "deferred": ["content_temporal_alignment_filter", "compound_edit_filter", "parent_video_regrouping"],
                "splits": {}}
    for name, rows in by_split.items():
        rows.sort(key=lambda row: hashlib.sha256(f"{seed}\0{row['sampling_instance_id']}".encode()).hexdigest())
        if len({r["sampling_instance_id"] for r in rows}) != len(rows):
            raise ValueError("duplicate sampling instance")
        directory = output / name
        directory.mkdir()
        count = 8 if name == "train" else 1
        sizes = [len(rows) // count + (i < len(rows) % count) for i in range(count)]
        files, offset = [], 0
        for i, size in enumerate(sizes):
            path = directory / f"mixed-{i:05d}-of-{count:05d}.parquet"
            pq.write_table(pa.Table.from_pylist(rows[offset:offset+size], schema=schema), path,
                           compression="zstd", row_group_size=128)
            files.append({"path": str(path.relative_to(output)), "rows": size, "sha256": sha256_file(path)})
            offset += size
        config = deepcopy(template)
        args = config["D1"].pop("datamake_multiturn_v2v_local")
        config["D1"]["datamake_mixed_v2v_local"] = args
        args["dataset_names"] = {"datamake_coinve_mixed": {"data_dir": [str(output / f["path"]) for f in files]}}
        yaml_path = directory / "lance_dataset.yaml"
        yaml_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True))
        manifest["splits"][name] = {"sample_count": len(rows), "chain_count": len(groups[name]),
            "unique_sample_count": len({r["sample_id"] for r in rows}),
            "origin_counts": dict(Counter(r["dataset_origin"] for r in rows)),
            "samples_per_target_round": dict(Counter(str(r["target_round"]) for r in rows)),
            "parquet_files": files, "dataset_config": str(yaml_path.relative_to(output)),
            "dataset_config_sha256": sha256_file(yaml_path)}
        if name == "train":
            manifest["distributed_allocation"] = choose_data_seed(sizes, math.ceil(len(rows)/4), 2081)
    with (output / "coinve_provenance.jsonl").open("w") as stream:
        for record in provenance:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    manifest["coinve_provenance_sha256"] = sha256_file(output / "coinve_provenance.jsonl")
    write_json(output / "split_manifest.json", manifest)
    train = manifest["splits"]["train"]
    sampling = {"schema_version": "datamake_coinve_mixed_sampling_v1", "seed": seed,
        "split_manifest": str(output / "split_manifest.json"),
        "split_manifest_sha256": sha256_file(output / "split_manifest.json"),
        "effective_train_rows": train["sample_count"], "unique_source_sample_ids": train["unique_sample_count"],
        "parquet_files": train["parquet_files"], "origin_counts": train["origin_counts"],
        "synthetic_round_repeats": weighted["round_repeats"], "coinve_repeats": 1,
        "distributed_allocation": manifest["distributed_allocation"]}
    write_json(output / "sampling_manifest.json", sampling)
    binding = {"data": {}, "run": {"data_seed": manifest["distributed_allocation"]["data_seed"]}}
    for key, path in [("split_manifest", output / "split_manifest.json"),
                      ("train_sampling_manifest", output / "sampling_manifest.json"),
                      *[(s + "_config", output / s / "lance_dataset.yaml") for s in by_split]]:
        binding["data"][key] = str(path)
        binding["data"][key + "_sha256"] = sha256_file(path)
    binding["data"].update(train_parquet_shards=8, train_chains=train["chain_count"],
        source_train_prefixes=train["unique_sample_count"], train_prefixes=train["sample_count"],
        validation_chains=manifest["splits"]["validation"]["chain_count"],
        validation_prefixes=manifest["splits"]["validation"]["sample_count"],
        test_chains=manifest["splits"]["test"]["chain_count"], test_prefixes=manifest["splits"]["test"]["sample_count"],
        split_seed=2026, sampling_seed=seed, round_repeats=weighted["round_repeats"],
        round_repeats_scope="ue_synthetic_only; CoinVE once", prompt_view="dialogue", language="en",
        temporal_crop_policy=CROP_POLICY)
    write_json(output / "profile_data_binding.json", binding)
    print(json.dumps({"output": str(output), "splits": {s: r["origin_counts"] for s, r in manifest["splits"].items()},
                      "allocation": manifest["distributed_allocation"]}, ensure_ascii=False))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATA_ROOT / "datamake_coinve4k_mixed_r5x3_seed20260911_v1")
    parser.add_argument("--coinve-root", type=Path, default=COINVE_ROOT)
    parser.add_argument("--seed", type=int, default=20260911)
    args = parser.parse_args()
    build(args.output_dir, args.coinve_root, args.seed)
