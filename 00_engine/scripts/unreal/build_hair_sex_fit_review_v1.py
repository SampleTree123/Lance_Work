"""Build the bounded M02/F02 hairstyle visual-review queue from the formal UE registry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from formal_wardrobe_registry_v1 import LEGACY_REGISTRY, read_registry


ENGINE = Path(__file__).resolve().parents[2]
REVIEW_ROOT = ENGINE / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
PLAN_PATH = REVIEW_ROOT / "review_plan.json"
VIEWS = ["front", "front_left", "left", "back", "right", "front_right"]
BODYFITS = {"female": "F02_Average", "male": "M02_Average"}


def build_plan(registry: dict, registry_sha256: str) -> dict:
    cases = []
    for sex, bodyfit_id in BODYFITS.items():
        for hair in registry["hair_assets"]:
            if hair["sex"] not in {sex, "both"}:
                continue
            cases.append({
                "review_index": len(cases) + 1,
                "sex": sex,
                "bodyfit_id": bodyfit_id,
                "hair_id": hair["hair_id"],
                "display_name": hair["display_name"],
                "hair_sex_rule": hair["sex"],
                "mesh_paths": [mesh["path"] for mesh in hair["meshes"]],
                "views": VIEWS,
                "visual_decision": "pending",
            })
    female = sum(case["sex"] == "female" for case in cases)
    male = sum(case["sex"] == "male" for case in cases)
    if (len(cases), female, male) != (51, 30, 21):
        raise ValueError(f"Unexpected bounded hair review: {len(cases)}/{female}/{male}")
    return {
        "schema_version": 1,
        "source_registry": str(LEGACY_REGISTRY),
        "registry_sha256": registry_sha256,
        "scope": "standard_average_bodyfit_hairstyle_appearance_only",
        "level_path": "/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001",
        "counts": {"total": len(cases), "female": female, "male": male},
        "cases": cases,
        "limitations": ["No per-identity head-shape acceptance", "No outfit compatibility decision"],
    }


def main() -> None:
    # The 2026-09-29 queue has 51 single-fit cases; keep its original source.
    registry = read_registry(LEGACY_REGISTRY)
    plan = build_plan(registry, hashlib.sha256(LEGACY_REGISTRY.read_bytes()).hexdigest())
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    if PLAN_PATH.exists():
        existing = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        if existing != plan:
            # Material-only registry updates do not alter the review cases or
            # invalidate captures; keep their frozen indices and refresh provenance.
            old_without_sha = {key: value for key, value in existing.items() if key != "registry_sha256"}
            new_without_sha = {key: value for key, value in plan.items() if key != "registry_sha256"}
            if old_without_sha != new_without_sha:
                raise FileExistsError(f"Review plan changed; create a new version: {PLAN_PATH}")
            PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        PLAN_PATH.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"plan": str(PLAN_PATH), "counts": plan["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
