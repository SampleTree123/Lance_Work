"""Build the 40-item scalp-hair export manifest from the user-reviewed pool."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_token(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return value[:48] or "hair"


def build(source_manifest: Path, review_path: Path, decisions_path: Path,
          catalog_path: Path, output_manifest: Path, export_root: Path,
          project_root: Path):
    source = read_json(source_manifest)
    review = read_json(review_path)
    decisions = read_json(decisions_path).get("decisions", {})
    catalog = read_json(catalog_path)
    catalog_by_id = {item["asset_id"]: item for item in catalog.get("assets", [])}
    source_presets = source.get("presets") or []
    if len(source_presets) != 1:
        raise ValueError("source manifest must contain exactly one pilot preset")
    template = source_presets[0]

    selected = []
    for item in review.get("items", []):
        asset_id = item.get("asset_id")
        decision = decisions.get(asset_id, {}).get("decision")
        if decision == "remove":
            continue
        if asset_id not in catalog_by_id:
            raise ValueError(f"reviewed hair asset missing from catalog: {asset_id}")
        selected.append(item)
    if len(selected) != 40:
        raise ValueError(f"expected 40 retained hair assets, found {len(selected)}")

    presets = []
    for item in selected:
        asset_id = item["asset_id"]
        catalog_item = catalog_by_id[asset_id]
        pack = item.get("hair_builder_pack") or {}
        pack_code = str(pack.get("pack_code") or "HAIR")
        asset_index = int(pack.get("asset_index") or item.get("sequence"))
        ordinal = f"{asset_index:02d}"
        stem = f"{pack_code}_{ordinal}"
        case_dir = export_root / f"HAIR_{stem}_F"
        preset = copy.deepcopy(template)
        preset["preset_id"] = f"HAIR_{stem}_F_BATCH20260924"
        preset["scalp_hair_asset_id"] = asset_id
        preset["scalp_hair_display_name"] = catalog_item.get("display_name") or item.get("display_name")
        preset["appearance_asset_ids"] = [asset_id]
        preset["appearance_recipe"] = {
            "assets": [{
                "asset_form": "group",
                "asset_id": asset_id,
                "display_name": preset["scalp_hair_display_name"],
                "sex_hint": catalog_item.get("sex_hint", "unknown"),
                "slot": "scalp_hair",
            }],
            "validated_preset_id": None,
        }
        assembly = preset.get("facial_assembly")
        if isinstance(assembly, dict):
            old_id = template.get("scalp_hair_asset_id")
            ids = list(assembly.get("asset_ids") or [])
            if old_id in ids:
                ids[ids.index(old_id)] = asset_id
            elif ids:
                ids[-1] = asset_id
            assembly["asset_ids"] = ids
        preset["production_output"] = {
            "project_path": str(project_root / f"F02_Average_{safe_token(stem)}.ccProject"),
            "export_root": str(case_dir / "fbx"),
            "export_basename": f"CC_HAIR_F_{stem}",
            "export_timeout_seconds": 900,
            "skip_preview_capture": True,
            "export_motion": False,
        }
        preset["batch_hair_metadata"] = {
            "sequence": item.get("sequence"),
            "asset_id": asset_id,
            "display_name": preset["scalp_hair_display_name"],
            "pack_code": pack_code,
            "asset_index": asset_index,
            "decision": "retain_pending_ue_visual_compatibility",
        }
        presets.append(preset)

    document = copy.deepcopy(source)
    document["library_id"] = "cc5_hair_builder_scalp_hair_female_neutral_batch_20260924_v1"
    document["diagnostic_mode"] = "scalp_hair_export_existing_project"
    document["presets"] = presets
    document["character_count"] = len(presets)
    document["requested_character_count"] = len(presets)
    document["selection"] = {
        "source_review": str(review_path),
        "source_decisions": str(decisions_path),
        "source_catalog": str(catalog_path),
        "target": "female_neutral_body",
        "retained_count": len(presets),
        "policy": "all user-retained 40 Hair Builder candidates; remove decisions excluded",
    }
    document["status"] = "batch_ready_for_cc_export"
    write_json(output_manifest, document)
    return document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()
    document = build(args.source_manifest.resolve(), args.review.resolve(), args.decisions.resolve(),
                     args.catalog.resolve(), args.output_manifest.resolve(),
                     args.export_root.resolve(), args.project_root.resolve())
    print(f"Built {len(document['presets'])} retained scalp-hair export presets")
    print(args.output_manifest.resolve())


if __name__ == "__main__":
    main()
