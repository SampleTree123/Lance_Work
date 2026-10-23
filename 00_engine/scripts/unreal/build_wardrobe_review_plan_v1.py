"""Resolve approved family selections to verified wardrobe meshes and v002 slots."""

from __future__ import annotations

import argparse
import copy
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "character_creator"))
import cc_build_modular_outfit_pilot_v1 as family_rules
from modular_outfit_runtime_plan_v2 import compile_variant, read_json, write_json


def compile_review(registry: dict, template: dict, selection: dict,
                   reports: list[dict], *, allow_multiple: bool = False) -> dict:
    families = {f["document"]["family_id"]: f["document"] for f in registry["families"]}
    units = {u["unit_id"]: u for u in registry["units"]}
    bindings = {(b["family_id"], b["asset_id"]): b for b in registry["asset_bindings"]}
    transferred = {}
    for report in reports:
        if report.get("success") is not True:
            raise ValueError("Review requires successful transfer reports")
        for case in report["cases"]:
            if case.get("transfer_passed") is not True:
                raise ValueError(f"Transfer not passed: {case['case_id']}")
            for module in case["modules"]:
                key = (case["case_id"], module["module_key"])
                if key in transferred:
                    raise ValueError(f"Repeated transfer module: {key}")
                transferred[key] = module
    plan = copy.deepcopy(template)
    plan.update(plan_id=selection["review_id"], runtime_approved=False,
                source_library_id=registry["library_id"],
                status="fixed_slot_ready_for_blueprint_build",
                review_selection=copy.deepcopy(selection),
                usage="reuse_existing_blueprints_for_review_only")
    for body in plan["bodyfits"]:
        body.update(candidate_mesh_registry=[], candidate_mesh_count=0, runtime_variants=[])
    bodies = {b["bodyfit_id"]: b for b in plan["bodyfits"]}
    seen_variants = set()
    for choice in selection["outfits"]:
        document = families[choice["family_id"]]
        body = bodies[choice["bodyfit_id"]]
        if document["sex"] != body["sex"]:
            raise ValueError("Family and bodyfit sex differ")
        enabled = choice["family_asset_ids"]
        shoes = choice.get("shared_shoe_ids", [])
        if len(enabled) != len(set(enabled)) or len(shoes) != len(set(shoes)):
            raise ValueError("Repeated asset in selection")
        selected = [{"asset_id": aid, "source": "family"} for aid in enabled]
        selected += [{"asset_id": aid, "source": "shared_inventory"} for aid in shoes]
        family_rules.validate_runtime_variant(
            document, family_rules.group_for(document, choice["group_id"]), selected)
        qualified = f"{choice['family_id']}::{choice['variant_id']}"
        if qualified in seen_variants:
            raise ValueError(f"Repeated review variant: {qualified}")
        seen_variants.add(qualified)
        sources = {}
        pairs = [(choice["family_id"], aid) for aid in enabled]
        pairs += [(f"{body['sex']}.SharedFootwear", aid) for aid in shoes]
        for pair in pairs:
            binding = bindings[pair]
            unit = units[binding["unit_id"]]
            if unit["bodyfit_id"] != body["bodyfit_id"]:
                raise ValueError(f"Wrong transferred bodyfit: {pair}")
            module = transferred[(binding["unit_id"], binding["module_key"])]
            for i, mesh in enumerate(module["mesh_paths"]):
                name = "Candidate_" + hashlib.sha256(mesh.encode("utf-8")).hexdigest()[:20]
                sources[name] = {
                    "component_name": name, "case_id": unit["unit_id"],
                    "qualified_module_id": f"{unit['unit_id']}::{module['module_key']}",
                    "module_key": module["module_key"], "slot": module["slot"],
                    "mesh_path": mesh, "mesh_name": module["mesh_names"][i],
                }
        variant = compile_variant({
            "qualified_variant_id": qualified, "variant_id": choice["variant_id"],
            "case_id": choice["family_id"], "enabled_component_names": list(sources),
            "purpose": "manual fit and motion review; not production approval",
        }, sources)
        if body["runtime_variants"] and not allow_multiple:
            raise ValueError("Review currently supports one outfit per bodyfit")
        body["runtime_variants"].append(variant)
        existing_paths = {c["mesh_path"] for c in body["candidate_mesh_registry"]}
        body["candidate_mesh_registry"].extend(
            c for c in sources.values() if c["mesh_path"] not in existing_paths)
        body["candidate_mesh_count"] = len(body["candidate_mesh_registry"])
    if any(not b["runtime_variants"] for b in bodies.values()):
        raise ValueError("Provide one complete outfit for each bodyfit")
    plan["runtime_variant_count"] = len(seen_variants)
    plan["candidate_mesh_count"] = sum(b["candidate_mesh_count"] for b in bodies.values())
    return plan


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--transfer-report", type=Path, action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise ValueError(f"Refusing to overwrite: {args.output}")
    registry = read_json(args.registry)
    for record in registry["families"]:
        family_rules.verify_file(record["manifest"], "Family contract")
    reports = [read_json(path) for path in args.transfer_report]
    for report in reports:
        family_rules.verify_file(report["manifest"], "Finalized import manifest")
    plan = compile_review(registry, read_json(args.template), read_json(args.selection), reports)
    plan["source_evidence"] = [
        family_rules.verify_file({"path": str(path.resolve())}, "Review input")
        for path in [args.registry, args.template, args.selection, *args.transfer_report]
    ]
    write_json(args.output, plan)
    print(f"Review plan: {args.output}; outfits={plan['runtime_variant_count']}")


if __name__ == "__main__":
    main()
