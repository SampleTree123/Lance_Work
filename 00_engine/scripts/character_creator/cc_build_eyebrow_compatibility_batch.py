"""Build the factorized adult eyebrow compatibility matrix."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_build_eyebrow_compatibility_batch_config.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_eyebrow_compatibility_batch_v1.json"
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


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise BatchError("{} IDs are invalid or duplicated".format(label))
        result[value] = item
    return result


def checked_file(path, label):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise BatchError("{} is missing: {}".format(label, path))
    return path


def validation_plan():
    return {
        "domain": "eyebrows",
        "pose_profile": "eyebrow_visibility_v1",
        "required_views": [
            "face_front",
            "face_three_quarter",
            "face_profile",
            "eyebrow_raise_front",
            "eyebrow_down_front",
            "eyebrow_asymmetric_front",
        ],
        "verification_mode": "scene_inventory",
        "visual_limitation": (
            "Adult CC5 HD faces only; child and third-party head "
            "generations require separate validation."
        ),
    }


def build(config_path, output_path):
    config_path = checked_file(config_path, "Config")
    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise BatchError("Unsupported eyebrow batch config schema")

    catalog_path = checked_file(
        config.get("appearance_catalog"), "Appearance catalog"
    )
    source_path = checked_file(
        config.get("source_quality_batch"), "Source quality batch"
    )
    catalog = read_json(catalog_path)
    source = read_json(source_path)
    assets = indexed(
        catalog.get("assets") or [], "asset_id", "Appearance asset"
    )
    source_presets = indexed(
        source.get("presets") or [], "preset_id", "Source preset"
    )
    source_by_sex = {
        sex: sorted(
            [
                preset
                for preset in source_presets.values()
                if preset.get("sex") == sex
            ],
            key=lambda item: item["preset_id"],
        )
        for sex in ("female", "male")
    }

    matrix = config.get("matrix")
    if not isinstance(matrix, dict):
        raise BatchError("Config matrix must be an object")
    presets = []
    matrix_summary = {}
    for sex in ("female", "male"):
        settings = matrix.get(sex)
        if not isinstance(settings, dict):
            raise BatchError("Missing matrix settings for {}".format(sex))
        asset_ids = settings.get("asset_ids")
        representative_ids = settings.get(
            "representative_source_preset_ids"
        )
        stress_ids = settings.get("stress_asset_ids")
        if (
            not isinstance(asset_ids, list)
            or not asset_ids
            or len(asset_ids) != len(set(asset_ids))
        ):
            raise BatchError("{} asset IDs are invalid".format(sex))
        if (
            not isinstance(representative_ids, list)
            or not representative_ids
            or len(representative_ids) != len(set(representative_ids))
        ):
            raise BatchError(
                "{} representative source IDs are invalid".format(sex)
            )
        if (
            not isinstance(stress_ids, list)
            or not stress_ids
            or len(stress_ids) != len(set(stress_ids))
            or not set(stress_ids).issubset(set(asset_ids))
        ):
            raise BatchError("{} stress asset IDs are invalid".format(sex))

        resolved_assets = []
        for asset_id in asset_ids:
            asset = assets.get(asset_id)
            if asset is None:
                raise BatchError("Unknown eyebrow asset: {}".format(asset_id))
            if asset.get("slot") != "eyebrows":
                raise BatchError(
                    "Asset is not an eyebrow: {}".format(asset_id)
                )
            if asset.get("sex_hint") != sex:
                raise BatchError(
                    "Eyebrow sex hint conflicts: {}".format(asset_id)
                )
            if asset.get("automation_status") != "candidate":
                raise BatchError(
                    "Eyebrow is not an automation candidate: {}".format(
                        asset_id
                    )
                )
            if not os.path.isfile(asset.get("preferred_path", "")):
                raise BatchError(
                    "Eyebrow file is missing: {}".format(asset_id)
                )
            resolved_assets.append(asset)

        representatives = []
        for preset_id in representative_ids:
            preset = source_presets.get(preset_id)
            if preset is None or preset.get("sex") != sex:
                raise BatchError(
                    "Representative source conflicts: {}".format(preset_id)
                )
            representatives.append(preset)

        combinations = set()
        for asset_id in asset_ids:
            for source_preset in representatives:
                combinations.add((asset_id, source_preset["preset_id"]))
        for asset_id in stress_ids:
            for source_preset in source_by_sex[sex]:
                combinations.add((asset_id, source_preset["preset_id"]))

        asset_order = dict(
            (asset_id, index + 1)
            for index, asset_id in enumerate(asset_ids)
        )
        face_order = dict(
            (preset["preset_id"], index + 1)
            for index, preset in enumerate(source_by_sex[sex])
        )
        prefix = "F" if sex == "female" else "M"
        for asset_id, source_id in sorted(
            combinations,
            key=lambda item: (
                asset_order[item[0]],
                face_order[item[1]],
            ),
        ):
            source_preset = source_presets[source_id]
            asset = assets[asset_id]
            asset_number = asset_order[asset_id]
            face_number = face_order[source_id]
            preset_id = "EB1_{}_A{:02d}_F{:02d}".format(
                prefix, asset_number, face_number
            )
            preset = copy.deepcopy(source_preset)
            preset["preset_id"] = preset_id
            preset["character_id"] = preset_id
            preset["appearance_recipe_id"] = (
                "EYEBROW_{}_A{:02d}_V1".format(prefix, asset_number)
            )
            preset["appearance_asset_ids"] = [asset_id]
            preset["appearance_recipe"] = {
                "source_preset_id": source_id,
                "assets": [
                    {
                        "asset_id": asset_id,
                        "display_name": asset.get("display_name"),
                        "slot": "eyebrows",
                        "asset_form": asset.get("asset_form"),
                        "sex_hint": sex,
                    }
                ],
            }
            preset["appearance_validation_plan"] = validation_plan()
            preset["review_status"] = "eyebrow-v1-compatibility-candidate"
            presets.append(preset)

        matrix_summary[sex] = {
            "asset_count": len(asset_ids),
            "representative_face_count": len(representatives),
            "stress_asset_count": len(stress_ids),
            "all_face_count": len(source_by_sex[sex]),
            "combination_count": len(combinations),
        }

    preset_ids = [item["preset_id"] for item in presets]
    if len(preset_ids) != len(set(preset_ids)):
        raise BatchError("Generated preset IDs are duplicated")
    result = copy.deepcopy(source)
    result["library_id"] = config["library_id"]
    result["generated_at"] = now()
    result["character_count"] = len(presets)
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
    result["eyebrow_matrix_design"] = matrix_summary
    result["execution_policy"] = {
        "recommended_chunk_size": 4,
        "run_chunks_sequentially": True,
    }
    output_path = os.path.realpath(os.path.abspath(output_path))
    write_json(result, output_path)
    return {
        "success": True,
        "output": output_path,
        "library_id": result["library_id"],
        "character_count": len(presets),
        "matrix": matrix_summary,
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
