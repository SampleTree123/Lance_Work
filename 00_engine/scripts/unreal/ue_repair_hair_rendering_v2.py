"""Apply clean source-driven hair instances, retaining previous material bindings."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/rendering_repair_v2"


def repair(hair_id):
    plan = json.loads((ROOT / "repair_plan.json").read_text(encoding="utf-8"))
    rows = [row for row in plan["rows"] if row["hair_id"] == hair_id]
    if not rows:
        raise ValueError("Unknown hairstyle " + hair_id)
    parent = unreal.load_asset(plan["parent"])
    library = unreal.MaterialEditingLibrary
    records = []
    opacity_records = []
    mesh_cache = {}
    slot_cache = {}
    for row in rows:
        if row["mesh"] not in mesh_cache:
            mesh = unreal.load_asset(row["mesh"])
            if not isinstance(mesh, unreal.SkeletalMesh):
                raise RuntimeError("Missing hair mesh " + row["mesh"])
            mesh_cache[row["mesh"]] = mesh
            slot_cache[row["mesh"]] = list(mesh.get_editor_property("materials"))
    # Start from the parent defaults, not a material instance belonging to another hairstyle.
    for row in rows:
        target = row["v2_material"]
        material = unreal.load_asset(target)
        if material is None:
            folder, name = target.rsplit("/", 1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        library.set_material_instance_parent(material, parent)
        library.clear_all_material_instance_parameters(material)
        textures = {str(name): library.get_material_default_texture_parameter_value(parent, name)
                    for name in library.get_texture_parameter_names(parent)}
        textures.update({"Base Color Map": unreal.load_asset(row["diffuse"]),
                         "Opacity Map": unreal.load_asset(row["opacity"])})
        for name, texture in textures.items():
            if texture is not None:
                # UE 5.8 setters return false even after setting the value; verify the getter.
                library.set_material_instance_texture_parameter_value(material, name, texture)
                actual = library.get_material_instance_texture_parameter_value(material, name)
                if actual is None or actual.get_path_name() != texture.get_path_name():
                    raise RuntimeError("Cannot set texture " + name)
        opacity = textures["Opacity Map"]
        old_settings = {"srgb": opacity.get_editor_property("srgb"),
                        "compression_settings": str(opacity.get_editor_property("compression_settings"))}
        if opacity.get_path_name() not in {item["path"] for item in opacity_records}:
            opacity.set_editor_property("srgb", False)
            opacity.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
            if not unreal.EditorAssetLibrary.save_loaded_asset(opacity, only_if_is_dirty=False):
                raise RuntimeError("Cannot save opacity texture")
            opacity_records.append({"path": opacity.get_path_name(), "before": old_settings,
                                    "after": {"srgb": False, "compression_settings": "TC_GRAYSCALE"}})
        scalar_names = {str(name) for name in library.get_scalar_parameter_names(material)}
        vector_names = {str(name) for name in library.get_vector_parameter_names(material)}
        switch_names = {str(name) for name in library.get_static_switch_parameter_names(material)}
        for name, value in row["scalars"].items():
            if name not in scalar_names:
                raise RuntimeError("Missing scalar " + name)
            library.set_material_instance_scalar_parameter_value(material, name, value)
            if abs(library.get_material_instance_scalar_parameter_value(material, name) - value) > 1e-5:
                raise RuntimeError("Scalar readback mismatch " + name)
        for name, value in row["vectors"].items():
            if name not in vector_names:
                raise RuntimeError("Missing vector " + name)
            library.set_material_instance_vector_parameter_value(material, name, unreal.LinearColor(*value))
            actual = library.get_material_instance_vector_parameter_value(material, name)
            if any(abs(a - b) > 1e-5 for a, b in zip((actual.r, actual.g, actual.b, actual.a), value)):
                raise RuntimeError("Vector readback mismatch " + name)
        for name, value in row["switches"].items():
            if name not in switch_names:
                raise RuntimeError("Missing switch " + name)
            library.set_material_instance_static_switch_parameter_value(material, name, value, update_material_instance=False)
        overrides = material.get_editor_property("base_property_overrides")
        overrides.set_editor_property("override_opacity_mask_clip_value", True)
        overrides.set_editor_property("opacity_mask_clip_value", plan["opacity_clip"])
        material.set_editor_property("base_property_overrides", overrides)
        library.update_material_instance(material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError("Cannot save clean hair material")
        slots = slot_cache[row["mesh"]]
        before = slots[row["slot_index"]].material_interface.get_path_name()
        allowed = (row["new_material"], target)
        if before.split(".", 1)[0] not in allowed:
            raise RuntimeError("Unexpected source material binding " + before)
        slots[row["slot_index"]].set_editor_property("material_interface", material)
        records.append({"mesh": row["mesh"], "slot": row["slot_index"], "old_material": before,
                        "new_material": material.get_path_name()})
    # Set and save once per mesh, so multi-slot styles don't rebuild the same mesh repeatedly.
    for mesh_path, mesh in mesh_cache.items():
        mesh.set_editor_property("materials", slot_cache[mesh_path])
        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError("Cannot save mesh binding " + mesh_path)
    result = {"success": True, "hair_id": hair_id, "slots": len(rows), "materials": records,
              "opacity_settings": opacity_records}
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / (hair_id + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("HAIR_RENDER_REPAIR=" + json.dumps({"hair_id": hair_id, "slots": len(rows), "success": True}))


if globals().get("DM_HAIR_RENDER_ID"):
    repair(DM_HAIR_RENDER_ID)
