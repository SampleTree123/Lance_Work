"""Build constrained multi-axis Headshot skull-profile candidates."""

import argparse
import hashlib
import json
import math
import os


SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
DEFAULT_SAFE_RANGES = os.path.join(
    SCRIPT_ROOT,
    "cc_headshot_skull_safe_ranges_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_ROOT,
    "cc_headshot_skull_composition_candidates_v1.json",
)

HEAD_SCALE_ID = "cc embed morphs/embed_full_head9"
MAX_ACTIVE_AXES = 3
MAX_NORMALIZED_L1 = 2.0
MAX_NORMALIZED_L2 = 1.2

AXIS_ORDER = (
    "head_width",
    "head_depth",
    "skull_height",
    "skull_width",
    "skull_depth",
    "skull_back_depth",
    "skull_peak",
)

PROFILES = (
    {
        "id": "C00_BASELINE",
        "label": "Baseline",
        "head_width": 0.0,
        "head_depth": 0.0,
        "skull_height": 0.0,
        "skull_width": 0.0,
        "skull_depth": 0.0,
        "skull_back_depth": 0.0,
        "skull_peak": 0.0,
    },
    {
        "id": "C01_BROAD_LOW",
        "label": "Broad low",
        "head_width": 0.48,
        "head_depth": 0.0,
        "skull_height": -0.30,
        "skull_width": 0.45,
        "skull_depth": 0.0,
        "skull_back_depth": 0.0,
        "skull_peak": 0.0,
    },
    {
        "id": "C02_NARROW_TALL",
        "label": "Narrow tall",
        "head_width": -0.46,
        "head_depth": 0.0,
        "skull_height": 0.45,
        "skull_width": -0.38,
        "skull_depth": 0.0,
        "skull_back_depth": 0.0,
        "skull_peak": 0.0,
    },
    {
        "id": "C03_LONG_DEEP",
        "label": "Long deep",
        "head_width": 0.0,
        "head_depth": 0.40,
        "skull_height": 0.0,
        "skull_width": 0.0,
        "skull_depth": 0.42,
        "skull_back_depth": 0.30,
        "skull_peak": 0.0,
    },
    {
        "id": "C04_COMPACT_SHALLOW",
        "label": "Compact shallow",
        "head_width": 0.0,
        "head_depth": -0.38,
        "skull_height": 0.0,
        "skull_width": 0.0,
        "skull_depth": -0.40,
        "skull_back_depth": -0.24,
        "skull_peak": 0.0,
    },
    {
        "id": "C05_HIGH_PEAK",
        "label": "High peak",
        "head_width": 0.0,
        "head_depth": 0.0,
        "skull_height": 0.42,
        "skull_width": 0.0,
        "skull_depth": 0.0,
        "skull_back_depth": 0.16,
        "skull_peak": 0.38,
    },
    {
        "id": "C06_LOW_FLAT",
        "label": "Low flat",
        "head_width": 0.0,
        "head_depth": 0.0,
        "skull_height": -0.38,
        "skull_width": 0.0,
        "skull_depth": 0.0,
        "skull_back_depth": -0.16,
        "skull_peak": -0.34,
    },
    {
        "id": "C07_BROAD_DEEP",
        "label": "Broad deep",
        "head_width": 0.36,
        "head_depth": 0.30,
        "skull_height": 0.0,
        "skull_width": 0.0,
        "skull_depth": 0.34,
        "skull_back_depth": 0.0,
        "skull_peak": 0.0,
    },
    {
        "id": "C08_NARROW_SHALLOW",
        "label": "Narrow shallow",
        "head_width": -0.36,
        "head_depth": -0.30,
        "skull_height": 0.0,
        "skull_width": -0.28,
        "skull_depth": 0.0,
        "skull_back_depth": 0.0,
        "skull_peak": 0.0,
    },
)

