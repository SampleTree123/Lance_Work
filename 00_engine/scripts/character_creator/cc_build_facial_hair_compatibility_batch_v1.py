"""Build the CC5 male facial-hair compatibility matrix."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CANONICAL_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json"
)
DEFAULT_FACE_BATCH = os.path.join(
    SCRIPT_DIR, "cc_face_quality_batch_v3_validation.json"
)
DEFAULT_ASSET_CATALOG_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_facial_hair_asset_catalog_v1.json"
)
DEFAULT_BATCH_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_facial_hair_compatibility_batch_v1.json"
)
FACIAL_HAIR_PROFILE = "facial_hair_visibility_v1"
ASSET_CATALOG_ID = "cc5_male_facial_hair_user_pool_v1"
BATCH_ID = "cc5_male_facial_hair_compatibility_v1"
TEMPLATE_ROOT = (
    r"D:\CharacterCreator_sucai\Reallusion Templates"
)
BEARD_ROOT = os.path.join(TEMPLATE_ROOT, "Hair", "Group", "Beard")
ASSETS = (
    {
        "asset_id": "CCAPP_FACIAL_HAIR_edbfa9f846a1",
        "display_name": "Country Style",
        "filename": "Country Style.rlhair",
        "recipe_id": "M_BEARD_COUNTRY_STYLE_V1",
        "slug": "COUNTRY",
    },
    {
        "asset_id": "CCAPP_FACIAL_HAIR_fe2419c94599",
        "display_name": "Stubble",
        "filename": "Stubble.rlHair",
        "recipe_id": "M_BEARD_STUBBLE_V1",
        "slug": "STUBBLE",
    },
    {
        "asset_id": "CCAPP_FACIAL_HAIR_ba8a532b109d",
        "display_name": "The Cowboy",
        "filename": "The Cowboy.rlhair",
        "recipe_id": "M_BEARD_COWBOY_V1",
        "slug": "COWBOY",
    },
    {
        "asset_id": "CCAPP_FACIAL_HAIR_0564f3beeae6",
        "display_name": "Thick Chin Curtain",
        "filename": "Thick Chin Curtain.rlHair",
        "recipe_id": "M_BEARD_CHIN_CURTAIN_V1",
        "slug": "CHINCURTAIN",
    },
    {
        "asset_id": "CCAPP_FACIAL_HAIR_eedcb805b235",
        "display_name": "Viking",
        "filename": "Viking.rlhair",
        "recipe_id": "M_BEARD_VIKING_V1",
        "slug": "VIKING",
    },
)


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


def build_asset_catalog(canonical_catalog_path):
    canonical = read_json(canonical_catalog_path)
    canonical_assets = {
        item["asset_id"]: item
        for item in (canonical.get("assets") or [])
        if isinstance(item, dict) and item.get("asset_id")
    }
    selected_assets = []
    for selection in ASSETS:
        asset_id = selection["asset_id"]
        canonical_asset = canonical_assets.get(asset_id)
        if canonical_asset is None:
            raise BatchBuildError(
                "Canonical catalog is missing {}".format(asset_id)
            )
        if (
            canonical_asset.get("slot") != "facial_hair"
            or canonical_asset.get("asset_form") != "group"
            or canonical_asset.get("automation_status") != "candidate"
        ):
            raise BatchBuildError(
                "Canonical asset is not a facial-hair group candidate: "
                "{}".format(asset_id)
            )
        path = resolved_file(
            os.path.join(BEARD_ROOT, selection["filename"]),
            selection["display_name"],
        )
        item = copy.deepcopy(canonical_asset)
        item["preferred_path"] = path
        item["selected_source"] = {
            "path": path,
            "sha256": sha256_file(path),
            "source_kind": "user_selected_template",
        }
        selected_assets.append(item)

    return {
        "assets": selected_assets,
        "catalog_id": ASSET_CATALOG_ID,
        "generated_at": now(),
        "roots": {"templates": TEMPLATE_ROOT},
        "schema_version": 1,
        "selection_policy": {
            "asset_count": len(selected_assets),
            "asset_form": "group",
            "sex": "male",
            "slot": "facial_hair",
            "source": "user_selected_template_paths",
        },
        "source_catalog": {
            "catalog_id": canonical.get("catalog_id"),
            "path": canonical_catalog_path,
            "sha256": sha256_file(canonical_catalog_path),
        },
    }


def male_primary_baselines(face_batch):
    baselines = [
        item
        for item in (face_batch.get("presets") or [])
        if item.get("sex") == "male"
        and (item.get("face_generation") or {}).get(
            "strength_tier"
        )
        == "baseline"
    ]
    baselines.sort(
        key=lambda item: (
            (item.get("face_generation") or {}).get(
                "primary_seed_id", ""
            ),
            item.get("preset_id", ""),
        )
    )
    primary_ids = [
        item["face_generation"]["primary_seed_id"]
        for item in baselines
    ]
    if len(baselines) != 9 or len(set(primary_ids)) != 9:
        raise BatchBuildError(
            "Expected nine unique male V3 primary baselines"
        )
    return baselines


def build_preset(baseline, asset, asset_index):
    preset = copy.deepcopy(baseline)
    primary_id = preset["face_generation"]["primary_seed_id"]
    preset_id = "BEARD_{}_A{:02d}_{}".format(
        primary_id.upper(),
        asset_index,
        asset["slug"],
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
                        "sex_hint": "male",
                        "slot": "facial_hair",
                    }
                ],
                "source_preset_id": baseline["preset_id"],
            },
            "appearance_recipe_id": asset["recipe_id"],
            "appearance_validation_plan": {
                "domain": "facial_hair",
                "pose_profile": FACIAL_HAIR_PROFILE,
                "required_views": [
                    "face_front",
                    "face_three_quarter",
                    "face_profile",
                    "smile_front",
                    "jaw_open_front",
                    "jaw_open_three_quarter",
                ],
                "verification_mode": "scene_inventory",
            },
            "character_id": preset_id,
            "preset_id": preset_id,
            "review_status": "facial-hair-v1-quality-candidate",
        }
    )
    return preset


def build_batch(face_batch, asset_catalog_path):
    baselines = male_primary_baselines(face_batch)
    presets = []
    for baseline in baselines:
        for asset_index, asset in enumerate(ASSETS, 1):
            presets.append(
                build_preset(baseline, asset, asset_index)
            )
    preset_ids = [item["preset_id"] for item in presets]
    if len(presets) != 45 or len(preset_ids) != len(set(preset_ids)):
        raise BatchBuildError(
            "Facial-hair matrix must contain 45 unique presets"
        )

    document = copy.deepcopy(face_batch)
    document.update(
        {
            "appearance_catalog": {
                "catalog_id": ASSET_CATALOG_ID,
                "path": asset_catalog_path,
            },
            "character_count": len(presets),
            "generated_at": now(),
            "library_id": BATCH_ID,
            "presets": presets,
            "selection": {
                "asset_count": len(ASSETS),
                "matrix_count": len(presets),
                "male_primary_face_count": len(baselines),
                "pilot_preset_ids": [
                    item["preset_id"]
                    for item in presets[: len(ASSETS)]
                ],
                "policy": (
                    "five complete beard groups across every "
                    "production male V3 primary face"
                ),
            },
            "status": "quality-review-only",
        }
    )
    return document


def build(
    canonical_catalog_path=DEFAULT_CANONICAL_CATALOG,
    face_batch_path=DEFAULT_FACE_BATCH,
    asset_catalog_output=DEFAULT_ASSET_CATALOG_OUTPUT,
    batch_output=DEFAULT_BATCH_OUTPUT,
):
    canonical_catalog_path = resolved_file(
        canonical_catalog_path, "Canonical appearance catalog"
    )
    face_batch_path = resolved_file(
        face_batch_path, "V3 face validation batch"
    )
    asset_catalog_output = os.path.realpath(
        os.path.abspath(asset_catalog_output)
    )
    batch_output = os.path.realpath(
        os.path.abspath(batch_output)
    )

    asset_catalog = build_asset_catalog(canonical_catalog_path)
    write_json(asset_catalog, asset_catalog_output)
    face_batch = read_json(face_batch_path)
    batch = build_batch(face_batch, asset_catalog_output)
    batch["source_face_validation_batch"] = {
        "library_id": face_batch.get("library_id"),
        "path": face_batch_path,
        "sha256": sha256_file(face_batch_path),
    }
    write_json(batch, batch_output)
    return {
        "asset_catalog": asset_catalog_output,
        "asset_count": len(asset_catalog["assets"]),
        "batch": batch_output,
        "matrix_count": len(batch["presets"]),
        "pilot_preset_ids": batch["selection"][
            "pilot_preset_ids"
        ],
        "success": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-catalog",
        default=DEFAULT_CANONICAL_CATALOG,
    )
    parser.add_argument(
        "--face-batch",
        default=DEFAULT_FACE_BATCH,
    )
    parser.add_argument(
        "--asset-catalog-output",
        default=DEFAULT_ASSET_CATALOG_OUTPUT,
    )
    parser.add_argument(
        "--batch-output",
        default=DEFAULT_BATCH_OUTPUT,
    )
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.canonical_catalog,
                args.face_batch,
                args.asset_catalog_output,
                args.batch_output,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
