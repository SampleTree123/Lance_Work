"""Build the CC5 scalp-hair dynamic validation matrix."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(
    SCRIPT_DIR, "cc_facial_production_registry_v1.json"
)
DEFAULT_FACE_BATCH = os.path.join(
    SCRIPT_DIR, "cc_face_quality_batch_v3_validation.json"
)
DEFAULT_HAIR_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_asset_catalog_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_dynamic_batch_v1.json"
)
BATCH_ID = "cc5_scalp_hair_dynamic_validation_v1"
SCALP_HAIR_PROFILE = "scalp_hair_visibility_v1"
BASELINE_PRIMARY_SEEDS = {
    "female": "F02_Camila",
    "male": "M02_Kevin",
}
MOTION_ROOT = os.path.join(
    r"D:\CharacterCreator_sucai\Reallusion Templates",
    "Animation",
    "Motion Plus",
    "1.Acting",
)
CAMERA_ROOT = os.path.join(
    r"D:\CharacterCreator_sucai\Reallusion Templates",
    "Stage",
    "Camera",
    "Headshot Ref",
)
MOTIONS = {
    "female": (
        (
            "idle",
            os.path.join(
                MOTION_ROOT,
                "02_Female",
                "CC5 HD",
                "HD Idle 01_F.iMotionPlus",
            ),
        ),
        (
            "walk",
            os.path.join(
                MOTION_ROOT,
                "02_Female",
                "CC5 HD",
                "HD Walk_F.iMotionPlus",
            ),
        ),
        (
            "emote",
            os.path.join(
                MOTION_ROOT,
                "02_Female",
                "CC5 HD",
                "HD Emote_F.iMotionPlus",
            ),
        ),
    ),
    "male": (
        (
            "idle",
            os.path.join(
                MOTION_ROOT,
                "01_Male",
                "CC5 HD",
                "HD Idle_M.iMotionPlus",
            ),
        ),
        (
            "walk",
            os.path.join(
                MOTION_ROOT,
                "01_Male",
                "CC5 HD",
                "HD Walk_M.iMotionPlus",
            ),
        ),
        (
            "emote",
            os.path.join(
                MOTION_ROOT,
                "01_Male",
                "CC5 HD",
                "HD Emote_M.iMotionPlus",
            ),
        ),
    ),
}
CAMERAS = {
    "female": os.path.join(CAMERA_ROOT, "Ref Cam Female L.ccCam"),
    "male": os.path.join(CAMERA_ROOT, "Ref Cam Male L.ccCam"),
}


class BatchBuildError(RuntimeError):
    pass


def now():
    return (
        datetime.datetime.now()
        .astimezone()
        .replace(microsecond=0)
        .isoformat()
    )


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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolved_file(path, label):
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise BatchBuildError("{} is missing: {}".format(label, path))
    return path


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            raise BatchBuildError("{} item has no {}".format(label, key))
        if value in result:
            raise BatchBuildError(
                "{} contains duplicate {} {!r}".format(label, key, value)
            )
        result[value] = item
    return result


def baseline_presets(face_batch):
    result = {}
    for preset in face_batch.get("presets") or []:
        generation = preset.get("face_generation") or {}
        sex = preset.get("sex")
        if (
            sex in BASELINE_PRIMARY_SEEDS
            and generation.get("strength_tier") == "baseline"
            and generation.get("primary_seed_id")
            == BASELINE_PRIMARY_SEEDS[sex]
        ):
            if sex in result:
                raise BatchBuildError(
                    "Duplicate {} dynamic baseline".format(sex)
                )
            result[sex] = preset
    if set(result) != set(BASELINE_PRIMARY_SEEDS):
        raise BatchBuildError(
            "Dynamic matrix is missing a male or female baseline"
        )
    return result


def default_presentation_sex(asset, neutral_index):
    score = float(asset.get("female_presentation_score"))
    if score < 0.5:
        return "male"
    if score > 0.5:
        return "female"
    return "male" if neutral_index % 2 == 0 else "female"


def motion_for_case(sex, motion_index, force_walk=False):
    candidates = MOTIONS[sex]
    if force_walk:
        motion_id, path = next(
            item for item in candidates if item[0] == "walk"
        )
    else:
        motion_id, path = candidates[motion_index % len(candidates)]
    return {
        "camera_path": resolved_file(
            CAMERAS[sex],
            "{} dynamic camera".format(sex),
        ),
        "motion_id": motion_id,
        "motion_path": resolved_file(
            path,
            "{} {} dynamic motion".format(sex, motion_id),
        ),
        "replace_existing_motion_clips": True,
        "sample_frames": [0, 30, 60, 90, 120],
        "segment_timeout_seconds": 20.0,
        "subject_position": {
            "x": -75.0 if motion_id == "walk" else -50.0,
            "y": 8.0,
            "z": 6.0,
        },
        "yaw_degrees": 90.0,
    }


def build_preset(
    baseline,
    asset,
    asset_index,
    case_phase,
    motion_index,
):
    preset = copy.deepcopy(baseline)
    sex = preset["sex"]
    sex_code = "M" if sex == "male" else "F"
    phase_code = "B" if case_phase == "base" else "X"
    preset_id = "HAIRDYN_{}_{:02d}_{}".format(
        phase_code,
        asset_index,
        sex_code,
    )
    motion = motion_for_case(
        sex,
        motion_index,
        force_walk=(case_phase == "cross_presentation"),
    )
    preset.update(
        {
            "appearance_asset_ids": [asset["asset_id"]],
            "appearance_recipe": {
                "assets": [
                    {
                        "asset_form": "group",
                        "asset_id": asset["asset_id"],
                        "display_name": asset["display_name"],
                        "sex_hint": "unknown",
                        "slot": "scalp_hair",
                    }
                ],
                "source_preset_id": baseline["preset_id"],
            },
            "appearance_recipe_id": "HAIRDYN_{}_{:02d}_V1".format(
                phase_code,
                asset_index,
            ),
            "appearance_validation_plan": {
                "asset_load_pacing": {
                    "default_after_seconds": 0.0,
                    "default_before_seconds": 0.0,
                    "slots": {
                        "scalp_hair": {
                            "after_seconds": 12.0,
                            "before_seconds": 8.0,
                        }
                    },
                },
                "domain": "scalp_hair",
                "hair_motion_validation": {
                    key: value
                    for key, value in motion.items()
                    if key != "motion_id"
                },
                "pose_profile": SCALP_HAIR_PROFILE,
                "required_views": [
                    "face_front",
                    "face_three_quarter",
                    "face_profile",
                    "hair_rear_three_quarter",
                    "hair_rear",
                    "hair_motion_frames",
                ],
                "subject_position_offset": {
                    "x": -25.0,
                    "z": 6.0,
                },
                "verification_mode": "scene_inventory_and_dynamic_physics",
                "visual_limitation": (
                    "Adult CC5 HD dynamic validation. Human review is "
                    "still required for collision and silhouette quality."
                ),
            },
            "character_id": preset_id,
            "preset_id": preset_id,
            "review_status": "scalp-hair-dynamic-candidate",
            "scalp_hair_dynamic_validation": {
                "case_phase": case_phase,
                "female_presentation_score": float(
                    asset["female_presentation_score"]
                ),
                "motion_id": motion["motion_id"],
                "presentation_sex": sex,
                "silhouette_family": asset.get(
                    "silhouette_family"
                ),
            },
        }
    )
    return preset


def build(
    registry_path=DEFAULT_REGISTRY,
    face_batch_path=DEFAULT_FACE_BATCH,
    hair_catalog_path=DEFAULT_HAIR_CATALOG,
    output_path=DEFAULT_OUTPUT,
):
    registry_path = resolved_file(registry_path, "Facial production registry")
    face_batch_path = resolved_file(face_batch_path, "V3 face batch")
    hair_catalog_path = resolved_file(hair_catalog_path, "Scalp-hair catalog")
    registry = read_json(registry_path)
    face_batch = read_json(face_batch_path)
    hair_catalog = read_json(hair_catalog_path)
    baselines = baseline_presets(face_batch)
    catalog_assets = indexed(
        hair_catalog.get("assets") or [],
        "asset_id",
        "Scalp-hair catalog",
    )
    production_assets = sorted(
        (
            copy.deepcopy(item)
            for item in (
                (registry.get("component_pools") or {}).get(
                    "scalp_hair"
                )
                or []
            )
        ),
        key=lambda item: item["asset_id"],
    )
    if len(production_assets) != 58:
        raise BatchBuildError(
            "Dynamic matrix requires 58 production scalp hairs"
        )
    pressure_ids = set(
        (registry.get("validation_design") or {}).get(
            "scalp_hair_static_pressure_asset_ids"
        )
        or []
    )
    if len(pressure_ids) != 16:
        raise BatchBuildError(
            "Dynamic cross-presentation set must contain 16 assets"
        )

    presets = []
    base_sexes = {}
    neutral_index = 0
    sex_motion_indexes = {"female": 0, "male": 0}
    for asset_index, production in enumerate(
        production_assets,
        1,
    ):
        asset_id = production["asset_id"]
        if asset_id not in catalog_assets:
            raise BatchBuildError(
                "Production hair is missing from catalog: {}".format(
                    asset_id
                )
            )
        asset = copy.deepcopy(catalog_assets[asset_id])
        asset.update(
            {
                "female_presentation_score": production.get(
                    "female_presentation_score"
                ),
                "silhouette_family": production.get(
                    "silhouette_family"
                ),
            }
        )
        sex = default_presentation_sex(asset, neutral_index)
        if float(asset["female_presentation_score"]) == 0.5:
            neutral_index += 1
        base_sexes[asset_id] = sex
        motion_index = sex_motion_indexes[sex]
        presets.append(
            build_preset(
                baselines[sex],
                asset,
                asset_index,
                "base",
                motion_index,
            )
        )
        sex_motion_indexes[sex] += 1

    for asset_index, production in enumerate(
        production_assets,
        1,
    ):
        asset_id = production["asset_id"]
        if asset_id not in pressure_ids:
            continue
        asset = copy.deepcopy(catalog_assets[asset_id])
        asset.update(
            {
                "female_presentation_score": production.get(
                    "female_presentation_score"
                ),
                "silhouette_family": production.get(
                    "silhouette_family"
                ),
            }
        )
        base_sex = base_sexes[asset_id]
        cross_sex = "female" if base_sex == "male" else "male"
        presets.append(
            build_preset(
                baselines[cross_sex],
                asset,
                asset_index,
                "cross_presentation",
                0,
            )
        )

    expected_base = int(
        (registry.get("validation_design") or {}).get(
            "scalp_hair_dynamic_base_case_count", 0
        )
    )
    expected_cross = int(
        (registry.get("validation_design") or {}).get(
            "scalp_hair_dynamic_cross_sex_case_count", 0
        )
    )
    base_count = sum(
        1
        for item in presets
        if item["scalp_hair_dynamic_validation"]["case_phase"]
        == "base"
    )
    cross_count = len(presets) - base_count
    if base_count != expected_base or cross_count != expected_cross:
        raise BatchBuildError(
            "Dynamic matrix expected {} base + {} cross cases; "
            "built {} + {}".format(
                expected_base,
                expected_cross,
                base_count,
                cross_count,
            )
        )
    if len({item["preset_id"] for item in presets}) != len(presets):
        raise BatchBuildError("Dynamic preset IDs are not unique")

    document = copy.deepcopy(face_batch)
    document.update(
        {
            "appearance_catalog": {
                "catalog_id": hair_catalog.get("catalog_id"),
                "path": hair_catalog_path,
                "sha256": sha256_file(hair_catalog_path),
            },
            "character_count": len(presets),
            "generated_at": now(),
            "library_id": BATCH_ID,
            "presets": presets,
            "selection": {
                "base_case_count": base_count,
                "cross_presentation_case_count": cross_count,
                "policy": (
                    "One deterministic default-presentation motion per "
                    "approved asset, plus opposite-presentation walk "
                    "stress tests for the 16 high-risk assets"
                ),
                "production_asset_count": len(production_assets),
            },
            "sources": {
                "facial_production_registry": {
                    "path": registry_path,
                    "sha256": sha256_file(registry_path),
                },
                "scalp_hair_catalog": {
                    "path": hair_catalog_path,
                    "sha256": sha256_file(hair_catalog_path),
                },
                "v3_face_batch": {
                    "path": face_batch_path,
                    "sha256": sha256_file(face_batch_path),
                },
            },
            "status": "dynamic-validation-pending",
        }
    )
    write_json(document, output_path)
    return document


def main():
    parser = argparse.ArgumentParser(
        description="Build the CC5 scalp-hair dynamic matrix."
    )
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--face-batch", default=DEFAULT_FACE_BATCH)
    parser.add_argument("--hair-catalog", default=DEFAULT_HAIR_CATALOG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_path = os.path.realpath(os.path.abspath(args.output))
    document = build(
        registry_path=args.registry,
        face_batch_path=args.face_batch,
        hair_catalog_path=args.hair_catalog,
        output_path=output_path,
    )
    print(
        "Built {} scalp-hair dynamic cases -> {}".format(
            document["character_count"],
            output_path,
        )
    )


if __name__ == "__main__":
    main()
