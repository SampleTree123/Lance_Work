#!/usr/bin/env python3
"""Freeze new complete validation chains for paired history-mode inference.

CPU only. Implementation/output owner: ../training_integration.md.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from build_datamake_teacher_forced_conversation import build_conversation, sha256_file

ROOT = Path(__file__).resolve().parents[4]
LANCE = ROOT / "10_research/model_experiments/lance"
DATA = LANCE / "outputs/training_data/datamake_coinve4k_mixed_r5x3_seed20260911_v1"
MEDIA = ROOT / "00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1"
SCHEMA = "datamake_complete_chain_review_v1"


def prior_chains(root):
    seen, evidence = set(), []
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("chain_id"), str):
                seen.add(value["chain_id"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for path in sorted(root.rglob("*.json")):
        visit(json.loads(path.read_text()))
        evidence.append({"path": str(path), "sha256": sha256_file(path)})
    return seen, evidence


def select_chains(rows, excluded, seed):
    full = {}
    for row in rows:
        if row["dataset_origin"] != "ue_synthetic" or row["chain_id"] in excluded:
            continue
        previous = full.get(row["chain_id"])
        if previous is None or row["target_round"] > previous["target_round"]:
            full[row["chain_id"]] = row
    selected, used_media = [], set()
    for length in (3, 4, 5):
        candidates = [r for r in full.values() if r["target_round"] == length]
        if not candidates:
            raise ValueError(f"No new complete {length}-round validation chain")
        def key(row):
            axes = set(row["edit_axes"])
            return (len(set(row["video_paths"]) & used_media),
                    -len(axes), -int("action_id" in axes), -int("camera_id" in axes),
                    hashlib.sha256(f"{seed}:{row['chain_id']}".encode()).hexdigest())
        chosen = min(candidates, key=key)
        selected.append(chosen)
        used_media.update(chosen["video_paths"])
    return selected


def make_cases(suite):
    cases = []
    media = Path(suite["media_root"])
    for row in suite["chains"]:
        chain = row["chain_id"]
        n = row["target_round"]
        for mode in ("teacher_forced", "autoregressive"):
            # GT mode: each round gets a fresh full GT prefix. Rollout mode:
            # one conversation, initial source only, all user turns generate.
            for end in (range(1, n + 1) if mode == "teacher_forced" else [n]):
                prefix = {**row, "target_round": end, "context_length": end}
                for field in ("prompts", "edit_axes", "turn_ids"):
                    prefix[field] = row[field][:end]
                prefix["video_paths"] = row["video_paths"][:end + 1]
                conversation = build_conversation(prefix, media)
                name = f"{chain}/{mode}" + (f"_r{end:02d}" if mode == "teacher_forced" else "")
                if mode == "autoregressive":
                    conversation["turns"] = [
                        {**t, "action": "edit_video"} for t in conversation["turns"]
                        if t["role"] == "user"
                    ]
                rounds = [end] if mode == "teacher_forced" else range(1, n + 1)
                outputs = []
                for index, round_no in enumerate(rounds):
                    gt_source = str(media / row["video_paths"][round_no - 1])
                    outputs.append({
                        "round": round_no, "prompt": row["prompts"][round_no - 1],
                        "edit_axis": row["edit_axes"][round_no - 1],
                        "gt_source": gt_source, "gt_target": str(media / row["video_paths"][round_no]),
                        "actual_source": f"{name}/turn{index - 1:02d}.mp4" if mode == "autoregressive" and index else gt_source,
                        "output": f"{name}/turn{index:02d}.mp4",
                    })
                cases.append({"name": name, "chain_id": chain, "sample_id": row["sample_id"],
                              "mode": mode, "conversation": conversation, "outputs": outputs})
    for row in suite.get("real_cases", []):
        source, target = row["video_paths"]
        name = f"real/{row['sample_id']}"
        if row["target_round"] != 1 or len(row["prompts"]) != 1 or len(row["video_paths"]) != 2:
            raise ValueError("Real review cases must be single-turn source/target pairs")
        cases.append({
            "name": name, "chain_id": row["chain_id"], "sample_id": row["sample_id"], "mode": "single_turn",
            "paired_crop": {"path": source, "start_seconds": row["crop_start_seconds"],
                            "duration_seconds": row["crop_duration_seconds"], "policy": row["crop_policy"]},
            "conversation": {"system_prompt": None, "turns": [{"role": "user", "action": "edit_video",
                "content": [{"type": "video", "value": source}, {"type": "text", "value": row["prompts"][0]}],
                "meta": {"sample_id": row["sample_id"], "chain_id": row["chain_id"], "round": 1}}]},
            "outputs": [{"round": 1, "prompt": row["prompts"][0], "edit_axis": ", ".join(row["edit_axes"]),
                         "gt_source": source, "gt_target": target, "actual_source": source, "output": f"{name}/turn00.mp4"}],
        })
    return cases


def load_suite(path):
    suite = json.loads(Path(path).read_text())
    if suite["schema_version"] != SCHEMA or suite["split"] != "validation":
        raise ValueError("Expected a complete-chain validation suite")
    if sha256_file(Path(suite["parquet"])) != suite["parquet_sha256"]:
        raise ValueError("Validation parquet changed")
    for name, digest in suite["media_sha256"].items():
        if sha256_file(Path(suite["media_root"]) / name) != digest:
            raise ValueError(f"Reference media changed: {name}")
    for name, digest in suite.get("real_media_sha256", {}).items():
        if sha256_file(Path(name)) != digest:
            raise ValueError(f"Real reference media changed: {name}")
    return suite


def select_real_cases(rows, excluded, seed, count=4):
    candidates = sorted((r for r in rows if r["dataset_origin"] == "coinve" and r["chain_id"] not in excluded),
                        key=lambda r: hashlib.sha256(f"{seed}:{r['sample_id']}".encode()).hexdigest())
    selected = []
    # Cover removal/background, object replacement, style, and addition.
    for axes in ({"Remove", "Replace"}, {"Replace"}, {"Replace", "Stylize"}, {"Add", "Replace"}):
        match = next((r for r in candidates if set(r["edit_axes"]) == axes), None)
        if match is not None:
            selected.append(match)
    selected += [r for r in candidates if r not in selected]
    if len(selected) < count:
        raise ValueError("Insufficient new real validation cases")
    return selected[:count]


def extend_real_suite(path, count):
    suite = load_suite(path)
    if suite.get("real_cases"):
        raise ValueError("Suite already contains real cases")
    rows = pq.read_table(suite["parquet"]).to_pylist()
    seen, _ = prior_chains(LANCE / "outputs/multiturn_chat")
    real = select_real_cases(rows, seen, suite["seed"], count)
    train_ids = set()
    for p in (Path(suite["parquet"]).parents[1] / "train").glob("*.parquet"):
        train_ids.update(pq.read_table(p, columns=["chain_id"])["chain_id"].to_pylist())
    if train_ids.intersection(r["chain_id"] for r in real):
        raise ValueError("Real validation sample occurs in training")
    suite["real_cases"] = real
    suite["real_selection_policy"] = "seeded validation-only; one-turn compound prompts retained; cover Remove/Replace/Stylize/Add combinations"
    suite["real_media_sha256"] = {p: sha256_file(Path(p)) for r in real for p in r["video_paths"]}
    suite["expected_generated_videos"] = sum(len(c["outputs"]) for c in make_cases(suite))
    path.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"real_cases": [r["sample_id"] for r in real], "generated_videos": suite["expected_generated_videos"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--extend-suite", type=Path, help="Keep existing UE cases and append real validation pairs")
    parser.add_argument("--real-count", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260911)
    args = parser.parse_args()
    if args.extend_suite:
        if args.output or args.real_count < 1:
            parser.error("--extend-suite needs a positive real count and no --output")
        extend_real_suite(args.extend_suite, args.real_count)
        return
    if not args.output:
        parser.error("provide --output or --extend-suite")
    parquet = next((DATA / "validation").glob("*.parquet"))
    rows = pq.read_table(parquet).to_pylist()
    seen, evidence = prior_chains(LANCE / "outputs/multiturn_chat")
    selected = select_chains(rows, seen, args.seed)
    train_ids = set()
    for p in (DATA / "train").glob("*.parquet"):
        train_ids.update(pq.read_table(p, columns=["chain_id"])["chain_id"].to_pylist())
    if train_ids.intersection(r["chain_id"] for r in selected):
        raise ValueError("Selected validation chain occurs in training")
    suite = {
        "schema_version": SCHEMA, "split": "validation", "seed": args.seed,
        "selection_policy": "new complete UE chains of length 3/4/5; minimize shared endpoints then maximize axis diversity; seeded tie-break",
        "excluded_prior_chain_ids": sorted(seen), "prior_review_evidence": evidence,
        "parquet": str(parquet), "parquet_sha256": sha256_file(parquet),
        "media_root": str(MEDIA), "chains": selected,
        "train_chain_overlap": [], "media_sha256": {
            name: sha256_file(MEDIA / name) for name in sorted({p for r in selected for p in r["video_paths"]})
        },
        "inference": {"diffusion_steps": 30, "cfg_text_scale": 1.0, "timestep_shift": 3.5,
                      "global_seed": 42, "noise_seed": 42, "use_KVcache": True},
    }
    cases = make_cases(suite)
    suite["expected_generated_videos"] = sum(len(c["outputs"]) for c in cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as f:
        f.write(json.dumps(suite, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"suite": str(args.output), "chains": [r["chain_id"] for r in selected],
                      "generated_videos": suite["expected_generated_videos"]}))


if __name__ == "__main__":
    main()
