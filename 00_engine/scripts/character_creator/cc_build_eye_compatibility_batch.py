"""Build eye compatibility probe and full-matrix batches for CC5."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_build_eye_equivalence_probe_config.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_eye_equivalence_probe_v1.json"
)
BODY_FIELDS = (
    "base_avatar",
    "source_project",
    "target_body_morphs",
    "target_junction_morphs",
    "body_and_junction_fingerprint",
    "body_class",
    "sex",
)


class EyeBatchError(RuntimeError):
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
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_file(path, label):
    resolved = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(resolved):
        raise EyeBatchError("{} is missing: {}".format(label, resolved))
    return resolved


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise EyeBatchError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    if not result:
        raise EyeBatchError("{} is empty".format(label))
    return result


def selected_faces(config, face_presets):
    by_recipe = indexed(face_presets, "face_recipe_id", "Face recipe")
    requested = config.get("face_recipe_ids")
    if requested is None:
        return sorted(
            face_presets,
            key=lambda item: (item["sex"], item["face_recipe_id"]),
        )
    if (
        not isinstance(requested, list)
        or not requested
        or len(requested) != len(set(requested))
    ):
        raise EyeBatchError("face_recipe_ids must be a non-empty unique list")
    missing = sorted(set(requested) - set(by_recipe))
    if missing:
        raise EyeBatchError(
            "Unknown face_recipe_ids: {}".format(", ".join(missing))
        )
    return [by_recipe[item] for item in requested]


def resolve_variants(config, assets):
    variants = copy.deepcopy(config.get("eye_variants"))
    if not isinstance(variants, list) or not variants:
        raise EyeBatchError("At least one eye variant is required")
    for key in ("code", "recipe_id", "asset_id"):
        values = [item.get(key) for item in variants]
        if (
            any(not isinstance(value, str) or not value for value in values)
            or len(values) != len(set(values))
        ):
            raise EyeBatchError(
                "Eye variant {} values are invalid or duplicated".format(key)
            )
    for variant in variants:
        asset = assets.get(variant["asset_id"])
        if asset is None:
            raise EyeBatchError(
                "Unknown eye asset: {}".format(variant["asset_id"])
            )
        if (
            asset.get("slot") != "eyes"
            or asset.get("automation_status") != "candidate"
        ):
            raise EyeBatchError(
                "Asset is not an automatable eye candidate: {}".format(
                    variant["asset_id"]
                )
            )
        variant["resolved_path"] = canonical_file(
            asset.get("preferred_path"),
            "Eye asset {}".format(variant["asset_id"]),
        )
        variant["display_name"] = asset.get("display_name")
    return variants


def choose_body(config, bodies_by_sex, sex, face_index):
    fixed = config.get("fixed_bodyfit_by_sex")
    if fixed is not None:
        if not isinstance(fixed, dict):
            raise EyeBatchError("fixed_bodyfit_by_sex must be an object")
        requested = fixed.get(sex)
        matches = [
            item
            for item in bodies_by_sex[sex]
            if item["preset_id"] == requested
        ]
        if len(matches) != 1:
            raise EyeBatchError(
                "Invalid fixed {} BodyFit: {}".format(sex, requested)
            )
        return matches[0]
    return bodies_by_sex[sex][face_index % len(bodies_by_sex[sex])]


def build(config_path, output_path):
    config_path = canonical_file(config_path, "Eye batch config")
    output_path = os.path.realpath(os.path.abspath(output_path))
    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise EyeBatchError("Unsupported eye batch config schema")

    face_batch_path = canonical_file(
        config.get("face_quality_batch"), "Face quality batch"
    )
    body_library_path = canonical_file(
        config.get("body_library"), "BodyFit library"
    )
    catalog_path = canonical_file(
        config.get("appearance_catalog"), "Appearance catalog"
    )
    face_batch = read_json(face_batch_path)
    body_library = read_json(body_library_path)
    catalog = read_json(catalog_path)
    faces = selected_faces(config, face_batch.get("presets") or [])
    bodies = indexed(
        body_library.get("presets") or [],
        "preset_id",
        "BodyFit preset",
    )
    assets = indexed(
        catalog.get("assets") or [],
        "asset_id",
        "Appearance asset",
    )
    variants = resolve_variants(config, assets)

    bodies_by_sex = {}
    faces_by_sex = {}
    for sex in ("male", "female"):
        bodies_by_sex[sex] = sorted(
            [item for item in bodies.values() if item.get("sex") == sex],
            key=lambda item: item["preset_id"],
        )
        faces_by_sex[sex] = sorted(
            [item for item in faces if item.get("sex") == sex],
            key=lambda item: item["face_recipe_id"],
        )
        if len(bodies_by_sex[sex]) != 4:
            raise EyeBatchError(
                "Expected four {} BodyFits, found {}".format(
                    sex, len(bodies_by_sex[sex])
                )
            )
        if not faces_by_sex[sex]:
            raise EyeBatchError(
                "Selected face set has no {} preset".format(sex)
            )

    prefix = config.get("preset_prefix")
    if not isinstance(prefix, str) or not prefix:
        raise EyeBatchError("preset_prefix must be a non-empty string")
    presets = []
    assignments = []
    for sex in ("male", "female"):
        for face_index, face_preset in enumerate(faces_by_sex[sex]):
            body = choose_body(
                config,
                bodies_by_sex,
                sex,
                face_index,
            )
            body_code = body["preset_id"].split("_", 1)[0]
            for variant in variants:
                preset = copy.deepcopy(face_preset)
                for field in BODY_FIELDS:
                    preset[field] = copy.deepcopy(body[field])
                preset["bodyfit_id"] = body["preset_id"]
                preset_id = "{}_{}_{:02d}_{}".format(
                    prefix,
                    body_code,
                    face_index + 1,
                    variant["code"],
                )
                preset["preset_id"] = preset_id
                preset["character_id"] = preset_id
                preset["appearance_recipe_id"] = variant["recipe_id"]
                preset["appearance_asset_ids"] = [variant["asset_id"]]
                preset["appearance_recipe"] = {
                    "source_face_preset_id": face_preset["preset_id"],
                    "eye_variant_code": variant["code"],
                    "assets": [
                        {
                            "asset_id": variant["asset_id"],
                            "display_name": variant["display_name"],
                            "slot": "eyes",
                            "asset_form": assets[
                                variant["asset_id"]
                            ].get("asset_form"),
                            "sex_hint": assets[
                                variant["asset_id"]
                            ].get("sex_hint"),
                        }
                    ],
                }
                preset["appearance_validation_plan"] = {
                    "domain": "eyes",
                    "pose_profile": "eye_visibility_v1",
                    "subject_position_offset": copy.deepcopy(
                        config.get(
                            "validation_subject_offset",
                            {"x": 0.0, "y": 0.0, "z": 0.0},
                        )
                    ),
                    "required_views": [
                        "face_front",
                        "face_three_quarter",
                        "eye_look_left_front",
                        "eye_look_right_front",
                        "eye_look_up_front",
                        "eye_look_down_front",
                    ],
                    "verification_mode": "material_fingerprint",
                    "visual_limitation": (
                        "Approval requires manual review of eyelid contact, "
                        "iris placement, and bilateral eye motion."
                    ),
                }
                preset["review_status"] = config.get(
                    "review_status",
                    "eye-compatibility-candidate",
                )
                presets.append(preset)
                assignments.append(
                    {
                        "preset_id": preset_id,
                        "sex": sex,
                        "bodyfit_id": body["preset_id"],
                        "face_recipe_id": face_preset["face_recipe_id"],
                        "eye_asset_id": variant["asset_id"],
                        "eye_variant_code": variant["code"],
                    }
                )

    expected_count = len(faces) * len(variants)
    if len(presets) != expected_count:
        raise EyeBatchError(
            "Eye matrix count mismatch: expected={} actual={}".format(
                expected_count, len(presets)
            )
        )
    preset_ids = [item["preset_id"] for item in presets]
    if len(preset_ids) != len(set(preset_ids)):
        raise EyeBatchError("Generated eye preset IDs are duplicated")

    result = copy.deepcopy(face_batch)
    result["library_id"] = config["library_id"]
    result["generated_at"] = now()
    result["status"] = config.get(
        "review_status",
        "eye-compatibility-candidate",
    )
    result["body_application_mode"] = body_library.get(
        "body_application_mode"
    )
    result["expected_eyeball_move_weight"] = body_library.get(
        "expected_eyeball_move_weight"
    )
    result["preview_lightroom"] = body_library.get("preview_lightroom")
    result["face_resources"] = {
        "seed_library": canonical_file(
            config.get("face_seed_library"), "Face seed library"
        ),
        "identity_policy": canonical_file(
            config.get("face_identity_policy"), "Face identity policy"
        ),
    }
    result["appearance_catalog"] = {
        "path": catalog_path,
        "catalog_id": catalog.get("catalog_id"),
        "sha256": sha256_file(catalog_path),
    }
    result["source_body_library"] = {
        "path": body_library_path,
        "library_id": body_library.get("library_id"),
        "sha256": sha256_file(body_library_path),
    }
    result["source_face_quality_batch"] = {
        "path": face_batch_path,
        "library_id": face_batch.get("library_id"),
        "sha256": sha256_file(face_batch_path),
    }
    result["eye_variants"] = variants
    result["character_count"] = len(presets)
    result["presets"] = presets
    result["selection"] = {
        "face_count": len(faces),
        "bodyfit_count": len(
            {item["bodyfit_id"] for item in assignments}
        ),
        "eye_variant_count": len(variants),
        "assignment": (
            "fixed_bodyfit_by_sex"
            if config.get("fixed_bodyfit_by_sex")
            else "round_robin_bodyfit_within_sex"
        ),
        "assignments": assignments,
    }
    result["execution_policy"] = {
        "recommended_chunk_size": int(
            config.get("recommended_chunk_size", 6)
        ),
        "preserve_projects": False,
    }
    write_json(result, output_path)
    return {
        "success": True,
        "output": output_path,
        "library_id": result["library_id"],
        "character_count": len(presets),
        "face_count": len(faces),
        "bodyfit_count": result["selection"]["bodyfit_count"],
        "eye_variant_count": len(variants),
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
