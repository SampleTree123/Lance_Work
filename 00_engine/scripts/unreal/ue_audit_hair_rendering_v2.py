"""Read actual shader parameters and texture settings for the hair rendering pilot."""
from pathlib import Path
import json
import unreal

ROOT = Path(__file__).resolve().parents[2] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
OUT = ROOT / "rendering_repair_v2"


def path(asset):
    return asset.get_path_name() if asset else None


def properties(obj, names):
    result = {}
    for name in names:
        try:
            value = obj.get_editor_property(name)
            result[name] = value if isinstance(value, (str, int, float, bool)) else str(value)
        except Exception as exc:
            result[name] = "unavailable: " + str(exc)
    return result


def inspect(material):
    library = unreal.MaterialEditingLibrary
    scalars = {str(name): library.get_material_instance_scalar_parameter_value(material, name)
               for name in library.get_scalar_parameter_names(material)}
    vectors = {}
    for name in library.get_vector_parameter_names(material):
        value = library.get_material_instance_vector_parameter_value(material, name)
        vectors[str(name)] = [value.r, value.g, value.b, value.a]
    textures = {}
    for name in library.get_texture_parameter_names(material):
        texture = library.get_material_instance_texture_parameter_value(material, name)
        textures[str(name)] = {"path": path(texture), "settings": properties(texture, (
            "srgb", "compression_settings", "filter", "mip_gen_settings", "lod_group",
            "dither_mip_map_alpha", "never_stream", "virtual_texture_streaming")) if texture else {}}
    switches = {str(name): library.get_material_instance_static_switch_parameter_value(material, name)
                for name in library.get_static_switch_parameter_names(material)}
    parent = material.get_editor_property("parent")
    overrides = material.get_editor_property("base_property_overrides")
    return {"path": path(material), "parent": path(parent), "scalars": scalars, "vectors": vectors,
            "textures": textures, "switches": switches,
            "overrides": properties(overrides, ("override_opacity_mask_clip_value", "opacity_mask_clip_value",
                "override_two_sided", "two_sided", "override_blend_mode", "blend_mode",
                "override_shading_model", "shading_model")),
            "parent_settings": properties(parent, ("blend_mode", "two_sided", "opacity_mask_clip_value",
                "dither_opacity_mask", "shading_model", "dithered_lod_transition"))}


def main():
    plan = json.loads((ROOT / "masked_repair_plan.json").read_text(encoding="utf-8"))
    verify_v2 = bool(globals().get("DM_HAIR_AUDIT_V2", False))
    rows = []
    if verify_v2:
        v2 = json.loads((OUT / "repair_plan.json").read_text(encoding="utf-8"))
        applied = {path.stem for path in (OUT / "reports").glob("HAIR_*.json")}
        rows = [row for row in v2["rows"] if row["hair_id"] in applied]
        paths = list(dict.fromkeys(row["v2_material"] for row in rows))
    else:
        paths = [plan["template"]] + list(dict.fromkeys(row["new_material"] for row in plan["rows"]
                                                     if row["hair_id"] == "HAIR_HB1_09"))
    records = []
    for name in paths:
        material = unreal.load_asset(name)
        if not isinstance(material, unreal.MaterialInstanceConstant):
            raise RuntimeError("Missing pilot material: " + name)
        records.append(inspect(material))
    OUT.mkdir(exist_ok=True)
    errors = []
    by_path = {record["path"].split(".", 1)[0]: record for record in records}
    for row in rows:
        record = by_path[row["v2_material"]]
        bound = unreal.load_asset(row["mesh"]).get_editor_property("materials")[row["slot_index"]].material_interface
        if path(bound).split(".", 1)[0] != row["v2_material"]:
            errors.append("mesh binding: " + row["mesh"])
        if any("/Game/Vendor/" in (item["path"] or "") for item in record["textures"].values()):
            errors.append("foreign hairstyle texture: " + row["v2_material"])
        opacity = record["textures"]["Opacity Map"]
        if (opacity["path"] != row["opacity"] or opacity["settings"]["srgb"] is not False
                or "TC_GRAYSCALE" not in opacity["settings"]["compression_settings"]):
            errors.append("opacity settings: " + row["v2_material"])
        if record["textures"]["Base Color Map"]["path"] != row["diffuse"]:
            errors.append("diffuse binding: " + row["v2_material"])
        for name, value in row["scalars"].items():
            if abs(record["scalars"][name] - value) > 1e-5:
                errors.append("scalar: " + name)
        for name, value in row["vectors"].items():
            if any(abs(a-b) > 1e-5 for a,b in zip(record["vectors"][name], value)):
                errors.append("vector: " + name)
        for name, value in row["switches"].items():
            if record["switches"][name] != value:
                errors.append("switch: " + name)
    unchanged = 0
    if verify_v2:
        repaired_keys = {(row["mesh"], row["slot_index"]) for row in rows}
        original = json.loads((ROOT / "material_slot_audit.json").read_text(encoding="utf-8"))
        for row in original["rows"]:
            if (row["mesh"], row["slot_index"]) in repaired_keys:
                continue
            bound = unreal.load_asset(row["mesh"]).get_editor_property("materials")[row["slot_index"]].material_interface
            if path(bound) != row["material"]:
                errors.append("non-hair material changed: " + row["mesh"])
            unchanged += 1
    result = {"success": not errors, "errors": errors, "verified_mesh_slots": len(rows),
        "verified_unchanged_accessory_or_other_slots": unchanged, "materials": records, "console": {name:
        unreal.SystemLibrary.get_console_variable_int_value(name) for name in (
            "r.AntiAliasingMethod", "r.TemporalAA.Quality", "r.SSR.Quality",
            "r.Lumen.Reflections.Allow", "r.Lumen.ScreenProbeGather.Temporal.MaxFramesAccumulated")}}
    filename = ("fresh_load_material_audit.json" if globals().get("DM_HAIR_AUDIT_FRESH") else
                "applied_material_audit.json" if verify_v2 else "initial_material_audit.json")
    (OUT / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("HAIR_RENDER_AUDIT=" + json.dumps({"materials": len(records), "slots": len(rows), "errors": errors, "success": not errors}))


main()
