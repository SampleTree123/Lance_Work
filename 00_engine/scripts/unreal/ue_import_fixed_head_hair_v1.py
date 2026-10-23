"""Resume-safe dual fixed-head hair import, restricted to a new batch root.

Execute in UE Python with DM_FIXED_HAIR_MANIFEST and DM_FIXED_HAIR_CONFIG.
Config permits case_ids and max_cases for the two-branch representative pilot.
No existing library, source project, registry or source material is modified.
"""
from __future__ import annotations

import hashlib
import json
import re
import traceback
import sys
from datetime import datetime, timezone
from pathlib import Path

import unreal

REPO = Path(__file__).resolve().parents[3]
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))
from hair_source_shader_v1 import create_material as create_source_hair_material, exact_material, is_rl_hair, is_ornament_slot
BATCH_ID = "fixed_head_hair_20261004_v1"
UE_ROOT = "/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1"
EXPORT_ROOT = Path("D:/UE/exports/character_creator") / BATCH_ID
REPORT_ROOT = REPO / "00_engine/outputs/unreal_character_import" / BATCH_ID
REVIEW_ROOT = REPO / "00_engine/outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
DEFAULT_PIPELINE = "/Game/DataMake/Config/Import/DM_Interchange_Split_Pipeline_v1"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def activity(phase, **details):
    value = {"phase": phase, "updated_at_utc": datetime.now(timezone.utc).isoformat(), **details}
    write(REPORT_ROOT / "activity.json", value)
    unreal.log("Fixed head hair activity: " + json.dumps(value, ensure_ascii=False))


def object_path(asset):
    return asset.get_path_name() if asset is not None else None


def package(path):
    return path.split(".", 1)[0]


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def token(value):
    return safe_name(value).casefold()


def material_role(value):
    # CC can allocate new material numeric IDs when opening the same hairstyle
    # on a different avatar. Role, mesh and slot position remain the anchors.
    return re.sub(r"[0-9]+", "", token(value))


def guard(path):
    if not (package(path) == UE_ROOT or package(path).startswith(UE_ROOT + "/")):
        raise RuntimeError("Mutation outside this batch: " + path)


def save(asset):
    guard(object_path(asset))
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + object_path(asset))


def assets(root, class_name=None):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    return [data.get_asset() for data in registry.get_assets_by_path(root, recursive=True)
            if class_name is None or str(data.asset_class_path.asset_name) == class_name]


def dependency_options():
    options = unreal.AssetRegistryDependencyOptions()
    # UE 5.8 additionally filters Game/editor-only edges. Match the existing
    # accepted restructure referencer audit instead of relying on defaults.
    for name in ("include_soft_package_references", "include_hard_package_references",
                 "include_game_package_references", "include_editor_only_package_references"):
        options.set_editor_property(name, True)
    return options


def duplicate(source, target):
    guard(target)
    result = unreal.load_asset(target)
    if result is None:
        result = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    if result is None:
        raise RuntimeError("Cannot duplicate " + source + " -> " + target)
    original = unreal.load_asset(source)
    if original is None or original.get_class() != result.get_class():
        raise RuntimeError("Destination class mismatch " + target)
    return result


def source_path(row, kind):
    value = row.get(kind) or row.get("source_" + kind)
    if value is None and "production_output" in row:
        output = row["production_output"]
        value = str(Path(output["export_root"]) / (output["export_basename"] + "." + kind))
    path = Path(value).resolve()
    if not path.is_relative_to(EXPORT_ROOT.resolve()) or not path.is_file():
        raise RuntimeError("Missing/out-of-batch " + kind + ": " + str(path))
    record = row.get(kind + "_record", {})
    if record.get("bytes") is not None and path.stat().st_size != record["bytes"]:
        raise RuntimeError("Source size differs from completed export " + str(path))
    expected = row.get(kind + "_sha256")
    if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError("Source hash mismatch " + str(path))
    return path


