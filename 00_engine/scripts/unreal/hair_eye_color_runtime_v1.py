"""Isolated material-instance color experiments for the six-person hair review.

Only component overrides and owned experiment MIC assets may be changed. This is
not production color acceptance: baked texture pigmentation remains visible.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

VERSION = "hair_eye_color_experiment_v1"
PROJECT_CONTENT = Path("D:/UE/projects/datatry_02/Content")
ENGINE_CONTENT = Path("D:/UE/UE_5.8/Engine/Content")
INTERCHANGE_CONTENT = Path("D:/UE/UE_5.8/Engine/Plugins/Interchange/Assets/Content")
HAIR_PARENT = "/Game/CC_Shaders/HairShader/RL_Hair_Specular.RL_Hair_Specular"
EYE_PARENT = "/Game/CC_Shaders/EyeShader/RL_EyeRefractive.RL_EyeRefractive"
# Linear multipliers compensate for the shared warm source texture; these are
# not display RGB values. New preset IDs preserve prior copper/golden assets.
PRESETS = {
    "hair": {"black": (.10, .10, .10, 1.),
             "blue": (.06, .25, 4., 1.), "pink": (2., .12, 1.2, 1.),
             "purple": (.65, .08, 2.5, 1.), "red": (1.8, .035, .06, 1.),
             "teal": (.04, 1.1, 1.4, 1.),
             "orange": (3., .65, .015, 1.), "gold": (4., 5., .12, 1.),
             "silver_white": (12., 24., 40., 1.)},
    "eye": {"brown": (.45, .24, .10, 1.), "blue": (.12, .38, .90, 1.),
            "green": (.22, .65, .25, 1.)},
}
PARAMETERS = {"hair": "Base Color Tint", "eye": "Iris Color"}
CAPABILITIES = {kind: ["original", *options] for kind, options in PRESETS.items()}
OWNER_KEY = "DM_HairEyeColor_Owner"
SPEC_KEY = "DM_HairEyeColor_Spec"
STATE_KEY = "DM_HairEyeColor_State"


def validate_request(request):
    result = dict(request)
    for kind, choices in CAPABILITIES.items():
        key = kind + "_color"
        choice = result.get(key, "original")
        if not isinstance(choice, str) or choice not in choices:
            raise ValueError("Unsupported " + key + ": " + repr(choice))
        result[key] = choice
    return result


def _ue():
    import unreal
    return unreal


def _path(asset):
    return asset.get_path_name() if asset else None


def _sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def package_file(asset_path):
    if ".." in asset_path.split("/") or "\\" in asset_path:
        raise RuntimeError("Unsupported protected source package " + asset_path)
    package = asset_path.split(".", 1)[0]
    roots = {"/Game/": PROJECT_CONTENT, "/Engine/": ENGINE_CONTENT,
             "/InterchangeAssets/": INTERCHANGE_CONTENT}
    mount = next((prefix for prefix in roots if package.startswith(prefix)), None)
    if mount is None:
        raise RuntimeError("Unsupported protected source package " + package)
    root = roots[mount].resolve()
    file = (root / (package[len(mount):] + ".uasset")).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        raise RuntimeError("Missing saved source package " + str(file))
    return file


def _chain(material):
    chain, seen = [], set()
    while material is not None:
        name = _path(material)
        if name in seen or len(chain) >= 8:
            raise RuntimeError("Invalid material parent chain " + name)
        seen.add(name)
        chain.append(material)
        if isinstance(material, _ue().MaterialInstance):
            material = material.get_editor_property("parent")
        else:
            break
    return chain


def _ornament(slot_name):
    normalized = re.sub(r"[0-9]+", "", slot_name).casefold()
    return normalized.startswith(("band", "hairring", "hair_ring", "hair_clip", "flower", "pearl", "butterfly"))


def classify_slot(component_name, slot_name, material_path, parents):
    """Classify by component, explicit ornament roles, and actual shader chain."""
    if material_path is None or "M_Coverage_ZeroMask" in material_path or _ornament(slot_name):
        return None
    if component_name == "Eyes":
        return "eye" if EYE_PARENT in parents else None
    if re.fullmatch(r"HairPart\d+", component_name):
        return "hair" if HAIR_PARENT in parents else None
    return None


def _rgba(color):
    return [float(color.r), float(color.g), float(color.b), float(color.a)]


def _assert_rgba(actual, expected):
    if len(actual) != 4 or any(abs(a - b) > 1e-5 for a, b in zip(actual, expected)):
        raise RuntimeError("Color parameter readback mismatch")


def _name(asset_root, slot, source_path, kind, preset):
    if not isinstance(slot, int) or isinstance(slot, bool) or not 0 <= slot <= 6:
        raise ValueError("Review slot must be an integer from 0 to 6")
    if (not isinstance(asset_root, str) or "//" in asset_root
            or not (asset_root == "/Game/DataMake/Appearance/Materials"
                    or re.fullmatch(r"/Game/DataMake/Validation/[A-Za-z0-9_/]+", asset_root))):
        raise ValueError("Expected isolated validation or formal appearance material root")
    identifier = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:20]
    return f"{asset_root.rstrip('/')}/ColorExperiments/S{slot:02d}/MI_{kind}_{preset}_{identifier}"


def _spec(source, source_hash, kind, preset, slot):
    return json.dumps({"version": VERSION, "source": _path(source), "source_sha256": source_hash,
                       "kind": kind, "preset": preset, "slot": slot,
                       "parameter": PARAMETERS[kind], "rgba": PRESETS[kind][preset]}, sort_keys=True)


def _verify_instance(instance, source, spec, kind, preset):
    u, lib = _ue(), _ue().MaterialEditingLibrary
    if not isinstance(instance, u.MaterialInstanceConstant):
        raise RuntimeError("Experiment asset has wrong class")
    for key, expected in ((OWNER_KEY, VERSION), (SPEC_KEY, spec), (STATE_KEY, "complete")):
        if str(u.EditorAssetLibrary.get_metadata_tag(instance, key)) != expected:
            raise RuntimeError("Unrecognized or incomplete experiment material: " + _path(instance))
    if _path(instance.get_editor_property("parent")) != _path(source):
        raise RuntimeError("Experiment parent mismatch")
    for field in ("scalar_parameter_values", "texture_parameter_values"):
        if list(instance.get_editor_property(field)):
            raise RuntimeError("Unexpected experiment parameter overrides")
    vectors = list(instance.get_editor_property("vector_parameter_values"))
    if len(vectors) != 1 or str(vectors[0].get_editor_property("parameter_info").get_editor_property("name")) != PARAMETERS[kind]:
        raise RuntimeError("Unexpected experiment vector overrides")
    actual = _rgba(lib.get_material_instance_vector_parameter_value(instance, PARAMETERS[kind]))
    _assert_rgba(actual, PRESETS[kind][preset])
    for name in lib.get_static_switch_parameter_names(source):
        if lib.get_material_instance_static_switch_parameter_value(instance, name) != lib.get_material_instance_static_switch_parameter_value(source, name):
            raise RuntimeError("Unexpected experiment static switch override")
    for name in lib.get_texture_parameter_names(source):
        if _path(lib.get_material_instance_texture_parameter_value(instance, name)) != _path(lib.get_material_instance_texture_parameter_value(source, name)):
            raise RuntimeError("Experiment did not inherit source texture")
    properties = instance.get_editor_property("base_property_overrides")
    for name in ("override_blend_mode", "override_shading_model", "override_two_sided", "override_opacity_mask_clip_value"):
        if properties.get_editor_property(name):
            raise RuntimeError("Unexpected experiment base material override")
    return actual


def _material(row, asset_root, slot):
    u, lib = _ue(), _ue().MaterialEditingLibrary
    source, kind, preset = row["source"], row["kind"], row["preset"]
    target = _name(asset_root, slot, _path(source), kind, preset)
    spec = _spec(source, row["source_sha256"], kind, preset, slot)
    if u.EditorAssetLibrary.does_asset_exist(target):
        instance = u.load_asset(target)
        actual = _verify_instance(instance, source, spec, kind, preset)
        return instance, actual, False
    folder, name = target.rsplit("/", 1)
    instance = u.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    if not isinstance(instance, u.MaterialInstanceConstant):
        raise RuntimeError("Cannot create isolated experiment material")
    lib.set_material_instance_parent(instance, source)
    u.EditorAssetLibrary.set_metadata_tag(instance, OWNER_KEY, VERSION)
    u.EditorAssetLibrary.set_metadata_tag(instance, SPEC_KEY, spec)
    u.EditorAssetLibrary.set_metadata_tag(instance, STATE_KEY, "in_progress")
    lib.set_material_instance_vector_parameter_value(instance, PARAMETERS[kind], u.LinearColor(*PRESETS[kind][preset]))
    lib.update_material_instance(instance)
    u.EditorAssetLibrary.set_metadata_tag(instance, STATE_KEY, "complete")
    actual = _verify_instance(instance, source, spec, kind, preset)
    if not u.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False):
        raise RuntimeError("Cannot save isolated experiment material")
    return instance, actual, True


def apply(request, components, slot, asset_root):
    """Apply after mesh assembly; return measured binding/parameter receipts.

    Original explicitly restores source slots. Mesh materials are read only.
    On failure component changes roll back; already created experiment assets
    remain isolated and may be reused after the error is resolved.
    """
    request = validate_request(request)
    _name(asset_root, slot, "validation", "hair", "black")
    u, lib = _ue(), _ue().MaterialEditingLibrary
    rows, protected, snapshots, counts = [], {}, {}, {"hair": 0, "eye": 0}
    protected_packages = set()
    dirty = {_path(p) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    for component_name, component in components.items():
        if component_name != "Eyes" and not re.fullmatch(r"HairPart\d+", component_name):
            continue
        mesh = component.get_skeletal_mesh_asset()
        if mesh is None:
            continue
        snapshots[component_name] = [component.get_material(i) for i in range(component.get_num_materials())]
        protected_assets = [mesh]
        for index, mesh_slot in enumerate(mesh.get_editor_property("materials")):
            source = mesh_slot.material_interface
            if source is None:
                continue
            chain = _chain(source)
            protected_assets.extend(chain)
            kind = classify_slot(component_name, str(mesh_slot.material_slot_name), _path(source), [_path(m) for m in chain])
            if kind is None:
                continue
            counts[kind] += 1
            preset = request[kind + "_color"]
            if preset != "original":
                if not isinstance(source, u.MaterialInstanceConstant):
                    raise RuntimeError("Color source must be a saved material instance")
                if PARAMETERS[kind] not in {str(n) for n in lib.get_vector_parameter_names(source)}:
                    raise RuntimeError("Source lacks required color parameter")
                if kind == "hair" and lib.get_material_instance_static_switch_parameter_value(source, "Activate Hair Color"):
                    raise RuntimeError("Unsupported pre-enabled hair dye source")
            rows.append({"component_name": component_name, "component": component, "index": index,
                         "source": source, "kind": kind, "preset": preset,
                         "source_sha256": _sha(package_file(_path(source)))})
        for asset in protected_assets:
            file = package_file(_path(asset))
            package = _path(asset).split(".", 1)[0]
            protected_packages.add(package)
            if package in dirty:
                raise RuntimeError("Protected source is dirty: " + package)
            protected[str(file)] = _sha(file)
    for kind, count in counts.items():
        if request[kind + "_color"] != "original" and count == 0:
            raise RuntimeError("No supported " + kind + " materials in this actor")
    bindings = []
    try:
        prepared = []
        for row in rows:
            if row["preset"] == "original":
                instance, actual, created = row["source"], None, False
            else:
                instance, actual, created = _material(row, asset_root, slot)
            prepared.append((row, instance, actual, created))
        for row, instance, actual, created in prepared:
            row["component"].set_material(row["index"], instance)
            if _path(row["component"].get_material(row["index"])) != _path(instance):
                raise RuntimeError("Color component binding mismatch")
            bindings.append({"component": row["component_name"], "material_index": row["index"],
                "source": _path(row["source"]), "source_sha256": row["source_sha256"],
                "material": _path(instance), "kind": row["kind"], "preset": row["preset"],
                "parameter": PARAMETERS[row["kind"]] if actual is not None else None,
                "rgba_readback": actual, "created": created})
        if any(_sha(Path(file)) != sha for file, sha in protected.items()):
            raise RuntimeError("Protected source package changed")
        dirty_after = {_path(p) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if (dirty_after - dirty) & protected_packages:
            raise RuntimeError("Protected source became dirty")
    except Exception:
        for name, original in snapshots.items():
            for index, material in enumerate(original):
                components[name].set_material(index, material)
        raise
    return {"hair_color": request["hair_color"], "eye_color": request["eye_color"], "slot": slot,
            "bindings": bindings, "protected_package_hashes": protected, "source_unchanged": True,
            "visual_acceptance": "pending", "scope": "isolated_review_experiment"}
