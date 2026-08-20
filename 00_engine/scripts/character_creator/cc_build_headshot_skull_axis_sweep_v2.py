"""Build the Headshot skull single-axis range-discovery matrix."""

import argparse
import hashlib
import json
import os


SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_ROOT,
    "cc_headshot_skull_axis_sweep_v2.json",
)

HEAD_SCALE_ID = "cc embed morphs/embed_full_head9"
AXES = (
    {
        "axis_id": "HEAD_WIDTH",
        "label": "Head Width",
        "parameter_key": "head_width",
        "morph_id": "2019-08-13-15-33-14_head width",
        "values": (-0.65, 0.65),
    },
    {
        "axis_id": "HEAD_DEPTH",
        "label": "Head Depth",
        "parameter_key": "head_depth",
        "morph_id": "2019-08-13-16-00-36_head depth",
        "values": (-0.60, 0.60),
    },
    {
        "axis_id": "SKULL_HEIGHT",
        "label": "Skull Height",
        "parameter_key": "skull_height",
        "morph_id": "2019-08-13-15-25-44_skull height",
        "values": (-0.65, 0.65),
    },
    {
        "axis_id": "SKULL_WIDTH",
        "label": "Skull Width",
        "parameter_key": "skull_width",
        "morph_id": "2019-08-13-15-26-49_skull width",
        "values": (-0.65, 0.65),
    },
    {
        "axis_id": "SKULL_DEPTH",
        "label": "Skull Depth",
        "parameter_key": "skull_depth",
        "morph_id": "2019-08-13-15-27-43_skull depth",
        "values": (-0.60, 0.60),
    },
    {
        "axis_id": "SKULL_BACK_DEPTH",
        "label": "Skull Back Depth",
        "parameter_key": "skull_back_depth",
        "morph_id": "2019-08-21-13-57-18_skull back depth",
        "values": (-0.70, 0.70),
    },
    {
        "axis_id": "SKULL_PEAK",
        "label": "Skull Peak",
        "parameter_key": "skull_peak",
        "morph_id": "2019-08-21-14-02-10_skull peak",
        "values": (-0.55, 0.55),
    },
)

CHARACTERS = (
    {
        "prefix": "F",
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
        "prefix": "M",
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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fixed_morphs(active_morph_id):
    return [
        {"morph_id": axis["morph_id"], "target": 0.0}
        for axis in AXES
        if axis["morph_id"] != active_morph_id
    ]


def review_block(axis, values):
    return {
        "head_scale": {
            "morph_id": HEAD_SCALE_ID,
            "target": 0.0,
        },
        "fixed_morphs": fixed_morphs(axis["morph_id"]),
        "morphs": [
            {
                "morph_id": axis["morph_id"],
                "review_id": axis["parameter_key"],
                "values": list(values),
            }
        ],
        "views": [
            {"view_id": "front", "yaw_degrees": 0.0},
            {"view_id": "three_quarter", "yaw_degrees": 45.0},
            {"view_id": "profile", "yaw_degrees": 90.0},
        ],
    }


def build_preset(character, axis, values, suffix):
    return {
        "preset_id": "{}_V2_{}".format(character["prototype_id"], suffix),
        "sex": character["sex"],
        "base_avatar": {"path": character["base_avatar"]},
        "source_project": {
            "path": character["source_project"],
            "sha256": character["source_sha256"],
        },
        "axis_sweep": {
            "axis_id": axis["axis_id"],
            "label": axis["label"],
            "parameter_key": axis["parameter_key"],
            "morph_id": axis["morph_id"],
            "values": list(values),
        },
        "neck_morph_review": review_block(axis, values),
    }


def validate_sources():
    for character in CHARACTERS:
        for key in ("base_avatar", "source_project"):
            path = character[key]
            if not os.path.isfile(path):
                raise RuntimeError("Missing {}: {}".format(key, path))
        actual = sha256_file(character["source_project"])
        if actual != character["source_sha256"]:
            raise RuntimeError(
                "Source project hash changed for {}".format(
                    character["prototype_id"]
                )
            )


def build_library():
    presets = []
    baseline_axis = AXES[0]
    for character in CHARACTERS:
        presets.append(
            build_preset(
                character,
                baseline_axis,
                (0.0,),
                "BASELINE",
            )
        )
        for axis in AXES:
            presets.append(
                build_preset(
                    character,
                    axis,
                    axis["values"],
                    axis["axis_id"],
                )
            )

    return {
        "schema_version": 1,
        "library_id": "cc_headshot_skull_axis_sweep_v2",
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
        "axis_sweep_policy": {
            "purpose": "visual-range-discovery-only",
            "canonical_projects_are_read_only": True,
            "composition": "single-axis-negative-baseline-positive",
            "case_count_per_sex": 15,
            "controlled_morphs": [axis["morph_id"] for axis in AXES],
            "excluded_domains": [
                "eyes",
                "eye sockets",
                "nose",
                "mouth",
                "jaw",
                "teeth",
            ],
        },
        "presets": presets,
    }


def write_json_atomic(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(
        description="Build the Headshot skull single-axis sweep v2 matrix"
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    validate_sources()
    library = build_library()
    output = os.path.realpath(os.path.abspath(args.output))
    write_json_atomic(library, output)
    print(
        "Created {} presets / {} visual cases -> {}".format(
            len(library["presets"]),
            30,
            output,
        )
    )


if __name__ == "__main__":
    main()
