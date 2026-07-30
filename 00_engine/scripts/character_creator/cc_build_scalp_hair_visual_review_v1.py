"""Build the final scalp-hair visual review from explicit review decisions."""

import argparse
import collections
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_compatibility_batch_v1.json"
)
DEFAULT_CATALOG = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_asset_catalog_v1.json"
)
DEFAULT_DECISIONS = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_visual_decisions_v1.json"
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_compatibility_visual_review_v1.json"
)
REQUIRED_ARTIFACT_KEYS = (
    "reconstructed_preview",
    "face_front_preview",
    "face_three_quarter_preview",
    "face_profile_preview",
    "hair_rear_three_quarter_preview",
    "hair_rear_preview",
)
ALLOWED_SEXES = frozenset(("male", "female"))
ALLOWED_PRODUCTION_STATUSES = frozenset(
    (
        "approved_static_dynamic_pending",
        "conditional_cleanup_required",
        "rejected",
    )
)
ALLOWED_PRESENTATION_LABELS = frozenset(
    ("male_primary", "female_primary", "unisex")
)


class ReviewError(RuntimeError):
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


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ReviewError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    return result


def silhouette_family(display_name):
    name = display_name.casefold()
    if "mullet" in name:
        return "mullet"
    if "undercut" in name:
        return "undercut"
    if "pixie" in name:
        return "short_pixie"
    if "half up" in name:
        return "half_up"
    if "pigtail" in name or "two ponytail" in name:
        return "twin_tail"
    if "ponytail" in name:
        return "ponytail"
    if "braid" in name:
        return "braid"
    if "bun" in name or "top knot" in name:
        return "bun_updo"
    if "long hair" in name or "long middle part" in name:
        return "long_loose"
    if "short" in name:
        return "short"
    return "medium_or_swept"


def style_tags(display_name):
    name = display_name.casefold()
    candidates = (
        ("braid", "braided"),
        ("bun", "bun"),
        ("curly", "curly"),
        ("fringe", "fringe"),
        ("half up", "half_up"),
        ("long", "long"),
        ("middle part", "middle_part"),
        ("mullet", "mullet"),
        ("pigtail", "pigtail"),
        ("ponytail", "ponytail"),
        ("short", "short"),
        ("side", "side_styled"),
        ("sleek", "sleek"),
        ("spiky", "spiky"),
        ("top knot", "top_knot"),
        ("undercut", "undercut"),
        ("wavy", "wavy"),
    )
    return [tag for token, tag in candidates if token in name]


def result_structure(result):
    steps = (
        (result.get("appearance_application") or {}).get("steps")
        or []
    )
    if len(steps) != 1:
        raise ReviewError(
            "Expected one scalp-hair application step: {}".format(
                result.get("preset_id")
            )
        )
    added = steps[0].get("added_objects") or []
    hair_names = sorted(
        item.get("name")
        for item in added
        if item.get("collection") == "GetHairs" and item.get("name")
    )
    accessory_names = sorted(
        item.get("name")
        for item in added
        if item.get("collection") == "GetAccessories"
        and item.get("name")
    )
    return {
        "accessory_count": len(accessory_names),
        "accessory_names": accessory_names,
        "hair_part_count": len(hair_names),
        "hair_part_names": hair_names,
    }


def allowed_component_morphs(result):
    policy = result.get("appearance_morph_policy") or {}
    return [
        {
            "actual": item.get("actual"),
            "allowed_reason": item.get("allowed_reason"),
            "categories": (
                (item.get("metadata") or {}).get("categories") or []
            ),
            "id": item.get("id"),
        }
        for item in policy.get("allowed_changes") or []
    ]


def validate_result(result):
    preset_id = result.get("preset_id")
    if result.get("success") is not True:
        raise ReviewError("Validation failed: {}".format(preset_id))
    if result.get("appearance_matches_recipe") is not True:
        raise ReviewError(
            "Appearance recipe mismatch: {}".format(preset_id)
        )
    if result.get("appearance_morphs_within_policy") is not True:
        raise ReviewError(
            "Protected morph policy failed: {}".format(preset_id)
        )
    artifacts = result.get("artifacts") or {}
    for key in REQUIRED_ARTIFACT_KEYS:
        path = artifacts.get(key)
        if (
            not isinstance(path, str)
            or not os.path.isfile(path)
            or os.path.getsize(path) <= 0
        ):
            raise ReviewError(
                "Required artifact is missing for {}: {}".format(
                    preset_id,
                    key,
                )
            )


