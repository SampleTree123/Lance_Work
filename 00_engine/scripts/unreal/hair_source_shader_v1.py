"""Source-driven CC RLHair material creation shared by import and remediation.

Importing this module does not import unreal or mutate assets. Dye is already
baked into exported diffuse maps: never enable the extra dye/vertex tint again.
"""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

PARENT = "/Game/CC_Shaders/HairShader/RL_Hair_Specular.RL_Hair_Specular"
HEADER = Path("D:/UE/projects/datatry_02/Plugins/RLPlugin/Source/RLPlugin/Private/RLShaderData.h")


def is_rl_hair(source):
    return str(source.get("Custom Shader", {}).get("Shader Name", "")).casefold() == "rlhair"


def is_ornament_slot(slot_name):
    # CC sometimes attaches RLHair metadata to a hair-band accessory. Actual
    # ornament roles retain their historical appearance despite that tag.
    role = re.sub(r"[0-9]+", "", str(slot_name)).casefold()
    return role.startswith(("band", "hairring", "hair_ring", "hair_clip", "flower", "pearl", "butterfly"))


def exact_material(sources, slot_name):
    """Resolve grouped braid JSON only by exact unique slot, never by substring."""
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", slot_name).casefold()
    matches = [value[normalized] for value in sources.values() if normalized in value]
    if not matches:
        return None
    if any(value != matches[0] for value in matches[1:]):
        raise RuntimeError("Conflicting exact CC source slot " + slot_name)
    return matches[0]


def shader_settings(source):
    if not is_rl_hair(source):
        raise ValueError("Only source-declared RLHair can use the hair shader")
    text = HEADER.read_text(encoding="utf-8")
    section = text.split("g_kHairMap =", 1)[1].split("};", 1)[0]
    mapping = dict(re.findall(r'\{\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\}', section))
    mapping.update({"TangentMapFlipGreen": "Flip Tangent Y", "ActiveChangeHairColor": "Activate Hair Color"})
    shader = source["Custom Shader"]
    if any(value.get("Texture Path") for value in shader.get("Image", {}).values()):
        raise RuntimeError("Custom hair maps require an explicit supported mapping")
    variables = shader.get("Variable", {})
    scalars = {"Increase Opacity Mask Min Value": 0., "Alpha Power": 1., "Alpha Multiplier": 1.,
               "Blend Strength": 0., "Glow Strength": 0., "Opacity": float(source.get("Opacity", 1.)),
               "Opacity Strength": 1., "PixelDepthOffset": 0.,
               "Specular Strength": float(variables.get("Specular Strength", .5))}
    vectors = {"Base Color Tint": [float(c)/255. for c in source.get("Diffuse Color", [255.]*3)] + [1.]}
    switches = {"Use Flow Map": False, "Use ORM Map": False, "Use Bump Map": False,
                "Activate Hair Color": False, "Flip Tangent Y": bool(variables.get("TangentMapFlipGreen", 0))}
    for cc_name, ue_name in mapping.items():
        if cc_name not in variables or ue_name in switches:
            continue
        value = variables[cc_name]
        if isinstance(value, list):
            vectors[ue_name] = [float(c)/255. for c in value] + [1.]
        else:
            scalars[ue_name] = float(value)
    scalars["Vertex Color Strength"] = 0.
    return {"scalars": scalars, "vectors": vectors, "switches": switches,
            "source_mapping": str(HEADER), "source_mapping_sha256": hashlib.sha256(HEADER.read_bytes()).hexdigest(),
            "unmapped_source_lighting_variables": {key:variables[key] for key in ("Secondary Specular Strength", "Transmission Strength") if key in variables},
            "unmapped_reason": "The accepted UE RL_Hair_Specular parent and plugin hair mapping expose no direct equivalent; preserve values as evidence, do not silently invent a mapping."}