CHARACTERS = (
    {
        "prototype_id": "F_HS_002",
        "sex": "female",
        "base_avatar": (
            r"D:\CharacterCreator_sucai\Reallusion Templates\Actor\Character"
            r"\_Mixer Ready\Base\_HD Neutral F.ccAvatar"
        ),
        "source_project": (
            r"D:\UE\Lance_Work\00_engine\assets\character_creator"
            r"\face_prototypes\v1\F_HS_002\identity_cc5_hd.ccProject"
        ),
        "source_sha256": (
            "0ae7d9b3ef7d5f5fcd17f4fab848870a813b9d0bc155db589269eca3f665e638"
        ),
    },
    {
        "prototype_id": "M_HS_002",
        "sex": "male",
        "base_avatar": (
            r"D:\CharacterCreator_sucai\Reallusion Templates\Actor\Character"
            r"\_Mixer Ready\Base\_HD Neutral M.ccAvatar"
        ),
        "source_project": (
            r"D:\UE\Lance_Work\00_engine\assets\character_creator"
            r"\face_prototypes\v1\M_HS_002\identity_cc5_hd.ccProject"
        ),
        "source_sha256": (
            "62f263c8f30a34ce7fa82c5c4a395ccd9c9bc012df992e615b885ee78370a4d4"
        ),
    },
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_axes(policy):
    axes = {}
    for axis in policy.get("axes") or []:
        axes[axis["parameter_key"]] = axis
    if set(axes) != set(AXIS_ORDER):
        raise RuntimeError("Safe-range policy does not define the expected seven axes")
    return axes


def profile_metrics(profile, axes):
    normalized = []
    for key in AXIS_ORDER:
        value = float(profile[key])
        if abs(value) <= 1e-9:
            continue
        axis = axes[key]
        limit = float(axis["maximum"] if value > 0.0 else abs(axis["minimum"]))
        normalized.append(abs(value) / limit)
    return {
        "active_axis_count": len(normalized),
        "normalized_l1": sum(normalized),
        "normalized_l2": math.sqrt(sum(value * value for value in normalized)),
    }


def validate_profiles(profiles, axes):
    profile_ids = [profile["id"] for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise RuntimeError("Candidate profile IDs must be unique")
    if profiles[0]["id"] != "C00_BASELINE":
        raise RuntimeError("The first candidate must be C00_BASELINE")

    metrics = {}
    for profile in profiles:
        missing = set(AXIS_ORDER) - set(profile)
        if missing:
            raise RuntimeError(
                "{} is missing axes: {}".format(profile["id"], sorted(missing))
            )
        for key in AXIS_ORDER:
            value = float(profile[key])
            axis = axes[key]
            if value < float(axis["minimum"]) or value > float(axis["maximum"]):
                raise RuntimeError(
                    "{} {}={} is outside [{}, {}]".format(
                        profile["id"],
                        key,
                        value,
                        axis["minimum"],
                        axis["maximum"],
                    )
                )
        result = profile_metrics(profile, axes)
        if result["active_axis_count"] > MAX_ACTIVE_AXES:
            raise RuntimeError("{} activates too many axes".format(profile["id"]))
        if result["normalized_l1"] > MAX_NORMALIZED_L1 + 1e-9:
            raise RuntimeError("{} exceeds normalized L1 gate".format(profile["id"]))
        if result["normalized_l2"] > MAX_NORMALIZED_L2 + 1e-9:
            raise RuntimeError("{} exceeds normalized L2 gate".format(profile["id"]))
        metrics[profile["id"]] = result

    if any(abs(float(profiles[0][key])) > 1e-9 for key in AXIS_ORDER):
        raise RuntimeError("C00_BASELINE must keep every skull axis at zero")
    return metrics


def review_block(profile, axes):
    active_keys = [key for key in AXIS_ORDER if abs(float(profile[key])) > 1e-9]
    driver_key = active_keys[0] if active_keys else AXIS_ORDER[0]
    return {
        "head_scale": {
            "morph_id": HEAD_SCALE_ID,
            "target": 0.0,
        },
        "fixed_morphs": [
            {
                "morph_id": axes[key]["morph_id"],
                "target": float(profile[key]),
            }
            for key in AXIS_ORDER
            if key != driver_key
        ],
        "morphs": [
            {
                "morph_id": axes[driver_key]["morph_id"],
                "review_id": profile["id"].lower(),
                "values": [float(profile[driver_key])],
            }
        ],
        "views": [
            {"view_id": "front", "yaw_degrees": 0.0},
            {"view_id": "three_quarter", "yaw_degrees": 45.0},
            {"view_id": "profile", "yaw_degrees": 90.0},
        ],
    }


def build_preset(character, profile, axes, metrics):
    return {
        "preset_id": "{}_{}".format(character["prototype_id"], profile["id"]),
        "sex": character["sex"],
        "base_avatar": {"path": character["base_avatar"]},
        "source_project": {
            "path": character["source_project"],
            "sha256": character["source_sha256"],
        },
        "head_shape_profile": dict(profile),
        "composition_metrics": {
            "active_axis_count": metrics["active_axis_count"],
            "normalized_l1": round(metrics["normalized_l1"], 6),
            "normalized_l2": round(metrics["normalized_l2"], 6),
        },
        "neck_morph_review": review_block(profile, axes),
    }


def validate_sources(characters=CHARACTERS):
    for character in characters:
        for key in ("base_avatar", "source_project"):
            if not os.path.isfile(character[key]):
                raise RuntimeError("Missing {}: {}".format(key, character[key]))
        actual = sha256_file(character["source_project"])
        if actual != character["source_sha256"]:
            raise RuntimeError(
                "Source project hash changed for {}".format(
                    character["prototype_id"]
                )
            )


def build_library(safe_range_path=DEFAULT_SAFE_RANGES):
    safe_policy = read_json(safe_range_path)
    if not safe_policy.get("composition_policy", {}).get(
        "single_axis_ranges_approved"
    ):
        raise RuntimeError("Single-axis safe ranges are not approved")
    axes = safe_axes(safe_policy)
    metrics = validate_profiles(PROFILES, axes)
    presets = [
        build_preset(character, profile, axes, metrics[profile["id"]])
        for character in CHARACTERS
        for profile in PROFILES
    ]
    return {
        "schema_version": 1,
        "library_id": "cc_headshot_skull_composition_candidates_v1",
        "diagnostic_mode": "targeted_morph_visual_matrix",
        "preview_capture_mode": "render_image",
        "preview_resolution": [1536, 1536],
        "inter_case_delay_seconds": 4.0,
        "targeted_morph_review_scene": {
            "preview_lightroom": (
                r"D:\CharacterCreator_sucai\Reallusion Templates\Stage"
                r"\Light Room\Default\Default_CC5.ccLightroom"
            ),
            "face_camera_by_sex": {
                "female": (
                    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage"
                    r"\Camera\Headshot Ref\Ref Cam Female L.ccCam"
                ),
                "male": (
                    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage"
                    r"\Camera\Headshot Ref\Ref Cam Male L.ccCam"
                ),
            },
            "face_position_by_sex": {
                "female": [0.0, 8.0, 6.0],
                "male": [0.0, 8.0, 6.0],
            },
            "views": [
                {"view_id": "front", "yaw_degrees": 90.0},
                {"view_id": "three_quarter", "yaw_degrees": 45.0},
                {"view_id": "profile", "yaw_degrees": 0.0},
            ],
        },
        "composition_candidate_policy": {
            "purpose": "select-up-to-three-variants-plus-baseline",
            "canonical_projects_are_read_only": True,
            "safe_range_policy": safe_range_path,
            "safe_range_policy_sha256": sha256_file(safe_range_path),
            "candidate_profile_count": len(PROFILES),
            "final_profile_budget": 4,
            "baseline_included_in_final_budget": True,
            "max_active_axes": MAX_ACTIVE_AXES,
            "max_normalized_l1": MAX_NORMALIZED_L1,
            "max_normalized_l2": MAX_NORMALIZED_L2,
            "production_approved": False,
            "selection_requires_human_review": True,
        },
        "presets": presets,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build constrained Headshot skull-profile candidates"
    )
    parser.add_argument("--safe-ranges", default=DEFAULT_SAFE_RANGES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-source-validation", action="store_true")
    args = parser.parse_args()
    safe_range_path = os.path.realpath(os.path.abspath(args.safe_ranges))
    if not args.skip_source_validation:
        validate_sources()
    library = build_library(safe_range_path)
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(library, output_path)
    print(output_path)
    print("presets={}".format(len(library["presets"])))
    print(
        "candidate_profiles={}".format(
            library["composition_candidate_policy"]["candidate_profile_count"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
