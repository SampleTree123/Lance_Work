"""Build a CC quality batch from approved body, face, and appearance IDs."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "cc_appearance_quality_batch_v1_config.json")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_appearance_quality_batch_v1.json")


class BatchError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def load_catalog(path):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise BatchError("Appearance catalog is missing: {}".format(path))
    document = read_json(path)
    assets = document.get("assets") or []
    by_id = {item.get("asset_id"): item for item in assets}
    if not by_id or len(by_id) != len(assets) or None in by_id:
        raise BatchError("Appearance catalog IDs are invalid or duplicated")
    return path, document, by_id


def validate_recipe(recipe, source_preset, asset_index):
    asset_ids = recipe.get("appearance_asset_ids")
    if not isinstance(asset_ids, list) or not asset_ids:
        raise BatchError("Appearance recipe must contain asset IDs")
    if len(asset_ids) != len(set(asset_ids)):
        raise BatchError("Appearance recipe contains duplicate asset IDs")
    missing = sorted(set(asset_ids) - set(asset_index))
    if missing:
        raise BatchError("Unknown appearance asset IDs: {}".format(missing))
    assets = [asset_index[item_id] for item_id in asset_ids]
    invalid = [
        item["asset_id"]
        for item in assets
        if item.get("automation_status") != "candidate"
    ]
    if invalid:
        raise BatchError("Appearance recipe contains component-only assets: {}".format(invalid))
    sex = source_preset.get("sex")
    conflicts = [
        item["asset_id"]
        for item in assets
        if item.get("sex_hint") in ("male", "female")
        and item.get("sex_hint") != sex
    ]
    if conflicts:
        raise BatchError("Appearance sex hints conflict with source: {}".format(conflicts))
    slots = [item.get("slot") for item in assets]
    duplicates = sorted(
        slot
        for slot in set(slots)
        if slot != "accessory_other" and slots.count(slot) > 1
    )
    if duplicates:
        raise BatchError("Appearance recipe repeats exclusive slots: {}".format(duplicates))
    if "full_body" in slots and any(
        slot in slots for slot in ("upper", "lower", "outerwear")
    ):
        raise BatchError("full_body conflicts with layered clothing")
    return assets


def validate_cleanup(recipe):
    names = recipe.get("remove_base_clothing_names") or []
    if not isinstance(names, list):
        raise BatchError("remove_base_clothing_names must be a list")
    if any(
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 128
        or "\n" in name
        or "\r" in name
        for name in names
    ):
        raise BatchError("remove_base_clothing_names contains an invalid name")
    names = [name.strip() for name in names]
    if len(names) != len(set(names)):
        raise BatchError("remove_base_clothing_names contains duplicates")
    return names


def validate_validation_plan(recipe, assets):
    plan = recipe.get("validation_plan")
    if plan is None:
        return None
    if not isinstance(plan, dict):
        raise BatchError("validation_plan must be an object")
    domain = plan.get("domain")
    if not isinstance(domain, str) or not domain:
        raise BatchError("validation_plan.domain must be a non-empty string")
    slots = {item.get("slot") for item in assets}
    if domain not in slots:
        raise BatchError(
            "validation_plan.domain does not match an appearance slot: {}".format(
                domain
            )
        )
    mode = plan.get("verification_mode")
    if mode not in ("scene_inventory", "material_fingerprint"):
        raise BatchError("validation_plan.verification_mode is unsupported")
    material_slots = {"skin", "skin_preset", "makeup", "eyes", "teeth"}
    expected_mode = (
        "material_fingerprint" if domain in material_slots else "scene_inventory"
    )
    if mode != expected_mode:
        raise BatchError(
            "validation_plan.verification_mode conflicts with domain {}".format(
                domain
            )
        )
    required_views = plan.get("required_views")
    allowed_views = {
        "full_body_front",
        "face_front",
        "face_three_quarter",
        "face_profile",
        "teeth_smile_front",
        "teeth_jaw_open_front",
        "teeth_jaw_open_three_quarter",
        "eyebrow_raise_front",
        "eyebrow_down_front",
        "eyebrow_asymmetric_front",
        "eyelash_blink_front",
        "eyelash_asymmetric_blink_front",
        "eyelash_wide_front",
    }
    if (
        not isinstance(required_views, list)
        or not required_views
        or any(view not in allowed_views for view in required_views)
        or len(required_views) != len(set(required_views))
    ):
        raise BatchError("validation_plan.required_views is invalid")
    limitation = plan.get("visual_limitation")
    if limitation is not None and (
        not isinstance(limitation, str) or not limitation.strip()
    ):
        raise BatchError("validation_plan.visual_limitation is invalid")
    pose_profile = plan.get("pose_profile")
    if pose_profile is not None:
        supported_profile = (
            (domain == "teeth" and pose_profile == "teeth_visibility_v1")
            or (
                domain == "eyebrows"
                and pose_profile == "eyebrow_visibility_v1"
            )
            or (
                domain == "eyelashes"
                and pose_profile == "eyelash_visibility_v1"
            )
        )
        if not supported_profile:
            raise BatchError(
                "validation_plan.pose_profile is unsupported for domain {}".format(
                    domain
                )
            )
        required_teeth_views = {
            "teeth_smile_front",
            "teeth_jaw_open_front",
            "teeth_jaw_open_three_quarter",
        }
        if (
            pose_profile == "teeth_visibility_v1"
            and not required_teeth_views.issubset(set(required_views))
        ):
            raise BatchError(
                "teeth_visibility_v1 requires all teeth visibility views"
            )
        required_eyebrow_views = {
            "eyebrow_raise_front",
            "eyebrow_down_front",
            "eyebrow_asymmetric_front",
        }
        if (
            pose_profile == "eyebrow_visibility_v1"
            and not required_eyebrow_views.issubset(set(required_views))
        ):
            raise BatchError(
                "eyebrow_visibility_v1 requires all eyebrow expression views"
            )
        required_eyelash_views = {
            "eyelash_blink_front",
            "eyelash_asymmetric_blink_front",
            "eyelash_wide_front",
        }
        if (
            pose_profile == "eyelash_visibility_v1"
            and not required_eyelash_views.issubset(set(required_views))
        ):
            raise BatchError(
                "eyelash_visibility_v1 requires all eyelash expression views"
            )
    return copy.deepcopy(plan)


def build(config_path, output_path):
    config_path = os.path.realpath(os.path.abspath(config_path))
    output_path = os.path.realpath(os.path.abspath(output_path))
    if not os.path.isfile(config_path):
        raise BatchError("Config is missing: {}".format(config_path))
    config = read_json(config_path)
    source_path = os.path.realpath(os.path.abspath(config["source_quality_batch"]))
    if not os.path.isfile(source_path):
        raise BatchError("Source quality batch is missing: {}".format(source_path))
    source = read_json(source_path)
    source_presets = source.get("presets") or []
    by_source_id = {item.get("preset_id"): item for item in source_presets}
    if not by_source_id or len(by_source_id) != len(source_presets):
        raise BatchError("Source quality preset IDs are invalid or duplicated")
    catalog_path, catalog, asset_index = load_catalog(config["appearance_catalog"])

    recipes = config.get("recipes")
    if not isinstance(recipes, list) or not recipes:
        raise BatchError("Config has no appearance recipes")
    output_ids = [item.get("preset_id") for item in recipes]
    if None in output_ids or len(output_ids) != len(set(output_ids)):
        raise BatchError("Output preset IDs are invalid or duplicated")

    presets = []
    for recipe in recipes:
        source_id = recipe.get("source_preset_id")
        if source_id not in by_source_id:
            raise BatchError("Unknown source preset: {}".format(source_id))
        source_preset = by_source_id[source_id]
        assets = validate_recipe(recipe, source_preset, asset_index)
        cleanup_names = validate_cleanup(recipe)
        validation_plan = validate_validation_plan(recipe, assets)
        preset = copy.deepcopy(source_preset)
        preset["preset_id"] = recipe["preset_id"]
        preset["character_id"] = recipe["preset_id"]
        preset["appearance_recipe_id"] = recipe["appearance_recipe_id"]
        preset["appearance_asset_ids"] = list(recipe["appearance_asset_ids"])
        preset["appearance_recipe"] = {
            "source_preset_id": source_id,
            "assets": [
                {
                    "asset_id": item["asset_id"],
                    "display_name": item.get("display_name"),
                    "slot": item.get("slot"),
                    "asset_form": item.get("asset_form"),
                    "sex_hint": item.get("sex_hint"),
                }
                for item in assets
            ],
        }
        if cleanup_names:
            preset["appearance_cleanup"] = {
                "remove_base_clothing_names": cleanup_names,
            }
        else:
            preset.pop("appearance_cleanup", None)
        if validation_plan is not None:
            preset["appearance_validation_plan"] = validation_plan
        else:
            preset.pop("appearance_validation_plan", None)
        preset["review_status"] = "appearance-v1-quality-candidate"
        presets.append(preset)

    result = copy.deepcopy(source)
    result["library_id"] = config["library_id"]
    result["character_count"] = len(presets)
    result["generated_at"] = now()
    result["presets"] = presets
    result["appearance_catalog"] = {
        "path": catalog_path,
        "catalog_id": catalog.get("catalog_id"),
    }
    result["appearance_batch_source"] = {
        "config": config_path,
        "source_quality_batch": source_path,
        "source_library_id": source.get("library_id"),
    }
    execution_policy = config.get("execution_policy")
    if execution_policy is not None:
        if not isinstance(execution_policy, dict):
            raise BatchError("execution_policy must be an object")
        result["execution_policy"] = copy.deepcopy(execution_policy)
    else:
        result.pop("execution_policy", None)
    write_json(result, output_path)
    return {
        "success": True,
        "output": output_path,
        "library_id": result["library_id"],
        "character_count": len(presets),
        "preset_ids": [item["preset_id"] for item in presets],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.config, args.output),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
