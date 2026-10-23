#!/usr/bin/env python3
"""Compile deduplicated Average bodyfit garment exports; preserve outfit rules."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import cc_build_modular_outfit_pilot_v1 as pilot


SLOT_DIRS = {
    "coats": "Coats", "shirts": "Shirts", "pants": "Pants",
    "skirts": "Skirts", "full_body": "FullBody", "shoes": "Shoes",
    "family_accessory": "Accessories",
}
DEFAULT_ROOT = Path(r"D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted")
DEFAULT_OUTPUT = pilot.SCRIPT_ROOT / "runtime_staging" / "wardrobe_average_20260906_v2"
DEFAULT_EXPORT = Path(r"D:\UE\exports\character_creator\wardrobe_average_20260906_v1")
VENDOR = "/Game/Vendor/Reallusion/CC5/Wardrobe"


def segment(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    if not result:
        raise ValueError(f"No safe asset segment: {value!r}")
    return result


def unit_key(sex: str, modules: list[dict], locked: bool) -> str:
    # Slots and import fit policies affect reuse even when source bytes match.
    value = [sex, locked, [
        [m["sha256"], m["slot"], m["cloth_options_policy"]] for m in modules
    ]]
    digest = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return ("M_" if sex == "male" else "F_") + digest[:20]


def compile_library(root: Path, export_root: Path) -> tuple[dict, dict, dict]:
    template = pilot.read_json(pilot.DEFAULT_CC_OUTPUT)
    previous = pilot.read_json(pilot.DEFAULT_UE_OUTPUT)
    bodies = {b["bodyfit_id"]: copy.deepcopy(b) for b in template["bodyfits"]}
    for body in bodies.values():
        body["source_project"] = pilot.verify_file(body["source_project"], "BodyFit")
    aliases, alias_evidence = pilot.load_aliases(pilot.DEFAULT_ALIAS_REGISTRY)
    shoes, shoe_evidence = pilot.shoe_inventory_index(
        {"path": str(root / "both" / "shoes" / "shoe_inventory.json")}
    )
    registry = {
        "schema_version": 1, "library_id": export_root.name,
        "scope": "average_bodyfits_garment_export_and_manual_ue_review",
        "bodyfits": list(bodies.values()), "families": [], "units": [],
        "asset_bindings": [], "shared_shoe_inventory": shoe_evidence,
        "compatibility_alias_registry": alias_evidence,
        "runtime_approved": False,
        "policy": {
            "cross_family_mixing": False,
            "export_unit_is_not_an_approved_outfit": True,
            "garment_fit_review": "pending_in_ue",
            "hair_beard_review": "deferred",
        },
    }
    units: dict[str, dict] = {}
    required_shoes: set[tuple[str, str]] = set()

    def resolve_module(directory, asset):
        if Path(asset["path"]).suffix.lower() == ".ccgloves" and asset["sha256"] not in aliases:
            source = pilot.verify_file({
                "path": str(directory / asset["path"]),
                "sha256": asset["sha256"], "size_bytes": asset["size_bytes"],
            }, "Gloves source")
            target = (pilot.LANCE_ROOT / "00_engine/assets/character_creator/"
                      "outfit_compatibility_aliases" / "wardrobe" /
                      (asset["sha256"] + ".ccCloth"))
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source["path"], target)
            alias = pilot.verify_file({"path": str(target), "sha256": source["sha256"],
                                       "size_bytes": source["size_bytes"]}, "Gloves alias")
            aliases[source["sha256"]] = {
                "source": source, "alias": alias,
                "alias_id": "wardrobe_gloves_" + asset["sha256"][:20],
            }
        return pilot.resolve_family_asset(directory, asset, aliases)

    def register(sex: str, family_id: str, modules: list[dict], locked=False):
        key = unit_key(sex, modules, locked)
        family_segment = segment(family_id.split(".", 1)[-1])
        category = "Bundle" if locked else SLOT_DIRS[modules[0]["slot"]]
        location = f"{sex.title()}/Average/{family_segment}/{category}/{key}"
        if key not in units:
            units[key] = {
                "unit_id": key, "sex": sex,
                "bodyfit_id": pilot.AVERAGE_BODYFITS[sex],
                "locked_bundle": locked, "modules": modules,
                "relative_directory": location,
                "ue_case_root": f"{VENDOR}/{location}",
                "fit_review": "pending", "export_status": "pending",
            }
        for index, module in enumerate(modules):
            registry["asset_bindings"].append({
                "family_id": family_id, "asset_id": module["asset_id"],
                "unit_id": key, "module_key": units[key]["modules"][index]["module_key"],
                "source_path": module["source_path"],
            })

    for sex in ("male", "female"):
        for directory in sorted((root / sex).iterdir()):
            if not directory.is_dir():
                continue
            path = directory / "outfit_family.json"
            doc = pilot.read_json(path)
            if doc.get("sex") != sex or doc.get("rules_status") != "confirmed":
                raise ValueError(f"Unconfirmed or wrong-sex family: {path}")
            records = pilot.asset_index(doc)
            modules = {aid: resolve_module(directory, a)
                       for aid, a in records.items()}
            registry["families"].append({
                "manifest": pilot.verify_file({"path": str(path)}, "Family"),
                "document": doc,
            })
            mode = doc.get("assembly_mode")
            if mode == "locked_bundle":
                ids = doc["assembly"]["bundle"]["required_assets"]
                if set(ids) != set(records) or len(ids) != len(set(ids)):
                    raise ValueError(f"Locked bundle does not cover family: {path}")
                register(sex, doc["family_id"], [modules[aid] for aid in ids], True)
            elif mode == "slot_groups":
                for module in modules.values():
                    register(sex, doc["family_id"], [module])
            else:
                raise ValueError(f"Unsupported assembly mode: {path}: {mode}")
            footwear = doc.get("footwear_policy") or {}
            if footwear.get("mode") == "shared_pool":
                for shoe_id in footwear.get("allowed_shared_shoe_ids", []):
                    required_shoes.add((sex, shoe_id))
    for sex, shoe_id in sorted(required_shoes):
        register(sex, f"{sex}.SharedFootwear", [pilot.resolve_shared_shoe(shoes[shoe_id], sex)])

    registry["units"] = list(units.values())
    registry["counts"] = {
        "families": len(registry["families"]), "export_units": len(units),
        "by_sex": dict(Counter(u["sex"] for u in units.values())),
        "source_bindings": len(registry["asset_bindings"]),
        "unique_modules": sum(len(u["modules"]) for u in units.values()),
        "shared_shoes_referenced": len(required_shoes),
        "locked_bundles": sum(u["locked_bundle"] for u in units.values()),
    }
    cc = copy.deepcopy(template)
    cc.update(pilot_id=export_root.name, library_id=export_root.name,
              revision_id="unique_asset_average_v1", status="export_pending",
              output_root=str(export_root), presets=[], counts=registry["counts"],
              scope=registry["policy"], bodyfits=list(bodies.values()),
              shared_shoe_inventory=shoe_evidence)
    for obsolete in ("source_spec", "frozen_at"):
        cc.pop(obsolete, None)
    ue = {
        "schema_version": 1, "pilot_id": export_root.name,
        "manifest_id": export_root.name, "status": "export_pending",
        "import_scope": "wardrobe_average_v1",
        "bodyfits": list(bodies.values()), "cases": [],
        "families": registry["families"],
    }
    for base in previous["cases"]:
        if base["case_role"] == "base_body":
            base = copy.deepcopy(base)
            base["ue_case_root"] = (
                "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/"
                f"{base['bodyfit_id']}/Cases/{base['case_id']}"
            )
            base["reuse_existing_base"] = True
            ue["cases"].append(base)
    for unit in units.values():
        uid = unit["unit_id"]
        body = bodies[unit["bodyfit_id"]]
        destination = export_root / unit["relative_directory"]
        basename = f"CC_WD_{uid}"
        planned = {
            "root": str(destination / "fbx"),
            "fbx": str(destination / "fbx" / f"{basename}.fbx"),
            "json": str(destination / "fbx" / f"{basename}.json"),
            "project": str(destination / f"{basename}.ccProject"),
        }
        preset = copy.deepcopy(template["presets"][0])
        preset.update(
            preset_id=uid, case_id=uid, case_role="outfit_modules",
            output_directory_name=uid, look_id=uid,
            subject_id=unit["bodyfit_id"], sex=unit["sex"],
            bodyfit_id=unit["bodyfit_id"], source_project=body["source_project"],
            selected_assets=copy.deepcopy(unit["modules"]),
            allow_empty_selected_assets=False, coverage_tags=["wardrobe_export_unit"],
            production_output={
                "project_path": planned["project"], "export_root": planned["root"],
                "export_basename": basename, "export_timeout_seconds": 1200.0,
                "skip_preview_capture": True,
            },
        )
        cc["presets"].append(preset)
        ue["cases"].append({
            "case_id": uid, "case_role": "outfit_modules", "sex": unit["sex"],
            "bodyfit_id": unit["bodyfit_id"], "source_project": body["source_project"],
            "modules": unit["modules"], "planned_export": planned,
            "ue_case_root": unit["ue_case_root"], "runtime_variants": [],
            "validation_status": "export_pending",
        })
    cc["counts"] = {**registry["counts"], "case_count": len(cc["presets"])}
    ue["counts"] = {**registry["counts"], "case_count": len(ue["cases"])}
    return registry, cc, ue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"Use a new manifest directory: {args.output_dir}")
    registry, cc, ue = compile_library(args.root.resolve(), args.export_root.resolve())
    for name, doc in (("wardrobe_registry.json", registry), ("cc_export.json", cc),
                      ("ue_import.json", ue)):
        pilot.write_json(args.output_dir / name, doc)
    print(json.dumps(registry["counts"], indent=2))


if __name__ == "__main__":
    main()