def import_fbx(row, root, skeleton=None, materials=False, combine=False):
    guard(root)
    source = source_path(row, "fbx")
    existing = assets(root, "SkeletalMesh")
    if existing:
        return existing
    pipeline_path = root + "/DM_FixedHead_ImportPipeline"
    pipeline = duplicate(DEFAULT_PIPELINE, pipeline_path)
    mesh = pipeline.get_editor_property("mesh_pipeline")
    common = pipeline.get_editor_property("common_skeletal_meshes_and_animations_properties")
    animation = pipeline.get_editor_property("animation_pipeline")
    material = pipeline.get_editor_property("material_pipeline")
    mesh.set_editor_properties({"import_skeletal_meshes": True, "import_static_meshes": False,
        "combine_skeletal_meshes_behavior": (unreal.InterchangeCombineSkeletalMeshesBehavior.BY_SKELETON
            if combine else unreal.InterchangeCombineSkeletalMeshesBehavior.DO_NOT_COMBINE),
        "import_morph_targets": False, "create_physics_asset": False, "physics_asset": None,
        "skeletal_mesh_import_content_type": unreal.InterchangeSkeletalMeshContentType.ALL})
    common.set_editor_properties({"skeleton": skeleton, "try_auto_select_skeleton": False,
                                 "import_only_animations": False})
    animation.set_editor_property("import_animations", False)
    material.set_editor_property("import_materials", materials)
    material.get_editor_property("texture_pipeline").set_editor_property("import_textures", materials)
    save(pipeline)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    cvar = "Interchange.FeatureFlags.Import.FBX"
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, cvar + " 1")
    try:
        params = unreal.ImportAssetParameters()
        params.set_editor_properties({"is_automated": True, "force_show_dialog": False,
            "replace_existing": False, "override_pipelines": [unreal.SoftObjectPath(object_path(pipeline))]})
        manager.import_asset(root, manager.create_source_data(str(source)), params)
    finally:
        unreal.SystemLibrary.execute_console_command(world, cvar + " " + str(previous))
    result = assets(root, "SkeletalMesh")
    if not result:
        raise RuntimeError("FBX import produced no skeletal meshes " + str(source))
    unreal.EditorAssetLibrary.save_directory(root, only_if_is_dirty=False, recursive=True)
    return result


def mesh_record(mesh):
    slots = list(mesh.get_editor_property("materials"))
    return {"name": mesh.get_name(), "path": object_path(mesh),
            "materials": [object_path(s.get_editor_property("material_interface")) for s in slots],
            "slot_names": [str(s.get_editor_property("material_slot_name")) for s in slots]}


def ensure_base(sex, row):
    shared = UE_ROOT + "/Shared/" + sex.title()
    activity("base_import", sex=sex)
    meshes = import_fbx(row, shared + "/CombinedBase", None, materials=True, combine=True)
    activity("base_import_complete", sex=sex, mesh_count=len(meshes))
    if len(meshes) != 1:
        raise RuntimeError("Combined naked base must produce exactly one SkeletalMesh for " + sex)
    body = meshes[0]
    # Interchange can classify Body/Arm/Leg normal maps as sRGB color textures.
    # Verify the exact CC skin slot and declared source file before correcting
    # texture metadata; do not apply a filename-wide texture sweep.
    from ue_fixed_head_skin_texture_utils_v1 import configure_imported_skin_normals, SKIN_SLOTS
    json_path, cc_mesh_materials = source_materials(row)
    exact_skin_sources = {}
    for name in SKIN_SLOTS:
        candidates = [materials[token(name)] for materials in cc_mesh_materials.values()
                      if token(name) in materials]
        if candidates:
            if any(candidate != candidates[0] for candidate in candidates[1:]):
                raise RuntimeError("Conflicting source skin material " + name)
            exact_skin_sources[name] = candidates[0]
    skin_normal_records = configure_imported_skin_normals(body, exact_skin_sources, json_path)
    skeleton = body.get_editor_property("skeleton")
    if skeleton is None:
        raise RuntimeError("Combined base has no Skeleton " + sex)
    save(skeleton)
    # The first failed attempt's split Base assets are confined to this batch.
    # Delete only after reverse dependency checks prove there are no external
    # saved referencers. CombinedBase's original mesh/Skeleton stay untouched.
    old_duplicate = shared + "/SK_FixedHead_" + sex.title()
    if unreal.EditorAssetLibrary.does_asset_exist(old_duplicate):
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        references = registry.get_referencers(old_duplicate, dependency_options()) or []
        if references:
            raise RuntimeError("Failed-attempt Skeleton still has saved referencers " + str(references))
        if not unreal.EditorAssetLibrary.delete_asset(old_duplicate):
            raise RuntimeError("Could not remove failed-attempt Skeleton")
    old_base = shared + "/Base"
    if unreal.EditorAssetLibrary.does_directory_exist(old_base):
        cleanup_staging(old_base, [])
    activity("base_complete", sex=sex)
    return skeleton, {"skeleton_path": object_path(skeleton), "meshes": [mesh_record(m) for m in meshes],
        "body_mesh": object_path(body), "source_reference_id": row.get("source_reference_id", sex + "01"),
        "source_fbx": str(source_path(row, "fbx")), "skin_normal_setup": skin_normal_records}


