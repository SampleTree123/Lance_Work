"""Build the human-selected canonical Headshot skull-profile library."""

import argparse
import copy
import json
import os


SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CANDIDATES = os.path.join(
    SCRIPT_ROOT,
    "cc_headshot_skull_composition_candidates_v1.json",
)
DEFAULT_SELECTION = os.path.join(
    SCRIPT_ROOT,
    "cc_headshot_skull_profile_selection_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_ROOT,
    "cc_headshot_skull_profile_library_v1.json",
)

REQUIRED_DYNAMIC_POSES = (
    "blink_bilateral_front",
    "smile_subtle_front",
    "smile_medium_front",
    "smile_broad_front",
    "jaw_open_front",
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


def validate_selection(selection, candidate_profiles):
    profiles = selection.get("profiles") or []
    budget = int(selection.get("profile_budget", 0))
    if len(profiles) != budget or budget != 4:
        raise RuntimeError("Canonical Headshot profile selection must contain four entries")
    canonical_ids = [item.get("canonical_profile_id") for item in profiles]
    source_ids = [item.get("source_candidate_id") for item in profiles]
    if len(canonical_ids) != len(set(canonical_ids)):
        raise RuntimeError("Canonical Headshot profile IDs must be unique")
    if len(source_ids) != len(set(source_ids)):
        raise RuntimeError("Source Headshot candidate IDs must be unique")
    if canonical_ids[0] != "H00_BASELINE" or source_ids[0] != "C00_BASELINE":
        raise RuntimeError("H00_BASELINE must map to C00_BASELINE")
    missing = sorted(set(source_ids) - set(candidate_profiles))
    if missing:
        raise RuntimeError("Selected Headshot candidates are unavailable: {}".format(missing))
    if selection.get("production_approved"):
        raise RuntimeError("Selection cannot be production approved before remaining gates")
    return sorted(profiles, key=lambda item: int(item["order"]))


def canonicalize_preset(candidate, selection_entry):
    preset = copy.deepcopy(candidate)
    source_id = selection_entry["source_candidate_id"]
    canonical_id = selection_entry["canonical_profile_id"]
    if preset["head_shape_profile"]["id"] != source_id:
        raise RuntimeError("Candidate preset/profile mismatch for {}".format(source_id))
    preset["preset_id"] = "{}_{}".format(
        preset["preset_id"].split("_C", 1)[0],
        canonical_id,
    )
    preset["head_shape_profile"]["source_candidate_id"] = source_id
    preset["head_shape_profile"]["id"] = canonical_id
    preset["head_shape_profile"]["label"] = selection_entry["label"]
    preset["selection_provenance"] = {
        "selection_id": "cc_headshot_skull_profile_selection_v1",
        "source_candidate_id": source_id,
        "human_selected": True,
    }
    review = preset["neck_morph_review"]
    review["morphs"][0]["review_id"] = canonical_id.lower()
    return preset


def build_library(candidate_path=DEFAULT_CANDIDATES, selection_path=DEFAULT_SELECTION):
    candidates = read_json(candidate_path)
    selection = read_json(selection_path)
    by_profile_and_sex = {}
    candidate_profiles = set()
    for preset in candidates.get("presets") or []:
        profile_id = preset["head_shape_profile"]["id"]
        sex = preset["sex"]
        candidate_profiles.add(profile_id)
        key = (profile_id, sex)
        if key in by_profile_and_sex:
            raise RuntimeError("Duplicate Headshot candidate preset: {}".format(key))
        by_profile_and_sex[key] = preset
    selected = validate_selection(selection, candidate_profiles)
    dynamic_visual_review = (
        (selection.get("human_decision") or {}).get("dynamic_visual_review") or {}
    )
    dynamic_validation_complete = bool(
        dynamic_visual_review.get("accepted")
        and "project_seed_then_bodyfit_pilot"
        in (selection.get("remaining_gates") or [])
    )
    presets = []
    for sex in ("female", "male"):
        for entry in selected:
            key = (entry["source_candidate_id"], sex)
            if key not in by_profile_and_sex:
                raise RuntimeError("Missing selected Headshot candidate: {}".format(key))
            presets.append(canonicalize_preset(by_profile_and_sex[key], entry))
    return {
        "schema_version": 1,
        "library_id": "cc_headshot_skull_profile_library_v1",
        "diagnostic_mode": "targeted_morph_visual_matrix",
        "preview_capture_mode": candidates.get("preview_capture_mode", "render_image"),
        "preview_resolution": candidates.get("preview_resolution", [1536, 1536]),
        "inter_case_delay_seconds": candidates.get("inter_case_delay_seconds", 4.0),
        "targeted_morph_review_scene": copy.deepcopy(
            candidates["targeted_morph_review_scene"]
        ),
        "targeted_morph_dynamic_pose_review": {
            "enabled": True,
            "profile": "cc5_hd_tiered_natural_smile_v1",
            "required_pose_ids": list(REQUIRED_DYNAMIC_POSES),
            "require_neutral_eye_integrity": True,
            "require_evidence_liveness": True,
            "require_controlled_morphs_unchanged": True,
        },
        "canonical_profile_policy": {
            "selection_file": os.path.realpath(selection_path),
            "selection_status": selection["status"],
            "profile_count": len(selected),
            "canonical_profile_ids": [
                item["canonical_profile_id"] for item in selected
            ],
            "shared_between_sexes": True,
            "human_static_selection_complete": True,
            "dynamic_validation_complete": dynamic_validation_complete,
            "production_approved": False,
        },
        "presets": presets,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build selected canonical Headshot skull profiles"
    )
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--selection", default=DEFAULT_SELECTION)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--selection-status-override")
    args = parser.parse_args()
    library = build_library(
        os.path.realpath(os.path.abspath(args.candidates)),
        os.path.realpath(os.path.abspath(args.selection)),
    )
    if args.selection_status_override:
        library["canonical_profile_policy"]["selection_status"] = (
            args.selection_status_override
        )
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(library, output_path)
    print(output_path)
    print("presets={}".format(len(library["presets"])))
    print(
        "canonical_profiles={}".format(
            library["canonical_profile_policy"]["profile_count"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
