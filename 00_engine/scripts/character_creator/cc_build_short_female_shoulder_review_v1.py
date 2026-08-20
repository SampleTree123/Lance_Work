"""Build the F05 shoulder-height fallback review library."""

import argparse
import json
import os

from cc_build_short_female_refinement_review_v1 import (
    DEFAULT_DECISIONS,
    DEFAULT_SOURCE,
    build,
    read_json,
    write_json,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR,
    "cc_short_female_shoulder_review_v1.json",
)
SHOULDER_REVIEWS = (
    {
        "morph_id": "2018-07-20-11-24-13_shoulder top adjust",
        "review_id": "shoulder_top_height_a",
        "values": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
    },
    {
        "morph_id": "2018-09-25-18-34-43_shoulder top peak",
        "review_id": "shoulder_top_height_b",
        "values": [0.0, 0.25, 0.5, 0.75, 1.0],
    },
)


def build_shoulder_review(source, decisions):
    document = build(source, decisions)
    document["library_id"] = "cc_short_female_shoulder_review_v1"
    preset = document["presets"][0]
    preset["character_id"] = "SHORT_FEMALE_SHOULDER_REVIEW"
    preset["preset_id"] = "SHORT_FEMALE_SHOULDER_REVIEW"
    preset["review_status"] = "pending-shoulder-height-review"
    preset["neck_morph_review"]["morphs"] = [
        dict(item) for item in SHOULDER_REVIEWS
    ]
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    document = build_shoulder_review(
        read_json(args.source),
        read_json(args.decisions),
    )
    output = os.path.realpath(os.path.abspath(args.output))
    write_json(document, output)
    print(
        json.dumps(
            {
                "output": output,
                "review_morph_count": len(SHOULDER_REVIEWS),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