def create_material(source, json_path, target, texture_root, texture_prefix):
    import unreal
    settings = shader_settings(source)
    library = unreal.MaterialEditingLibrary
    parent = unreal.load_asset(PARENT)
    if not isinstance(parent, unreal.Material):
        raise RuntimeError("Missing accepted RL hair parent")
    paths = {}
    for parameter, channel in (("Base Color Map", "Base Color"), ("Opacity Map", "Opacity")):
        relative = source.get("Textures", {}).get(channel, {}).get("Texture Path")
        if not relative:
            raise RuntimeError("Required exact hair map missing " + channel)
        physical = (Path(json_path).parent / relative).resolve()
        if not physical.is_file():
            raise RuntimeError("Required exact hair map file missing " + str(physical))
        name = "T_" + re.sub(r"[^A-Za-z0-9_]", "_", texture_prefix + "_" + channel)
        destination = texture_root + "/" + name
        texture = unreal.load_asset(destination)
        if texture is None:
            task = unreal.AssetImportTask()
            task.set_editor_properties({"filename": str(physical), "destination_path": texture_root,
                "destination_name": name, "automated": True, "save": True, "replace_existing": False})
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            texture = unreal.load_asset(destination)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError("Cannot import exact source texture " + destination)
        texture.set_editor_properties({"srgb": channel == "Base Color",
            "compression_settings": unreal.TextureCompressionSettings.TC_DEFAULT if channel == "Base Color" else unreal.TextureCompressionSettings.TC_GRAYSCALE})
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False):
            raise RuntimeError("Cannot save texture settings " + destination)
        paths[parameter] = {"texture": texture.get_path_name(), "source_file": str(physical),
                            "sha256": hashlib.sha256(physical.read_bytes()).hexdigest()}
    material = unreal.load_asset(target)
    if material is None:
        folder,name = target.rsplit("/",1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if not isinstance(material, unreal.MaterialInstanceConstant):
        raise RuntimeError("Wrong remediation asset class " + target)
    library.set_material_instance_parent(material, parent)
    library.clear_all_material_instance_parameters(material)
    textures = {str(name):library.get_material_default_texture_parameter_value(parent,name) for name in library.get_texture_parameter_names(parent)}
    textures.update({name:unreal.load_asset(value["texture"]) for name,value in paths.items()})
    for name,texture in textures.items():
        if texture is None:
            continue
        library.set_material_instance_texture_parameter_value(material,name,texture)
        actual = library.get_material_instance_texture_parameter_value(material,name)
        if actual is None or actual.get_path_name() != texture.get_path_name():
            raise RuntimeError("Texture readback mismatch " + name)
    for name,value in settings["scalars"].items():
        if name not in {str(n) for n in library.get_scalar_parameter_names(material)}:
            raise RuntimeError("Unsupported accepted shader scalar " + name)
        library.set_material_instance_scalar_parameter_value(material,name,value)
        if abs(library.get_material_instance_scalar_parameter_value(material,name)-value)>1e-5:
            raise RuntimeError("Scalar readback mismatch " + name)
    for name,value in settings["vectors"].items():
        if name not in {str(n) for n in library.get_vector_parameter_names(material)}:
            raise RuntimeError("Unsupported accepted shader vector " + name)
        library.set_material_instance_vector_parameter_value(material,name,unreal.LinearColor(*value))
        actual = library.get_material_instance_vector_parameter_value(material,name)
        if any(abs(a-b)>1e-5 for a,b in zip((actual.r,actual.g,actual.b,actual.a),value)):
            raise RuntimeError("Vector readback mismatch " + name)
    for name,value in settings["switches"].items():
        if name not in {str(n) for n in library.get_static_switch_parameter_names(material)}:
            raise RuntimeError("Unsupported accepted shader switch " + name)
        library.set_material_instance_static_switch_parameter_value(material,name,value,update_material_instance=False)
    overrides = material.get_editor_property("base_property_overrides")
    overrides.set_editor_properties({"override_opacity_mask_clip_value":True,"opacity_mask_clip_value":.15})
    material.set_editor_property("base_property_overrides",overrides)
    library.update_material_instance(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):
        raise RuntimeError("Cannot save source hair material")
    return material,{"material":material.get_path_name(),"parent":PARENT,"textures":paths,**settings}