def zero_material():
    path = UE_ROOT + "/Shared/Materials/M_Coverage_ZeroMask"
    material = unreal.load_asset(path)
    if material is None:
        folder, name = path.rsplit("/", 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
        material.set_editor_properties({"blend_mode": unreal.BlendMode.BLEND_MASKED,
            "shading_model": unreal.MaterialShadingModel.MSM_UNLIT, "used_with_skeletal_mesh": True})
        zero = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant)
        zero.set_editor_property("r", 0.)
        unreal.MaterialEditingLibrary.connect_material_property(zero, "", unreal.MaterialProperty.MP_OPACITY_MASK)
        unreal.MaterialEditingLibrary.recompile_material(material)
        save(material)
    return material


def source_materials(row):
    path = source_path(row, "json")
    document = read(path)
    actor = next(iter(next(iter(document.values()))["Object"].values()))
    result = {}
    for mesh_name, mesh in actor["Meshes"].items():
        entries = {}
        for name, material in mesh.get("Materials", {}).items():
            key = token(name)
            if key in entries and entries[key] != material:
                raise RuntimeError("Conflicting CC material " + name)
            entries[key] = material
        result[token(mesh_name)] = entries
    return path, result


def source_mesh_materials(sources, expected_name):
    wanted = token(expected_name)
    matches = [(key, value) for key, value in sources.items() if key == wanted]
    if not matches:
        matches = [(key, value) for key, value in sources.items() if key.endswith("_" + wanted)]
    if len(matches) != 1:
        raise RuntimeError("CC JSON hair mesh mapping ambiguous/missing " + expected_name)
    return matches[0][1]


def texture_from_source(path, source, channel, destination, name):
    relative = source.get("Textures", {}).get(channel, {}).get("Texture Path")
    if not relative:
        raise RuntimeError("Required hair texture missing: " + name + "/" + channel)
    physical = (path.parent / relative).resolve()
    if not physical.is_file():
        raise RuntimeError("Missing hair texture " + str(physical))
    target = destination + "/T_" + safe_name(name) + "_" + safe_name(channel)
    texture = unreal.load_asset(target)
    if texture is None:
        task = unreal.AssetImportTask()
        task.set_editor_properties({"filename": str(physical), "destination_path": destination,
            "destination_name": "T_" + safe_name(name) + "_" + safe_name(channel), "automated": True,
            "save": True, "replace_existing": False})
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = unreal.load_asset(target)
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError("Failed texture import " + target)
    if channel == "Opacity":
        texture.set_editor_properties({"srgb": False,
            "compression_settings": unreal.TextureCompressionSettings.TC_GRAYSCALE})
        save(texture)
    return texture


