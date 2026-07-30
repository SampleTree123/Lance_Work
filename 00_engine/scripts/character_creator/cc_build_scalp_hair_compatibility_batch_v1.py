"""Build the CC5 Hair Builder dual-sex compatibility matrix."""

import argparse
import collections
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
    SCRIPT_DIR, "cc_scalp_hair_asset_catalog_v1.json"
)
DEFAULT_BATCH_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_compatibility_batch_v1.json"
)
SCALP_HAIR_PROFILE = "scalp_hair_visibility_v1"
ASSET_CATALOG_ID = "cc5_hair_builder_scalp_hair_user_pool_v1"
BATCH_ID = "cc5_hair_builder_scalp_hair_compatibility_v1"
CUSTOM_ROOT = r"D:\CharacterCreator_sucai\Reallusion Custom"
HAIR_GROUP_ROOT = os.path.join(
    CUSTOM_ROOT, "Hair", "Group", "Hair"
)
BASELINE_PRIMARY_SEEDS = {
    "male": "M02_Kevin",
    "female": "F02_Camila",
}
PACKS = (
    {
        "pack_id": "hair_builder_1",
        "pack_code": "HB1",
        "directory": "Hair Builder",
        "official_intent": "universal_female_leaning",
    },
    {
        "pack_id": "hair_builder_2_egirl",
        "pack_code": "HB2",
        "directory": "Hair Builder 2 - eGirl",
        "official_intent": "female_primary",
    },
    {
        "pack_id": "hair_builder_3_edgy",
        "pack_code": "HB3",
        "directory": "Hair Builder 3 - Edgy",
        "official_intent": "male_primary_mixed",
    },
)
HB1_MALE_PRIMARY = frozenset(
    (
        "Top knot samurai",
        "Top knot short ponytail",
    )
)
HB3_FEMALE_PRIMARY = frozenset(
    (
        "Deep Side Part with Braids",
        "Side Braid Long Hair",
        "Side Clip Long Hair",
        "Side Tucked Long Hair",
        "Side-swept Long Hair",
        "Sleek Deep Side Part",
        "Sleek Tucked Long Hair",
    )
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


def presentation_prior(pack_id, display_name):
    if pack_id == "hair_builder_2_egirl":
        score = 0.90
    elif pack_id == "hair_builder_1":
        score = 0.15 if display_name in HB1_MALE_PRIMARY else 0.85
    elif pack_id == "hair_builder_3_edgy":
        score = 0.85 if display_name in HB3_FEMALE_PRIMARY else 0.15
    else:
        raise BatchBuildError("Unsupported Hair Builder pack: {}".format(pack_id))
    return {
        "female_presentation_score": score,
        "label": "female_primary" if score >= 0.67 else "male_primary",
        "source": "user_visual_prior_2026-07-27",
        "technical_sex_restriction": None,
    }


def matching_canonical_asset(canonical_assets, display_name):
    matches = [
        item
        for item in canonical_assets
        if item.get("display_name") == display_name
        and item.get("slot") == "scalp_hair"
        and item.get("asset_form") == "group"
    ]
    if len(matches) != 1:
        raise BatchBuildError(
            "Expected one canonical scalp-hair group named {!r}, found {}".format(
                display_name,
                len(matches),
            )
        )
    return matches[0]


def discover_selected_assets(canonical_catalog):
    canonical_assets = canonical_catalog.get("assets") or []
    selected = []
    hashes = set()
    for pack in PACKS:
        pack_root = os.path.join(HAIR_GROUP_ROOT, pack["directory"])
        if not os.path.isdir(pack_root):
            raise BatchBuildError(
                "Hair Builder directory is missing: {}".format(pack_root)
            )
        files = sorted(
            (
                os.path.join(pack_root, filename)
                for filename in os.listdir(pack_root)
                if os.path.isfile(os.path.join(pack_root, filename))
                and os.path.splitext(filename)[1].casefold() == ".rlhair"
            ),
            key=lambda path: os.path.basename(path).casefold(),
        )
        if len(files) != 20:
            raise BatchBuildError(
                "{} must contain exactly 20 complete .rlHair files".format(
                    pack["directory"]
                )
            )
        for index, path in enumerate(files, 1):
            display_name = os.path.splitext(os.path.basename(path))[0]
            canonical_asset = matching_canonical_asset(
                canonical_assets,
                display_name,
            )
            digest = sha256_file(path)
            if digest in hashes:
                raise BatchBuildError(
                    "Duplicate Hair Builder file content: {}".format(path)
                )
            hashes.add(digest)
            item = copy.deepcopy(canonical_asset)
            current_relative_path = (
                os.path.relpath(path, CUSTOM_ROOT).replace(os.sep, "/")
            )
            original_preferred_path = item.get("preferred_path")
            item["preferred_origin"] = "custom"
            item["preferred_path"] = os.path.realpath(path)
            item["sex_hint"] = "unknown"
            matching_variants = [
                variant
                for variant in item.get("variants") or []
                if variant.get("origin") == "custom"
                and variant.get("asset_form") == "group"
                and str(variant.get("extension", "")).casefold()
                == ".rlhair"
            ]
            if len(matching_variants) != 1:
                raise BatchBuildError(
                    "Expected one custom group variant for {!r}".format(
                        display_name
                    )
                )
            matching_variants[0].update(
                {
                    "bytes": os.path.getsize(path),
                    "path": os.path.realpath(path),
                    "relative_path": current_relative_path,
                    "root": CUSTOM_ROOT,
                }
            )
            if os.path.normcase(
                os.path.realpath(original_preferred_path)
            ) != os.path.normcase(os.path.realpath(path)):
                item["path_migration"] = {
                    "current_relative_path": current_relative_path,
                    "original_preferred_path": original_preferred_path,
                    "stable_asset_id_preserved": True,
                    "stable_logical_relative_path": item.get(
                        "logical_relative_path"
                    ),
                }
            item["selected_source"] = {
                "bytes": os.path.getsize(path),
                "path": os.path.realpath(path),
                "sha256": digest,
                "source_kind": "user_selected_custom",
            }
            item["hair_builder_pack"] = {
                "asset_index": index,
                "directory": pack["directory"],
                "official_intent": pack["official_intent"],
                "pack_code": pack["pack_code"],
                "pack_id": pack["pack_id"],
            }
            item["presentation_prior"] = presentation_prior(
                pack["pack_id"],
                display_name,
            )
            selected.append(item)
    if len(selected) != 60:
        raise BatchBuildError("Expected 60 selected Hair Builder assets")
    asset_ids = [item["asset_id"] for item in selected]
    if len(asset_ids) != len(set(asset_ids)):
        raise BatchBuildError("Selected Hair Builder asset IDs are not unique")
    return selected


def build_asset_catalog(canonical_catalog_path):
    canonical = read_json(canonical_catalog_path)
    selected = discover_selected_assets(canonical)
    by_pack = collections.Counter(
        item["hair_builder_pack"]["pack_id"] for item in selected
    )
    by_prior = collections.Counter(
        item["presentation_prior"]["label"] for item in selected
    )
    return {
        "assets": selected,
        "catalog_id": ASSET_CATALOG_ID,
        "generated_at": now(),
        "roots": {
            "custom": CUSTOM_ROOT,
            "hair_group": HAIR_GROUP_ROOT,
        },
        "schema_version": 1,
        "selection_policy": {
            "asset_count": len(selected),
            "asset_form": "group",
            "exact_content_duplicates": 0,
            "pack_counts": dict(sorted(by_pack.items())),
            "presentation_prior_counts": dict(sorted(by_prior.items())),
            "slot": "scalp_hair",
            "source": "user_selected_hair_builder_directories",
        },
        "source_catalog": {
            "catalog_id": canonical.get("catalog_id"),
            "path": canonical_catalog_path,
            "sha256": sha256_file(canonical_catalog_path),
        },
    }


def representative_baselines(face_batch):
    selected = {}
    for preset in face_batch.get("presets") or []:
        generation = preset.get("face_generation") or {}
        sex = preset.get("sex")
        if (
            sex in BASELINE_PRIMARY_SEEDS
            and generation.get("strength_tier") == "baseline"
            and generation.get("primary_seed_id")
            == BASELINE_PRIMARY_SEEDS[sex]
        ):
            if sex in selected:
                raise BatchBuildError(
                    "Duplicate representative {} baseline".format(sex)
                )
            selected[sex] = preset
    if set(selected) != set(BASELINE_PRIMARY_SEEDS):
        raise BatchBuildError(
            "Missing representative male or female V3 baseline"
        )
    return selected


def build_preset(baseline, asset):
    preset = copy.deepcopy(baseline)
    pack = asset["hair_builder_pack"]
    sex = preset["sex"]
    preset_id = "HAIR_{}_{:02d}_{}".format(
        pack["pack_code"],
        pack["asset_index"],
        "M" if sex == "male" else "F",
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
            "appearance_recipe_id": "{}_{}_V1".format(
                pack["pack_code"],
                pack["asset_index"],
            ),
            "appearance_validation_plan": {
                "domain": "scalp_hair",
                "pose_profile": SCALP_HAIR_PROFILE,
                "subject_position_offset": {"x": -25.0, "z": 6.0},
                "required_views": [
                    "reconstructed_preview",
                    "face_front",
                    "face_three_quarter",
                    "face_profile",
                    "hair_rear_three_quarter",
                    "hair_rear",
                ],
                "verification_mode": "scene_inventory",
                "visual_limitation": (
                    "Adult CC5 HD representative faces; dynamic hair "
                    "physics and child or third-party heads are separate."
                ),
            },
            "character_id": preset_id,
            "hair_builder_pack": copy.deepcopy(pack),
            "presentation_prior": copy.deepcopy(
                asset["presentation_prior"]
            ),
            "preset_id": preset_id,
            "review_status": "scalp-hair-v1-quality-candidate",
        }
    )
    return preset


