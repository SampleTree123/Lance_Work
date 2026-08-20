"""Build a no-render height measurement matrix for all ten BodyFits."""

import argparse
import copy
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_LIBRARY_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_body_preset_library_v1.json",
)
SHORT_LIBRARY_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_short_bodyfit_candidates_v1.json",
)
DECISIONS_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_head_bodyfit_scale_decisions_v1.json",
)
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_bodyfit_height_matrix_v1.json",
)


class HeightBuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def build(short_head_scales, baseline=False):
    base_library = read_json(BASE_LIBRARY_PATH)
    short_library = read_json(SHORT_LIBRARY_PATH)
    decisions = read_json(DECISIONS_PATH)
    decision_by_id = dict(
        (item["bodyfit_id"], item)
        for item in decisions.get("selections") or []
    )
    head_scale_id = decisions["head_scale_morph"]["id"]
    presets = []
    all_bodies = list(base_library.get("presets") or []) + list(
        short_library.get("presets") or []
    )
    if len(all_bodies) != 10:
        raise HeightBuildError("Expected ten BodyFits")
    for body in all_bodies:
        bodyfit_id = body["preset_id"]
        measurement_morphs = []
        if baseline:
            pass
        elif bodyfit_id in decision_by_id:
            decision = decision_by_id[bodyfit_id]
            measurement_morphs.append(
                {
                    "display": decisions["head_scale_morph"]["display"],
                    "id": head_scale_id,
                    "target": float(decision["head_scale_weight"]),
                }
            )
            neck = decision.get("neck_adjustment")
            if neck:
                measurement_morphs.append(
                    {
                        "display": neck["display"],
                        "id": neck["morph_id"],
                        "target": float(neck["weight"]),
                    }
                )
        else:
            if bodyfit_id not in short_head_scales:
                raise HeightBuildError(
                    "Short BodyFit Head Scale is missing: {}".format(
                        bodyfit_id
                    )
                )
            measurement_morphs.append(
                {
                    "display": decisions["head_scale_morph"]["display"],
                    "id": head_scale_id,
                    "target": float(short_head_scales[bodyfit_id]),
                }
            )
        presets.append(
            {
                "base_avatar": copy.deepcopy(body["base_avatar"]),
                "preset_id": bodyfit_id,
                "sex": body["sex"],
                "body_class": body["body_class"],
                "source_project": copy.deepcopy(body["source_project"]),
                "measurement_morphs": measurement_morphs,
            }
        )
    return {
        "schema_version": 1,
        "library_id": "adult_bodyfit_height_matrix_v1",
        "diagnostic_mode": "targeted_bodyfit_height_matrix",
        "generated_at": now(),
        "measurement_policy": {
            "baseline_source_projects_only": bool(baseline),
            "coordinate_space": "world",
            "formula": "avatar_bounds.maximum_z - avatar_bounds.minimum_z",
            "unit": "cm",
            "includes_selected_head_and_neck_bodyfit_adjustments": (
                not baseline
            ),
        },
        "presets": presets,
        "status": "measurement-ready",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--male-short-head-scale", type=float, default=0.0)
    parser.add_argument("--female-short-head-scale", type=float, default=0.0)
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    short_head_scales = {
        "M05_Short_Average": args.male_short_head_scale,
        "F05_Short_Average": args.female_short_head_scale,
    }
    document = build(short_head_scales, baseline=args.baseline)
    output_path = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "output": output_path,
                "preset_count": len(document["presets"]),
                "baseline": args.baseline,
                "short_head_scales": short_head_scales,
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