def repaired_material(row, template, json_path, cc_source, root, fallback_records):
    # Duplicate this exact hairstyle/slot's accepted clean V2 instance. Its parent
    # and shader defaults remain shared, and the new export supplies its own maps.
    target = root + "/Materials/MI_" + safe_name(template["slot_name"]) + "_StrandsV2"
    material = duplicate(template["v2_material"], target)
    library = unreal.MaterialEditingLibrary
    for parameter, channel in (("Base Color Map", "Base Color"), ("Opacity Map", "Opacity")):
        relative = cc_source.get("Textures", {}).get(channel, {}).get("Texture Path")
        if relative:
            texture = texture_from_source(json_path, cc_source, channel, root + "/Textures", template["slot_name"])
        else:
            # Some CC hair parts omit an optional channel after rebaking dye.
            # Geometry refitting does not alter UVs. Reuse only this exact
            # retained hairstyle/mesh/slot's already accepted texture, never
            # another hairstyle's diffuse or opacity map.
            texture = unreal.load_asset(template["diffuse" if channel == "Base Color" else "opacity"])
            if not isinstance(texture, unreal.Texture2D):
                raise RuntimeError("Missing exact accepted fallback " + template["slot_name"] + "/" + channel)
            fallback_records.append({"hair_id": row["hair_id"], "mesh": template["mesh"],
                "slot_index": template["slot_index"], "slot_name": template["slot_name"], "channel": channel,
                "accepted_texture": object_path(texture), "reason": "channel omitted by this CC export"})
        library.set_material_instance_texture_parameter_value(material, parameter, texture)
        if object_path(library.get_material_instance_texture_parameter_value(material, parameter)) != object_path(texture):
            raise RuntimeError("Texture setter readback mismatch " + parameter)
    overrides = material.get_editor_property("base_property_overrides")
    overrides.set_editor_properties({"override_opacity_mask_clip_value": True, "opacity_mask_clip_value": .15})
    material.set_editor_property("base_property_overrides", overrides)
    library.update_material_instance(material)
    save(material)
    return material


def select_mesh(imported, expected):
    wanted = token(expected)
    exact = [mesh for mesh in imported if token(mesh.get_name()) == wanted]
    if not exact:
        exact = [mesh for mesh in imported if token(mesh.get_name()).endswith("_" + wanted)]
    if len(exact) != 1:
        raise RuntimeError("Hair mesh name mapping ambiguous/missing: " + expected + " / " + str([m.get_name() for m in imported]))
    return exact[0]


def cleanup_staging(staging, final_meshes):
    guard(staging)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = dependency_options()
    for mesh in final_meshes:
        direct = [object_path(mesh.get_editor_property("skeleton")),
                  object_path(mesh.get_editor_property("physics_asset"))]
        direct += [object_path(s.get_editor_property("material_interface"))
                   for s in mesh.get_editor_property("materials")]
        if any(p and package(p).startswith(staging + "/") for p in direct):
            raise RuntimeError("Final mesh has a direct staging reference " + object_path(mesh))
        for slot in mesh.get_editor_property("materials"):
            material = slot.get_editor_property("material_interface")
            if isinstance(material, unreal.MaterialInstanceConstant):
                support = [object_path(material.get_editor_property("parent"))]
                support += [object_path(parameter.get_editor_property("parameter_value"))
                    for parameter in material.get_editor_property("texture_parameter_values") or []]
                if any(p and package(p).startswith(staging + "/") for p in support):
                    raise RuntimeError("Runtime hair material retains a staging parent/texture " + object_path(material))
        dependencies = [str(p) for p in registry.get_dependencies(package(object_path(mesh)), options) or []]
        if any(p.startswith(staging + "/") for p in dependencies):
            raise RuntimeError("Final mesh still refers to staging " + object_path(mesh))
    # Include material dependency chains in the reverse check: no surviving
    # package outside this case's staging may reference an asset being removed.
    for asset in assets(staging):
        referencers = [str(p) for p in registry.get_referencers(package(object_path(asset)), options) or []]
        external = [p for p in referencers if not p.startswith(staging + "/")]
        if external:
            raise RuntimeError("Staging has external referencers " + str(external))
    if not unreal.EditorAssetLibrary.delete_directory(staging):
        raise RuntimeError("Cannot remove this batch's staging " + staging)