def build_batch(face_batch, asset_catalog, asset_catalog_path):
    baselines = representative_baselines(face_batch)
    presets = []
    for asset in asset_catalog["assets"]:
        for sex in ("male", "female"):
            presets.append(build_preset(baselines[sex], asset))
    preset_ids = [item["preset_id"] for item in presets]
    if len(presets) != 120 or len(preset_ids) != len(set(preset_ids)):
        raise BatchBuildError(
            "Scalp-hair matrix must contain 120 unique presets"
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
                "asset_count": 60,
                "female_baseline": BASELINE_PRIMARY_SEEDS["female"],
                "matrix_count": len(presets),
                "male_baseline": BASELINE_PRIMARY_SEEDS["male"],
                "policy": (
                    "all 60 complete Hair Builder groups on one V3 "
                    "male and one V3 female representative face"
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
        canonical_catalog_path,
        "Canonical appearance catalog",
    )
    face_batch_path = resolved_file(
        face_batch_path,
        "V3 face validation batch",
    )
    asset_catalog_output = os.path.realpath(
        os.path.abspath(asset_catalog_output)
    )
    batch_output = os.path.realpath(os.path.abspath(batch_output))
    asset_catalog = build_asset_catalog(canonical_catalog_path)
    write_json(asset_catalog, asset_catalog_output)
    face_batch = read_json(face_batch_path)
    batch = build_batch(
        face_batch,
        asset_catalog,
        asset_catalog_output,
    )
    batch["source_face_validation_batch"] = {
        "library_id": face_batch.get("library_id"),
        "path": face_batch_path,
        "sha256": sha256_file(face_batch_path),
    }
    write_json(batch, batch_output)
    return {
        "asset_catalog_path": asset_catalog_output,
        "asset_count": len(asset_catalog["assets"]),
        "batch_path": batch_output,
        "female_primary_prior_count": sum(
            1
            for item in asset_catalog["assets"]
            if item["presentation_prior"]["label"] == "female_primary"
        ),
        "male_primary_prior_count": sum(
            1
            for item in asset_catalog["assets"]
            if item["presentation_prior"]["label"] == "male_primary"
        ),
        "matrix_count": len(batch["presets"]),
        "success": True,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--canonical-catalog",
        default=DEFAULT_CANONICAL_CATALOG,
    )
    parser.add_argument("--face-batch", default=DEFAULT_FACE_BATCH)
    parser.add_argument(
        "--asset-catalog-output",
        default=DEFAULT_ASSET_CATALOG_OUTPUT,
    )
    parser.add_argument(
        "--batch-output",
        default=DEFAULT_BATCH_OUTPUT,
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print(
        json.dumps(
            build(
                canonical_catalog_path=args.canonical_catalog,
                face_batch_path=args.face_batch,
                asset_catalog_output=args.asset_catalog_output,
                batch_output=args.batch_output,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
