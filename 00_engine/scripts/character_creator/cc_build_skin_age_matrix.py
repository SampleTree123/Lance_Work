"""Build the frozen CC5 young-skin pool and three-stage age matrix."""

import argparse
import copy
import datetime
import hashlib
import json
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_build_skin_age_matrix_config.json"
)
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_skin_age_matrix_v1.json")
SKIN_NAME_PATTERN = re.compile(
    r"^Age(?P<age>\d+)-(?P<identity>.+)_2k\.ccSkin$",
    re.IGNORECASE,
)


class SkinMatrixError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


def normalized(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def read_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
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
    if not isinstance(path, str) or not os.path.isfile(path):
        raise SkinMatrixError("{} is missing: {}".format(label, path))
    return os.path.realpath(os.path.abspath(path))


def checked_directory(path, label):
    if not isinstance(path, str) or not os.path.isdir(path):
        raise SkinMatrixError("{} is missing: {}".format(label, path))
    return os.path.realpath(os.path.abspath(path))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise SkinMatrixError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    return result


def physical_skin_records(root, group_codes):
    records = []
    unexpected = []
    for current_root, unused_directories, filenames in os.walk(root):
        for filename in filenames:
            path = os.path.join(current_root, filename)
            relative_path = os.path.relpath(path, root)
            match = SKIN_NAME_PATTERN.match(filename)
            if match is None:
                unexpected.append(relative_path)
                continue
            group = os.path.relpath(current_root, root)
            if group not in group_codes:
                raise SkinMatrixError(
                    "Skin is under an unknown group: {}".format(
                        relative_path
                    )
                )
            sex = "female" if group.startswith("Female ") else "male"
            region = group.split(" ", 1)[1]
            records.append(
                {
                    "age": int(match.group("age")),
                    "group": group,
                    "group_code": group_codes[group],
                    "identity_label": match.group("identity"),
                    "path": os.path.realpath(os.path.abspath(path)),
                    "region_label": region,
                    "relative_path": relative_path.replace(os.sep, "/"),
                    "sex": sex,
                }
            )
    if unexpected:
        raise SkinMatrixError(
            "Unexpected files in skin root: {}".format(
                sorted(unexpected)
            )
        )
    return sorted(
        records,
        key=lambda item: (
            item["sex"],
            item["region_label"],
            item["age"],
            item["identity_label"],
        ),
    )


def compact_source_preset(source):
    return {
        "base_avatar": copy.deepcopy(source.get("base_avatar")),
        "bodyfit_id": source.get("bodyfit_id"),
        "face_camera": source.get("face_camera"),
        "preset_id": source.get("preset_id"),
        "sex": source.get("sex"),
        "source_project": copy.deepcopy(source.get("source_project")),
    }


def build(config_path, output_path):
    config_path = checked_file(config_path, "Config")
    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise SkinMatrixError("Unsupported skin matrix config schema")

    root = checked_directory(config.get("skin_root"), "Skin root")
    catalog_path = checked_file(
        config.get("appearance_catalog"), "Appearance catalog"
    )
    source_path = checked_file(
        config.get("source_quality_batch"), "Source quality batch"
    )
    catalog = read_json(catalog_path)
    source = read_json(source_path)
    group_codes = config.get("group_codes")
    if (
        not isinstance(group_codes, dict)
        or len(group_codes) != 8
        or len(set(group_codes.values())) != 8
    ):
        raise SkinMatrixError("group_codes must contain eight unique groups")

    records = physical_skin_records(root, group_codes)
    expected_total_count = int(config.get("expected_total_count", -1))
    if len(records) != expected_total_count:
        raise SkinMatrixError(
            "Expected {} physical skins, found {}".format(
                expected_total_count, len(records)
            )
        )

    maximum_age = int(config.get("maximum_filename_age", -1))
    selected = [
        item for item in records if item["age"] <= maximum_age
    ]
    expected_selected_count = int(
        config.get("expected_selected_count", -1)
    )
    if len(selected) != expected_selected_count:
        raise SkinMatrixError(
            "Expected {} selected skins, found {}".format(
                expected_selected_count, len(selected)
            )
        )

    assets_by_path = {}
    for asset in catalog.get("assets") or []:
        path = asset.get("preferred_path")
        if not isinstance(path, str) or not path:
            continue
        key = normalized(path)
        if key in assets_by_path:
            raise SkinMatrixError(
                "Catalog preferred paths are duplicated: {}".format(path)
            )
        assets_by_path[key] = asset

    source_presets = indexed(
        source.get("presets") or [],
        "preset_id",
        "Source preset",
    )
    source_ids = config.get("source_preset_ids")
    if not isinstance(source_ids, dict):
        raise SkinMatrixError("source_preset_ids must be an object")
    sources = {}
    for sex in ("male", "female"):
        source_preset = source_presets.get(source_ids.get(sex))
        if source_preset is None or source_preset.get("sex") != sex:
            raise SkinMatrixError(
                "Source preset is missing or has wrong sex: {}".format(
                    sex
                )
            )
        checked_file(
            (source_preset.get("base_avatar") or {}).get("path"),
            "{} base avatar".format(sex),
        )
        checked_file(
            (source_preset.get("source_project") or {}).get("path"),
            "{} source project".format(sex),
        )
        checked_file(
            source_preset.get("face_camera"),
            "{} face camera".format(sex),
        )
        sources[sex] = compact_source_preset(source_preset)

    presets = []
    group_indexes = {}
    for record in selected:
        asset = assets_by_path.get(normalized(record["path"]))
        if asset is None:
            raise SkinMatrixError(
                "Selected skin is absent from catalog: {}".format(
                    record["path"]
                )
            )
        if (
            asset.get("slot") != "skin"
            or asset.get("automation_status") != "candidate"
            or asset.get("sex_hint") != record["sex"]
            or asset.get("extension", "").lower() != ".ccskin"
        ):
            raise SkinMatrixError(
                "Catalog metadata is invalid for {}".format(
                    record["path"]
                )
            )
        group_indexes[record["group_code"]] = (
            group_indexes.get(record["group_code"], 0) + 1
        )
        preset_id = "SKA_{}_{:02d}_A{:02d}".format(
            record["group_code"],
            group_indexes[record["group_code"]],
            record["age"],
        )
        stat = os.stat(record["path"])
        presets.append(
            {
                "age_from_filename": record["age"],
                "base_avatar": copy.deepcopy(
                    sources[record["sex"]]["base_avatar"]
                ),
                "bodyfit_id": sources[record["sex"]]["bodyfit_id"],
                "face_camera": sources[record["sex"]]["face_camera"],
                "group": record["group"],
                "identity_label": record["identity_label"],
                "preset_id": preset_id,
                "region_label": record["region_label"],
                "sex": record["sex"],
                "skin_asset": {
                    "asset_form": asset.get("asset_form"),
                    "asset_id": asset["asset_id"],
                    "bytes": int(stat.st_size),
                    "display_name": asset["display_name"],
                    "extension": asset["extension"],
                    "path": record["path"],
                    "sha256": sha256_file(record["path"]),
                    "slot": asset["slot"],
                },
                "source_project": copy.deepcopy(
                    sources[record["sex"]]["source_project"]
                ),
                "source_preset_id": sources[record["sex"]]["preset_id"],
            }
        )

    preset_ids = [item["preset_id"] for item in presets]
    if len(preset_ids) != len(set(preset_ids)):
        raise SkinMatrixError("Generated preset IDs are duplicated")

    age_morph = config.get("age_morph")
    age_levels = config.get("age_levels")
    if (
        not isinstance(age_morph, dict)
        or not isinstance(age_morph.get("id"), str)
        or not isinstance(age_levels, list)
        or [item.get("label") for item in age_levels]
        != ["young", "middle", "older"]
        or [float(item.get("weight")) for item in age_levels]
        != [0.0, 0.5, 1.0]
    ):
        raise SkinMatrixError("Age morph or age levels are invalid")

    preview_lightroom = checked_file(
        source.get("preview_lightroom"),
        "Preview Lightroom",
    )
    selected_by_sex = {
        sex: len([item for item in presets if item["sex"] == sex])
        for sex in ("female", "male")
    }
    selected_by_group = {
        group: len([item for item in presets if item["group"] == group])
        for group in sorted(group_codes)
    }
    result = {
        "age_levels": copy.deepcopy(age_levels),
        "age_morph": copy.deepcopy(age_morph),
        "appearance_catalog": {
            "catalog_id": catalog.get("catalog_id"),
            "path": catalog_path,
        },
        "diagnostic_mode": "skin_age_direct_matrix",
        "execution_policy": copy.deepcopy(
            config.get("execution_policy") or {}
        ),
        "generated_at": now(),
        "library_id": config["library_id"],
        "presets": presets,
        "preview_lightroom": preview_lightroom,
        "schema_version": 1,
        "skin_pool_design": {
            "excluded_count": len(records) - len(selected),
            "maximum_filename_age": maximum_age,
            "selected_by_group": selected_by_group,
            "selected_by_sex": selected_by_sex,
            "selected_count": len(selected),
            "skin_root": root,
            "total_physical_count": len(records),
            "validation_state_count": len(selected) * len(age_levels),
        },
        "source_quality_batch": source_path,
    }
    output_path = os.path.realpath(os.path.abspath(output_path))
    write_json(result, output_path)
    return {
        "library_id": result["library_id"],
        "output": output_path,
        "preset_count": len(presets),
        "preset_ids": preset_ids,
        "success": True,
        "validation_state_count": len(presets) * len(age_levels),
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