def import_case(row, skeleton, base, hair, repairs, coverage, invisible):
    sex, hair_id = row["sex"], row["hair_id"]
    root = UE_ROOT + "/Hair/" + hair_id.removeprefix("HAIR_") + "/" + sex.title()
    staging = UE_ROOT + "/_Staging/" + safe_name(row["case_id"])
    activity("hair_import", case_id=row["case_id"])
    meshes = import_fbx(row, staging, skeleton, materials=False)
    activity("hair_import_complete", case_id=row["case_id"], mesh_count=len(meshes))
    # Import may append accessory bones to the explicit shared Skeleton. Save
    # it outside staging before removing the transient complete-avatar import.
    save(skeleton)
    json_path, sources = source_materials(row)
    final, hidden, fallbacks, source_shader_records = [], [], [], []
    for expected in hair["meshes"]:
        activity("hair_materials", case_id=row["case_id"], mesh=expected["name"])
        source_mesh = select_mesh(meshes, expected["name"])
        own_sources = None
        if object_path(source_mesh.get_editor_property("skeleton")) != object_path(skeleton):
            raise RuntimeError("Imported hair has wrong Skeleton " + object_path(source_mesh))
        reference = unreal.load_asset(expected["path"])
        if reference is None:
            raise RuntimeError("Missing accepted slot template " + expected["path"])
        old_slots = list(reference.get_editor_property("materials"))
        slots = list(source_mesh.get_editor_property("materials"))
        if len(slots) != len(old_slots):
            raise RuntimeError("Hair material slot count changed " + expected["name"])
        target = root + "/Meshes/" + expected["name"]
        mesh = duplicate(object_path(source_mesh), target)
        for index, (slot, old) in enumerate(zip(slots, old_slots)):
            actual = str(slot.get_editor_property("material_slot_name"))
            known = str(old.get_editor_property("material_slot_name"))
            if material_role(actual) != material_role(known):
                raise RuntimeError("Slot role/layout changed " + actual + " != " + known)
            key = (hair_id, package(expected["path"]), index, known)
            if key in coverage:
                bound = invisible
                hidden.append({"mesh": target, "slot_index": index, "slot_name": known,
                               "imported_slot_name": actual,
                               "approved_original_mesh": expected["path"]})
            else:
                template = repairs.get(key)
                if template:
                    # Resolve the exact new slot only for V2 map rebinding.
                    # Solid adornments can be separate FBX meshes while their
                    # CC JSON remains one grouped mesh; their accepted material
                    # is preserved and needs no source-texture lookup.
                    if own_sources is None:
                        own_sources = source_mesh_materials(sources, expected["name"])
                    cc_source = own_sources.get(token(actual))
                    if cc_source is None:
                        imported_name = str(slot.get_editor_property("imported_material_slot_name"))
                        cc_source = own_sources.get(token(imported_name))
                    if cc_source is None:
                        raise RuntimeError("No exact CC JSON material for " + expected["name"] + "/" + actual)
                    bound = repaired_material(row, template, json_path, cc_source, root, fallbacks)
                else:
                    # Source shader semantics, not the Transparency substring,
                    # distinguish real hair braids from Band/jewelry ornaments.
                    # CC groups separate FBX braid meshes in one JSON mesh, so
                    # resolve only the exact unique slot across source groups.
                    cc_source = exact_material(sources, actual)
                    if cc_source is None:
                        cc_source = exact_material(sources, str(slot.get_editor_property("imported_material_slot_name")))
                    if cc_source is not None and is_rl_hair(cc_source) and not is_ornament_slot(actual):
                        target_material = root + "/Materials/MI_" + safe_name(actual) + "_SourceHairV1"
                        bound, _source_record = create_source_hair_material(
                            cc_source, json_path, target_material, root + "/Textures", actual)
                        source_shader_records.append({"mesh": target, "slot_index": index,
                            "slot_name": actual, **_source_record})
                    else:
                        # Preserve this exact hairstyle's actual ornaments.
                        bound = old.get_editor_property("material_interface")
                        if bound is None:
                            raise RuntimeError("Missing solid hair/ornament material " + known)
            slot.set_editor_property("material_interface", bound)
        mesh.set_editor_properties({"materials": slots, "physics_asset": None})
        if object_path(mesh.get_editor_property("skeleton")) != object_path(skeleton):
            raise RuntimeError("Duplicated hair did not preserve shared Skeleton")
        save(mesh)
        final.append(mesh)
    activity("hair_cleanup", case_id=row["case_id"])
    cleanup_staging(staging, final)
    activity("hair_complete", case_id=row["case_id"])
    return {"case_id": row["case_id"], "hair_id": hair_id, "sex": sex, "success": True,
        "skeleton_path": object_path(skeleton), "source_reference_id": base["source_reference_id"],
        "meshes": [mesh_record(m) for m in final], "coverage_hidden_slots": hidden,
        "source_fbx": str(source_path(row, "fbx")), "source_json": str(json_path),
        "staging_removed": True, "runtime_mesh_count": len(final),
        "runtime_support_closure_verified": True, "accepted_texture_fallbacks": fallbacks,
        "source_shader_material_bindings": source_shader_records}


