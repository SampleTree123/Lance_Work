"""Import the four P0 runtime pilot animations onto their matching UE skeletons."""

from __future__ import annotations


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_import_p0_runtime_motions.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")


import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


MANIFEST_PATH = Path(
    r"D:\UE\exports\character_creator\p0_ue_runtime_pilot_20260818_v1"
    r"\export_bundle_manifest.json"
)
REPORT_PATH = Path(
    r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import"
    r"\p0_runtime_pilot_20260819_v1\motion_import_report.json"
)
DEFAULT_PIPELINE = "/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline"
CONFIG_ROOT = "/Game/DataMake/Config/Import"
ANIMATION_ROOT = "/Game/DataMake/Animations/CC5/P0RuntimePilot"

ACTORS = {
    "p0_female_clothed": {
        "skeleton": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/F02/FullReference/"
            "F02_Clothed_Skeleton.F02_Clothed_Skeleton"
        ),
        "destination": f"{ANIMATION_ROOT}/F02",
        "pipeline": f"{CONFIG_ROOT}/DM_CC5_P0_F02_Animation_Pipeline_v001",
    },
    "p0_male_clothed": {
        "skeleton": (
            "/Game/Vendor/Reallusion/CC5/P0RuntimePilot/M02/FullReference/"
            "M02_Clothed_Skeleton.M02_Clothed_Skeleton"
        ),
        "destination": f"{ANIMATION_ROOT}/M02",
        "pipeline": f"{CONFIG_ROOT}/DM_CC5_P0_M02_Animation_Pipeline_v001",
    },
}

MOTION_NAMES = {
    "p0_001_city_walk_normal_f": "A_CC_P0_Walk_F_Root_v001",
    "p0_004_legacy_stand_idle_f": "A_CC_P0_Idle_F_InPlace_v001",
    "p0_009_city_walk_normal_m": "A_CC_P0_Walk_M_Root_v001",
    "p0_014_signal_understood": "A_CC_P0_Understood_M_InPlace_v001",
}

# The UE5 reference skeleton keeps CC helper names such as
# ``r_thightwist01``.  The legacy ``patched_fbx`` variant prefixes those
# tracks with ``cc_base_`` and is therefore incompatible with this skeleton.
MOTION_SOURCE_KEY = "raw_ascii_fbx"
REQUIRED_TRACK_NAMES = {
    "root",
    "pelvis",
    "pelvis_0",
    "facialbone",
    "l_forearmtwist01",
    "r_forearmtwist01",
    "l_thightwist01",
    "r_thightwist01",
    "ik_foot_root",
    "ik_hand_root",
}
MIN_EXPECTED_BONE_TRACKS = 100


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(entry: dict) -> dict:
    path = Path(entry["path"])
    exists = path.is_file()
    actual_bytes = path.stat().st_size if exists else None
    actual_sha256 = sha256(path) if exists else None
    return {
        "path": str(path),
        "exists": exists,
        "expected_bytes": entry["bytes"],
        "actual_bytes": actual_bytes,
        "expected_sha256": entry["sha256"],
        "actual_sha256": actual_sha256,
        "passed": exists
        and actual_bytes == entry["bytes"]
        and actual_sha256 == entry["sha256"],
    }


def object_record(obj: unreal.Object) -> dict:
    return {
        "class": obj.get_class().get_name(),
        "name": obj.get_name(),
        "path": obj.get_path_name(),
    }


def animation_record(animation: unreal.AnimSequence) -> dict:
    skeleton = animation.get_editor_property("skeleton")
    model = animation.data_model_interface
    track_names = [str(name) for name in model.get_bone_track_names()]
    track_name_set = set(track_names)
    return {
        **object_record(animation),
        "skeleton": skeleton.get_path_name() if skeleton else None,
        "play_length_seconds": animation.get_play_length(),
        "frame_count": int(model.get_number_of_frames()),
        "frame_rate": str(model.get_frame_rate()),
        "bone_track_count": len(track_names),
        "has_root_track": "root" in track_name_set,
        "has_pelvis_track": "pelvis" in track_name_set,
        "has_pelvis_aux_track": "pelvis_0" in track_name_set,
        "missing_required_tracks": sorted(REQUIRED_TRACK_NAMES - track_name_set),
    }


def animation_tracks_are_complete(animation: unreal.AnimSequence) -> bool:
    record = animation_record(animation)
    return (
        record["bone_track_count"] >= MIN_EXPECTED_BONE_TRACKS
        and not record["missing_required_tracks"]
    )


