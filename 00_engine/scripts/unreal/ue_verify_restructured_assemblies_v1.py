"""Apply 173 reviewed outfit variants and load 40 hair styles from new paths."""

from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

import unreal


ENGINE = Path(r"D:\UE\Lance_Work\00_engine")
ROOT = ENGINE / "outputs/unreal_character_import/asset_restructure_full_20260929_v1"
PLAN = ROOT / "review_plans/wardrobe_coverage/review_plan.json"
REGISTRY = ENGINE / "assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json"
WORKER = ENGINE / "scripts/unreal/ue_build_modular_outfit_runtime_v2.py"


def run():
    spec = importlib.util.spec_from_file_location("dm_restructure_runtime_worker", WORKER)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    wardrobe = json.loads(REGISTRY.read_text(encoding="utf-8"))
    worker.validate_runtime_plan(plan)
    choices = plan["review_selection"]["outfits"]
    assert len(choices) == 173
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rows = []
    for bodyfit_id in ("M02_Average", "F02_Average"):
        bodyfit = worker.bodyfit_for_id(plan, bodyfit_id)
        blueprint = worker.load_blueprint(bodyfit)
        actor = actors.spawn_actor_from_class(blueprint.generated_class(), unreal.Vector(), unreal.Rotator(), transient=True)
        if actor is None:
            raise RuntimeError(f"cannot spawn {bodyfit_id}")
        try:
            for choice in choices:
                if choice["bodyfit_id"] != bodyfit_id:
                    continue
                variant = worker.variant_for_id(bodyfit, choice["qualified_variant_id"])
                application = worker.apply_variant(actor, bodyfit, variant)
                errors = worker.validate_variant_application(application)
                rows.append({"review_index": choice["review_index"], "bodyfit_id": bodyfit_id,
                             "variant_id": choice["qualified_variant_id"], "errors": errors})
                if len(rows) % 25 == 0:
                    unreal.log(f"DataMake restructured assembly {len(rows)}/173")
        finally:
            actors.destroy_actor(actor)
    hair_rows = []
    for style in wardrobe["hair_assets"]:
        meshes = []
        for item in style["meshes"]:
            mesh = unreal.load_asset(item["path"])
            if not isinstance(mesh, unreal.SkeletalMesh):
                raise RuntimeError(f"missing hair mesh: {item['path']}")
            meshes.append(item["path"])
        hair_rows.append({"hair_id": style["hair_id"], "mesh_count": len(meshes)})
    result = {"schema_version": 1, "outfit_count": len(rows), "hair_count": len(hair_rows),
              "outfit_errors": [row for row in rows if row["errors"]],
              "by_bodyfit": dict(Counter(row["bodyfit_id"] for row in rows)),
              "hair_meshes": sum(row["mesh_count"] for row in hair_rows),
              "success": len(rows) == 173 and len(hair_rows) == 40 and not any(row["errors"] for row in rows)}
    (ROOT / "assembly_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake restructured assembly verification: {result}")
    if not result["success"]:
        raise RuntimeError("restructured assembly verification failed")


run()