def validate_record(row):
    if not row.get("success") or not row.get("staging_removed"):
        return False
    for item in row.get("meshes", []):
        mesh = unreal.load_asset(item["path"])
        if mesh is None or object_path(mesh.get_editor_property("skeleton")) != row["skeleton_path"]:
            return False
        current_materials = mesh_record(mesh)["materials"]
        if current_materials != item["materials"]:
            # Completed import evidence is immutable. Reconcile only exact
            # subsequently authorized material-only repair bindings, without
            # reopening exports/staging or changing the original import report.
            receipt_path = REPO / "00_engine/outputs/unreal_character_import/fixed_head_material_repair_20261005_v1/hair/hair_apply_latest.json"
            receipt = read(receipt_path) if receipt_path.is_file() else {}
            authorized = {(r["mesh"], r["slot_index"]): r for r in receipt.get("records", [])}
            if not receipt.get("success") or receipt.get("mode") != "apply" or len(current_materials) != len(item["materials"]):
                return False
            for index, (before, after) in enumerate(zip(item["materials"], current_materials)):
                if before == after:
                    continue
                repair = authorized.get((item["path"], index), {})
                if (repair.get("before") != before or repair.get("material") != after or
                    not after.startswith("/Game/DataMake/CharacterFactory/MaterialRemediation_20261005_v1/Hair/")):
                    return False
        staging = UE_ROOT + "/_Staging/" + safe_name(row["case_id"])
        if mesh.get_editor_property("physics_asset") is not None:
            return False
        for slot in mesh.get_editor_property("materials"):
            material = slot.get_editor_property("material_interface")
            if material is None or package(object_path(material)).startswith(staging + "/"):
                return False
            if isinstance(material, unreal.MaterialInstanceConstant):
                parent = material.get_editor_property("parent")
                if parent is None or package(object_path(parent)).startswith(staging + "/"):
                    return False
                for parameter in material.get_editor_property("texture_parameter_values") or []:
                    texture = parameter.get_editor_property("parameter_value")
                    if texture is not None and package(object_path(texture)).startswith(staging + "/"):
                        return False
    return bool(row.get("meshes"))