def prepare_pipeline(config: dict, skeleton: unreal.Skeleton):
    pipeline = unreal.load_asset(config["pipeline"])
    if pipeline is None:
        pipeline = unreal.EditorAssetLibrary.duplicate_asset(
            DEFAULT_PIPELINE, config["pipeline"]
        )
    if pipeline is None:
        raise RuntimeError(f"Unable to create pipeline: {config['pipeline']}")

    mesh = pipeline.get_editor_property("mesh_pipeline")
    common = pipeline.get_editor_property(
        "common_skeletal_meshes_and_animations_properties"
    )
    animation = pipeline.get_editor_property("animation_pipeline")
    material = pipeline.get_editor_property("material_pipeline")
    texture = material.get_editor_property("texture_pipeline")

    mesh.set_editor_property("import_skeletal_meshes", False)
    mesh.set_editor_property("import_static_meshes", False)
    mesh.set_editor_property("create_physics_asset", False)
    mesh.set_editor_property("physics_asset", None)
    common.set_editor_property("skeleton", skeleton)
    common.set_editor_property("try_auto_select_skeleton", False)
    common.set_editor_property("import_only_animations", True)
    animation.set_editor_property("import_animations", True)
    material.set_editor_property("import_materials", False)
    texture.set_editor_property("import_textures", False)

    if not unreal.EditorAssetLibrary.save_loaded_asset(
        pipeline, only_if_is_dirty=False
    ):
        raise RuntimeError(f"Unable to save pipeline: {config['pipeline']}")
    return pipeline


def import_asset(manager, world, source: Path, destination: str, desired_name: str, pipeline):
    desired_path = f"{destination}/{desired_name}"
    replaced_invalid_existing = False
    if unreal.EditorAssetLibrary.does_asset_exist(desired_path):
        existing = unreal.load_asset(desired_path)
        if not isinstance(existing, unreal.AnimSequence):
            raise RuntimeError(f"Existing asset is not AnimSequence: {desired_path}")
        if animation_tracks_are_complete(existing):
            return existing, [], [], True, False
        if not unreal.EditorAssetLibrary.delete_asset(desired_path):
            raise RuntimeError(f"Unable to replace incomplete animation: {desired_path}")
        replaced_invalid_existing = True

    before = set(
        unreal.EditorAssetLibrary.list_assets(
            destination, recursive=False, include_folder=False
        )
    )
    source_data = manager.create_source_data(str(source))
    if source_data is None:
        raise RuntimeError(f"Unable to create source data: {source}")

    parameters = unreal.ImportAssetParameters()
    parameters.set_editor_property("is_automated", True)
    parameters.set_editor_property("force_show_dialog", False)
    parameters.set_editor_property("replace_existing", False)
    parameters.set_editor_property("destination_name", desired_name)
    parameters.set_editor_property(
        "override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())]
    )

    fbx_cvar = "Interchange.FeatureFlags.Import.FBX"
    previous_value = unreal.SystemLibrary.get_console_variable_int_value(fbx_cvar)
    if previous_value != 1:
        unreal.SystemLibrary.execute_console_command(world, f"{fbx_cvar} 1")
    try:
        returned = manager.import_asset(destination, source_data, parameters) or []
    finally:
        if previous_value != 1:
            unreal.SystemLibrary.execute_console_command(
                world, f"{fbx_cvar} {previous_value}"
            )

    after = set(
        unreal.EditorAssetLibrary.list_assets(
            destination, recursive=False, include_folder=False
        )
    )
    new_paths = sorted(after - before)
    animations = []
    for asset_path in new_paths:
        asset = unreal.load_asset(asset_path)
        if isinstance(asset, unreal.AnimSequence):
            animations.append(asset)
    if len(animations) != 1:
        raise RuntimeError(
            f"Expected one AnimSequence from {source}; found {len(animations)}; "
            f"new assets={new_paths}"
        )

    imported = animations[0]
    if imported.get_name() != desired_name:
        source_asset_path = imported.get_path_name().split(".", 1)[0]
        if not unreal.EditorAssetLibrary.rename_asset(
            source_asset_path, desired_path
        ):
            raise RuntimeError(
                f"Unable to rename {source_asset_path} to {desired_path}"
            )
        imported = unreal.load_asset(desired_path)
    if imported is None:
        raise RuntimeError(f"Imported asset unavailable: {desired_path}")
    return (
        imported,
        [object_record(obj) for obj in returned],
        new_paths,
        False,
        replaced_invalid_existing,
    )


if not MANIFEST_PATH.is_file():
    raise FileNotFoundError(str(MANIFEST_PATH))
