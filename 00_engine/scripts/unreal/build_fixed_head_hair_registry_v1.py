"""Publish an independent dual-fit wardrobe index from a completed UE import.

Does not launch CC/UE or overwrite the preserved single-fit registry. The
hash-bound publication receipt switches default consumers to the new index.
Usage: python build_fixed_head_hair_registry_v1.py --report <import_report.json>
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from formal_wardrobe_registry_v1 import LEGACY_REGISTRY, validate_registry


ENGINE = Path(__file__).resolve().parents[2]
BATCH_ID = "fixed_head_hair_20261004_v1"
DEFAULT_REPORT = ENGINE / f"outputs/unreal_character_import/{BATCH_ID}/import_report.json"
DEFAULT_OUTPUT = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_registry(source: dict, report: dict) -> dict:
    validate_registry(source)
    if report.get("batch_id") != BATCH_ID:
        raise ValueError("import report belongs to another batch")
    if report.get("success") is not True or report.get("complete") is not True:
        raise ValueError("publish requires a completed successful UE import")
    hair_ids = {h["hair_id"] for h in source["hair_assets"]}
    if len(hair_ids) != 40:
        raise ValueError("source must contain exactly the 40 retained hairstyles")
    expected = {(hair_id, sex) for hair_id in hair_ids for sex in ("male", "female")}
    records = report.get("records", [])
    pairs = [(r.get("hair_id"), r.get("sex")) for r in records]
    if len(pairs) != 80 or set(pairs) != expected:
        raise ValueError("report must contain each retained hairstyle/sex pair exactly once (80/80)")
    root = report.get("ue_root")
    if not isinstance(root, str) or not root.startswith("/Game/DataMake/CharacterFactory/"):
        raise ValueError("missing independent UE batch root")
    if root == "/Game/DataMake/CharacterFactory" or root.endswith("/Hair"):
        raise ValueError("report root must identify the new batch")
    by_pair = dict(zip(pairs, records))
    result = deepcopy(source)
    skeletons: dict[str, str] = {}
    for hair in result["hair_assets"]:
        hair.pop("meshes", None)
        hair.pop("preset_id", None)  # Obsolete female-only CC export identifier.
        hair["fit_variants"] = {}
        for sex in ("female", "male"):
            row = by_pair[(hair["hair_id"], sex)]
            if row.get("success") is not True:
                raise ValueError(f"unsuccessful case: {hair['hair_id']}/{sex}")
            skeleton = row.get("skeleton_path")
            if not isinstance(skeleton, str) or not skeleton.startswith(root + "/"):
                raise ValueError(f"Skeleton escapes new batch root: {hair['hair_id']}/{sex}")
            if skeletons.setdefault(sex, skeleton) != skeleton:
                raise ValueError(f"{sex} cases do not share one Skeleton")
            meshes = row.get("meshes")
            if not isinstance(meshes, list) or not meshes:
                raise ValueError(f"missing meshes: {hair['hair_id']}/{sex}")
            fit_meshes = []
            for mesh in meshes:
                path = mesh.get("path", "")
                if not path.startswith(root + "/"):
                    raise ValueError(f"mesh escapes new batch root: {path}")
                fit_meshes.append({key: deepcopy(mesh[key]) for key in ("name", "path", "materials") if key in mesh})
            hair["fit_variants"][sex] = {"skeleton_path": skeleton, "meshes": fit_meshes}
    if skeletons["male"] == skeletons["female"]:
        raise ValueError("male and female references must retain separate shared Skeletons")
    validate_registry(result)
    assert result["families"] == source["families"]
    assert result["shared_shoe_assets"] == source["shared_shoe_assets"]
    assert [(h["hair_id"], h["sex"]) for h in result["hair_assets"]] == [
        (h["hair_id"], h["sex"]) for h in source["hair_assets"]]
    return result


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-registry", type=Path, default=LEGACY_REGISTRY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.resolve() in {LEGACY_REGISTRY.resolve(), args.source_registry.resolve()}:
        raise ValueError("publish to an independent version; accepted source registry is protected")
    result = build_registry(read(args.source_registry), read(args.report))
    write_atomic(args.output, result)
    provenance = {
        "schema_version": 1, "batch_id": BATCH_ID, "success": True,
        "source_registry": str(args.source_registry.resolve()),
        "source_registry_sha256": hashlib.sha256(args.source_registry.read_bytes()).hexdigest(),
        "import_report": str(args.report.resolve()),
        "import_report_sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
        "output_registry": str(args.output.resolve()),
        "output_registry_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "counts": {"hairstyles": 40, "fits": 80},
        "families_and_usage_permissions_preserved": True,
    }
    write_atomic(args.report.parent / "registry_publication_report.json", provenance)
    print(json.dumps(provenance, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
