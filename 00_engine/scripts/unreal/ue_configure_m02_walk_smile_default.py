"""Configure the M02 modular pilot to default to walk plus subtle smile."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ANIM_BLUEPRINT_PATH = (
    "/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v002"
)
CHARACTER_BLUEPRINT_PATH = (
    "/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\m02_walk_smile_default_configuration.json"
)


anim_blueprint = unreal.load_asset(ANIM_BLUEPRINT_PATH)
character_blueprint = unreal.load_asset(CHARACTER_BLUEPRINT_PATH)
if not isinstance(anim_blueprint, unreal.AnimBlueprint):
    raise RuntimeError(f"AnimBlueprint unavailable: {ANIM_BLUEPRINT_PATH}")
if not isinstance(character_blueprint, unreal.Blueprint):
    raise RuntimeError(
        f"Character Blueprint unavailable: {CHARACTER_BLUEPRINT_PATH}"
    )

anim_class = anim_blueprint.generated_class()
anim_default = unreal.get_default_object(anim_class)
before_selectors = {
    "BodyMotionIndex": anim_default.get_editor_property("BodyMotionIndex"),
    "FacePairIndex": anim_default.get_editor_property("FacePairIndex"),
    "FaceVariantIndex": anim_default.get_editor_property("FaceVariantIndex"),
}
anim_default.set_editor_property("BodyMotionIndex", 1)
anim_default.set_editor_property("FacePairIndex", 1)
anim_default.set_editor_property("FaceVariantIndex", 1)
if not unreal.EditorAssetLibrary.save_loaded_asset(
    anim_blueprint, only_if_is_dirty=False
):
    raise RuntimeError("Unable to save AnimBlueprint defaults")

subobject_subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
handles = subobject_subsystem.k2_gather_subobject_data_for_blueprint(
    character_blueprint
)
body_templates = []
seen_paths = set()
for handle in handles:
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
    component = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(
        data
    )
    if not isinstance(component, unreal.SkeletalMeshComponent):
        continue
    if component.get_name() != "Body_GEN_VARIABLE":
        continue
    if component.get_path_name() in seen_paths:
        continue
    seen_paths.add(component.get_path_name())
    body_templates.append(component)

if len(body_templates) != 1:
    raise RuntimeError(
        f"Expected one unique Body template, found {len(body_templates)}"
    )
body_template = body_templates[0]
before_body = {
    "animation_mode": str(body_template.get_editor_property("animation_mode")),
    "anim_class": (
        body_template.get_editor_property("anim_class").get_path_name()
        if body_template.get_editor_property("anim_class") is not None
        else None
    ),
}
body_template.set_editor_property(
    "animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT
)
body_template.set_editor_property("anim_class", anim_class)
unreal.BlueprintEditorLibrary.compile_blueprint(character_blueprint)
if not unreal.EditorAssetLibrary.save_loaded_asset(
    character_blueprint, only_if_is_dirty=False
):
    raise RuntimeError("Unable to save character Blueprint animation defaults")

# Spawn once from the compiled class to verify that the component template and
# AnimInstance defaults survive compilation and are inherited by a real actor.
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actor = actor_subsystem.spawn_actor_from_class(
    character_blueprint.generated_class(),
    unreal.Vector(450.0, 20.0, 0.0),
    unreal.Rotator(),
    transient=True,
)
if actor is None:
    raise RuntimeError("Unable to spawn verification actor")
body = next(
    component
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent)
    if component.get_name() == "Body"
)
instance = body.get_anim_instance()
verification = {
    "body_animation_mode": str(body.get_editor_property("animation_mode")),
    "body_anim_class": (
        body.get_editor_property("anim_class").get_path_name()
        if body.get_editor_property("anim_class") is not None
        else None
    ),
    "anim_instance_class": (
        instance.get_class().get_path_name() if instance is not None else None
    ),
    "selectors": (
        {
            "BodyMotionIndex": instance.get_editor_property("BodyMotionIndex"),
            "FacePairIndex": instance.get_editor_property("FacePairIndex"),
            "FaceVariantIndex": instance.get_editor_property(
                "FaceVariantIndex"
            ),
        }
        if instance is not None
        else None
    ),
}
actor_subsystem.destroy_actor(actor)

expected_class = anim_class.get_path_name()
errors = []
if verification["body_anim_class"] != expected_class:
    errors.append("Spawned Body did not inherit the formal AnimBlueprint")
if verification["selectors"] != {
    "BodyMotionIndex": 1,
    "FacePairIndex": 1,
    "FaceVariantIndex": 1,
}:
    errors.append("Spawned AnimInstance did not inherit walk/smile selectors")

report = {
    "schema_version": 1,
    "anim_blueprint": anim_blueprint.get_path_name(),
    "character_blueprint": character_blueprint.get_path_name(),
    "before_selectors": before_selectors,
    "after_selectors": {
        "BodyMotionIndex": anim_default.get_editor_property("BodyMotionIndex"),
        "FacePairIndex": anim_default.get_editor_property("FacePairIndex"),
        "FaceVariantIndex": anim_default.get_editor_property(
            "FaceVariantIndex"
        ),
    },
    "before_body": before_body,
    "body_template": body_template.get_path_name(),
    "verification": verification,
    "errors": errors,
    "success": not errors,
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
if errors:
    raise RuntimeError(f"Walk/smile default configuration failed: {errors}")

asset_editor = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
asset_editor.open_editor_for_assets([anim_blueprint, character_blueprint])
print(
    "DM_WALK_SMILE_DEFAULT="
    + json.dumps(
        {
            "report_path": str(REPORT_PATH),
            "after_selectors": report["after_selectors"],
            "body_anim_class": verification["body_anim_class"],
            "success": report["success"],
        },
        sort_keys=True,
    )
)
