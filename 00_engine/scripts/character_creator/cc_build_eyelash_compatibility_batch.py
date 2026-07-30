"""Build the factorized adult eyelash compatibility batch."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR,
    "cc_build_eyelash_compatibility_batch_config.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_eyelash_compatibility_batch_v1.json",
)


class BatchError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        handle.write("\n")
    os.replace(temporary, path)


def checked_file(path, label):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise BatchError("{} is missing: {}".format(label, path))
    return path


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise BatchError("{} IDs are invalid or duplicated".format(label))
        result[value] = item
    return result


def validation_plan():
    return {
        "domain": "eyelashes",
        "pose_profile": "eyelash_visibility_v1",
        "required_views": [
            "face_front",
            "face_three_quarter",
            "face_profile",
            "eyelash_blink_front",
            "eyelash_asymmetric_blink_front",
            "eyelash_wide_front",
        ],
        "verification_mode": "scene_inventory",
        "visual_limitation": (
            "Adult CC5 HD faces only; child and third-party head "
            "generations require separate validation."
        ),
    }


def use_source_project_face(preset):
    for key in (
        "face_generation",
        "face_recipe_id",
        "target_face_fingerprint",
        "target_face_morphs",
    ):
        preset.pop(key, None)
    preset["face_validation_source"] = "source_project_unchanged"
    return preset


def clone_baseline(source_preset, sex, direct_source_face=False):
    prefix = "M" if sex == "male" else "F"
    preset = copy.deepcopy(source_preset)
    if direct_source_face:
        use_source_project_face(preset)
    preset_id = "EYL1_{}_BASELINE_F01".format(prefix)
    preset["preset_id"] = preset_id
    preset["character_id"] = preset_id
    preset.pop("appearance_asset_ids", None)
    preset.pop("appearance_recipe", None)
    preset.pop("appearance_recipe_id", None)
    preset.pop("appearance_cleanup", None)
    preset["appearance_validation_plan"] = validation_plan()
    preset["review_status"] = "eyelash-v1-pose-baseline"
    return preset


def clone_asset_preset(
    source_preset,
    asset,
    asset_number,
    sex,
    direct_source_face=False,
):
    prefix = "M" if sex == "male" else "F"
    preset = copy.deepcopy(source_preset)
    if direct_source_face:
        use_source_project_face(preset)
    preset_id = "EYL1_{}_A{:02d}_F01".format(prefix, asset_number)
    preset["preset_id"] = preset_id
    preset["character_id"] = preset_id
    preset["appearance_recipe_id"] = "EYELASH_U_A{:02d}_V1".format(
        asset_number
    )
    preset["appearance_asset_ids"] = [asset["asset_id"]]
    preset["appearance_recipe"] = {
        "source_preset_id": source_preset["preset_id"],
        "assets": [
            {
                "asset_id": asset["asset_id"],
                "display_name": asset.get("display_name"),
                "slot": "eyelashes",
                "asset_form": asset.get("asset_form"),
                "sex_hint": asset.get("sex_hint"),
            }
        ],
    }
    preset["appearance_validation_plan"] = validation_plan()
    preset["review_status"] = "eyelash-v1-compatibility-candidate"
    return preset


def build(config_path, output_path):
    config_path = checked_file(config_path, "Config")
    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise BatchError("Unsupported eyelash batch config schema")

    catalog_path = checked_file(
        config.get("appearance_catalog"),
        "Appearance catalog",
    )
    source_path = checked_file(
        config.get("source_quality_batch"),
        "Source quality batch",
    )
    catalog = read_json(catalog_path)
    source = read_json(source_path)
    assets = indexed(
        catalog.get("assets") or [],
        "asset_id",
        "Appearance asset",
    )
    source_presets = indexed(
        source.get("presets") or [],
        "preset_id",
        "Source preset",
    )

    source_ids = config.get("source_preset_ids")
    if not isinstance(source_ids, dict):
        raise BatchError("source_preset_ids must be an object")
    sources = {}
    for sex in ("male", "female"):
        preset = source_presets.get(source_ids.get(sex))
        if preset is None or preset.get("sex") != sex:
            raise BatchError(
                "Source preset is missing or has the wrong sex: {}".format(
                    sex
                )
            )
        sources[sex] = preset

    asset_ids = config.get("asset_ids")
    stress_ids = config.get("female_stress_asset_ids")
    if (
        not isinstance(asset_ids, list)
        or not asset_ids
        or len(asset_ids) != len(set(asset_ids))
    ):
        raise BatchError("asset_ids are invalid")
    if (
        not isinstance(stress_ids, list)
        or not stress_ids
        or len(stress_ids) != len(set(stress_ids))
        or not set(stress_ids).issubset(set(asset_ids))
    ):
        raise BatchError("female_stress_asset_ids are invalid")

    resolved_assets = []
    for asset_id in asset_ids:
        asset = assets.get(asset_id)
        if asset is None:
            raise BatchError("Unknown eyelash asset: {}".format(asset_id))
        if asset.get("slot") != "eyelashes":
            raise BatchError("Asset is not an eyelash: {}".format(asset_id))
        if asset.get("automation_status") != "candidate":
            raise BatchError(
                "Eyelash is not an automation candidate: {}".format(asset_id)
            )
        if asset.get("sex_hint") not in ("unknown", None):
            raise BatchError(
                "Selected Natural eyelash has an unexpected sex hint: {}".format(
                    asset_id
                )
            )
        if not os.path.isfile(asset.get("preferred_path", "")):
            raise BatchError("Eyelash file is missing: {}".format(asset_id))
        resolved_assets.append(asset)

    direct_source_face = config.get("direct_source_face", False)
    if not isinstance(direct_source_face, bool):
        raise BatchError("direct_source_face must be a boolean")
    body_application_mode = config.get("body_application_mode")
    if body_application_mode not in (None, "raw_morph_weights", "source_project"):
        raise BatchError("body_application_mode is invalid")
    diagnostic_mode = config.get("diagnostic_mode")
    if diagnostic_mode not in (None, "eyelash_direct_matrix"):
        raise BatchError("diagnostic_mode is invalid")

    presets = [
        clone_baseline(
            sources["male"],
            "male",
            direct_source_face=direct_source_face,
        ),
        clone_baseline(
            sources["female"],
            "female",
            direct_source_face=direct_source_face,
        ),
    ]
    for index, asset in enumerate(resolved_assets, 1):
        presets.append(
            clone_asset_preset(
                sources["male"],
                asset,
                index,
                "male",
                direct_source_face=direct_source_face,
            )
        )
        if asset["asset_id"] in stress_ids:
            presets.append(
                clone_asset_preset(
                    sources["female"],
                    asset,
                    index,
                    "female",
                    direct_source_face=direct_source_face,
                )
            )

    preset_ids = [item["preset_id"] for item in presets]
    if len(preset_ids) != len(set(preset_ids)):
        raise BatchError("Generated preset IDs are duplicated")

    result = copy.deepcopy(source)
    result["library_id"] = config["library_id"]
    result["generated_at"] = now()
    result["character_count"] = len(presets)
    result["presets"] = presets
    if body_application_mode is not None:
        result["body_application_mode"] = body_application_mode
    if diagnostic_mode is not None:
        result["diagnostic_mode"] = diagnostic_mode
    result["appearance_catalog"] = {
        "path": catalog_path,
        "catalog_id": catalog.get("catalog_id"),
    }
    result["appearance_batch_source"] = {
        "config": config_path,
        "source_quality_batch": source_path,
        "source_library_id": source.get("library_id"),
    }
    result["eyelash_matrix_design"] = {
        "baseline_count": 2,
        "body_application_mode": result.get(
            "body_application_mode",
            "raw_morph_weights",
        ),
        "direct_source_face": direct_source_face,
        "male_asset_count": len(resolved_assets),
        "female_stress_asset_count": len(stress_ids),
        "total_count": len(presets),
    }
    result["execution_policy"] = {
        "recommended_chunk_size": 1,
        "run_chunks_sequentially": True,
    }
    output_path = os.path.realpath(os.path.abspath(output_path))
    write_json(result, output_path)
    return {
        "success": True,
        "output": output_path,
        "library_id": result["library_id"],
        "character_count": len(presets),
        "preset_ids": preset_ids,
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
