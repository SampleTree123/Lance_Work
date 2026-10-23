#!/usr/bin/env python3
"""Audit optional single-image GT prefixes and prepare an isolated DDP profile.

This tool does not create examples or submit training. Preparation requires a
complete data binding JSON (the profile's ``data`` object), not a partial patch
to the old dataset. Paths in that binding and YAML must be absolute.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

import pyarrow.parquet as pq
from PIL import Image
import yaml

from datamake_runtime import LANCE_ROOT, sha256_file, workspace_path

SCHEMA = "datamake_reference_image_audit_v1"
MODE = "optional_single_vit_v1"
DATA_FILES = ("train_config", "validation_config", "test_config",
              "train_sampling_manifest", "split_manifest")


def absolute_file(value, label):
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError(f"{label} must be an absolute file path")
    path = Path(value).resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"{label} is not a regular file: {path}")
    return path


def audit_dataset(config_path, *, require_reference=True):
    """Check every row/image; hash exact inputs without decoding source videos."""
    if str(LANCE_ROOT) not in sys.path:
        sys.path.insert(0, str(LANCE_ROOT))
    from data.datamake_reference_image import normalize_reference_images

    config_path = Path(config_path).resolve(strict=True)
    config = yaml.safe_load(config_path.read_text())
    if not isinstance(config, dict) or len(config) != 1:
        raise ValueError("dataset YAML must contain exactly one outer group")
    group = next(iter(config.values()))
    if not isinstance(group, dict) or len(group) != 1:
        raise ValueError("dataset YAML must contain exactly one implementation")
    implementation, dataset = next(iter(group.items()))
    if implementation not in ("datamake_mixed_v2v_local", "datamake_multiturn_v2v_local"):
        raise ValueError("reference-image preparation supports GT prefix datasets only")
    if dataset.get("datamake_record_level", "dialogue_prefix") != "dialogue_prefix":
        raise ValueError("reference-image preparation does not support chain records")
    raw_media_root = Path(dataset["media_root"])
    if not raw_media_root.is_absolute():
        raise ValueError("media_root must be absolute to bind reference paths unambiguously")
    media_root = raw_media_root.resolve()
    resolutions = {str(raw_media_root): str(media_root)}
    paths = []
    for name, item in dataset["dataset_names"].items():
        values = item["data_dir"]
        for value in ([values] if isinstance(values, str) else values):
            path = absolute_file(value, f"{name}.data_dir")
            paths.append(path)
            resolutions[value] = str(path)
    if not paths or len(set(paths)) != len(paths):
        raise ValueError("parquet paths must be nonempty and unique")
    receipts = {str(config_path): sha256_file(config_path)}
    image_paths, chain_ids = set(), set()
    rows = reference_rows = current_reference_rows = occurrences = 0
    for path in paths:
        parquet = pq.ParquetFile(path)
        if parquet.metadata.num_rows == 0:
            raise ValueError(f"empty training shard: {path}")
        receipts[str(path)] = sha256_file(path)
        for batch in parquet.iter_batches(batch_size=256):
            for row in batch.to_pylist():
                prompts = row.get("prompts")
                if not isinstance(prompts, list) or not prompts or any(
                    not isinstance(prompt, str) or not prompt.strip() for prompt in prompts
                ):
                    raise ValueError(f"invalid prompts in {row.get('sample_id')!r}")
                if len(row.get("video_paths") or []) != len(prompts) + 1:
                    raise ValueError("GT prefix must contain one more video than prompts")
                if row.get("target_round") != len(prompts):
                    raise ValueError("target_round must match prefix prompt count")
                if not isinstance(row.get("chain_id"), str) or not row["chain_id"]:
                    raise ValueError("chain_id is required for data binding")
                refs = normalize_reference_images(row)
                present = [value for value in refs if value is not None]
                if present and "vit" not in dataset.get("vision_cond_type", []):
                    raise ValueError("reference image conditioning requires the ViT stream")
                rows += 1
                chain_ids.add(row["chain_id"])
                reference_rows += bool(present)
                current_reference_rows += refs[-1] is not None
                occurrences += len(present)
                for value in present:
                    image_path = Path(value)
                    original_path = image_path if image_path.is_absolute() else media_root / image_path
                    if not image_path.is_absolute():
                        image_path = (media_root / image_path).resolve(strict=True)
                        if not image_path.is_relative_to(media_root):
                            raise ValueError("reference image path escapes media_root")
                    image_path = absolute_file(str(image_path), "reference_images")
                    resolutions[str(original_path)] = str(image_path)
                    if image_path in image_paths:
                        continue
                    with Image.open(image_path) as image:
                        if getattr(image, "n_frames", 1) != 1:
                            raise ValueError(f"reference must be one static image: {image_path}")
                        image.convert("RGB").load()
                    receipts[str(image_path)] = sha256_file(image_path)
                    image_paths.add(image_path)
    # A reference only in historical context does not demonstrate supervision
    # of an edit conditioned on its own image. Require current-turn examples.
    if require_reference and current_reference_rows == 0:
        raise ValueError("no current-turn reference examples; refusing reference-training preparation")
    return {
        "schema_version": SCHEMA, "dataset_config": str(config_path),
        "parquet_shards": len(paths), "rows": rows, "chains": len(chain_ids),
        "rows_with_reference_history": reference_rows,
        "rows_with_current_reference": current_reference_rows,
        "rows_without_reference": rows - reference_rows,
        "reference_occurrences": occurrences, "unique_images": len(image_paths),
        "files_sha256": receipts,
        "path_resolutions": resolutions,
        "validation_scope": "all row schemas, static-image decode and byte hashes; source/target videos and GPU token budgets not checked",
    }


def validate_reference_profile(profile):
    """Launcher hook: verify receipts again so image/parquet edits invalidate binding."""
    data = profile["data"]
    fields = {"reference_image_audit", "reference_image_audit_sha256", "reference_image_mode"}
    if not fields.intersection(data):
        return
    if not fields.issubset(data):
        raise ValueError("reference profile requires mode and audit path/hash together")
    if data.get("reference_image_mode") != MODE:
        raise ValueError("unsupported reference image conditioning mode")
    audit_path = absolute_file(data["reference_image_audit"], "reference audit")
    if sha256_file(audit_path) != data["reference_image_audit_sha256"]:
        raise ValueError("reference audit hash mismatch")
    report = json.loads(audit_path.read_text())
    if report.get("schema_version") != SCHEMA:
        raise ValueError("unsupported reference audit schema")
    verified = set()
    for split in ("train", "validation", "test"):
        audit = report["datasets"][split]
        config = workspace_path(profile["data"][split + "_config"])
        if str(config) != audit["dataset_config"]:
            raise ValueError(f"reference audit is bound to a different {split} config")
        receipts = audit["files_sha256"]
        for original, expected in audit["path_resolutions"].items():
            if str(Path(original).resolve(strict=True)) != expected:
                raise ValueError(f"reference data path changed since audit: {original}")
        if receipts.get(str(config)) != profile["data"][split + "_config_sha256"]:
            raise ValueError(f"reference audit lacks matching {split} YAML receipt")
        for name, expected in receipts.items():
            receipt = (name, expected)
            if receipt not in verified and sha256_file(absolute_file(name, "audit input")) != expected:
                raise ValueError(f"reference data changed since audit: {name}")
            verified.add(receipt)
    train = report["datasets"]["train"]
    if train["rows_with_current_reference"] <= 0:
        raise ValueError("reference training requires current-turn reference examples")
    if (train["rows"] != profile["data"]["train_prefixes"] or
            train["parquet_shards"] != profile["data"]["train_parquet_shards"]):
        raise ValueError("reference audit training counts differ from profile")


def prepare_profile(base_path, data_binding, run_name, output_dir):
    """Create a fresh disabled profile/recipe with full independently audited data."""
    from run_datamake_ddp_training import load_profile

    base = load_profile(base_path)
    if base["history"]["mode"] != "teacher_forced":
        raise ValueError("first reference-image version supports GT history only")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,119}", run_name):
        raise ValueError("run_name must be a simple, nonempty directory name")
    if run_name == base["run"]["run_name"]:
        raise ValueError("new reference run must have a distinct run_name")
    wandb_id = run_name.replace("_", "-")
    if wandb_id == base["wandb"]["run_id"]:
        raise ValueError("new reference run must have a distinct W&B run_id")
    if (workspace_path(base["run"]["output_root"]) / run_name).exists():
        raise FileExistsError("requested training run already exists")
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    data = deepcopy(data_binding)
    reference_keys = {"reference_image_audit", "reference_image_audit_sha256", "reference_image_mode"}
    if not isinstance(data, dict) or not set(base["data"]) - reference_keys <= set(data):
        raise ValueError("data-binding must supply the complete base profile data object")
    for key in DATA_FILES:
        path = absolute_file(data[key], key)
        data[key], data[key + "_sha256"] = str(path), sha256_file(path)
    report = {"schema_version": SCHEMA, "datasets": {}}
    for split in ("train", "validation", "test"):
        audit = audit_dataset(data[split + "_config"], require_reference=split == "train")
        report["datasets"][split] = audit
        for suffix, actual in (("prefixes", audit["rows"]), ("chains", audit["chains"])):
            if data[split + "_" + suffix] != actual:
                raise ValueError(f"{split}_{suffix} does not match parquet audit")
    expected_shards = base["distributed"]["gpus_per_node"] * base["run"]["num_workers_per_rank"]
    if data["train_parquet_shards"] != expected_shards or report["datasets"]["train"]["parquet_shards"] != expected_shards:
        raise ValueError("reference train shards must match rank/worker slots")
    audit_path, recipe_path = output_dir / "reference_audit.json", output_dir / "recipe.json"
    profile_path = output_dir / "profile.json"
    audit_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    data.update(reference_image_mode=MODE, reference_image_audit=str(audit_path),
                reference_image_audit_sha256=hashlib.sha256(audit_text.encode()).hexdigest())
    profile = deepcopy(base)
    profile.update(profile_id=run_name, created_at=date.today().isoformat(),
                   status="reference_data_audited_gpu_validation_pending", training_authorized=False)
    profile["data"] = data
    profile["run"]["run_name"] = run_name
    profile["run"]["data_seed_selection"] = "new reference dataset binding; indexed GT prefix schedule unchanged"
    profile["wandb"].update(run_id=wandb_id, group="single-reference-vit-v1")
    profile["wandb"]["tags"] = list(dict.fromkeys(base["wandb"]["tags"] + ["optional-reference-image", "vit-only"]))
    profile["ddp"]["source_profile"] = str(recipe_path)
    profile["slurm"]["job_script"] = None
    profile["preparation"]["gpu_validation"] = "pending; no training submitted by preparation"
    profile["source"]["overrides"] = "optional single-image ViT conditions, GT prefixes; new explicit data binding"
    profile["source"]["recipe_reference"] = str(recipe_path)
    recipe = deepcopy(profile)
    recipe["run"]["run_name"] += "_recipe"
    recipe["wandb"]["run_id"] += "-recipe"
    output_dir.mkdir(parents=True)
    for path, contents in ((audit_path, audit_text), (recipe_path, json.dumps(recipe, indent=2) + "\n"),
                           (profile_path, json.dumps(profile, indent=2) + "\n")):
        with path.open("x", encoding="utf-8") as stream:
            stream.write(contents)
    validate_reference_profile(profile)
    load_profile(profile_path)
    return profile_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--dataset-config", type=Path, required=True)
    audit.add_argument("--report", type=Path, required=True)
    audit.add_argument("--allow-no-reference", action="store_true", help="diagnostic audit only")
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--base-profile", type=Path, required=True)
    prepare.add_argument("--data-binding", type=Path, required=True)
    prepare.add_argument("--run-name", required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "audit":
        report = audit_dataset(args.dataset_config, require_reference=not args.allow_no_reference)
        with args.report.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(args.report)
    else:
        print(prepare_profile(args.base_profile, json.loads(args.data_binding.read_text()),
                              args.run_name, args.output_dir))


if __name__ == "__main__":
    main()