def run():
    manifest_path = Path(globals().get("DM_FIXED_HAIR_MANIFEST", EXPORT_ROOT / "manifests/batch.json"))
    config_path = globals().get("DM_FIXED_HAIR_CONFIG")
    config = read(config_path) if config_path else {}
    manifest = read(manifest_path)
    if manifest.get("batch_id") != BATCH_ID:
        raise RuntimeError("Wrong batch manifest")
    cases = manifest["cases"]
    ids = [r["case_id"] for r in cases]
    if len(ids) != len(set(ids)) or any(r["sex"] not in ("male", "female") for r in cases):
        raise RuntimeError("Invalid case identities")
    old = read(REPO / "00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json")
    accepted = read(REVIEW_ROOT / "coverage_visibility_acceptance_20260930_v1/approved_coverage_slots.json")
    registry_path = REPO / accepted["registry_path"]
    if hashlib.sha256(registry_path.read_bytes()).hexdigest() != accepted["registry_sha256"]:
        raise RuntimeError("Accepted coverage registry changed")
    repair_plan = read(REVIEW_ROOT / "rendering_repair_v2/repair_plan.json")
    key = lambda r: (r["hair_id"], package(r["mesh"]), r["slot_index"], r["slot_name"])
    repairs = {key(r): r for r in repair_plan["rows"]}
    coverage = {key(r) for r in accepted["slots"]}
    hair_lookup = {r["hair_id"]: r for r in old["hair_assets"]}
    report_path = REPORT_ROOT / "import_report.json"
    report = read(report_path) if report_path.exists() else {
        "schema_version": 1, "batch_id": BATCH_ID, "ue_root": UE_ROOT, "bases": {}, "records": []}
    if report.get("complete"):
        if all(validate_record(row) for row in report.get("records", [])) and len(report.get("records", [])) == len(ids):
            unreal.log("Completed fixed-head import already valid; original import evidence left untouched")
            return
        raise RuntimeError("Completed fixed-head import has an unreconciled maintenance change; do not reopen or regenerate the completed batch")
    report.update({"success": False, "complete": False, "manifest": str(manifest_path),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(), "phase": "bases"})
    write(report_path, report)
    skeletons = {}
    for sex in ("female", "male"):
        skeletons[sex], report["bases"][sex] = ensure_base(sex, manifest["bases"][sex])
        write(report_path, report)
    invisible = zero_material()
    done = {r["case_id"]: r for r in report["records"] if validate_record(r)}
    selected = set(config.get("case_ids") or ids)
    if selected - set(ids):
        raise RuntimeError("Unknown selected case IDs")
    pending = [r for r in cases if r["case_id"] in selected and r["case_id"] not in done]
    limit = int(config.get("max_cases", 80))
    if not 1 <= limit <= 80:
        raise RuntimeError("max_cases must be 1..80")
    for row in pending[:limit]:
        report.update({"phase": "importing", "current_case": row["case_id"],
                       "updated_at_utc": datetime.now(timezone.utc).isoformat()})
        write(report_path, report)
        try:
            result = import_case(row, skeletons[row["sex"]], report["bases"][row["sex"]],
                                 hair_lookup[row["hair_id"]], repairs, coverage, invisible)
        except Exception:
            result = {"case_id": row["case_id"], "hair_id": row["hair_id"], "sex": row["sex"],
                      "success": False, "error": traceback.format_exc()}
            report["records"] = [r for r in report["records"] if r["case_id"] != row["case_id"]] + [result]
            report["phase"] = "failed"
            write(report_path, report)
            raise
        report["records"] = [r for r in report["records"] if r["case_id"] != row["case_id"]] + [result]
        write(report_path, report)
        unreal.log("Fixed head hair: " + row["case_id"] + " complete")
    valid = {r["case_id"] for r in report["records"] if validate_record(r)}
    for row in report["records"]:
        if row["case_id"] in valid:
            row["runtime_support_closure_verified"] = True
    fallback_rows = [item for row in report["records"] if row.get("success")
                     for item in row.get("accepted_texture_fallbacks", [])]
    report["accepted_texture_fallback_summary"] = {
        "channel_bindings": len(fallback_rows),
        "cases": sum(bool(row.get("accepted_texture_fallbacks")) for row in report["records"] if row.get("success")),
        "hairstyles": sorted({item["hair_id"] for item in fallback_rows}),
        "accepted_textures": sorted({item["accepted_texture"] for item in fallback_rows}),
        "policy": "Only the exact retained hair/mesh/slot's accepted texture when this CC JSON omits the channel"}
    report.update({"phase": "complete" if valid == set(ids) else "batch_complete",
        "completed_cases": len(valid), "expected_cases": len(ids), "complete": valid == set(ids),
        "success": valid == set(ids), "current_case": None,
        "updated_at_utc": datetime.now(timezone.utc).isoformat()})
    write(report_path, report)
    unreal.log("Fixed head hair batch result: " + str(report_path))


if globals().get("DM_FIXED_HAIR_RUN", True):
    run()