manifest = read_json(MANIFEST_PATH)
if manifest.get("status") != "ready_for_ue_import":
    raise RuntimeError(f"Unexpected Bundle status: {manifest.get('status')}")
if len(manifest.get("motions", [])) != 4:
    raise RuntimeError("P0 runtime Pilot must contain exactly four motions")

unreal.EditorAssetLibrary.make_directory(CONFIG_ROOT)
unreal.EditorAssetLibrary.make_directory(ANIMATION_ROOT)
manager = unreal.InterchangeManager.get_interchange_manager_scripted()
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

skeletons = {}
pipelines = {}
for actor_id, actor_config in ACTORS.items():
    skeleton = unreal.load_asset(actor_config["skeleton"])
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError(f"Missing target skeleton: {actor_config['skeleton']}")
    unreal.EditorAssetLibrary.make_directory(actor_config["destination"])
    skeletons[actor_id] = skeleton
    pipelines[actor_id] = prepare_pipeline(actor_config, skeleton)

imports = []
for motion in manifest["motions"]:
    case_id = motion["case_id"]
    if case_id not in MOTION_NAMES:
        raise RuntimeError(f"Unexpected motion case: {case_id}")
    actor_id = motion["actor_binding_id"]
    if actor_id not in ACTORS:
        raise RuntimeError(f"Unexpected actor binding: {actor_id}")

    source_check = verify_file(motion[MOTION_SOURCE_KEY])
    if not source_check["passed"]:
        raise RuntimeError(f"Motion source hash failed: {source_check}")
    config = ACTORS[actor_id]
    source = Path(motion[MOTION_SOURCE_KEY]["path"])
    animation, returned, new_paths, reused, replaced_invalid_existing = import_asset(
        manager,
        world,
        source,
        config["destination"],
        MOTION_NAMES[case_id],
        pipelines[actor_id],
    )
    if animation.get_editor_property("skeleton") != skeletons[actor_id]:
        raise RuntimeError(
            f"Skeleton mismatch for {case_id}: "
            f"{animation.get_editor_property('skeleton')} != {skeletons[actor_id]}"
        )
    imports.append(
        {
            "case_id": case_id,
            "actor_binding_id": actor_id,
            "source_variant": MOTION_SOURCE_KEY,
            "root_motion_policy": motion["root_motion_policy"],
            "expected_source_frames": motion["clip"]["length_frame"],
            "source_check": source_check,
            "pipeline": pipelines[actor_id].get_path_name(),
            "returned_objects": returned,
            "new_asset_paths": new_paths,
            "reused_existing": reused,
            "replaced_invalid_existing": replaced_invalid_existing,
            "animation": animation_record(animation),
        }
    )

unreal.EditorAssetLibrary.save_directory(
    ANIMATION_ROOT, only_if_is_dirty=False, recursive=True
)
report = {
    "schema_version": 1,
    "created_at_utc": utc_now(),
    "manifest_path": str(MANIFEST_PATH),
    "manifest_sha256": sha256(MANIFEST_PATH),
    "animation_root": ANIMATION_ROOT,
    "motion_source_variant": MOTION_SOURCE_KEY,
    "rejected_source_variant": {
        "key": "patched_fbx",
        "reason": (
            "Legacy patch prefixes 47 helper tracks with cc_base_, but the "
            "validated UE5 reference skeleton retains the unprefixed names."
        ),
    },
    "imports": imports,
    "import_count": len(imports),
    "success": len(imports) == 4
    and all(item["source_check"]["passed"] for item in imports)
    and all(item["animation"]["has_root_track"] for item in imports),
    "validation": {
        "expected_import_count": 4,
        "minimum_bone_track_count": MIN_EXPECTED_BONE_TRACKS,
        "required_track_names": sorted(REQUIRED_TRACK_NAMES),
        "all_required_tracks_present": all(
            not item["animation"]["missing_required_tracks"] for item in imports
        ),
        "all_track_counts_plausible": all(
            item["animation"]["bone_track_count"] >= MIN_EXPECTED_BONE_TRACKS
            for item in imports
        ),
        "all_frame_counts_match_cc_last_frame_rule": all(
            item["animation"]["frame_count"]
            == item["expected_source_frames"] + 1
            for item in imports
        ),
    },
    "production_status": "not_approved",
}
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.write_text(
    json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
    encoding="utf-8",
)
report["success"] = report["success"] and all(report["validation"].values())
if not report["success"]:
    raise RuntimeError(f"P0 motion import failed validation: {REPORT_PATH}")
unreal.log(f"DataMake P0 motion import passed: {REPORT_PATH}")
print("DM_P0_MOTION_IMPORT=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