def presentation_decision(asset, overrides):
    prior = asset["presentation_prior"]
    decision = {
        "female_presentation_score": float(
            prior["female_presentation_score"]
        ),
        "label": prior["label"],
        "source": prior["source"],
    }
    override = overrides.get(asset["asset_id"]) or {}
    decision.update(override)
    if decision["label"] not in ALLOWED_PRESENTATION_LABELS:
        raise ReviewError(
            "Unsupported presentation label for {}".format(
                asset["asset_id"]
            )
        )
    score = float(decision["female_presentation_score"])
    if score < 0.0 or score > 1.0:
        raise ReviewError(
            "Presentation score is out of range for {}".format(
                asset["asset_id"]
            )
        )
    decision["female_presentation_score"] = score
    return decision


def build(
    catalog_path,
    batch_path,
    validation_path,
    decisions_path,
    output_path,
):
    paths = [
        os.path.realpath(os.path.abspath(path))
        for path in (
            catalog_path,
            batch_path,
            validation_path,
            decisions_path,
        )
    ]
    catalog_path, batch_path, validation_path, decisions_path = paths
    output_path = os.path.realpath(os.path.abspath(output_path))
    for path in paths:
        if not os.path.isfile(path):
            raise ReviewError("Input is missing: {}".format(path))

    catalog = read_json(catalog_path)
    batch = read_json(batch_path)
    validation = read_json(validation_path)
    decisions = read_json(decisions_path)
    if decisions.get("review_complete") is not True:
        raise ReviewError(
            "Review decisions are not marked complete"
        )

    assets = indexed(catalog.get("assets") or [], "asset_id", "Asset")
    presets = indexed(batch.get("presets") or [], "preset_id", "Preset")
    results = indexed(
        validation.get("results") or [],
        "preset_id",
        "Validation result",
    )
    if len(assets) != 60 or len(results) != 120:
        raise ReviewError(
            "Expected 60 assets and 120 completed validations"
        )
    if set(results) != set(presets):
        raise ReviewError("Batch and validation preset sets differ")

    default_sexes = list(decisions.get("default_accepted_sexes") or [])
    if (
        not default_sexes
        or len(default_sexes) != len(set(default_sexes))
        or not set(default_sexes).issubset(ALLOWED_SEXES)
    ):
        raise ReviewError("Default accepted sexes are invalid")
    default_status = decisions.get("default_production_status")
    if default_status not in ALLOWED_PRODUCTION_STATUSES:
        raise ReviewError("Default production status is invalid")
    asset_overrides = decisions.get("asset_overrides") or {}
    presentation_overrides = decisions.get("presentation_overrides") or {}
    unknown_overrides = (
        set(asset_overrides).union(presentation_overrides).difference(assets)
    )
    if unknown_overrides:
        raise ReviewError(
            "Decision overrides reference unknown assets: {}".format(
                ", ".join(sorted(unknown_overrides))
            )
        )

    records = collections.defaultdict(list)
    for preset_id, result in results.items():
        validate_result(result)
        preset = presets[preset_id]
        asset_ids = preset.get("appearance_asset_ids") or []
        if len(asset_ids) != 1 or asset_ids[0] not in assets:
            raise ReviewError(
                "Preset does not reference one selected asset: {}".format(
                    preset_id
                )
            )
        records[asset_ids[0]].append((preset, result))
    if set(records) != set(assets):
        raise ReviewError("Not every selected asset has validation results")

    reviews = []
    asset_notes = {}
    presentation_reviews = []
    status_counts = collections.Counter()
    accepted_combination_count = 0
    for asset_id in sorted(assets):
        asset = assets[asset_id]
        pair = records[asset_id]
        if {item[0].get("sex") for item in pair} != ALLOWED_SEXES:
            raise ReviewError(
                "Asset lacks male/female pair: {}".format(asset_id)
            )
        override = asset_overrides.get(asset_id) or {}
        production_status = override.get(
            "production_status",
            default_status,
        )
        if production_status not in ALLOWED_PRODUCTION_STATUSES:
            raise ReviewError(
                "Invalid production status for {}".format(asset_id)
            )
        accepted_sexes = list(
            override.get("accepted_sexes", default_sexes)
        )
        if (
            len(accepted_sexes) != len(set(accepted_sexes))
            or not set(accepted_sexes).issubset(ALLOWED_SEXES)
        ):
            raise ReviewError(
                "Invalid accepted sexes for {}".format(asset_id)
            )
        if (
            production_status != "approved_static_dynamic_pending"
            and accepted_sexes
        ):
            raise ReviewError(
                "{} cannot accept sexes while status is {}".format(
                    asset_id,
                    production_status,
                )
            )

        presentation = presentation_decision(
            asset,
            presentation_overrides,
        )
        structures = {
            preset["sex"]: result_structure(result)
            for preset, result in pair
        }
        component_morphs = {
            preset["sex"]: allowed_component_morphs(result)
            for preset, result in pair
        }
        risk_tags = list(override.get("risk_tags") or [])
        notes = list(override.get("notes") or [])
        if production_status == "approved_static_dynamic_pending":
            notes.insert(
                0,
                (
                    "Six static views were reviewed on one adult male and "
                    "one adult female V3 representative face; no obvious "
                    "hairline, ear-side, rear-head, neck, or shoulder "
                    "penetration was observed on the accepted sex(es)."
                ),
            )
        notes.append(
            "Dynamic hair physics and animation deformation remain pending."
        )
        notes.append(
            (
                "Presentation label {} (female score {:.2f}) controls "
                "sampling preference, not technical sex compatibility."
            ).format(
                presentation["label"],
                presentation["female_presentation_score"],
            )
        )
        asset_notes[asset_id] = notes
        status_counts[production_status] += 1
        presentation_reviews.append(
            {
                "accepted_sexes": accepted_sexes,
                "asset_id": asset_id,
                "display_name": asset["display_name"],
                "female_presentation_score": presentation[
                    "female_presentation_score"
                ],
                "hair_builder_pack": asset["hair_builder_pack"],
                "allowed_component_morphs_by_sex": component_morphs,
                "presentation_label": presentation["label"],
                "presentation_source": presentation["source"],
                "production_status": production_status,
                "risk_tags": risk_tags,
                "silhouette_family": silhouette_family(
                    asset["display_name"]
                ),
                "structures_by_sex": structures,
                "style_tags": style_tags(asset["display_name"]),
            }
        )

        sex_notes = override.get("sex_notes") or {}
        for preset, result in pair:
            sex = preset["sex"]
            accepted = (
                production_status
                == "approved_static_dynamic_pending"
                and sex in accepted_sexes
            )
            if accepted:
                accepted_combination_count += 1
            review_notes = list(notes)
            review_notes.extend(sex_notes.get(sex) or [])
            reviews.append(
                {
                    "notes": review_notes,
                    "preset_id": preset["preset_id"],
                    "visual_status": (
                        "accepted" if accepted else "rejected"
                    ),
                }
            )

    review = {
        "schema_version": 1,
        "review_id": "cc_scalp_hair_compatibility_visual_review_v1",
        "generated_at": now(),
        "scope": (
            "Static six-view review of 60 selected Hair Builder groups on "
            "one adult V3 male and one adult V3 female representative face. "
            "Dynamic physics, children, third-party heads, and expanded "
            "HeadFit ranges are outside this approval."
        ),
        "sources": {
            "asset_catalog": catalog_path,
            "batch": batch_path,
            "decisions": decisions_path,
            "validation": validation_path,
            "contact_sheet_directory": os.path.join(
                os.path.dirname(validation_path),
                "review",
                "scalp_hair",
            ),
        },
        "summary": {
            "accepted_combination_count": accepted_combination_count,
            "asset_count": len(assets),
            "production_status_counts": dict(sorted(status_counts.items())),
            "technical_validation_count": len(results),
        },
        "asset_notes": asset_notes,
        "presentation_reviews": presentation_reviews,
        "reviews": sorted(reviews, key=lambda item: item["preset_id"]),
    }
    write_json(review, output_path)
    return {
        "success": True,
        "output": output_path,
        "summary": review["summary"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                args.catalog,
                args.batch,
                args.validation,
                args.decisions,
                args.output,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
