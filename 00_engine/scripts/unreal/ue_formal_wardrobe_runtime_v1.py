"""Apply formal UE registry selections to reusable character Blueprints in UE.

Run with ue_remote_exec.py. The registry is read at every invocation; no
historical pilot or migrated review plan supplies production outfit choices.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import unreal


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import formal_wardrobe_registry_v1 as formal  # noqa: E402
import ue_build_modular_outfit_runtime_v2 as base  # noqa: E402


REPORT_ROOT = ROOT.parents[1] / "outputs/unreal_character_import/formal_registry_runtime_v1"
STAGE_PREFIX = "DM_FormalRegistry_"
HAIR_CAPACITY = 17
BODYFITS = {
    "M02_Average": {
        "sex": "male",
        "body_mesh_path": "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/M02_Average/Cases/M_BASE/FullReference/CC_MOD_M_BASE_UE58.CC_MOD_M_BASE_UE58",
        "skeleton_path": "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/M02_Average/Cases/M_BASE/FullReference/CC_MOD_M_BASE_UE58_Skeleton.CC_MOD_M_BASE_UE58_Skeleton",
    },
    "F02_Average": {
        "sex": "female",
        "body_mesh_path": "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/F_BASE/FullReference/CC_MOD_F_BASE_UE58.CC_MOD_F_BASE_UE58",
        "skeleton_path": "/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/F02_Average/Cases/F_BASE/FullReference/CC_MOD_F_BASE_UE58_Skeleton.CC_MOD_F_BASE_UE58_Skeleton",
    },
}
HAIR_SKELETON = BODYFITS["F02_Average"]["skeleton_path"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bodyfit_record(bodyfit_id: str) -> dict:
    if bodyfit_id not in BODYFITS:
        raise ValueError(f"unknown average bodyfit: {bodyfit_id}")
    spec = BODYFITS[bodyfit_id]
    names = (["UpperInner", "UpperOuter", "Bottom", "FullBody", "Footwear"]
             + [f"BundlePart{i:02d}" for i in range(1, 11)]
             + [f"HairPart{i:02d}" for i in range(1, HAIR_CAPACITY + 1)])
    return {"bodyfit_id": bodyfit_id, **spec,
            "blueprint_path": f"/Game/DataMake/Characters/CharacterFactoryRuntime/{bodyfit_id}/BP_DM_{bodyfit_id}_CharacterFactory_v003",
            "template_component_count": len(names),
            "template_component_names": names,
            "template_components": [{"component_name": name} for name in names]}


def _write_report(name: str, report: dict) -> Path:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = REPORT_ROOT / name
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def _blueprint(bodyfit: dict):
    blueprint = unreal.load_asset(bodyfit["blueprint_path"])
    if not isinstance(blueprint, unreal.Blueprint):
        raise RuntimeError(f"formal registry Blueprint is missing: {bodyfit['blueprint_path']}")
    return blueprint


def _verify_blueprint(bodyfit: dict) -> dict:
    blueprint = _blueprint(bodyfit)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_subsystem.spawn_actor_from_class(
        blueprint.generated_class(), unreal.Vector(), unreal.Rotator(), transient=True
    )
    if actor is None:
        raise RuntimeError("cannot spawn character factory verification actor")
    try:
        body, followers = base.actor_components(actor, bodyfit)
        if base.object_path(body.get_skeletal_mesh_asset()) != bodyfit["body_mesh_path"]:
            raise RuntimeError("body mesh differs from formal runtime bodyfit")
        if any(component.get_editor_property("leader_pose_component") != body for component in followers):
            raise RuntimeError("a reusable component has no Body leader")
        if any(component.get_skeletal_mesh_asset() is not None for component in followers):
            raise RuntimeError("Blueprint contains a candidate mesh hard reference")
        return {"blueprint_path": bodyfit["blueprint_path"],
                "template_component_count": len(followers), "success": True}
    finally:
        actor_subsystem.destroy_actor(actor)


def build(bodyfit: dict) -> dict:
    if unreal.EditorAssetLibrary.does_asset_exist(bodyfit["blueprint_path"]):
        return {"created": False, **_verify_blueprint(bodyfit)}
    result = base.build_bodyfit_blueprint(bodyfit)
    if not result["success"]:
        raise RuntimeError("formal registry Blueprint build did not validate")
    return {"created": True, **_verify_blueprint(bodyfit)}


def _loaded_hair(selection: dict) -> list:
    assignments = selection["hair_assignments"]
    if len(assignments) > HAIR_CAPACITY:
        raise RuntimeError("hairstyle exceeds reserved HairPart capacity")
    loaded = []
    for assignment in assignments:
        mesh = unreal.load_asset(assignment["mesh_path"])
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(f"hairstyle mesh unavailable: {assignment['mesh_path']}")
        expected_skeleton = selection.get("hair_skeleton_path") or HAIR_SKELETON
        if base.object_path(mesh.get_editor_property("skeleton")) != expected_skeleton:
            raise RuntimeError(f"hairstyle has unexpected source Skeleton: {assignment['mesh_path']}")
        loaded.append(mesh)
    return loaded


def apply_selection(actor, bodyfit: dict, selection: dict) -> dict:
    # Validate the entire hairstyle before the outfit core clears any slot.
    hair_meshes = _loaded_hair(selection)
    outfit_record = base.apply_variant(actor, bodyfit, selection)
    errors = base.validate_variant_application(outfit_record)
    if errors:
        raise RuntimeError(f"outfit application failed: {errors}")
    body, followers = base.actor_components(actor, bodyfit)
    by_name = {component.get_name(): component for component in followers}
    for assignment, mesh in zip(selection["hair_assignments"], hair_meshes):
        component = by_name[assignment["target_component"]]
        if component.get_editor_property("leader_pose_component") != body:
            raise RuntimeError(f"hair component has no Body leader: {component.get_name()}")
        component.set_skeletal_mesh_asset(mesh)
        component.set_visibility(True, False)
        component.set_hidden_in_game(False)
    active = [component.get_name() for component in followers
              if component.get_name().startswith("HairPart") and component.get_skeletal_mesh_asset() is not None]
    expected = [item["target_component"] for item in selection["hair_assignments"]]
    if active != expected:
        raise RuntimeError(f"hairstyle component mismatch: {active} != {expected}")
    return {"outfit": outfit_record, "hair_id": selection["resolved_hair_id"],
            "hair_reason": selection["hair_reason"], "active_hair_components": active,
            "success": True}


def _stage_actor(bodyfit: dict):
    label = STAGE_PREFIX + bodyfit["bodyfit_id"]
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [actor for actor in actor_subsystem.get_all_level_actors()
               if actor.get_actor_label() == label]
    if len(matches) > 1:
        raise RuntimeError(f"multiple staged actors share label {label}")
    if matches:
        actor = matches[0]
        if actor.get_class() != _blueprint(bodyfit).generated_class():
            raise RuntimeError("staged actor class differs from formal registry Blueprint")
        return actor, False
    actor = actor_subsystem.spawn_actor_from_class(
        _blueprint(bodyfit).generated_class(), unreal.Vector(), unreal.Rotator(), transient=False
    )
    if actor is None:
        raise RuntimeError("could not spawn formal registry actor")
    actor.set_actor_label(label)
    return actor, True


def stage(bodyfit: dict, selection: dict) -> dict:
    actor, created = _stage_actor(bodyfit)
    result = apply_selection(actor, bodyfit, selection)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors([actor])
    return {"actor": actor.get_path_name(), "actor_created": created,
            "selection": selection, "application": result, "success": True}


def verify(bodyfit: dict, selection: dict) -> dict:
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actor_subsystem.spawn_actor_from_class(
        _blueprint(bodyfit).generated_class(), unreal.Vector(), unreal.Rotator(), transient=True
    )
    if actor is None:
        raise RuntimeError("could not spawn transient verification actor")
    try:
        return {"selection": selection, "application": apply_selection(actor, bodyfit, selection),
                "success": True}
    finally:
        actor_subsystem.destroy_actor(actor)


def cleanup(bodyfit: dict) -> dict:
    label = STAGE_PREFIX + bodyfit["bodyfit_id"]
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = [actor for actor in actor_subsystem.get_all_level_actors()
              if actor.get_actor_label() == label]
    for actor in actors:
        actor_subsystem.destroy_actor(actor)
    return {"destroyed_actor_count": len(actors), "success": True}


def main() -> dict:
    mode = globals().get("DM_FORMAL_MODE")
    bodyfit_id = globals().get("DM_FORMAL_BODYFIT_ID")
    request = globals().get("DM_FORMAL_SELECTION")
    report = {"schema_version": 1, "mode": mode, "bodyfit_id": bodyfit_id,
              "created_at_utc": utc_now(), "success": False}
    try:
        bodyfit = bodyfit_record(bodyfit_id)
        registry_path = Path(globals().get("DM_FORMAL_REGISTRY_PATH") or formal.current_registry_path())
        registry = formal.read_registry(registry_path)
        if max(formal.hair_mesh_capacity(hair) for hair in registry["hair_assets"]) > HAIR_CAPACITY:
            raise RuntimeError("registry hairstyle exceeds Blueprint HairPart capacity")
        report["registry_path"] = str(registry_path)
        report["registry_sha256"] = hashlib.sha256(registry_path.read_bytes()).hexdigest()
        if mode == "build":
            report["result"] = build(bodyfit)
        elif mode == "cleanup":
            report["result"] = cleanup(bodyfit)
        elif mode in {"stage", "verify"}:
            if not isinstance(request, dict):
                raise ValueError("DM_FORMAL_SELECTION must be a selection object")
            selection = formal.resolve_selection(registry, character_sex=bodyfit["sex"], **request)
            report["result"] = stage(bodyfit, selection) if mode == "stage" else verify(bodyfit, selection)
        else:
            raise ValueError(f"unsupported formal registry mode: {mode}")
        report["success"] = report["result"]["success"]
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc))
        unreal.log_error(f"Formal wardrobe runtime failed: {exc}")
    name = f"{bodyfit_id}_{mode}_{report['created_at_utc'].replace(':', '').replace('+', '_')}.json"
    path = _write_report(name, report)
    print("DM_FORMAL_REGISTRY_RESULT=" + json.dumps({"success": report["success"],
          "mode": mode, "bodyfit_id": bodyfit_id, "report_path": str(path)}, ensure_ascii=False))
    if not report["success"]:
        raise RuntimeError(f"Formal wardrobe runtime failed; see {path}")
    return report


if __name__ == "__main__" or "DM_FORMAL_MODE" in globals():
    main()
