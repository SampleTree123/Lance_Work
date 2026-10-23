"""Build deterministic, non-exhaustive outfit witnesses for every imported mesh."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from build_wardrobe_review_plan_v1 import compile_review, family_rules
from modular_outfit_runtime_plan_v2 import read_json, write_json


def groups(document):
    if document["assembly_mode"] == "locked_bundle":
        return [document["assembly"]["bundle"]]
    if document["assembly_mode"] != "slot_groups":
        raise ValueError(f"Unsupported assembly mode: {document['family_id']}")
    return document["assembly"]["groups"]


def allowed_ids(group):
    result = set(group.get("required_assets", [])) | set(group.get("optional_assets", []))
    for slot in group.get("required_slots", []) + group.get("optional_slots", []):
        result.update(group.get("slot_pools", {}).get(slot, []))
    return result


def make_choice(document, group, uncovered, shoe_id=None):
    if group.get("optional_assets") and group.get("optional_asset_policy") != "independent_subset":
        raise ValueError("Unknown optional accessory policy")
    ids = list(group.get("required_assets", []))
    # All approved independent accessories may appear together in this witness.
    ids.extend(group.get("optional_assets", []))
    for slot in group.get("required_slots", []) + group.get("optional_slots", []):
        pool = group["slot_pools"][slot]
        if not pool:
            if slot in group.get("required_slots", []):
                raise ValueError(f"Empty required pool: {document['family_id']}/{slot}")
            continue
        ids.append(next((aid for aid in pool if aid in uncovered), pool[0]))
    footwear = document["footwear_policy"]
    shoes = []
    if footwear["mode"] == "shared_pool":
        pool = footwear.get("allowed_shared_shoe_ids", [])
        if shoe_id is None and pool:
            shoe_id = pool[0]
        if shoe_id:
            shoes = [shoe_id]
    choice = {
        "bodyfit_id": "M02_Average" if document["sex"] == "male" else "F02_Average",
        "family_id": document["family_id"],
        "family_display_name": document.get("display_name", document["family_id"]),
        "group_id": group.get("group_id", group.get("bundle_id")),
        "family_asset_ids": list(dict.fromkeys(ids)), "shared_shoe_ids": shoes,
    }
    selected = [{"asset_id": aid, "source": "family"} for aid in choice["family_asset_ids"]]
    selected += [{"asset_id": aid, "source": "shared_inventory"} for aid in shoes]
    family_rules.validate_runtime_variant(document, group, selected)
    return choice


def build_selection(registry, review_id):
    choices = []
    covered_shoes = set()
    for record in registry["families"]:
        doc = record["document"]
        if doc.get("rules_status") != "confirmed":
            raise ValueError(f"Unconfirmed family: {doc['family_id']}")
        remaining = set(family_rules.asset_index(doc))
        for group in groups(doc):
            first = True
            while first or remaining & allowed_ids(group):
                first = False
                pool = doc["footwear_policy"].get("allowed_shared_shoe_ids", [])
                shoe = next((s for s in pool if (doc["sex"], s) not in covered_shoes), None)
                choice = make_choice(doc, group, remaining, shoe)
                gained = remaining & set(choice["family_asset_ids"])
                choices.append(choice)
                remaining -= gained
                covered_shoes.update((doc["sex"], s) for s in choice["shared_shoe_ids"])
                if not gained and remaining & allowed_ids(group):
                    raise ValueError(f"Cannot cover assets without changing rules: {doc['family_id']}")
        if remaining:
            raise ValueError(f"Family assets outside approved groups: {doc['family_id']}: {sorted(remaining)}")
    # Shared shoes are deduplicated library assets, not a reason to multiply every family.
    required_shoes = {(b["family_id"].split('.')[0], b["asset_id"])
                      for b in registry["asset_bindings"] if b["family_id"].endswith('.SharedFootwear')}
    for sex, shoe in sorted(required_shoes - covered_shoes):
        document = next((f["document"] for f in registry["families"]
                         if f["document"]["sex"] == sex and
                         shoe in f["document"]["footwear_policy"].get("allowed_shared_shoe_ids", [])), None)
        if document is None:
            raise ValueError(f"No approved outfit for shared shoe: {sex}/{shoe}")
        choices.append(make_choice(document, groups(document)[0], set(), shoe))
    choices.sort(key=lambda c: (c["family_id"], c["group_id"]))
    for index, choice in enumerate(choices, 1):
        choice["variant_id"] = f"coverage_{index:03d}"
        choice["review_index"] = index
    return {"review_id": review_id, "outfits": choices,
            "policy": "one_or_more_approved_outfit_witnesses_per_mesh_not_cartesian_product"}


def compile_coverage(registry, template, reports, review_id):
    selection = build_selection(registry, review_id)
    plan = compile_review(registry, template, selection, reports, allow_multiple=True)
    expected = {p for report in reports for case in report["cases"]
                for module in case["modules"] for p in module["mesh_paths"]}
    if not expected:
        raise ValueError("Empty transferred wardrobe")
    witnesses = {path: [] for path in sorted(expected)}
    lookup = {v["qualified_variant_id"]: v for b in plan["bodyfits"] for v in b["runtime_variants"]}
    bindings = {(b["family_id"], b["asset_id"]): b for b in registry["asset_bindings"]}
    assets = {(f["document"]["family_id"], a["asset_id"]): a
              for f in registry["families"] for a in f["document"]["assets"]}
    pages = []
    for choice in selection["outfits"]:
        qid = f"{choice['family_id']}::{choice['variant_id']}"
        variant = lookup[qid]
        choice["qualified_variant_id"] = qid
        choice["assets"] = []
        pairs = [(choice["family_id"], aid) for aid in choice["family_asset_ids"]]
        sex = choice["family_id"].split('.')[0]
        pairs += [(f"{sex}.SharedFootwear", aid) for aid in choice["shared_shoe_ids"]]
        for pair in pairs:
            binding = bindings[pair]
            choice["assets"].append({
                "asset_id": pair[1], "source_path": binding.get("source_path"),
                "display_name": assets.get(pair, {}).get("display_name", pair[1]),
                "unit_id": binding["unit_id"], "module_key": binding["module_key"],
            })
        for path in {a["mesh_path"] for a in variant["assignments"]}:
            witnesses[path].append(choice["review_index"])
        # Two outfits per page, never share a page across family boundaries.
        if not pages or pages[-1]["family_id"] != choice["family_id"] or len(pages[-1]["review_indices"]) == 2:
            pages.append({"page": len(pages) + 1, "family_id": choice["family_id"], "review_indices": []})
        pages[-1]["review_indices"].append(choice["review_index"])
        choice["page"] = pages[-1]["page"]
    uncovered = [p for p, indices in witnesses.items() if not indices]
    if uncovered:
        raise ValueError(f"Uncovered imported meshes: {uncovered}")
    plan["review_selection"] = selection
    plan["coverage"] = {
        "scope": "all_imported_meshes_in_at_least_one_approved_outfit",
        "planned_mesh_count": len(witnesses), "uncovered_mesh_paths": uncovered,
        "outfit_count": len(selection["outfits"]), "page_count": len(pages),
        "by_sex": dict(Counter(c["family_id"].split('.')[0] for c in selection["outfits"])),
        "mesh_witnesses": witnesses, "pages": pages,
        "assembly_execution": "pending", "visual_acceptance": "pending",
        "does_not_prove": ["all_combinations", "all_motion_fit", "hair_compatibility", "occluded_inner_surface_quality"],
    }
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--reports-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    registry = read_json(args.registry)
    for record in registry["families"]:
        family_rules.verify_file(record["manifest"], "Frozen Family contract")
    paths = sorted(args.reports_root.glob("batch_*/wardrobe_modules.json"))
    reports = [read_json(p) for p in paths]
    for report in reports:
        family_rules.verify_file(report["manifest"], "Finalized transfer manifest")
    plan = compile_coverage(registry, read_json(args.template), reports, args.output.parent.name)
    plan["source_evidence"] = [family_rules.verify_file({"path": str(p.resolve())}, "Coverage input")
                               for p in [args.registry, args.template, *paths]]
    write_json(args.output, plan)
    write_json(args.output.with_name("coverage_index.json"), {
        "coverage": plan["coverage"], "outfits": plan["review_selection"]["outfits"]})
    print({k: v for k, v in plan["coverage"].items() if k not in ("mesh_witnesses", "pages")})


if __name__ == "__main__":
    main()
