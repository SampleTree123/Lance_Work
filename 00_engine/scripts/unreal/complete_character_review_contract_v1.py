"""Read-only catalog for the complete-character clothing/hair review.

Index 0 is reserved by the consumer for no outfit, no hair, or a static pose.
The historical plan supplies accepted choices; all mesh assignments are freshly
resolved against its preserved material-repair registry. The filtered fixed-slot
review uses a separate catalog. This catalog does not certify
clothing fit, animation retargeting, or skeleton compatibility on the new bodies.
Action availability follows the current graph and action pool, with a disk-only
package existence check. Historical import receipts alone are not availability.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import formal_wardrobe_registry_v1 as formal


ENGINE = Path(__file__).resolve().parents[2]
SOURCE_PLAN = ENGINE / "outputs/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/review_plan.json"
RUN_ROOT = ENGINE / "outputs/unreal_character_import/complete_character_skeleton_pilot_20261005_v1"
STANDARD_REGISTRY = RUN_ROOT / "standard_candidate_registry.json"
CURRENT_ACTION_REGISTRY = ENGINE / "assets/character_creator/current_review_actions_20261012_v1.json"
CURRENT_ACTION_GRAPH = ENGINE / "scripts/dataset/first_batch_graph_source_20260824_v1.json"
CURRENT_ACTION_POOL = ENGINE / "scripts/character_creator/cc_first_batch_action_pool_20260824_v1.json"
PROJECT_CONTENT = ENGINE.parents[1] / "projects/datatry_02/Content"
ACTION_IDS = {
    "female": (
        "ACT_F03_AUDIENCE_01", "ACT_F02_CATCH_BREATH",
        "ACT_F05_TIE_SHOES", "ACT_F06_ELEVATOR_GREETING", "ACT_F01_SEXY_DANCE",
    ),
    "male": (
        "ACT_M02_AUDIENCE_01", "ACT_M05_ELEVATOR_GREETING",
        "ACT_M04_LIVING_ROOM_SWING", "ACT_M06_CHEER_HANDS_STEP_DANCE", "ACT_M01_BATTLE_DANCE",
    ),
}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _source(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _english_label(value: str, fallback: str) -> str:
    return value if value and value.isascii() else fallback.replace("_", " ").title()


def current_actions(sources: dict) -> dict:
    """Read the durable current catalog, not removed historical output receipts.

    UE packages match retained copy receipts. This does not re-certify the deleted
    original import audit or cross-sex retargeting. Rebuilt FBXs are current inputs.
    """
    registry = _read(CURRENT_ACTION_REGISTRY)
    graph, pool = _read(CURRENT_ACTION_GRAPH), _read(CURRENT_ACTION_POOL)
    sources.update(current_action_registry=_source(CURRENT_ACTION_REGISTRY),
                   current_action_graph=_source(CURRENT_ACTION_GRAPH),
                   current_action_pool=_source(CURRENT_ACTION_POOL),
                   action_reports={}, action_packages={})
    by_id = {r["action_id"]: r for r in registry["records"]}
    expected = {a for ids in ACTION_IDS.values() for a in ids}
    if len(registry["records"]) != 10 or set(by_id) != expected:
        raise ValueError("Current action catalog must contain exactly ten retained actions")
    excluded = {r["action_id"] for r in pool["excluded_actions"]}
    actions = {"male": [], "female": []}
    for sex, ids in ACTION_IDS.items():
        if (set(ids) != {a.upper() for a in graph["actions_by_sex"][sex]}
                or set(ids) != set(pool["active_actions"][sex]) or set(ids) & excluded):
            raise ValueError(f"Review actions differ from current authority: {sex}")
        for index, aid in enumerate(ids, 1):
            row = by_id[aid]
            package = row["path"].split(".", 1)[0]
            package_file = PROJECT_CONTENT / (package.removeprefix("/Game/") + ".uasset")
            if row["sex"] != sex or f"/{sex.title()}/BodyOnly/" not in package:
                raise ValueError(f"Invalid action sex or body-only path: {aid}")
            receipt = row["retained_copy_receipt"]
            if _source(Path(receipt["path"]))["sha256"] != receipt["sha256"]:
                raise ValueError(f"Retained copy receipt changed: {aid}")
            previous = _read(Path(receipt["path"]))
            if (previous["source"] != row["path"] or previous["source_skeleton"] != row["source_skeleton"]
                    or previous["source_package_sha256"] != row["asset_sha256"]):
                raise ValueError(f"Current action differs from retained source: {aid}")
            if not package_file.is_file():
                raise ValueError(f"Current body-only package is absent: {aid}")
            actual = _source(package_file)
            if actual["sha256"] != row["asset_sha256"]:
                raise ValueError(f"Current action package changed: {aid}")
            for path_key, hash_key in (("source_fbx_path", "source_fbx_sha256"),
                                        ("import_fbx_path", "import_fbx_sha256")):
                if _source(Path(row[path_key]))["sha256"] != row[hash_key]:
                    raise ValueError(f"Current action FBX changed: {aid}/{path_key}")
            keys = ("action_id", "path", "source_skeleton", "asset_file_path", "source_fbx_path",
                    "source_fbx_sha256", "import_fbx_path", "import_fbx_sha256", "expected_basename")
            item = {k: row[k] for k in keys}
            item.update(index=index, label=aid.split("_", 2)[2].replace("_", " ").title())
            actions[sex].append(item)
            sources["action_reports"][aid] = _source(Path(receipt["path"]))
            sources["action_packages"][aid] = actual
    return actions


def catalog() -> dict[str, Any]:
    """Return fresh JSON-compatible choices and hash-bound source provenance.

    Every call rereads sources; callers may keep one returned object for a single
    operation. It is intentionally not a process-wide cached catalog.
    """
    # Preserve the historical 173-look/40-hair review contract after publication
    # of the narrower pool. The new fixed-slot review has its own catalog.
    registry_path = formal.MATERIAL_REPAIR_REGISTRY
    registry = formal.read_registry(registry_path)
    plan = _read(SOURCE_PLAN)
    standard = _read(STANDARD_REGISTRY)
    if {case["sex"] for case in standard["cases"]} != {"male", "female"}:
        raise ValueError("Complete-character registry must contain both sexes")
    families = {row["family_id"]: row for row in registry["families"]}
    shoes = {row["asset_id"]: row for row in registry["shared_shoe_assets"]}
    witnesses = {
        row["qualified_variant_id"]: row
        for bodyfit in plan["bodyfits"] for row in bodyfit["runtime_variants"]
    }
    outfits: dict[str, list[dict[str, Any]]] = {"female": [], "male": []}
    seen_reviews = set()
    for row in plan["review_selection"]["outfits"]:
        if row["review_index"] in seen_reviews:
            raise ValueError("Duplicate historical outfit review index")
        seen_reviews.add(row["review_index"])
        family = families[row["family_id"]]
        sex = family["sex"]
        if row["bodyfit_id"] != {"female": "F02_Average", "male": "M02_Average"}[sex]:
            raise ValueError("Outfit witness sex differs from formal family")
        if len(row["shared_shoe_ids"]) > 1:
            raise ValueError("A reviewed outfit cannot select multiple shared shoes")
        choice = {
            "family_id": row["family_id"], "group_id": row["group_id"],
            "family_asset_ids": list(row["family_asset_ids"]),
            "shared_shoe_id": next(iter(row["shared_shoe_ids"]), None),
        }
        resolved = formal.resolve_selection(registry, character_sex=sex, **choice)
        actual = [(a["target_component"], a["mesh_path"]) for a in resolved["assignments"]]
        expected = [(a["target_component"], a["mesh_path"])
                    for a in witnesses[row["qualified_variant_id"]]["assignments"]]
        if sorted(actual) != sorted(expected):
            raise ValueError(f"Formal outfit differs from accepted witness: {row['review_index']}")
        if len({path for _, path in actual}) != len(actual):
            raise ValueError("The same source mesh is assigned twice within an outfit")
        chosen = [asset for asset in family["assets"]
                  if asset["asset_id"] in resolved["selected_family_asset_ids"]]
        deny = family["hair_interface"]["deny_all"] or any(
            asset.get("hair_interface", {}).get("deny_all", False) for asset in chosen
        )
        names = [_english_label(a.get("display_name", ""), a["asset_id"].split(".")[-1])
                 for a in chosen]
        if choice["shared_shoe_id"]:
            shoe = shoes[choice["shared_shoe_id"]]
            names.append(_english_label(shoe.get("display_name", ""), shoe["asset_id"]))
        family_label = _english_label(family.get("display_name", ""), family["family_id"].split(".", 1)[1])
        outfits[sex].append({
            "index": len(outfits[sex]) + 1, "label": f"{family_label}: {' + '.join(names)}",
            "choice": choice, "resolved": resolved, "hair_deny": bool(deny),
        })
    if {sex: len(rows) for sex, rows in outfits.items()} != {"female": 95, "male": 78}:
        raise ValueError("Expected the accepted 95 female and 78 male coverage outfits")
    hairs = []
    for index, hair in enumerate(sorted(registry["hair_assets"], key=lambda row: row["hair_id"]), 1):
        fits = hair.get("fit_variants", {})
        if set(fits) != {"female", "male"}:
            raise ValueError(f"Missing sex-specific hair fit: {hair['hair_id']}")
        hairs.append({"index": index, "hair_id": hair["hair_id"], "display_name": hair["display_name"],
                      "sex": hair["sex"], "fit_variants": fits})
    if len(hairs) != 40 or len({hair["hair_id"] for hair in hairs}) != 40:
        raise ValueError("Expected 40 unique dual-fit hairstyles")
    sources: dict[str, Any] = {
        "registry": _source(registry_path), "source_plan": _source(SOURCE_PLAN),
        "standard_candidate_registry": _source(STANDARD_REGISTRY),
    }
    actions = current_actions(sources)
    return {"female_outfits": outfits["female"], "male_outfits": outfits["male"],
            "hairs": hairs, "actions_by_sex": actions, "sources": sources}


if __name__ == "__main__":
    print(json.dumps(catalog(), ensure_ascii=False, indent=2))
