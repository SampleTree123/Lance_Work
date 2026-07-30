"""Build a two-teeth compatibility batch across current faces and BodyFits."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_build_teeth_compatibility_batch_config.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_teeth_compatibility_batch_v1.json"
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


class TeethBatchError(RuntimeError):
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
        raise TeethBatchError("{} is missing: {}".format(label, resolved))
    return resolved


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise TeethBatchError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    if not result:
        raise TeethBatchError("{} is empty".format(label))
    return result


def build(config_path, output_path):
    config_path = canonical_file(config_path, "Teeth batch config")
    output_path = os.path.realpath(os.path.abspath(output_path))
    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise TeethBatchError("Unsupported teeth batch config schema")

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
    face_presets = face_batch.get("presets") or []
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

    bodies_by_sex = {}
    faces_by_sex = {}
    for sex in ("male", "female"):
        bodies_by_sex[sex] = sorted(
            [item for item in bodies.values() if item.get("sex") == sex],
            key=lambda item: item["preset_id"],
        )
        faces_by_sex[sex] = sorted(
            [item for item in face_presets if item.get("sex") == sex],
            key=lambda item: item["face_recipe_id"],
        )
        if len(bodies_by_sex[sex]) != 4:
            raise TeethBatchError(
                "Expected four {} BodyFits, found {}".format(
                    sex, len(bodies_by_sex[sex])
                )
            )
        if not faces_by_sex[sex]:
            raise TeethBatchError(
                "Face quality batch has no {} presets".format(sex)
            )

    variants = config.get("teeth_variants")
    if not isinstance(variants, list) or len(variants) != 2:
        raise TeethBatchError("Exactly two teeth variants are required")
    variant_codes = [item.get("code") for item in variants]
    recipe_ids = [item.get("recipe_id") for item in variants]
    asset_ids = [item.get("asset_id") for item in variants]
    if (
        any(
            not isinstance(value, str) or not value
            for value in variant_codes + recipe_ids + asset_ids
        )
        or len(set(variant_codes)) != len(variant_codes)
        or len(set(recipe_ids)) != len(recipe_ids)
        or len(set(asset_ids)) != len(asset_ids)
    ):
        raise TeethBatchError("Teeth variant IDs are invalid or duplicated")
    for variant in variants:
        asset = assets.get(variant["asset_id"])
        if asset is None:
            raise TeethBatchError(
                "Unknown teeth asset: {}".format(variant["asset_id"])
            )
        if (
            asset.get("slot") != "teeth"
            or asset.get("automation_status") != "candidate"
        ):
            raise TeethBatchError(
                "Asset is not an automatable teeth candidate: {}".format(
                    variant["asset_id"]
                )
            )
        preferred_path = canonical_file(
            asset.get("preferred_path"),
            "Teeth asset {}".format(variant["asset_id"]),
        )
        variant["resolved_path"] = preferred_path
        variant["display_name"] = asset.get("display_name")

    presets = []
    assignments = []
    for sex in ("male", "female"):
        for face_index, face_preset in enumerate(
            faces_by_sex[sex], start=1
        ):
            body = bodies_by_sex[sex][
                (face_index - 1) % len(bodies_by_sex[sex])
            ]
            body_code = body["preset_id"].split("_", 1)[0]
            for variant in variants:
                preset = copy.deepcopy(face_preset)
                for field in BODY_FIELDS:
                    preset[field] = copy.deepcopy(body[field])
                preset["bodyfit_id"] = body["preset_id"]
                preset_id = "TV1_{}_{:02d}_{}".format(
                    body_code,
                    face_index,
                    variant["code"],
                )
                preset["preset_id"] = preset_id
                preset["character_id"] = preset_id
                preset["appearance_recipe_id"] = variant["recipe_id"]
                preset["appearance_asset_ids"] = [variant["asset_id"]]
                preset["appearance_recipe"] = {
                    "source_face_preset_id": face_preset["preset_id"],
                    "teeth_variant_code": variant["code"],
                    "assets": [
                        {
                            "asset_id": variant["asset_id"],
                            "display_name": variant["display_name"],
                            "slot": "teeth",
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
                    "domain": "teeth",
                    "pose_profile": "teeth_visibility_v1",
                    "subject_position_offset": copy.deepcopy(
                        config.get(
                            "validation_subject_offset",
                            {"x": 0.0, "y": 0.0, "z": 0.0},
                        )
                    ),
                    "required_views": [
                        "face_front",
                        "teeth_smile_front",
                        "teeth_jaw_open_front",
                        "teeth_jaw_open_three_quarter",
                    ],
                    "verification_mode": "material_fingerprint",
                    "visual_limitation": (
                        "Approval requires manual review of teeth visibility "
                        "poses; material fingerprints alone are insufficient."
                    ),
                }
                preset["review_status"] = (
                    "teeth-v1-compatibility-candidate"
                )
                presets.append(preset)
                assignments.append(
                    {
                        "preset_id": preset_id,
                        "sex": sex,
                        "bodyfit_id": body["preset_id"],
                        "face_recipe_id": face_preset["face_recipe_id"],
                        "teeth_asset_id": variant["asset_id"],
                        "teeth_variant_code": variant["code"],
                    }
                )

    expected_count = len(face_presets) * len(variants)
    if len(presets) != expected_count:
        raise TeethBatchError(
            "Teeth matrix count mismatch: expected={} actual={}".format(
                expected_count, len(presets)
            )
        )
    preset_ids = [item["preset_id"] for item in presets]
    if len(preset_ids) != len(set(preset_ids)):
        raise TeethBatchError("Generated teeth preset IDs are duplicated")

    result = copy.deepcopy(face_batch)
    result["library_id"] = config["library_id"]
    result["generated_at"] = now()
    result["status"] = "teeth-v1-compatibility-candidate"
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
    result["teeth_variants"] = variants
    result["character_count"] = len(presets)
    result["presets"] = presets
    result["selection"] = {
        "face_count": len(face_presets),
        "bodyfit_count": len(bodies),
        "teeth_variant_count": len(variants),
        "assignment": "round_robin_bodyfit_within_sex",
        "assignments": assignments,
    }
    result["execution_policy"] = {
        "recommended_chunk_size": int(
            config.get("recommended_chunk_size", 8)
        ),
        "preserve_projects": False,
    }
    write_json(result, output_path)
    return {
        "success": True,
        "output": output_path,
        "library_id": result["library_id"],
        "character_count": len(presets),
        "face_count": len(face_presets),
        "bodyfit_count": len(bodies),
        "teeth_variant_count": len(variants),
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
