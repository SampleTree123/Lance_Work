"""Prepare one isolated scalp-hair CC export manifest from the frozen hair batch."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def prepare(source: Path, output: Path, preset_id: str, export_root: Path,
            project_path: Path, export_basename: str, source_preset_id: str | None = None,
            hair_asset_id: str | None = None):
    source_doc = read_json(source)
    presets = source_doc.get("presets")
    if not isinstance(presets, list):
        raise ValueError("source manifest has no presets list")
    source_preset_id = source_preset_id or preset_id
    matches = [item for item in presets if item.get("preset_id") == source_preset_id]
    if len(matches) != 1:
        raise ValueError("expected one preset {}, found {}".format(source_preset_id, len(matches)))

    document = copy.deepcopy(source_doc)
    preset = copy.deepcopy(matches[0])
    preset["preset_id"] = preset_id
    if hair_asset_id:
        preset["scalp_hair_asset_id"] = hair_asset_id
        assembly = preset.get("facial_assembly")
        if isinstance(assembly, dict):
            canonical_order = [
                "skin", "age_morph", "dynamic_wrinkle_profile", "teeth",
                "eyebrows", "eyelashes", "eyes_material_only", "facial_hair",
                "scalp_hair", "shared_hair_pigmentation",
                "face_material_quality_profile",
            ]
            assembly["application_order"] = canonical_order
            asset_ids = list(assembly.get("asset_ids") or [])
            old_hair = matches[0].get("scalp_hair_asset_id")
            if old_hair in asset_ids:
                asset_ids[asset_ids.index(old_hair)] = hair_asset_id
            elif asset_ids:
                asset_ids[-1] = hair_asset_id
            assembly["asset_ids"] = asset_ids
        preset["appearance_asset_ids"] = [hair_asset_id]
        preset["appearance_recipe"] = {
            "assets": [{
                "asset_form": "group",
                "asset_id": hair_asset_id,
                "display_name": "Curly long ponytail",
                "sex_hint": "unknown",
                "slot": "scalp_hair",
            }],
            "validated_preset_id": None,
        }
    preset["production_output"] = {
        "project_path": str(project_path),
        "export_root": str(export_root),
        "export_basename": export_basename,
        "export_timeout_seconds": 900,
        "skip_preview_capture": True,
    }
    document["presets"] = [preset]
    document["library_id"] = "cc5_hair_builder_scalp_hair_female_neutral_export_pilot_v1"
    document["selection"] = {
        "source_library": str(source),
        "preset_id": preset_id,
        "target": "female_neutral_body",
        "purpose": "first_export_smoke_test",
    }
    document["status"] = "pilot_ready"
    write_json(output, document)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preset-id", required=True)
    parser.add_argument("--source-preset-id")
    parser.add_argument("--hair-asset-id")
    parser.add_argument("--diagnostic-mode")
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--project-path", type=Path, required=True)
    parser.add_argument("--export-basename", required=True)
    args = parser.parse_args()
    prepare(
        args.source.resolve(),
        args.output.resolve(),
        args.preset_id,
        args.export_root.resolve(),
        args.project_path.resolve(),
        args.export_basename,
        args.source_preset_id,
        args.hair_asset_id,
    )
    if args.diagnostic_mode:
        document = read_json(args.output.resolve())
        document["diagnostic_mode"] = args.diagnostic_mode
        write_json(args.output.resolve(), document)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
