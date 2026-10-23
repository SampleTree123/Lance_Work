"""Isolated F02 shorts derivative import; never modifies accepted wardrobe assets."""


# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_wardrobe_geometry_probe_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

from pathlib import Path
import hashlib
import importlib.util
import json
import time

import unreal

ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\optimization_20260907")
SOURCE = ROOT / "F_SHORTS/shorts_only.fbx"
DESTINATION = "/Game/DataMake/Validation/Wardrobe/OptimizationProbe20260907/F_Shorts"
BASELINE = "/Game/Vendor/Reallusion/CC5/Wardrobe/Female/Average/summer_girl_four_colors/Pants/F_a7b1636c2cba1e14fd66/Modules/shorts_001"


def main():
    gate = json.loads((ROOT / "native_validation.json").read_text(encoding="utf-8"))
    if gate.get("success") is not True:
        raise RuntimeError("Native mesh/skin/skeleton roundtrip did not pass")
    for key, hash_key in (("derivative", "derivative_sha256"), ("source", "source_sha256"),
                          ("native_report", "native_report_sha256")):
        if hashlib.sha256(Path(gate[key]).read_bytes()).hexdigest() != gate[hash_key]:
            raise RuntimeError(f"Probe input changed: {key}")
    if Path(gate["derivative"]).resolve() != SOURCE.resolve():
        raise RuntimeError("Validated derivative path differs")
    if unreal.EditorAssetLibrary.list_assets(DESTINATION, recursive=True):
        raise RuntimeError("Refusing to overwrite existing probe assets")
    path = Path(__file__).with_name("ue_modular_outfit_pilot_import_v1.py")
    spec = importlib.util.spec_from_file_location("wardrobe_geometry_probe_import", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    baseline = unreal.load_asset(BASELINE)
    if not isinstance(baseline, unreal.SkeletalMesh):
        raise RuntimeError("Accepted baseline shorts mesh missing")
    before = worker.skeletal_mesh_record(baseline)
    pipeline = unreal.EditorAssetLibrary.duplicate_asset(
        worker.DEFAULT_INTERCHANGE_PIPELINE, DESTINATION + "/Pipeline")
    worker.configure_split_pipeline(pipeline, baseline.get_editor_property("skeleton"))
    unreal.EditorAssetLibrary.save_loaded_asset(pipeline)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cvar = "Interchange.FeatureFlags.Import.FBX"
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    params = unreal.ImportAssetParameters()
    params.set_editor_property("is_automated", True)
    params.set_editor_property("force_show_dialog", False)
    params.set_editor_property("replace_existing", False)
    params.set_editor_property("override_pipelines", [unreal.SoftObjectPath(pipeline.get_path_name())])
    started = time.monotonic()
    try:
        unreal.SystemLibrary.execute_console_command(world, cvar + " 1")
        manager.import_asset(DESTINATION, manager.create_source_data(str(SOURCE)), params)
    finally:
        unreal.SystemLibrary.execute_console_command(world, f"{cvar} {previous}")
    seconds = time.monotonic() - started
    meshes = worker.skeletal_meshes_under(DESTINATION)
    if len(meshes) != 1:
        raise RuntimeError(f"Expected exactly one garment mesh, got {len(meshes)}")
    target = meshes[0]
    after = worker.skeletal_mesh_record(target)
    keys = ("skeleton", "lod_count", "lod0_vertices", "material_slot_names",
            "imported_material_slot_names", "morph_count")
    differences = [key for key in keys if before[key] != after[key]]
    if after["physics_asset"] is not None or after["lod0_vertices"] <= 0:
        differences.append("unexpected_physics_or_empty_mesh")
    # Only the newly imported test mesh receives the existing material slots.
    if not differences:
        target.set_editor_property("materials", baseline.get_editor_property("materials"))
        unreal.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False)
    unreal.EditorAssetLibrary.save_directory(DESTINATION)
    result = {"schema_version": 1, "scope": "experimental_f02_shorts_geometry_filter",
              "source": str(SOURCE), "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              "destination": DESTINATION, "ue_import_seconds": seconds,
              "baseline": before, "derivative": worker.skeletal_mesh_record(target),
              "differences": differences, "success": not differences,
              "runtime_approved": False, "visual_review": "pending"}
    (ROOT / "ue_probe.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("WARDROBE_GEOMETRY_PROBE", json.dumps({"success": result["success"], "seconds": seconds, "differences": differences}))
    if differences:
        raise RuntimeError("Derivative differs from the accepted mesh; see ue_probe.json")


if globals().get("DM_RUN_WARDROBE_GEOMETRY_PROBE"):
    main()
