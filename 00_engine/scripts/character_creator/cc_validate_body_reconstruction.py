"""Rebuild canonical BodyFit presets on clean CC5 neutral bases and validate them."""

import collections
import datetime
import hashlib
import json
import math
import os
import struct
import subprocess
import time
import traceback

import RLPy
from PySide2 import QtCore, QtWidgets


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DEFAULT_LIBRARY = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v1.json")
DEFAULT_FACE_SEED_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_face_seed_library_v1.json"
)
DEFAULT_FACE_IDENTITY_POLICY = os.path.join(
    SCRIPT_DIR, "cc_face_identity_policy_v1.json"
)
OUTPUT_ROOT = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_body_reconstruction"
)
REPLACE_DIALOG_GUARD_PATH = os.path.join(
    ENGINE_ROOT,
    "character_creator_bridge",
    "cc_replace_dialog_once.ps1",
)
REPLACE_DIALOG_GUARD_OUTPUT_ROOT = os.path.join(
    ENGINE_ROOT,
    "outputs",
    "character_creator_bridge",
    "dialog_guard",
)

FACE_TERMS = (
    "head", "face", "eye", "brow", "nose", "mouth", "lip", "jaw",
    "chin", "cheek", "ear", "forehead", "teeth", "tongue",
    "expression", "viseme",
)
BODY_TERMS = (
    "body", "torso", "chest", "breast", "shoulder", "arm", "elbow",
    "hand", "waist", "abdomen", "belly", "stomach", "hip", "pelvis",
    "butt", "glute", "leg", "thigh", "calf", "foot", "feet", "muscle",
    "fat", "height", "scale", "proportion", "ratio",
)
JUNCTION_TERMS = ("neck", "clavicle", "collar")

MATERIAL_VERIFICATION_SLOTS = frozenset(
    ("skin", "skin_preset", "makeup", "eyes", "teeth")
)
SCENE_VERIFICATION_SLOTS = frozenset(
    (
        "underwear",
        "full_body",
        "upper",
        "lower",
        "outerwear",
        "footwear",
        "gloves",
        "scalp_hair",
        "eyebrows",
        "eyelashes",
        "facial_hair",
        "accessory_head",
        "accessory_torso",
        "accessory_arm",
        "accessory_leg",
        "accessory_other",
        "clothing_other",
    )
)
APPEARANCE_SLOT_ORDER = {
    "skin": 10,
    "skin_preset": 20,
    "makeup": 30,
    "eyes": 40,
    "teeth": 50,
    "underwear": 100,
    "full_body": 110,
    "upper": 120,
    "lower": 130,
    "outerwear": 140,
    "footwear": 150,
    "gloves": 160,
    "clothing_other": 170,
    "scalp_hair": 180,
    "eyebrows": 190,
    "eyelashes": 200,
    "facial_hair": 210,
    "accessory_head": 220,
    "accessory_torso": 230,
    "accessory_arm": 240,
    "accessory_leg": 250,
    "accessory_other": 260,
}
MATERIAL_TEXTURE_CHANNELS = (
    ("diffuse", "EMaterialTextureChannel_Diffuse"),
    ("normal", "EMaterialTextureChannel_Normal"),
    ("roughness", "EMaterialTextureChannel_Roughness"),
    ("specular", "EMaterialTextureChannel_Specular"),
    ("metallic", "EMaterialTextureChannel_Metallic"),
    ("ambient_occlusion", "EMaterialTextureChannel_AmbientOcclusion"),
    ("opacity", "EMaterialTextureChannel_Opacity"),
    ("bump", "EMaterialTextureChannel_Bump"),
    ("displacement", "EMaterialTextureChannel_Displacement"),
    ("glow", "EMaterialTextureChannel_Glow"),
)
BODY_APPLICATION_MODES = frozenset(("raw_morph_weights", "source_project"))
EYEBALL_MOVE_MORPH_ID = "cc embed morphs/embed_eye9"
TEETH_VISIBILITY_PROFILE = "teeth_visibility_v1"
EYE_VISIBILITY_PROFILE = "eye_visibility_v1"
EYEBROW_VISIBILITY_PROFILE = "eyebrow_visibility_v1"
EYELASH_VISIBILITY_PROFILE = "eyelash_visibility_v1"
FACIAL_HAIR_VISIBILITY_PROFILE = "facial_hair_visibility_v1"
SCALP_HAIR_VISIBILITY_PROFILE = "scalp_hair_visibility_v1"
SCALP_HAIR_VIEW_Y_OFFSETS = {
    "profile": 0.0,
    "three_quarter": 4.0,
    "front": 8.0,
    "rear_three_quarter": -4.0,
    "rear": -8.0,
}
FACE_IDENTITY_SAFETY_PROFILE = "face_identity_safety_v1"
FACE_IDENTITY_POSE_OFFSET_FRAMES = 10
FACE_IDENTITY_CLIP_LENGTH_FRAMES = 40
RENDER_PREVIEW_SETTLE_SECONDS = 0.25
RENDER_PREVIEW_STABLE_SECONDS = 0.20
RENDER_PREVIEW_TIMEOUT_SECONDS = 60.0
VIEWPORT_PREVIEW_WIDTH = 512
VIEWPORT_PREVIEW_HEIGHT = 512
FACE_EVIDENCE_MIN_RMSE = 0.35
COMPLETE_PRIMARY_FACE_PIPELINE = (
    "complete_primary_face_plus_local_morphs_v1"
)
TEETH_EXPRESSION_ALIASES = {
    "jaw_open": (
        "Jaw_Open",
        "Mouth_Jaw_Open",
        "Mouth_Open",
        "Jaw Open",
        "Mouth Open",
    ),
    "smile": (
        "Mouth_Smile",
        "Mouth_Smile_Both",
        "Smile",
    ),
    "smile_left": (
        "Mouth_Smile_L",
        "Mouth_Corner_Pull_L",
        "Mouth_CornerPull_L",
        "Mouth Smile Left",
    ),
    "smile_right": (
        "Mouth_Smile_R",
        "Mouth_Corner_Pull_R",
        "Mouth_CornerPull_R",
        "Mouth Smile Right",
    ),
    "upper_lip_raise_left": (
        "Mouth_UpperLip_Raise_L",
        "Mouth_Upper_Lip_Raise_L",
    ),
    "upper_lip_raise_right": (
        "Mouth_UpperLip_Raise_R",
        "Mouth_Upper_Lip_Raise_R",
    ),
    "lower_lip_depress_left": (
        "Mouth_LowerLip_Depress_L",
        "Mouth_Lower_Lip_Depress_L",
    ),
    "lower_lip_depress_right": (
        "Mouth_LowerLip_Depress_R",
        "Mouth_Lower_Lip_Depress_R",
    ),
    "stretch_left": (
        "Mouth_Stretch_L",
        "Mouth_StretchLeft",
    ),
    "stretch_right": (
        "Mouth_Stretch_R",
        "Mouth_StretchRight",
    ),
}
TEETH_MORPH_TERMS = ("teeth", "tongue", "gum")
EYE_EXPRESSION_ALIASES = {
    "look_left_left": (
        "Eye_Look_Left_L",
        "Eye_LookLeft_L",
    ),
    "look_left_right": (
        "Eye_Look_Left_R",
        "Eye_LookLeft_R",
    ),
    "look_right_left": (
        "Eye_Look_Right_L",
        "Eye_LookRight_L",
    ),
    "look_right_right": (
        "Eye_Look_Right_R",
        "Eye_LookRight_R",
    ),
    "look_up_left": (
        "Eye_Look_Up_L",
        "Eye_LookUp_L",
    ),
    "look_up_right": (
        "Eye_Look_Up_R",
        "Eye_LookUp_R",
    ),
    "look_down_left": (
        "Eye_Look_Down_L",
        "Eye_LookDown_L",
    ),
    "look_down_right": (
        "Eye_Look_Down_R",
        "Eye_LookDown_R",
    ),
}
EYEBROW_EXPRESSION_ALIASES = {
    "down_left": ("Brow_Down_L",),
    "down_right": ("Brow_Down_R",),
    "raise_inner_left": ("Brow_Raise_In_L",),
    "raise_inner_right": ("Brow_Raise_In_R",),
    "raise_outer_left": ("Brow_Raise_Outer_L",),
    "raise_outer_right": ("Brow_Raise_Outer_R",),
}
EYELASH_EXPRESSION_ALIASES = {
    "blink_left": ("Eye_Blink_L", "Blink_L"),
    "blink_right": ("Eye_Blink_R", "Blink_R"),
    "blink_corrective_left": ("C_BlinkL",),
    "blink_corrective_right": ("C_BlinkR",),
    "widen_left": ("Eye_Widen_L", "Widen_L"),
    "widen_right": ("Eye_Widen_R", "Widen_R"),
    "lash_down_inner_left": ("Eyelashes_Down_IN_L",),
    "lash_down_outer_left": ("Eyelashes_Down_OUT_L",),
    "lash_down_inner_right": ("Eyelashes_Down_IN_R",),
    "lash_down_outer_right": ("Eyelashes_Down_OUT_R",),
    "lash_up_inner_left": ("Eyelashes_Up_IN_L",),
    "lash_up_outer_left": ("Eyelashes_Up_OUT_L",),
    "lash_up_inner_right": ("Eyelashes_Up_IN_R",),
    "lash_up_outer_right": ("Eyelashes_Up_OUT_R",),
}
REPLACEABLE_AVATAR_PART_SLOTS = {
    "eyes": "EAvatarPartType_Eyes",
    "teeth": "EAvatarPartType_Teeth",
    "eyebrows": "EAvatarPartType_Brow",
    "eyelashes": "EAvatarPartType_Eyelash",
    "facial_hair": "EAvatarPartType_Beard",
}
DUAL_REPRESENTATION_AVATAR_PART_SLOTS = frozenset(("facial_hair",))
MATERIAL_ONLY_DIALOG_SLOTS = frozenset(("eyes",))
CHARACTER_PRESET_DIALOG_SLOTS = frozenset(("eyelashes",))
FACIAL_ASSEMBLY_ORDER = (
    "skin",
    "age_morph",
    "dynamic_wrinkle_profile",
    "teeth",
    "eyebrows",
    "eyelashes",
    "eyes_material_only",
    "facial_hair",
    "scalp_hair",
    "shared_hair_pigmentation",
)
WRINKLE_FACE_PART_CONSTANTS = (
    "EWrinkleFacePart_Blink",
    "EWrinkleFacePart_BrowDrop",
    "EWrinkleFacePart_BrowRaise",
    "EWrinkleFacePart_Cheek",
    "EWrinkleFacePart_Chin",
    "EWrinkleFacePart_Jaw",
    "EWrinkleFacePart_MouthStretch",
    "EWrinkleFacePart_Neck",
    "EWrinkleFacePart_Nose",
    "EWrinkleFacePart_PurseLips",
    "EWrinkleFacePart_Smile",
    "EWrinkleFacePart_Squint",
    "EWrinkleFacePart_Sneer",
)
DYNAMIC_WRINKLE_POSE_ARTIFACT_KEYS = {
    "blink_bilateral_front": (
        "face_blink_bilateral_preview",
        "dynamic_wrinkle_baseline_blink_bilateral_preview",
    ),
    "brow_raise_front": (
        "face_brow_raise_preview",
        "dynamic_wrinkle_baseline_brow_raise_preview",
    ),
    "brow_down_front": (
        "face_brow_down_preview",
        "dynamic_wrinkle_baseline_brow_down_preview",
    ),
    "squint_bilateral_front": (
        "face_squint_preview",
        "dynamic_wrinkle_baseline_squint_preview",
    ),
    "smile_front": (
        "face_smile_preview",
        "dynamic_wrinkle_baseline_smile_preview",
    ),
}
SMART_HAIR_SHADER = "Digital_Human Hair"
SMART_HAIR_COLOR_PARAMETERS = {
    "root_srgb": "RootColor",
    "end_srgb": "TipColor",
    "highlight_a_srgb": "_1st Dye Color",
    "highlight_b_srgb": "_2nd Dye Color",
}
SMART_HAIR_SCALAR_PARAMETERS = {
    "ActiveChangeHairColor": 1.0,
    "RootColorStrength": 1.0,
    "TipColorStrength": 1.0,
    "UseRootTipColor": 1.0,
    "_1st Dye Strength": 0.35,
    "_2nd Dye Strength": 0.35,
}


class ReconstructionError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_existing_file(path, label):
    if not isinstance(path, str) or not path:
        raise ReconstructionError("{} path must be a non-empty string".format(label))
    resolved = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(resolved):
        raise ReconstructionError("{} is missing: {}".format(label, resolved))
    return resolved


def require_file_extension(path, expected_extension, label):
    if os.path.splitext(path)[1].lower() != expected_extension.lower():
        raise ReconstructionError(
            "{} must use the {} file type".format(
                label, expected_extension
            )
        )
    return path


def is_actor_part_morph_entry(item):
    categories = [
        str(value).replace("\\", "/").strip().lower()
        for value in (item.get("categories") or [])
    ]
    return any(
        category == "actor parts"
        or category.startswith("actor parts/")
        for category in categories
    )


def is_head_geometry_actor_part_morph_entry(item):
    categories = [
        str(value).replace("\\", "/").strip().lower()
        for value in (item.get("categories") or [])
    ]
    return any(
        category == "actor parts/cc_base_eye"
        or category.startswith("actor parts/cc_base_eye/")
        or category == "actor parts/cc_base_teeth"
        or category.startswith("actor parts/cc_base_teeth/")
        for category in categories
    )


def require_matching_content_reference(
    manifest_reference,
    expected_path,
    expected_hash,
    label,
    application_mode=None,
    policy_binding=None,
):
    if not isinstance(manifest_reference, dict):
        raise ReconstructionError(
            "{} must be explicit in the character manifest".format(label)
        )
    manifest_path = canonical_existing_file(
        manifest_reference.get("path"), label
    )
    if (
        os.path.normcase(manifest_path)
        != os.path.normcase(expected_path)
        or manifest_reference.get("sha256") != expected_hash
    ):
        raise ReconstructionError(
            "{} differs from the primary seed policy".format(label)
        )
    if (
        application_mode is not None
        and manifest_reference.get("application_mode")
        != application_mode
    ):
        raise ReconstructionError(
            "{} application mode differs from policy".format(label)
        )
    if (
        policy_binding is not None
        and manifest_reference.get("policy_binding")
        != policy_binding
    ):
        raise ReconstructionError(
            "{} binding differs from policy".format(label)
        )


def resolve_face_application_context(library, preset):
    generation = preset.get("face_generation")
    if not isinstance(generation, dict):
        raise ReconstructionError(
            "Eye-safe face reconstruction requires face_generation metadata"
        )
    primary_seed_id = generation.get("primary_seed_id")
    if not isinstance(primary_seed_id, str) or not primary_seed_id:
        raise ReconstructionError(
            "Eye-safe face reconstruction requires primary_seed_id"
        )

    resources = library.get("face_resources") or {}
    if not isinstance(resources, dict):
        raise ReconstructionError("face_resources must be an object")
    seed_library_path = canonical_existing_file(
        resources.get("seed_library", DEFAULT_FACE_SEED_LIBRARY),
        "Face seed library",
    )
    identity_policy_path = canonical_existing_file(
        resources.get("identity_policy", DEFAULT_FACE_IDENTITY_POLICY),
        "Face identity policy",
    )
    seed_library = read_json(seed_library_path)
    identity_policy = read_json(identity_policy_path)

    seeds = seed_library.get("seeds") or []
    seed_index = dict(
        (item.get("seed_id"), item)
        for item in seeds
        if isinstance(item, dict) and isinstance(item.get("seed_id"), str)
    )
    primary_seed = seed_index.get(primary_seed_id)
    if primary_seed is None:
        raise ReconstructionError(
            "Primary face seed is missing: {}".format(primary_seed_id)
        )
    sex = preset.get("sex")
    if primary_seed.get("sex") != sex:
        raise ReconstructionError(
            "Primary face seed sex mismatch: {} expected={} actual={}".format(
                primary_seed_id, sex, primary_seed.get("sex")
            )
        )

    source_head_preset = primary_seed.get("source_head_preset") or {}
    source_head_preset_path = canonical_existing_file(
        source_head_preset.get("path"),
        "Primary face head preset",
    )
    pipeline = generation.get("pipeline")
    if pipeline is not None and pipeline != COMPLETE_PRIMARY_FACE_PIPELINE:
        raise ReconstructionError(
            "Unsupported face generation pipeline: {}".format(pipeline)
        )
    profile_policy = {}
    profile_policy_binding = None
    source_facial_profile = None
    source_facial_profile_path = None
    if pipeline == COMPLETE_PRIMARY_FACE_PIPELINE:
        profile_policy = (
            seed_library.get("facial_profile_policy") or {}
        )
        profile_defaults = profile_policy.get("default_by_sex") or {}
        profile_overrides = profile_policy.get("seed_overrides") or {}
        if primary_seed_id in profile_overrides:
            source_facial_profile = profile_overrides[primary_seed_id]
            profile_policy_binding = "seed_override"
        else:
            source_facial_profile = profile_defaults.get(sex)
            profile_policy_binding = "default_by_sex"
        if not isinstance(source_facial_profile, dict):
            raise ReconstructionError(
                "Primary face seed has no Facial Profile policy: {}".format(
                    primary_seed_id
                )
            )
        source_facial_profile_path = canonical_existing_file(
            source_facial_profile.get("path"),
            "Primary face Facial Profile",
        )
        require_file_extension(
            source_facial_profile_path,
            ".ccFacialProfile",
            "Primary face Facial Profile",
        )

    approved_morphs = identity_policy.get("approved_morphs") or []
    approved_by_id = dict(
        (item.get("id"), item)
        for item in approved_morphs
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
    )
    if len(approved_by_id) != len(approved_morphs):
        raise ReconstructionError(
            "Identity policy approved Morph IDs are invalid"
        )

    if pipeline == COMPLETE_PRIMARY_FACE_PIPELINE:
        neutral_ids = set(
            (identity_policy.get("neutral_policy") or {}).get(
                "neutral_seed_ids"
            )
            or []
        )
        if (
            primary_seed_id in neutral_ids
            or "neutral" in primary_seed_id.lower()
        ):
            raise ReconstructionError(
                "Neutral face seed cannot be a production primary"
            )
        expected_source_hash = source_head_preset.get("sha256")
        if (
            not isinstance(expected_source_hash, str)
            or len(expected_source_hash) != 64
        ):
            raise ReconstructionError(
                "Primary face head preset has no valid SHA256"
            )
        actual_source_hash = sha256_file(source_head_preset_path)
        if actual_source_hash != expected_source_hash:
            raise ReconstructionError(
                "Primary face head preset hash changed"
            )
        expected_profile_hash = source_facial_profile.get("sha256")
        if (
            not isinstance(expected_profile_hash, str)
            or len(expected_profile_hash) != 64
        ):
            raise ReconstructionError(
                "Primary face Facial Profile has no valid SHA256"
            )
        actual_profile_hash = sha256_file(
            source_facial_profile_path
        )
        if actual_profile_hash != expected_profile_hash:
            raise ReconstructionError(
                "Primary face Facial Profile hash changed"
            )
        profile_application_mode = profile_policy.get(
            "application_mode"
        )
        if (
            profile_application_mode
            != "selected_avatar_content_load"
        ):
            raise ReconstructionError(
                "Unsupported primary Facial Profile application mode"
            )
        require_matching_content_reference(
            preset.get("source_head_preset"),
            source_head_preset_path,
            expected_source_hash,
            "Primary face head preset",
        )
        require_matching_content_reference(
            preset.get("source_facial_profile"),
            source_facial_profile_path,
            expected_profile_hash,
            "Primary face Facial Profile",
            application_mode=profile_application_mode,
            policy_binding=profile_policy_binding,
        )

        if preset.get("target_face_morphs") is not None:
            raise ReconstructionError(
                "V3 face recipes must not contain target_face_morphs"
            )
        local_morphs = preset.get("local_face_morphs")
        if not isinstance(local_morphs, list):
            raise ReconstructionError(
                "V3 face recipes require local_face_morphs"
            )
        local_ids = [
            item.get("id")
            for item in local_morphs
            if isinstance(item, dict)
        ]
        if (
            len(local_ids) != len(local_morphs)
            or any(not isinstance(item, str) or not item for item in local_ids)
            or len(local_ids) != len(set(local_ids))
        ):
            raise ReconstructionError(
                "V3 local face Morph IDs are invalid or duplicated"
            )
        unapproved = sorted(set(local_ids) - set(approved_by_id))
        if unapproved:
            raise ReconstructionError(
                "V3 face recipe contains unapproved local Morphs: {}".format(
                    unapproved
                )
            )

        primary_seed_targets = (
            primary_seed.get("target_face_morphs") or []
        )
        primary_vector = {
            item["id"]: float(item["weight"])
            for item in primary_seed_targets
        }
        for item in local_morphs:
            morph_id = item["id"]
            try:
                baseline = float(item["baseline_weight"])
                target = float(item["weight"])
            except Exception:
                raise ReconstructionError(
                    "V3 local face Morph weights are invalid: {}".format(
                        morph_id
                    )
                )
            if not math.isfinite(baseline) or not math.isfinite(target):
                raise ReconstructionError(
                    "V3 local face Morph weights must be finite"
                )
            expected_baseline = float(primary_vector.get(morph_id, 0.0))
            if abs(baseline - expected_baseline) > 1e-6:
                raise ReconstructionError(
                    "V3 local Morph baseline differs from primary seed: "
                    "{} expected={} recipe={}".format(
                        morph_id, expected_baseline, baseline
                    )
                )

        seed_metadata_by_id = {}
        primary_identity_ids = set()
        for seed in seeds:
            if not isinstance(seed, dict) or seed.get("sex") != sex:
                continue
            for item in seed.get("target_face_morphs") or []:
                if isinstance(item, dict) and isinstance(
                    item.get("id"), str
                ):
                    seed_metadata_by_id.setdefault(item["id"], item)
                    if not is_actor_part_morph_entry(item):
                        primary_identity_ids.add(item["id"])
            for item in seed.get("face_delta") or []:
                if isinstance(item, dict) and isinstance(
                    item.get("id"), str
                ):
                    metadata = seed_metadata_by_id.get(item["id"])
                    if (
                        metadata is not None
                        and not is_actor_part_morph_entry(metadata)
                    ):
                        primary_identity_ids.add(item["id"])

        primary_expected_by_id = {}
        primary_support_targets = []
        for item in primary_seed_targets:
            if is_actor_part_morph_entry(item):
                primary_support_targets.append(item)
                continue
            primary_expected_by_id[item["id"]] = {
                "id": item["id"],
                "weight": float(item["weight"]),
            }
        for item in primary_seed.get("face_delta") or []:
            morph_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(morph_id, str) or not morph_id:
                raise ReconstructionError(
                    "Primary seed face_delta has an invalid Morph ID"
                )
            metadata = seed_metadata_by_id.get(morph_id)
            if metadata is None:
                raise ReconstructionError(
                    "Primary seed face_delta Morph lacks metadata: {}".format(
                        morph_id
                    )
                )
            if is_actor_part_morph_entry(metadata):
                continue
            try:
                before = float(item["before"])
                after = float(item["after"])
                delta = float(item["delta"])
            except Exception:
                raise ReconstructionError(
                    "Primary seed face_delta weights are invalid: {}".format(
                        morph_id
                    )
                )
            if (
                not all(math.isfinite(value) for value in (before, after, delta))
                or abs((after - before) - delta) > 1e-6
            ):
                raise ReconstructionError(
                    "Primary seed face_delta is inconsistent: {}".format(
                        morph_id
                    )
                )
            primary_expected_by_id[morph_id] = {
                "id": morph_id,
                "weight": after,
            }
            primary_identity_ids.add(morph_id)

        return {
            "mode": COMPLETE_PRIMARY_FACE_PIPELINE,
            "primary_seed_id": primary_seed_id,
            "source_head_preset": {
                "path": source_head_preset_path,
                "sha256": expected_source_hash,
            },
            "source_facial_profile": {
                "application_mode": profile_application_mode,
                "path": source_facial_profile_path,
                "policy_binding": profile_policy_binding,
                "sha256": expected_profile_hash,
            },
            "seed_library": {
                "path": seed_library_path,
                "library_id": seed_library.get("library_id"),
            },
            "identity_policy": {
                "path": identity_policy_path,
                "policy_id": identity_policy.get("policy_id"),
            },
            "modifiable_morph_ids": sorted(approved_by_id),
            "modified_morph_ids": sorted(local_ids),
            "primary_identity_morph_ids": sorted(
                primary_identity_ids
            ),
            "primary_expected_head_morphs": sorted(
                primary_expected_by_id.values(),
                key=lambda item: item["id"],
            ),
            "primary_support_target_morphs": primary_support_targets,
        }

    owned_ids = set()
    for item in approved_morphs:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            owned_ids.add(item["id"])
    for seed in seeds:
        if not isinstance(seed, dict) or seed.get("sex") != sex:
            continue
        for item in seed.get("target_face_morphs") or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                owned_ids.add(item["id"])

    target_ids = {
        item.get("id")
        for item in (preset.get("target_face_morphs") or [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    unowned_targets = sorted(target_ids - owned_ids)
    if unowned_targets:
        raise ReconstructionError(
            "Face recipe contains morphs outside identity ownership: {}".format(
                unowned_targets
            )
        )

    return {
        "mode": "primary_head_preset_then_identity_targets",
        "primary_seed_id": primary_seed_id,
        "source_head_preset": {
            "path": source_head_preset_path,
            "sha256": source_head_preset.get("sha256"),
        },
        "seed_library": {
            "path": seed_library_path,
            "library_id": seed_library.get("library_id"),
        },
        "identity_policy": {
            "path": identity_policy_path,
            "policy_id": identity_policy.get("policy_id"),
        },
        "owned_morph_ids": sorted(owned_ids),
        "owned_morph_count": len(owned_ids),
    }


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def checked(label, status):
    if status is None:
        return {"returned": False, "is_error": False}
    try:
        is_error = bool(status.IsError())
    except Exception:
        is_error = False
    detail = {"returned": True, "is_error": is_error}
    try:
        detail["status_code"] = str(status.GetStatusCode())
    except Exception:
        pass
    if is_error:
        raise ReconstructionError("{} failed: {}".format(label, detail))
    return detail


def classify(display, morph_id, categories):
    text = " ".join([display, morph_id] + categories).lower()
    if any(term in text for term in JUNCTION_TERMS):
        return "junction"
    if any(term in text for term in FACE_TERMS):
        return "face"
    if any(term in text for term in BODY_TERMS):
        return "body"
    return "other"


def vector_fingerprint(entries):
    canonical = json.dumps(
        [
            (item["id"], round(float(item["weight"]), 8))
            for item in sorted(entries, key=lambda value: value["id"])
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def float32_value(value):
    return struct.unpack("f", struct.pack("f", float(value)))[0]


def runtime_target_fingerprint(entries):
    return vector_fingerprint(
        [
            {"id": item["id"], "weight": float32_value(item["weight"])}
            for item in entries
        ]
    )


def morph_catalog(avatar):
    component = avatar.GetAvatarShapingComponent()
    if component is None:
        raise ReconstructionError("Avatar has no shaping component")
    catalog = {}
    categories = [
        str(item) for item in (component.GetShapingMorphCatergoryNames() or [])
    ]
    for category in categories:
        ids = list(component.GetShapingMorphIDs(category) or [])
        names = list(component.GetShapingMorphDisplayNames(category) or [])
        for index, raw_id in enumerate(ids):
            morph_id = str(raw_id)
            display = str(names[index] if index < len(names) else morph_id)
            item = catalog.setdefault(
                morph_id, {"id": morph_id, "display": display, "categories": []}
            )
            if category not in item["categories"]:
                item["categories"].append(category)
    for morph_id, item in catalog.items():
        item["classification"] = classify(
            item["display"], morph_id, item["categories"]
        )
    return component, catalog, categories


def capture_vectors(avatar):
    component, catalog, categories = morph_catalog(avatar)
    grouped = dict((name, []) for name in ("body", "junction", "face", "other"))
    for morph_id in sorted(catalog):
        try:
            weight = float(component.GetShapingMorphWeight(morph_id))
        except Exception:
            continue
        if abs(weight) <= 1e-8:
            continue
        source = catalog[morph_id]
        grouped[source["classification"]].append(
            {
                "id": morph_id,
                "display": source["display"],
                "categories": source["categories"],
                "classification": source["classification"],
                "weight": weight,
            }
        )
    groups = {}
    for name, entries in grouped.items():
        groups[name] = {
            "entries": entries,
            "nonzero_count": len(entries),
            "fingerprint_sha256": vector_fingerprint(entries),
        }
    body_and_junction = grouped["body"] + grouped["junction"]
    return {
        "catalog_morph_count": len(catalog),
        "category_count": len(categories),
        "groups": groups,
        "body_and_junction_nonzero_count": len(body_and_junction),
        "body_and_junction_fingerprint_sha256": vector_fingerprint(
            body_and_junction
        ),
    }


def vector_entries_for_ids(vectors, morph_ids):
    selected = set(morph_ids)
    entries = []
    for group in (vectors.get("groups") or {}).values():
        for item in group.get("entries") or []:
            if item.get("id") in selected:
                entries.append(item)
    return sorted(entries, key=lambda item: item["id"])


def unowned_entries(vectors, owned_morph_ids, classifications):
    owned = set(owned_morph_ids)
    entries = []
    for classification in classifications:
        group = (vectors.get("groups") or {}).get(classification) or {}
        for item in group.get("entries") or []:
            if item.get("id") not in owned:
                entries.append(item)
    return sorted(entries, key=lambda item: item["id"])


def head_preset_support_entries(vectors):
    entries = []
    for classification in ("face", "other"):
        group = (vectors.get("groups") or {}).get(classification) or {}
        for item in group.get("entries") or []:
            if (
                classification == "other"
                or item.get("id") == EYEBALL_MOVE_MORPH_ID
                or is_actor_part_morph_entry(item)
            ):
                entries.append(item)
    return sorted(entries, key=lambda item: item["id"])


def head_preset_identity_entries(vectors):
    group = (vectors.get("groups") or {}).get("face") or {}
    return sorted(
        [
            item
            for item in (group.get("entries") or [])
            if (
                item.get("id") != EYEBALL_MOVE_MORPH_ID
                and not is_actor_part_morph_entry(item)
            )
        ],
        key=lambda item: item["id"],
    )


def capture_body_catalog(avatar, base_avatar):
    component, catalog, unused_categories = morph_catalog(avatar)
    entries = []
    for morph_id in sorted(catalog):
        source = catalog[morph_id]
        if source["classification"] not in ("body", "junction"):
            continue
        bounds = component.GetShapingMorphMinMax(morph_id)
        entries.append(
            {
                "id": morph_id,
                "display": source["display"],
                "categories": source["categories"],
                "classification": source["classification"],
                "minimum": float(bounds.first),
                "maximum": float(bounds.second),
                "default_weight": float(component.GetShapingMorphWeight(morph_id)),
            }
        )
    canonical = json.dumps(
        [
            (
                item["id"],
                item["classification"],
                round(item["minimum"], 8),
                round(item["maximum"], 8),
                round(item["default_weight"], 8),
            )
            for item in entries
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return {
        "schema_version": 1,
        "captured_at": now(),
        "product": {
            "name": str(RLPy.RApplication.GetProductName()),
            "edition": str(RLPy.RApplication.GetProductEdition()),
            "version": str(RLPy.RApplication.GetProductVersion()),
            "api_version": str(RLPy.RApplication.GetApiVersion()),
        },
        "base_avatar": base_avatar,
        "body_and_junction_morph_count": len(entries),
        "body_morph_count": sum(item["classification"] == "body" for item in entries),
        "junction_morph_count": sum(
            item["classification"] == "junction" for item in entries
        ),
        "catalog_fingerprint_sha256": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest(),
        "entries": entries,
    }


def capture_face_catalog(avatar, base_avatar):
    component, catalog, unused_categories = morph_catalog(avatar)
    entries = []
    for morph_id in sorted(catalog):
        source = catalog[morph_id]
        if source["classification"] != "face":
            continue
        bounds = component.GetShapingMorphMinMax(morph_id)
        entries.append(
            {
                "id": morph_id,
                "display": source["display"],
                "categories": source["categories"],
                "classification": source["classification"],
                "minimum": float(bounds.first),
                "maximum": float(bounds.second),
                "default_weight": float(component.GetShapingMorphWeight(morph_id)),
            }
        )
    canonical = json.dumps(
        [
            (
                item["id"],
                round(item["minimum"], 8),
                round(item["maximum"], 8),
                round(item["default_weight"], 8),
            )
            for item in entries
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return {
        "schema_version": 1,
        "captured_at": now(),
        "product": {
            "name": str(RLPy.RApplication.GetProductName()),
            "edition": str(RLPy.RApplication.GetProductEdition()),
            "version": str(RLPy.RApplication.GetProductVersion()),
            "api_version": str(RLPy.RApplication.GetApiVersion()),
        },
        "base_avatar": base_avatar,
        "face_morph_count": len(entries),
        "catalog_fingerprint_sha256": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest(),
        "entries": entries,
    }


def group_delta(expected_entries, actual_entries, tolerance=1e-7):
    expected = dict((item["id"], float(item["weight"])) for item in expected_entries)
    actual = dict((item["id"], float(item["weight"])) for item in actual_entries)
    result = []
    for morph_id in sorted(set(expected) | set(actual)):
        expected_value = expected.get(morph_id, 0.0)
        actual_value = actual.get(morph_id, 0.0)
        if abs(actual_value - expected_value) > tolerance:
            result.append(
                {
                    "id": morph_id,
                    "expected": expected_value,
                    "actual": actual_value,
                    "delta": actual_value - expected_value,
                }
            )
    return result


def evaluate_appearance_morph_policy(
    appearance_assets,
    before_vectors,
    after_vectors,
    deltas,
):
    slots = {item.get("slot") for item in appearance_assets}
    metadata = {}
    for vectors in (before_vectors, after_vectors):
        for classification, group in (vectors.get("groups") or {}).items():
            for entry in group.get("entries") or []:
                metadata.setdefault(
                    entry["id"],
                    {
                        "id": entry["id"],
                        "display": entry.get("display"),
                        "categories": entry.get("categories") or [],
                        "classification": classification,
                    },
                )

    allowed = []
    disallowed = []
    for classification, changes in deltas.items():
        for change in changes:
            item = dict(change)
            item["classification"] = classification
            item["metadata"] = metadata.get(change["id"])
            record = item["metadata"] or {"id": change["id"]}
            text = " ".join(
                [record.get("id") or "", record.get("display") or ""]
                + list(record.get("categories") or [])
            ).lower()
            is_teeth_support = (
                "teeth" in slots
                and classification not in ("body", "junction")
                and any(term in text for term in TEETH_MORPH_TERMS)
            )
            is_eyelash_style = (
                "eyelashes" in slots
                and classification not in ("body", "junction")
                and any(
                    "actor/eyelash" in str(category).replace("\\", "/").lower()
                    for category in record.get("categories") or []
                )
            )
            scalp_hair_categories = [
                str(category).replace("\\", "/").lower()
                for category in record.get("categories") or []
            ]
            scalp_hair_actor_part_categories = [
                normalized
                for normalized in scalp_hair_categories
                if normalized.startswith("actor parts/")
                and not any(
                    protected in normalized
                    for protected in (
                        "brow",
                        "eye",
                        "eyelash",
                        "eyeocclusion",
                        "tearline",
                        "teeth",
                        "tongue",
                    )
                )
            ]
            is_scalp_hair_style = (
                "scalp_hair" in slots
                and classification not in ("body", "junction")
                and bool(scalp_hair_actor_part_categories)
            )
            is_scalp_hair_accessory = (
                "scalp_hair" in slots
                and classification not in ("body", "junction")
                and any(
                    normalized == "accessory"
                    or normalized.startswith("accessory/")
                    for normalized in scalp_hair_categories
                )
            )
            if is_teeth_support:
                item["allowed_reason"] = "teeth_asset_oral_support_morph"
                allowed.append(item)
            elif is_eyelash_style:
                item["allowed_reason"] = (
                    "eyelash_asset_replaces_identity_eyelash_component"
                    if "cc5 characters" in text
                    else "eyelash_asset_style_morph"
                )
                allowed.append(item)
            elif is_scalp_hair_style:
                item["allowed_reason"] = "scalp_hair_asset_style_morph"
                allowed.append(item)
            elif is_scalp_hair_accessory:
                item["allowed_reason"] = (
                    "scalp_hair_asset_accessory_morph"
                )
                allowed.append(item)
            else:
                disallowed.append(item)
    return {
        "schema_version": 1,
        "slots": sorted(item for item in slots if item),
        "status": "accepted" if not disallowed else "rejected",
        "protected_morphs_unchanged": not bool(disallowed),
        "allowed_change_count": len(allowed),
        "disallowed_change_count": len(disallowed),
        "allowed_changes": allowed,
        "disallowed_changes": disallowed,
    }


def maximum_abs_delta(expected_entries, actual_entries):
    expected = dict((item["id"], float(item["weight"])) for item in expected_entries)
    actual = dict((item["id"], float(item["weight"])) for item in actual_entries)
    return max(
        [
            abs(actual.get(morph_id, 0.0) - expected.get(morph_id, 0.0))
            for morph_id in set(expected) | set(actual)
        ]
        or [0.0]
    )


def remove_current_avatars():
    errors = []
    for avatar in list(RLPy.RScene.GetAvatars() or []):
        try:
            RLPy.RScene.RemoveObject(avatar)
        except Exception as exc:
            errors.append("{}: {}".format(avatar.GetName(), exc))
    if errors:
        raise ReconstructionError("Unable to clear avatars: {}".format(errors))


def resolve_avatar():
    avatars = list(RLPy.RScene.GetAvatars() or [])
    if not avatars:
        raise ReconstructionError("No avatar exists in the current CC scene")
    avatar = avatars[0]
    RLPy.RScene.SelectObject(avatar)
    return avatar, avatars


def load_base(path):
    remove_current_avatars()
    attempts = []
    try:
        loaded = RLPy.RFileIO.LoadObject(path, True)
        attempts.append({"api": "LoadObject", "returned_type": type(loaded).__name__})
    except Exception as exc:
        attempts.append({"api": "LoadObject", "exception": str(exc)})
    avatars = list(RLPy.RScene.GetAvatars() or [])
    if not avatars:
        attempts.append(
            {
                "api": "LoadFile",
                "status": checked("Load base", RLPy.RFileIO.LoadFile(path)),
            }
        )
        avatars = list(RLPy.RScene.GetAvatars() or [])
    if not avatars:
        raise ReconstructionError("No avatar after base load: {}".format(attempts))
    avatar = avatars[0]
    RLPy.RScene.SelectObject(avatar)
    return avatar, attempts


def resolve_body_application_mode(library, preset):
    mode = preset.get(
        "body_application_mode",
        library.get("body_application_mode", "raw_morph_weights"),
    )
    if mode not in BODY_APPLICATION_MODES:
        raise ReconstructionError(
            "Unsupported body_application_mode: {}".format(mode)
        )
    return mode


def apply_bodyfit(avatar, body_targets, junction_targets):
    component, catalog, unused_categories = morph_catalog(avatar)
    targets = {}
    expected_classes = {}
    for classification, entries in (
        ("body", body_targets),
        ("junction", junction_targets),
    ):
        for item in entries:
            morph_id = item["id"]
            if morph_id in targets:
                raise ReconstructionError("Duplicate target morph: {}".format(morph_id))
            targets[morph_id] = float(item["weight"])
            expected_classes[morph_id] = classification

    missing = sorted(set(targets) - set(catalog))
    if missing:
        raise ReconstructionError("BodyFit morph IDs are unavailable: {}".format(missing))
    misclassified = sorted(
        morph_id
        for morph_id, expected in expected_classes.items()
        if catalog[morph_id]["classification"] != expected
    )
    if misclassified:
        raise ReconstructionError(
            "BodyFit morph classifications changed: {}".format(misclassified)
        )

    controlled_ids = sorted(
        morph_id
        for morph_id, item in catalog.items()
        if item["classification"] in ("body", "junction")
    )
    changed = []
    for morph_id in controlled_ids:
        target = targets.get(morph_id, 0.0)
        previous = float(component.GetShapingMorphWeight(morph_id))
        if abs(previous - target) <= 1e-7:
            continue
        bounds = component.GetShapingMorphMinMax(morph_id)
        minimum = float(bounds.first)
        maximum = float(bounds.second)
        if target < minimum - 1e-7 or target > maximum + 1e-7:
            raise ReconstructionError(
                "Body morph outside bounds: {} target={} bounds=[{}, {}]".format(
                    morph_id, target, minimum, maximum
                )
            )
        checked(
            "Set body morph {}".format(catalog[morph_id]["display"]),
            component.SetShapingMorphWeight(morph_id, target),
        )
        changed.append({"id": morph_id, "previous": previous, "target": target})
    if changed:
        checked(
            "Refresh body morph weights",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
    return {
        "available_body_and_junction_morph_count": len(controlled_ids),
        "target_count": len(targets),
        "changed": changed,
    }


def load_primary_head_preset(avatar, face_context):
    path = face_context["source_head_preset"]["path"]
    avatar_id = scene_object_id(avatar)
    RLPy.RScene.SelectObject(avatar)
    status, dialog_policy = (
        load_file_with_optional_character_preset_dialog(
            path,
            "Load primary face head preset",
        )
    )
    QtWidgets.QApplication.processEvents()
    current_avatars = list(RLPy.RScene.GetAvatars() or [])
    matches = [
        candidate
        for candidate in current_avatars
        if scene_object_id(candidate) == avatar_id
    ]
    if len(matches) != 1:
        raise ReconstructionError(
            "Avatar identity changed while loading primary face head preset"
        )
    return matches[0], {
        "primary_seed_id": face_context["primary_seed_id"],
        "source_head_preset": face_context["source_head_preset"],
        "dialog_policy": dialog_policy,
        "load_status": status,
    }


def load_primary_facial_profile(avatar, face_context):
    profile = face_context["source_facial_profile"]
    if profile.get("application_mode") != (
        "selected_avatar_content_load"
    ):
        raise ReconstructionError(
            "Unsupported Facial Profile application mode: {}".format(
                profile.get("application_mode")
            )
        )
    path = profile["path"]
    require_file_extension(
        path,
        ".ccFacialProfile",
        "Primary face Facial Profile",
    )
    avatar_id = scene_object_id(avatar)
    RLPy.RScene.SelectObject(avatar)
    status, dialog_policy = load_file_with_optional_undo_warning(
        path,
        "Load primary face Facial Profile",
    )
    QtWidgets.QApplication.processEvents()
    current_avatars = list(RLPy.RScene.GetAvatars() or [])
    matches = [
        candidate
        for candidate in current_avatars
        if scene_object_id(candidate) == avatar_id
    ]
    if len(matches) != 1:
        raise ReconstructionError(
            "Avatar identity changed while loading primary Facial Profile"
        )
    return matches[0], {
        "application_mode": profile["application_mode"],
        "dialog_policy": dialog_policy,
        "load_status": status,
        "path": path,
        "sha256": profile["sha256"],
    }


def apply_target_face(avatar, target_morphs, owned_morph_ids):
    component, catalog, unused_categories = morph_catalog(avatar)
    targets = {}
    for item in target_morphs:
        morph_id = item["id"]
        if morph_id in targets:
            raise ReconstructionError("Duplicate target face morph: {}".format(morph_id))
        targets[morph_id] = float(item["weight"])
    missing = sorted(set(targets) - set(catalog))
    if missing:
        raise ReconstructionError("Face morph IDs are unavailable: {}".format(missing))
    owned_ids = set(owned_morph_ids)
    unowned_targets = sorted(set(targets) - owned_ids)
    if unowned_targets:
        raise ReconstructionError(
            "Face targets are outside identity ownership: {}".format(
                unowned_targets
            )
        )
    misclassified = sorted(
        morph_id
        for morph_id in targets
        if catalog[morph_id]["classification"] != "face"
    )
    if misclassified:
        raise ReconstructionError(
            "Face morph classifications changed: {}".format(misclassified)
        )
    available_owned_ids = sorted(
        morph_id
        for morph_id in owned_ids
        if morph_id in catalog
    )
    unavailable_owned_ids = sorted(owned_ids - set(catalog))
    face_ids = {
        morph_id
        for morph_id, item in catalog.items()
        if item["classification"] == "face"
    }
    preserved_face_ids = sorted(face_ids - set(available_owned_ids))
    changed = []
    for morph_id in available_owned_ids:
        target = targets.get(morph_id, 0.0)
        previous = float(component.GetShapingMorphWeight(morph_id))
        if abs(previous - target) <= 1e-7:
            continue
        bounds = component.GetShapingMorphMinMax(morph_id)
        minimum = float(bounds.first)
        maximum = float(bounds.second)
        reported_out_of_bounds = target < minimum - 1e-7 or target > maximum + 1e-7
        signed_embed = morph_id.lower().startswith("cc embed morphs/")
        if reported_out_of_bounds and not signed_embed:
            raise ReconstructionError(
                "Face morph outside bounds: {} target={} bounds=[{}, {}]".format(
                    morph_id, target, minimum, maximum
                )
            )
        checked(
            "Set face morph {}".format(catalog[morph_id]["display"]),
            component.SetShapingMorphWeight(morph_id, target),
        )
        changed.append({"id": morph_id, "previous": previous, "target": target})
    if changed:
        checked(
            "Refresh face morph weights",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        QtWidgets.QApplication.processEvents()
    return {
        "available_face_morph_count": len(face_ids),
        "available_owned_morph_count": len(available_owned_ids),
        "unavailable_owned_morph_ids": unavailable_owned_ids,
        "preserved_face_morph_count": len(preserved_face_ids),
        "preserved_face_morph_ids": preserved_face_ids,
        "target_count": len(targets),
        "changed": changed,
    }


def apply_primary_head_support(
    avatar,
    target_morphs,
    active_support_entries,
):
    component, catalog, unused_categories = morph_catalog(avatar)
    targets = {}
    for item in target_morphs:
        morph_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(morph_id, str) or not morph_id:
            raise ReconstructionError(
                "Primary support target has an invalid Morph ID"
            )
        if morph_id in targets:
            raise ReconstructionError(
                "Duplicate primary support Morph: {}".format(morph_id)
            )
        targets[morph_id] = float(item["weight"])

    missing = sorted(set(targets) - set(catalog))
    if missing:
        raise ReconstructionError(
            "Primary support Morph IDs are unavailable: {}".format(missing)
        )
    invalid_targets = sorted(
        morph_id
        for morph_id in targets
        if not is_head_geometry_actor_part_morph_entry(catalog[morph_id])
    )
    if invalid_targets:
        raise ReconstructionError(
            "Primary support targets are not Actor Parts Morphs: {}".format(
                invalid_targets
            )
        )

    active_actor_part_ids = {
        item["id"]
        for item in active_support_entries
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and is_head_geometry_actor_part_morph_entry(item)
    }
    replacement_domain_ids = sorted(
        set(targets) | active_actor_part_ids
    )
    changed = []
    for morph_id in replacement_domain_ids:
        if morph_id not in catalog:
            raise ReconstructionError(
                "Active support Morph ID is unavailable: {}".format(
                    morph_id
                )
            )
        if not is_head_geometry_actor_part_morph_entry(catalog[morph_id]):
            raise ReconstructionError(
                "Active support Morph is no longer an Actor Parts Morph: "
                "{}".format(morph_id)
            )
        target = targets.get(morph_id, 0.0)
        previous = float(component.GetShapingMorphWeight(morph_id))
        if abs(previous - target) <= 1e-7:
            continue
        bounds = component.GetShapingMorphMinMax(morph_id)
        minimum = float(bounds.first)
        maximum = float(bounds.second)
        if target < minimum - 1e-7 or target > maximum + 1e-7:
            raise ReconstructionError(
                "Primary support Morph outside bounds: {} target={} "
                "bounds=[{}, {}]".format(
                    morph_id,
                    target,
                    minimum,
                    maximum,
                )
            )
        checked(
            "Set primary support Morph {}".format(
                catalog[morph_id]["display"]
            ),
            component.SetShapingMorphWeight(morph_id, target),
        )
        changed.append(
            {
                "id": morph_id,
                "previous": previous,
                "target": target,
            }
        )
    if changed:
        checked(
            "Refresh primary support Morph weights",
            RLPy.RGlobal.ObjectModified(
                avatar,
                RLPy.EObjectModifiedType_MorphWeight,
            ),
        )
        QtWidgets.QApplication.processEvents()
    return {
        "active_actor_part_morph_ids_before": sorted(
            active_actor_part_ids
        ),
        "changed": changed,
        "replacement_domain_ids": replacement_domain_ids,
        "target_count": len(targets),
        "target_morph_ids": sorted(targets),
    }


def apply_local_face_morphs(
    avatar,
    local_morphs,
    modifiable_morph_ids,
    baseline_tolerance=1e-6,
):
    component, catalog, unused_categories = morph_catalog(avatar)
    modifiable_ids = set(modifiable_morph_ids)
    local_ids = [item["id"] for item in local_morphs]
    if len(local_ids) != len(set(local_ids)):
        raise ReconstructionError(
            "Duplicate V3 local face Morph ID"
        )
    unapproved = sorted(set(local_ids) - modifiable_ids)
    if unapproved:
        raise ReconstructionError(
            "V3 local face Morphs are outside the approved policy: {}".format(
                unapproved
            )
        )
    missing = sorted(set(local_ids) - set(catalog))
    if missing:
        raise ReconstructionError(
            "V3 local face Morph IDs are unavailable: {}".format(missing)
        )
    misclassified = sorted(
        morph_id
        for morph_id in local_ids
        if catalog[morph_id]["classification"] != "face"
    )
    if misclassified:
        raise ReconstructionError(
            "V3 local Morph classifications changed: {}".format(
                misclassified
            )
        )

    baseline_observations = []
    for item in local_morphs:
        morph_id = item["id"]
        expected = float(item["baseline_weight"])
        actual = float(component.GetShapingMorphWeight(morph_id))
        baseline_observations.append(
            {
                "actual": actual,
                "expected": expected,
                "id": morph_id,
                "matches": abs(actual - expected)
                <= baseline_tolerance,
            }
        )
    baseline_mismatches = [
        item for item in baseline_observations if not item["matches"]
    ]
    if baseline_mismatches:
        raise ReconstructionError(
            "V3 primary Head Preset local Morph baseline mismatch: {}".format(
                baseline_mismatches
            )
        )

    changed = []
    for item in local_morphs:
        morph_id = item["id"]
        target = float(item["weight"])
        previous = float(component.GetShapingMorphWeight(morph_id))
        bounds = component.GetShapingMorphMinMax(morph_id)
        minimum = float(bounds.first)
        maximum = float(bounds.second)
        reported_out_of_bounds = (
            target < minimum - 1e-7 or target > maximum + 1e-7
        )
        signed_embed = morph_id.lower().startswith(
            "cc embed morphs/"
        )
        if reported_out_of_bounds and not signed_embed:
            raise ReconstructionError(
                "V3 local face Morph outside bounds: "
                "{} target={} bounds=[{}, {}]".format(
                    morph_id, target, minimum, maximum
                )
            )
        if abs(previous - target) <= 1e-7:
            continue
        checked(
            "Set V3 local face Morph {}".format(
                catalog[morph_id]["display"]
            ),
            component.SetShapingMorphWeight(morph_id, target),
        )
        changed.append(
            {
                "id": morph_id,
                "previous": previous,
                "target": target,
            }
        )
    if changed:
        checked(
            "Refresh V3 local face Morph weights",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        QtWidgets.QApplication.processEvents()

    face_ids = {
        morph_id
        for morph_id, item in catalog.items()
        if item["classification"] == "face"
    }
    return {
        "available_face_morph_count": len(face_ids),
        "baseline_mismatch_count": len(baseline_mismatches),
        "baseline_observations": baseline_observations,
        "changed": changed,
        "local_target_count": len(local_morphs),
        "mode": COMPLETE_PRIMARY_FACE_PIPELINE,
        "preserved_face_morph_count": len(
            face_ids - set(local_ids)
        ),
        "written_morph_ids": sorted(local_ids),
    }


def apply_single_morph_weight(avatar, morph_id, target, label):
    component, catalog, unused_categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "{} Morph is unavailable: {}".format(label, morph_id)
        )
    target = float(target)
    bounds = component.GetShapingMorphMinMax(morph_id)
    minimum = float(bounds.first)
    maximum = float(bounds.second)
    if target < minimum - 1e-7 or target > maximum + 1e-7:
        raise ReconstructionError(
            "{} Morph target is outside bounds: {} target={} "
            "bounds=[{}, {}]".format(
                label,
                morph_id,
                target,
                minimum,
                maximum,
            )
        )
    previous = float(component.GetShapingMorphWeight(morph_id))
    if abs(previous - target) > 1e-7:
        checked(
            "Set {} Morph {}".format(label, catalog[morph_id]["display"]),
            component.SetShapingMorphWeight(morph_id, target),
        )
        checked(
            "Refresh {} Morph".format(label),
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        QtWidgets.QApplication.processEvents()
    actual = float(component.GetShapingMorphWeight(morph_id))
    if abs(actual - target) > 1e-6:
        raise ReconstructionError(
            "{} Morph did not reach target".format(label)
        )
    return {
        "actual": actual,
        "display": catalog[morph_id]["display"],
        "id": morph_id,
        "previous": previous,
        "target": target,
    }


def path_is_within(path, roots):
    path = os.path.normcase(os.path.realpath(os.path.abspath(path)))
    for root in roots:
        root = os.path.normcase(os.path.realpath(os.path.abspath(root)))
        try:
            if os.path.commonpath([path, root]) == root:
                return True
        except ValueError:
            continue
    return False


def load_appearance_catalog(library):
    reference = library.get("appearance_catalog")
    if reference is None:
        return None
    if isinstance(reference, str):
        path = reference
        expected_id = None
    elif isinstance(reference, dict):
        path = reference.get("path")
        expected_id = reference.get("catalog_id")
    else:
        raise ReconstructionError("appearance_catalog must be a path or object")
    if not isinstance(path, str) or not os.path.isfile(path):
        raise ReconstructionError("Appearance catalog is missing: {}".format(path))
    path = os.path.realpath(os.path.abspath(path))
    document = read_json(path)
    if int(document.get("schema_version", -1)) != 1:
        raise ReconstructionError("Unsupported appearance catalog schema")
    if expected_id and document.get("catalog_id") != expected_id:
        raise ReconstructionError("Appearance catalog ID changed")
    roots = [
        value
        for value in (document.get("roots") or {}).values()
        if isinstance(value, str) and value
    ]
    if not roots:
        raise ReconstructionError("Appearance catalog has no allowed roots")
    assets = document.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ReconstructionError("Appearance catalog has no assets")
    by_id = {}
    for item in assets:
        item_id = item.get("asset_id")
        if not isinstance(item_id, str) or not item_id or item_id in by_id:
            raise ReconstructionError("Appearance catalog IDs are invalid or duplicated")
        by_id[item_id] = item
    return {
        "path": path,
        "catalog_id": document.get("catalog_id"),
        "roots": roots,
        "assets": by_id,
    }


def resolve_appearance_assets(preset, catalog):
    asset_ids = preset.get("appearance_asset_ids")
    if asset_ids is None:
        return []
    if not isinstance(asset_ids, list) or not asset_ids:
        raise ReconstructionError("appearance_asset_ids must be a non-empty list")
    if len(asset_ids) != len(set(asset_ids)):
        raise ReconstructionError("appearance_asset_ids contains duplicates")
    if catalog is None:
        raise ReconstructionError("Appearance assets require appearance_catalog")

    missing = sorted(set(asset_ids) - set(catalog["assets"]))
    if missing:
        raise ReconstructionError("Unknown appearance asset IDs: {}".format(missing))
    resolved = []
    slots = []
    for item_id in asset_ids:
        item = catalog["assets"][item_id]
        if item.get("automation_status") != "candidate":
            raise ReconstructionError(
                "Appearance asset is not a standalone candidate: {}".format(item_id)
            )
        path = item.get("preferred_path")
        if not isinstance(path, str) or not os.path.isfile(path):
            raise ReconstructionError("Appearance asset is missing: {}".format(item_id))
        if not path_is_within(path, catalog["roots"]):
            raise ReconstructionError(
                "Appearance asset is outside catalog roots: {}".format(item_id)
            )
        sex_hint = item.get("sex_hint")
        if sex_hint in ("male", "female") and sex_hint != preset.get("sex"):
            raise ReconstructionError(
                "Appearance asset sex hint conflicts with preset: {}".format(item_id)
            )
        slots.append(item.get("slot"))
        slot = item.get("slot")
        if slot in MATERIAL_VERIFICATION_SLOTS:
            verification_mode = "material_fingerprint"
        elif slot in SCENE_VERIFICATION_SLOTS:
            verification_mode = "scene_inventory"
        else:
            raise ReconstructionError(
                "Appearance asset uses an unsupported slot: {} ({})".format(
                    slot, item_id
                )
            )
        resolved.append(
            {
                "asset_id": item_id,
                "display_name": item.get("display_name"),
                "asset_type": item.get("asset_type"),
                "slot": slot,
                "asset_form": item.get("asset_form"),
                "extension": item.get("extension"),
                "verification_mode": verification_mode,
                "path": os.path.realpath(path),
            }
        )

    repeatable = {"accessory_other"}
    duplicate_slots = sorted(
        slot for slot in set(slots) if slot not in repeatable and slots.count(slot) > 1
    )
    if duplicate_slots:
        raise ReconstructionError(
            "Appearance recipe repeats exclusive slots: {}".format(duplicate_slots)
        )
    if "full_body" in slots and any(
        slot in slots for slot in ("upper", "lower", "outerwear")
    ):
        raise ReconstructionError("full_body conflicts with layered clothing slots")
    return sorted(
        resolved,
        key=lambda item: (
            APPEARANCE_SLOT_ORDER.get(item["slot"], 1000),
            item["asset_id"],
        ),
    )


def resolve_appearance_cleanup(preset):
    cleanup = preset.get("appearance_cleanup") or {}
    if not isinstance(cleanup, dict):
        raise ReconstructionError("appearance_cleanup must be an object")
    names = cleanup.get("remove_base_clothing_names") or []
    if not isinstance(names, list):
        raise ReconstructionError("remove_base_clothing_names must be a list")
    if any(
        not isinstance(name, str)
        or not name.strip()
        or len(name) > 128
        or "\n" in name
        or "\r" in name
        for name in names
    ):
        raise ReconstructionError("remove_base_clothing_names contains an invalid name")
    names = [name.strip() for name in names]
    if len(names) != len(set(names)):
        raise ReconstructionError("remove_base_clothing_names contains duplicates")
    return names


def render_static_hair_views_enabled(plan):
    if not plan:
        return False
    integrated = plan.get("integrated_facial_assembly_validation")
    integrated_enabled = False
    if integrated is not None:
        if not isinstance(integrated, dict):
            raise ReconstructionError(
                "integrated_facial_assembly_validation must be an object"
            )
        value = integrated.get("render_static_hair_views", False)
        if not isinstance(value, bool):
            raise ReconstructionError(
                "render_static_hair_views must be a boolean"
            )
        integrated_enabled = value
    return bool(
        plan.get("pose_profile") == SCALP_HAIR_VISIBILITY_PROFILE
        or integrated_enabled
    )


def resolve_dynamic_wrinkle_validation(plan):
    if not plan:
        return None
    validation = plan.get("dynamic_wrinkle_validation")
    if validation is None:
        return None
    if not isinstance(validation, dict):
        raise ReconstructionError(
            "dynamic_wrinkle_validation must be an object"
        )
    if plan.get("domain") != "face_identity":
        raise ReconstructionError(
            "dynamic_wrinkle_validation requires the face_identity domain"
        )
    if plan.get("pose_profile") != FACE_IDENTITY_SAFETY_PROFILE:
        raise ReconstructionError(
            "dynamic_wrinkle_validation requires {}".format(
                FACE_IDENTITY_SAFETY_PROFILE
            )
        )
    normalized = {}
    for key in ("baseline_strength", "target_strength"):
        value = validation.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0.0 <= float(value) <= 1.0
        ):
            raise ReconstructionError(
                "{} must be a number between 0 and 1".format(key)
            )
        normalized[key] = float(value)
    if normalized["baseline_strength"] == normalized["target_strength"]:
        raise ReconstructionError(
            "Dynamic wrinkle baseline and target strengths must differ"
        )
    pose_ids = validation.get("pose_ids")
    if (
        not isinstance(pose_ids, list)
        or not pose_ids
        or any(
            not isinstance(pose_id, str) or not pose_id
            for pose_id in pose_ids
        )
    ):
        raise ReconstructionError(
            "dynamic_wrinkle_validation.pose_ids must be a non-empty list"
        )
    if len(pose_ids) != len(set(pose_ids)):
        raise ReconstructionError(
            "dynamic_wrinkle_validation.pose_ids contains duplicates"
        )
    unknown_pose_ids = sorted(
        set(pose_ids) - set(DYNAMIC_WRINKLE_POSE_ARTIFACT_KEYS)
    )
    if unknown_pose_ids:
        raise ReconstructionError(
            "Unsupported dynamic wrinkle pose IDs: {}".format(
                unknown_pose_ids
            )
        )
    normalized["pose_ids"] = list(pose_ids)
    return normalized


def resolve_appearance_validation_plan(preset):
    plan = preset.get("appearance_validation_plan")
    if plan is None:
        return None
    if not isinstance(plan, dict):
        raise ReconstructionError("appearance_validation_plan must be an object")
    domain = plan.get("domain")
    if not isinstance(domain, str) or not domain:
        raise ReconstructionError(
            "appearance_validation_plan.domain must be a non-empty string"
        )
    pose_profile = plan.get("pose_profile")
    supported_profiles = (
        TEETH_VISIBILITY_PROFILE,
        EYE_VISIBILITY_PROFILE,
        EYEBROW_VISIBILITY_PROFILE,
        EYELASH_VISIBILITY_PROFILE,
        FACIAL_HAIR_VISIBILITY_PROFILE,
        SCALP_HAIR_VISIBILITY_PROFILE,
        FACE_IDENTITY_SAFETY_PROFILE,
    )
    if pose_profile is not None and pose_profile not in supported_profiles:
        raise ReconstructionError(
            "Unsupported appearance pose profile: {}".format(pose_profile)
        )
    if pose_profile == TEETH_VISIBILITY_PROFILE and domain != "teeth":
        raise ReconstructionError(
            "{} is only valid for the teeth domain".format(
                TEETH_VISIBILITY_PROFILE
            )
        )
    if pose_profile == EYE_VISIBILITY_PROFILE and domain != "eyes":
        raise ReconstructionError(
            "{} is only valid for the eyes domain".format(
                EYE_VISIBILITY_PROFILE
            )
        )
    if (
        pose_profile == EYEBROW_VISIBILITY_PROFILE
        and domain != "eyebrows"
    ):
        raise ReconstructionError(
            "{} is only valid for the eyebrows domain".format(
                EYEBROW_VISIBILITY_PROFILE
            )
        )
    if (
        pose_profile == EYELASH_VISIBILITY_PROFILE
        and domain != "eyelashes"
    ):
        raise ReconstructionError(
            "{} is only valid for the eyelashes domain".format(
                EYELASH_VISIBILITY_PROFILE
            )
        )
    if (
        pose_profile == FACIAL_HAIR_VISIBILITY_PROFILE
        and domain != "facial_hair"
    ):
        raise ReconstructionError(
            "{} is only valid for the facial_hair domain".format(
                FACIAL_HAIR_VISIBILITY_PROFILE
            )
        )
    if (
        pose_profile == SCALP_HAIR_VISIBILITY_PROFILE
        and domain != "scalp_hair"
    ):
        raise ReconstructionError(
            "{} is only valid for the scalp_hair domain".format(
                SCALP_HAIR_VISIBILITY_PROFILE
            )
        )
    if (
        pose_profile == FACE_IDENTITY_SAFETY_PROFILE
        and domain != "face_identity"
    ):
        raise ReconstructionError(
            "{} is only valid for the face_identity domain".format(
                FACE_IDENTITY_SAFETY_PROFILE
            )
        )
    render_static_hair_views_enabled(plan)
    resolve_dynamic_wrinkle_validation(plan)
    return plan


def resolve_asset_load_pacing(preset):
    plan = preset.get("appearance_validation_plan") or {}
    pacing = plan.get("asset_load_pacing")
    if pacing is None:
        return {
            "default_after_seconds": 0.0,
            "default_before_seconds": 0.0,
            "slots": {},
        }
    if not isinstance(pacing, dict):
        raise ReconstructionError(
            "asset_load_pacing must be an object"
        )

    def duration(value, label):
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ReconstructionError(
                "{} must be numeric".format(label)
            )
        if value < 0.0 or value > 60.0:
            raise ReconstructionError(
                "{} must be between 0 and 60 seconds".format(label)
            )
        return value

    resolved = {
        "default_after_seconds": duration(
            pacing.get("default_after_seconds", 0.0),
            "asset_load_pacing.default_after_seconds",
        ),
        "default_before_seconds": duration(
            pacing.get("default_before_seconds", 0.0),
            "asset_load_pacing.default_before_seconds",
        ),
        "slots": {},
    }
    slots = pacing.get("slots") or {}
    if not isinstance(slots, dict):
        raise ReconstructionError(
            "asset_load_pacing.slots must be an object"
        )
    for slot, values in slots.items():
        if not isinstance(slot, str) or not slot:
            raise ReconstructionError(
                "asset_load_pacing contains an invalid slot"
            )
        if not isinstance(values, dict):
            raise ReconstructionError(
                "asset_load_pacing slot values must be objects"
            )
        resolved["slots"][slot] = {
            "after_seconds": duration(
                values.get(
                    "after_seconds",
                    resolved["default_after_seconds"],
                ),
                "asset_load_pacing.{}.after_seconds".format(slot),
            ),
            "before_seconds": duration(
                values.get(
                    "before_seconds",
                    resolved["default_before_seconds"],
                ),
                "asset_load_pacing.{}.before_seconds".format(slot),
            ),
        }
    return resolved


def asset_load_pacing_for_slot(pacing, slot):
    override = (pacing.get("slots") or {}).get(slot) or {}
    return {
        "after_seconds": float(
            override.get(
                "after_seconds",
                pacing.get("default_after_seconds", 0.0),
            )
        ),
        "before_seconds": float(
            override.get(
                "before_seconds",
                pacing.get("default_before_seconds", 0.0),
            )
        ),
    }


def settle_cc_ui(seconds):
    seconds = float(seconds)
    if seconds <= 0.0:
        return
    deadline = time.time() + seconds
    while True:
        QtWidgets.QApplication.processEvents()
        remaining = deadline - time.time()
        if remaining <= 0.0:
            break
        time.sleep(min(0.05, remaining))
    QtWidgets.QApplication.processEvents()


def scene_object_id(scene_object):
    try:
        return str(scene_object.GetID())
    except Exception:
        return "memory:{}".format(id(scene_object))


def scene_object_name(scene_object):
    try:
        return str(scene_object.GetName())
    except Exception:
        return "<unnamed>"


def avatar_asset_inventory(avatar):
    records = []
    for getter_name in ("GetClothes", "GetAccessories", "GetHairs"):
        try:
            objects = list(getattr(avatar, getter_name)() or [])
        except Exception as exc:
            records.append(
                {
                    "id": "getter-error:{}".format(getter_name),
                    "name": str(exc),
                    "python_type": "GetterError",
                    "collection": getter_name,
                }
            )
            continue
        for scene_object in objects:
            records.append(
                {
                    "id": scene_object_id(scene_object),
                    "name": scene_object_name(scene_object),
                    "python_type": type(scene_object).__name__,
                    "collection": getter_name,
                }
            )
    records.sort(key=lambda item: (item["collection"], item["id"], item["name"]))
    return {"object_count": len(records), "objects": records}


def material_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    for attributes in (("r", "g", "b", "a"), ("x", "y", "z", "w")):
        values = []
        complete = True
        for attribute in attributes:
            if not hasattr(value, attribute):
                complete = False
                break
            member = getattr(value, attribute)
            try:
                member = member() if callable(member) else member
                values.append(round(float(member), 8))
            except Exception:
                complete = False
                break
        if complete:
            return values
    if not isinstance(value, (bytes, bytearray)):
        try:
            sequence = list(value)
        except Exception:
            sequence = None
        if sequence is not None:
            return [material_value(item) for item in sequence]
    converted = {}
    for method_name in ("ToString", "ToFloat", "ToDouble", "ToInt", "ToBool"):
        method = getattr(value, method_name, None)
        if not callable(method):
            continue
        try:
            converted[method_name] = material_value(method())
        except Exception:
            continue
    if converted:
        return converted
    try:
        return round(float(value), 8)
    except Exception:
        return {"python_type": type(value).__name__}


def material_call(component, method_name, mesh_name, material_name):
    method = getattr(component, method_name)
    return material_value(method(mesh_name, material_name))


def hair_material_component(avatar, owner):
    getter = getattr(owner, "GetMaterialComponent", None)
    if callable(getter):
        component = getter()
        if component is not None:
            return component, "owner"
    getter = getattr(avatar, "GetMaterialComponent", None)
    if callable(getter):
        component = getter()
        if component is not None:
            return component, "avatar"
    return None, None


def hair_shader_owner_records(avatar, owner, domain):
    component, component_source = hair_material_component(
        avatar, owner
    )
    if component is None:
        return [
            {
                "domain": domain,
                "error": "no_material_component",
                "owner_id": scene_object_id(owner),
                "owner_name": scene_object_name(owner),
                "material_component_source": component_source,
            }
        ]
    try:
        mesh_names = sorted(
            str(name) for name in (owner.GetMeshNames() or [])
        )
    except Exception as exc:
        return [
            {
                "domain": domain,
                "error": "mesh_names: {}".format(exc),
                "owner_id": scene_object_id(owner),
                "owner_name": scene_object_name(owner),
                "material_component_source": component_source,
            }
        ]
    records = []
    for mesh_name in mesh_names:
        try:
            material_names = sorted(
                str(name)
                for name in (
                    component.GetMaterialNames(mesh_name) or []
                )
            )
        except Exception as exc:
            records.append(
                {
                    "domain": domain,
                    "error": "material_names: {}".format(exc),
                    "mesh": mesh_name,
                    "owner_id": scene_object_id(owner),
                    "owner_name": scene_object_name(owner),
                    "material_component_source": component_source,
                }
            )
            continue
        for material_name in material_names:
            try:
                shader = str(
                    component.GetShader(mesh_name, material_name)
                )
            except Exception as exc:
                shader = "<error: {}>".format(exc)
            try:
                parameter_names = sorted(
                    str(name)
                    for name in (
                        component.GetShaderParameterNames(
                            mesh_name, material_name
                        )
                        or []
                    )
                )
            except Exception as exc:
                parameter_names = []
                parameter_error = str(exc)
            else:
                parameter_error = None
            parameters = {}
            for parameter_name in parameter_names:
                try:
                    raw = component.GetShaderParameter(
                        mesh_name,
                        material_name,
                        parameter_name,
                    )
                    parameters[parameter_name] = {
                        "python_type": type(raw).__name__,
                        "repr": repr(raw)[:512],
                        "value": material_value(raw),
                    }
                except Exception as exc:
                    parameters[parameter_name] = {
                        "error": str(exc),
                    }
            record = {
                "domain": domain,
                "material": material_name,
                "mesh": mesh_name,
                "owner_id": scene_object_id(owner),
                "owner_name": scene_object_name(owner),
                "material_component_source": component_source,
                "parameters": parameters,
                "shader": shader,
            }
            if parameter_error is not None:
                record["parameter_error"] = parameter_error
            records.append(record)
    return records


def current_hair_shader_records(avatar):
    return [
        record
        for owner, domain in current_hair_material_owners(avatar)
        for record in hair_shader_owner_records(
            avatar, owner, domain
        )
    ]


def current_hair_material_owners(avatar):
    owners = []
    seen = set()

    def add(owner, domain):
        owner_id = scene_object_id(owner)
        if owner_id in seen:
            return
        seen.add(owner_id)
        owners.append((owner, domain))

    for owner in list(avatar.GetHairs() or []):
        add(owner, "scalp_hair")
    for slot, domain in (
        ("eyebrows", "eyebrows"),
        ("facial_hair", "facial_hair"),
    ):
        part_type = avatar_part_type_for_slot(slot)
        for owner in avatar_parts_of_type(avatar, part_type):
            add(owner, domain)
    return owners


def srgb_hex_triplet(value):
    if (
        not isinstance(value, str)
        or len(value) != 7
        or not value.startswith("#")
    ):
        raise ReconstructionError(
            "Hair color is not #RRGGBB: {}".format(value)
        )
    try:
        channels = [
            int(value[index:index + 2], 16) / 255.0
            for index in (1, 3, 5)
        ]
    except ValueError:
        raise ReconstructionError(
            "Hair color is not #RRGGBB: {}".format(value)
        )
    return tuple(channels)


def gray_blended_triplet(color, gray, fraction):
    fraction = float(fraction)
    if not 0.0 <= fraction <= 1.0:
        raise ReconstructionError(
            "Visible gray fraction must be in [0, 1]"
        )
    return tuple(
        source + (target - source) * fraction
        for source, target in zip(color, gray)
    )


def shader_parameter_triplet(value):
    converted = material_value(value)
    if not isinstance(converted, list) or len(converted) < 3:
        return None
    try:
        return tuple(float(item) for item in converted[:3])
    except (TypeError, ValueError):
        return None


def shader_parameter_scalar(value):
    converted = material_value(value)
    if isinstance(converted, list) and len(converted) == 1:
        try:
            return float(converted[0])
        except (TypeError, ValueError):
            return None
    if isinstance(converted, (int, float)):
        return float(converted)
    return None


def apply_shared_hair_pigmentation(
    avatar,
    hair_color,
    visible_gray_fraction,
):
    if not isinstance(hair_color, dict):
        raise ReconstructionError("Hair color payload must be an object")
    silver = srgb_hex_triplet("#C4C7C9")
    target_colors = {
        parameter: gray_blended_triplet(
            srgb_hex_triplet(hair_color[field]),
            silver,
            visible_gray_fraction,
        )
        for field, parameter in SMART_HAIR_COLOR_PARAMETERS.items()
    }
    owners = current_hair_material_owners(avatar)
    domain_counts = collections.Counter()
    material_records = []
    for owner, domain in owners:
        component, component_source = hair_material_component(
            avatar, owner
        )
        if component is None:
            raise ReconstructionError(
                "Hair owner has no material component: {}".format(
                    scene_object_name(owner)
                )
            )
        mesh_names = sorted(
            str(name) for name in (owner.GetMeshNames() or [])
        )
        for mesh_name in mesh_names:
            material_names = sorted(
                str(name)
                for name in (
                    component.GetMaterialNames(mesh_name) or []
                )
            )
            for material_name in material_names:
                shader = str(
                    component.GetShader(mesh_name, material_name)
                )
                parameter_names = set(
                    str(name)
                    for name in (
                        component.GetShaderParameterNames(
                            mesh_name, material_name
                        )
                        or []
                    )
                )
                color_parameter_intersection = (
                    set(SMART_HAIR_COLOR_PARAMETERS.values())
                    & parameter_names
                )
                if shader != SMART_HAIR_SHADER:
                    if color_parameter_intersection:
                        raise ReconstructionError(
                            "Unknown hair-color shader signature: "
                            "{} {} {}".format(
                                shader,
                                mesh_name,
                                sorted(parameter_names),
                            )
                        )
                    continue
                missing = sorted(
                    set(SMART_HAIR_COLOR_PARAMETERS.values())
                    - parameter_names
                )
                if missing:
                    raise ReconstructionError(
                        "Smart Hair material lacks color parameters: "
                        "{} {} {}".format(
                            mesh_name,
                            material_name,
                            missing,
                        )
                    )
                before = {}
                for parameter, target in sorted(target_colors.items()):
                    before[parameter] = material_value(
                        component.GetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                        )
                    )
                    checked(
                        "Set Smart Hair {} {} {}".format(
                            domain, material_name, parameter
                        ),
                        component.SetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                            target,
                        ),
                    )
                scalar_before = {}
                for parameter, target in sorted(
                    SMART_HAIR_SCALAR_PARAMETERS.items()
                ):
                    if parameter not in parameter_names:
                        continue
                    scalar_before[parameter] = material_value(
                        component.GetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                        )
                    )
                    checked(
                        "Set Smart Hair scalar {} {} {}".format(
                            domain, material_name, parameter
                        ),
                        component.SetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                            (target,),
                        ),
                    )
                after = {
                    parameter: material_value(
                        component.GetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                        )
                    )
                    for parameter in target_colors
                }
                scalar_after = {
                    parameter: material_value(
                        component.GetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                        )
                    )
                    for parameter in SMART_HAIR_SCALAR_PARAMETERS
                    if parameter in parameter_names
                }
                color_mismatches = []
                for parameter, target in target_colors.items():
                    actual = shader_parameter_triplet(
                        component.GetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                        )
                    )
                    if actual is None or any(
                        abs(left - right) > 1e-5
                        for left, right in zip(actual, target)
                    ):
                        color_mismatches.append(
                            {
                                "actual": actual,
                                "parameter": parameter,
                                "target": target,
                            }
                        )
                scalar_mismatches = []
                for parameter, target in (
                    SMART_HAIR_SCALAR_PARAMETERS.items()
                ):
                    if parameter not in parameter_names:
                        continue
                    actual = shader_parameter_scalar(
                        component.GetShaderParameter(
                            mesh_name,
                            material_name,
                            parameter,
                        )
                    )
                    if actual is None or abs(actual - target) > 1e-5:
                        scalar_mismatches.append(
                            {
                                "actual": actual,
                                "parameter": parameter,
                                "target": target,
                            }
                        )
                if color_mismatches or scalar_mismatches:
                    raise ReconstructionError(
                        "Smart Hair parameter write did not round-trip: "
                        "{} {}".format(
                            color_mismatches,
                            scalar_mismatches,
                        )
                    )
                domain_counts[domain] += 1
                material_records.append(
                    {
                        "after": after,
                        "before": before,
                        "domain": domain,
                        "material": material_name,
                        "mesh": mesh_name,
                        "owner_id": scene_object_id(owner),
                        "owner_name": scene_object_name(owner),
                        "material_component_source": component_source,
                        "scalar_after": scalar_after,
                        "scalar_before": scalar_before,
                        "shader": shader,
                    }
                )
    required_domains = {"scalp_hair", "eyebrows"}
    if avatar_parts_of_type(
        avatar, avatar_part_type_for_slot("facial_hair")
    ):
        required_domains.add("facial_hair")
    missing_domains = sorted(required_domains - set(domain_counts))
    if missing_domains:
        raise ReconstructionError(
            "No approved Smart Hair material was found for domains: {}".format(
                missing_domains
            )
        )
    checked(
        "Refresh shared hair pigmentation",
        RLPy.RGlobal.ObjectModified(
            avatar, RLPy.EObjectModifiedType_Material
        ),
    )
    QtWidgets.QApplication.processEvents()
    return {
        "domain_material_counts": dict(sorted(domain_counts.items())),
        "material_count": len(material_records),
        "materials": material_records,
        "shader": SMART_HAIR_SHADER,
        "target_colors": {
            key: list(value)
            for key, value in sorted(target_colors.items())
        },
        "visible_gray_fraction": float(visible_gray_fraction),
    }


def image_sample(component, mesh_name, material_name, channel):
    image = component.GetImage(mesh_name, material_name, channel)
    if image is None:
        return None
    qimage = image.GetQImage()
    if qimage is None or qimage.isNull():
        return None
    width = int(qimage.width())
    height = int(qimage.height())
    if width <= 0 or height <= 0:
        return None
    xs = sorted(set((0, width // 4, width // 2, (3 * width) // 4, width - 1)))
    ys = sorted(set((0, height // 4, height // 2, (3 * height) // 4, height - 1)))
    pixels = [
        "{:08x}".format(int(qimage.pixel(x, y)) & 0xFFFFFFFF)
        for y in ys
        for x in xs
    ]
    return {
        "width": width,
        "height": height,
        "sample_argb": pixels,
    }


def avatar_material_fingerprint(avatar):
    component = avatar.GetMaterialComponent()
    if component is None:
        raise ReconstructionError("Avatar has no material component")
    try:
        mesh_names = sorted(str(name) for name in (avatar.GetMeshNames() or []))
    except Exception as exc:
        raise ReconstructionError("Unable to enumerate avatar meshes: {}".format(exc))
    records = []
    errors = []
    texture_count = 0
    property_methods = (
        "GetAmbientColor",
        "GetDiffuseColor",
        "GetSpecularColor",
        "GetGlossinessWeight",
        "GetSpecularWeight",
        "GetSelfIlluminationWeight",
        "GetOpacity",
        "GetTextureWeights",
        "GetRefraction",
        "GetReflection",
        "GetShader",
    )
    for mesh_name in mesh_names:
        try:
            material_names = sorted(
                str(name) for name in (component.GetMaterialNames(mesh_name) or [])
            )
        except Exception as exc:
            errors.append(
                {
                    "mesh": mesh_name,
                    "stage": "material_names",
                    "error": str(exc),
                }
            )
            continue
        for material_name in material_names:
            record = {
                "mesh": mesh_name,
                "material": material_name,
                "properties": {},
                "shader_parameters": {},
                "textures": {},
            }
            for method_name in property_methods:
                try:
                    record["properties"][method_name] = material_call(
                        component, method_name, mesh_name, material_name
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "mesh": mesh_name,
                            "material": material_name,
                            "stage": method_name,
                            "error": str(exc),
                        }
                    )
            try:
                parameter_names = sorted(
                    str(name)
                    for name in (
                        component.GetShaderParameterNames(mesh_name, material_name) or []
                    )
                )
            except Exception as exc:
                parameter_names = []
                errors.append(
                    {
                        "mesh": mesh_name,
                        "material": material_name,
                        "stage": "shader_parameter_names",
                        "error": str(exc),
                    }
                )
            for parameter_name in parameter_names:
                try:
                    record["shader_parameters"][parameter_name] = material_value(
                        component.GetShaderParameter(
                            mesh_name, material_name, parameter_name
                        )
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "mesh": mesh_name,
                            "material": material_name,
                            "stage": "shader_parameter:{}".format(parameter_name),
                            "error": str(exc),
                        }
                    )
            for channel_name, constant_name in MATERIAL_TEXTURE_CHANNELS:
                channel = getattr(RLPy, constant_name, None)
                if channel is None:
                    continue
                try:
                    sample = image_sample(
                        component, mesh_name, material_name, channel
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "mesh": mesh_name,
                            "material": material_name,
                            "stage": "texture:{}".format(channel_name),
                            "error": str(exc),
                        }
                    )
                    continue
                if sample is not None:
                    record["textures"][channel_name] = sample
                    texture_count += 1
            records.append(record)
    payload = {
        "mesh_names": mesh_names,
        "materials": records,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    mesh_digests = {}
    for mesh_name in mesh_names:
        mesh_payload = {
            "mesh": mesh_name,
            "materials": [
                record for record in records if record["mesh"] == mesh_name
            ],
        }
        mesh_encoded = json.dumps(
            mesh_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        mesh_digests[mesh_name] = hashlib.sha256(mesh_encoded).hexdigest()
    return {
        "digest": hashlib.sha256(encoded).hexdigest(),
        "mesh_names": mesh_names,
        "mesh_digests": mesh_digests,
        "mesh_count": len(mesh_names),
        "material_count": len(records),
        "texture_count": texture_count,
        "observation_error_count": len(errors),
        "observation_errors": errors[:20],
    }


def remove_base_clothing(avatar, requested_names, allow_missing=False):
    before = avatar_asset_inventory(avatar)
    if not requested_names:
        return avatar, {
            "requested_names": [],
            "removed_objects": [],
            "before_inventory": before,
            "after_inventory": before,
        }

    clothes = list(avatar.GetClothes() or [])
    by_name = collections.defaultdict(list)
    for item in clothes:
        by_name[scene_object_name(item)].append(item)
    missing = sorted(set(requested_names) - set(by_name))
    if missing and not allow_missing:
        raise ReconstructionError(
            "Requested base clothing was not found: {}".format(missing)
        )

    avatar_id = scene_object_id(avatar)
    removals = []
    for name in requested_names:
        for item in by_name[name]:
            record = {
                "id": scene_object_id(item),
                "name": scene_object_name(item),
                "python_type": type(item).__name__,
                "collection": "GetClothes",
            }
            record["remove_status"] = checked(
                "Remove base clothing {}".format(name),
                RLPy.RScene.RemoveObject(item),
            )
            removals.append(record)
            QtWidgets.QApplication.processEvents()

    current_avatars = list(RLPy.RScene.GetAvatars() or [])
    matches = [
        candidate
        for candidate in current_avatars
        if scene_object_id(candidate) == avatar_id
    ]
    if len(matches) != 1:
        raise ReconstructionError("Avatar identity changed during clothing cleanup")
    avatar = matches[0]
    after = avatar_asset_inventory(avatar)
    after_ids = {item["id"] for item in after["objects"]}
    remaining = [item["id"] for item in removals if item["id"] in after_ids]
    if remaining:
        raise ReconstructionError(
            "Base clothing cleanup did not remove objects: {}".format(remaining)
        )
    return avatar, {
        "requested_names": list(requested_names),
        "missing_names": missing,
        "removed_objects": removals,
        "before_inventory": before,
        "after_inventory": after,
    }


def avatar_parts_of_type(avatar, part_type):
    try:
        return list(avatar.GetAvatarParts(part_type) or [])
    except Exception:
        return [
            part
            for part in list(avatar.GetAvatarParts() or [])
            if part.GetAvatarPartType() == part_type
        ]


def stable_geometry_value(value):
    if isinstance(value, float):
        return round(value, 7)
    if isinstance(value, list):
        return [stable_geometry_value(item) for item in value]
    if isinstance(value, dict):
        return dict(
            (key, stable_geometry_value(item))
            for key, item in sorted(value.items())
        )
    return value


def avatar_part_record(part):
    try:
        mesh_names = sorted(
            str(name) for name in (part.GetMeshNames() or [])
        )
    except Exception as exc:
        mesh_names = []
        mesh_names_error = str(exc)
    else:
        mesh_names_error = None
    face_hair_type = None
    get_face_hair_type = getattr(part, "GetFaceHairType", None)
    if callable(get_face_hair_type):
        try:
            face_hair_type = str(get_face_hair_type())
        except Exception:
            face_hair_type = None
    geometry = {
        "python_type": type(part).__name__,
        "avatar_part_type": str(part.GetAvatarPartType()),
        "face_hair_type": face_hair_type,
        "mesh_names": mesh_names,
        "bounds": capture_bounds(part),
        "local_transform": _transform_data(part.LocalTransform()),
        "world_transform": _transform_data(part.WorldTransform()),
    }
    stable_geometry = stable_geometry_value(geometry)
    encoded = json.dumps(
        stable_geometry,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    record = {
        "id": scene_object_id(part),
        "name": scene_object_name(part),
        "python_type": type(part).__name__,
        "avatar_part_type": str(part.GetAvatarPartType()),
        "face_hair_type": face_hair_type,
        "mesh_names": mesh_names,
        "geometry": stable_geometry,
        "geometry_digest": hashlib.sha256(encoded).hexdigest(),
        "mesh_related_methods": _callable_names(
            part,
            ("mesh", "vertex", "face", "polygon", "material", "bound"),
        ),
    }
    if mesh_names_error is not None:
        record["mesh_names_error"] = mesh_names_error
    return record


def avatar_part_type_for_slot(slot):
    constant_name = REPLACEABLE_AVATAR_PART_SLOTS.get(slot)
    if constant_name is None:
        raise ReconstructionError(
            "Appearance slot is not replaceable as an avatar part: {}".format(
                slot
            )
        )
    part_type = getattr(RLPy, constant_name, None)
    if part_type is None:
        raise ReconstructionError(
            "CC runtime has no {} avatar-part type ({})".format(
                slot, constant_name
            )
        )
    return part_type


def is_eye_part_morph(item):
    categories = [
        str(category).replace("\\", "/").lower()
        for category in item.get("categories") or []
    ]
    return any(
        "actor parts/cc_base_eye" in category
        for category in categories
    )


def capture_eye_part_morph_weights(avatar):
    component, catalog, unused_categories = morph_catalog(avatar)
    entries = []
    for morph_id in sorted(catalog):
        item = catalog[morph_id]
        if not is_eye_part_morph(item):
            continue
        entries.append(
            {
                "id": morph_id,
                "display": item["display"],
                "categories": item["categories"],
                "classification": item["classification"],
                "weight": float(
                    component.GetShapingMorphWeight(morph_id)
                ),
            }
        )
    return entries


def restore_eye_part_morph_weights(avatar, expected_entries):
    component, catalog, unused_categories = morph_catalog(avatar)
    expected = dict(
        (item["id"], float(item["weight"]))
        for item in expected_entries
    )
    available_eye_ids = {
        morph_id
        for morph_id, item in catalog.items()
        if is_eye_part_morph(item)
    }
    missing = sorted(set(expected) - set(catalog))
    if missing:
        raise ReconstructionError(
            "Eye replacement removed required support morphs: {}".format(
                missing
            )
        )
    changed = []
    for morph_id in sorted(expected):
        target = expected[morph_id]
        previous = float(component.GetShapingMorphWeight(morph_id))
        if abs(previous - target) <= 1e-7:
            continue
        bounds = component.GetShapingMorphMinMax(morph_id)
        minimum = float(bounds.first)
        maximum = float(bounds.second)
        signed_embed = morph_id.lower().startswith("cc embed morphs/")
        if (
            (target < minimum - 1e-7 or target > maximum + 1e-7)
            and not signed_embed
        ):
            raise ReconstructionError(
                "Eye support morph outside bounds: {} target={} bounds=[{}, {}]".format(
                    morph_id,
                    target,
                    minimum,
                    maximum,
                )
            )
        checked(
            "Restore eye support morph {}".format(
                catalog[morph_id]["display"]
            ),
            component.SetShapingMorphWeight(morph_id, target),
        )
        changed.append(
            {
                "id": morph_id,
                "display": catalog[morph_id]["display"],
                "previous": previous,
                "target": target,
            }
        )
    if changed:
        checked(
            "Refresh restored eye support morphs",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        QtWidgets.QApplication.processEvents()
    final_entries = capture_eye_part_morph_weights(avatar)
    final = dict(
        (item["id"], float(item["weight"]))
        for item in final_entries
    )
    mismatches = [
        {
            "id": morph_id,
            "expected": expected[morph_id],
            "actual": final.get(morph_id),
        }
        for morph_id in sorted(expected)
        if morph_id not in final
        or abs(final[morph_id] - expected[morph_id]) > 1e-7
    ]
    unexpected_nonzero = [
        item
        for item in final_entries
        if item["id"] not in expected and abs(item["weight"]) > 1e-7
    ]
    if mismatches:
        raise ReconstructionError(
            "Eye support morph restoration did not reproduce the source state"
        )
    return {
        "mode": "restore_existing_eye_part_morphs",
        "expected_count": len(expected),
        "available_eye_morph_count": len(available_eye_ids),
        "changed_count": len(changed),
        "changed": changed,
        "missing": missing,
        "mismatches": mismatches,
        "unexpected_nonzero": unexpected_nonzero,
        "final_nonzero_count": len(
            [
                item
                for item in final_entries
                if abs(item["weight"]) > 1e-7
            ]
        ),
    }


def remove_existing_avatar_part(avatar, slot):
    part_type = avatar_part_type_for_slot(slot)
    avatar_id = scene_object_id(avatar)
    removals = []
    for part in avatar_parts_of_type(avatar, part_type):
        record = avatar_part_record(part)
        record["remove_status"] = checked(
            "Remove existing {} part".format(slot),
            RLPy.RScene.RemoveObject(part),
        )
        removals.append(record)
        QtWidgets.QApplication.processEvents()

    current_avatars = list(RLPy.RScene.GetAvatars() or [])
    matches = [
        candidate
        for candidate in current_avatars
        if scene_object_id(candidate) == avatar_id
    ]
    if len(matches) != 1:
        raise ReconstructionError(
            "Avatar identity changed while removing existing {}".format(slot)
        )
    avatar = matches[0]
    remaining = avatar_parts_of_type(avatar, part_type)
    if remaining:
        raise ReconstructionError(
            "Existing {} part was not fully removed before replacement".format(
                slot
            )
        )
    return avatar, {
        "mode": "remove_existing_avatar_part",
        "slot": slot,
        "avatar_part_constant": REPLACEABLE_AVATAR_PART_SLOTS[slot],
        "removed_count": len(removals),
        "removed_parts": removals,
        "remaining_count": len(remaining),
    }


def remove_existing_teeth_part(avatar):
    return remove_existing_avatar_part(avatar, "teeth")


def remove_existing_eye_part(avatar):
    return remove_existing_avatar_part(avatar, "eyes")


def normalized_dialog_text(value):
    return " ".join(
        str(value or "").replace("&", "").split()
    ).strip().lower()


UNDO_MANAGER_WARNING_TEXT = (
    "Failed to record undo/redo step. Undo manager will restart."
)
CHARACTER_PRESET_DIALOG_TITLE = "Apply Character Preset"
CHARACTER_PRESET_CHECKBOX_TEXTS = (
    "Apply Morph",
    "Apply Textures",
    "Restore neutral lash strip before application.",
)
SKIN_MATERIAL_DIALOG_TITLE = "Apply Material"
SKIN_MATERIAL_CHECKBOX_STATES = (
    ("Material Settings and Textures", True),
    ("Ignore Head Diffuse Texture", False),
    ("Ignore Head Normal Texture", False),
    ("Apply Head Color to Body", True),
    ("Shader Textures", True),
    ("Shader Parameters", True),
    ("Expression Wrinkles", False),
    ("Don't show this again", False),
)


def cc_dialog_snapshot(widget):
    labels = []
    for label_widget in widget.findChildren(QtWidgets.QLabel):
        text = str(label_widget.text() or "")
        if text:
            labels.append(text)
    direct_text = []
    for method_name in ("text", "informativeText", "detailedText"):
        method = getattr(widget, method_name, None)
        if not callable(method):
            continue
        try:
            value = str(method() or "")
        except Exception:
            continue
        if value:
            direct_text.append(value)
    button_records = []
    for button in widget.findChildren(QtWidgets.QAbstractButton):
        button_records.append(
            {
                "class_name": type(button).__name__,
                "text": str(button.text() or ""),
                "visible": bool(button.isVisible()),
                "enabled": bool(button.isEnabled()),
                "checkable": bool(button.isCheckable()),
                "checked": (
                    bool(button.isChecked())
                    if button.isCheckable()
                    else None
                ),
            }
        )
    window_title = str(widget.windowTitle() or "")
    all_text = [window_title] + labels + direct_text + [
        item["text"] for item in button_records
    ]
    return {
        "class_name": type(widget).__name__,
        "window_title": window_title,
        "labels": labels,
        "direct_text": direct_text,
        "buttons": button_records,
        "normalized_text": normalized_dialog_text(" ".join(all_text)),
    }


def exact_dialog_buttons(
    widget,
    text,
    checkable=None,
    visible_only=True,
):
    target = normalized_dialog_text(text)
    matches = []
    for button in widget.findChildren(QtWidgets.QAbstractButton):
        if (
            (visible_only and not button.isVisible())
            or not button.isEnabled()
        ):
            continue
        if normalized_dialog_text(button.text()) != target:
            continue
        if (
            checkable is not None
            and bool(button.isCheckable()) != bool(checkable)
        ):
            continue
        matches.append(button)
    return matches


def exact_undo_warning_button(widget, snapshot=None):
    snapshot = snapshot or cc_dialog_snapshot(widget)
    expected_text = normalized_dialog_text(UNDO_MANAGER_WARNING_TEXT)
    text_matches = [
        text
        for text in snapshot["labels"] + snapshot["direct_text"]
        if normalized_dialog_text(text) == expected_text
    ]
    visible_action_buttons = [
        button
        for button in widget.findChildren(QtWidgets.QAbstractButton)
        if (
            button.isVisible()
            and button.isEnabled()
            and not button.isCheckable()
        )
    ]
    if (
        normalized_dialog_text(snapshot["window_title"])
        == normalized_dialog_text("Character Creator 5")
        and len(text_matches) == 1
        and len(visible_action_buttons) == 1
        and normalized_dialog_text(visible_action_buttons[0].text())
        == normalized_dialog_text("OK")
    ):
        return visible_action_buttons[0]
    return None


class ExactUndoWarningGuard(object):
    """Dismiss only CC's exact known Undo Manager warning for a whole run."""

    def __init__(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.inspect)
        self.handled_widgets = set()
        self.report = {
            "policy": "exact_undo_warning_whole_run",
            "required_text": UNDO_MANAGER_WARNING_TEXT,
            "poll_count": 0,
            "matched_count": 0,
            "clicked_count": 0,
            "dialogs": [],
        }

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def inspect(self):
        self.report["poll_count"] += 1
        candidates = []
        active = QtWidgets.QApplication.activeModalWidget()
        if active is not None:
            candidates.append(active)
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if not widget.isVisible():
                continue
            if any(widget is candidate for candidate in candidates):
                continue
            candidates.append(widget)
        for widget in candidates:
            snapshot = cc_dialog_snapshot(widget)
            button = exact_undo_warning_button(widget, snapshot)
            if button is None:
                continue
            widget_key = id(widget)
            if widget_key in self.handled_widgets:
                return
            self.handled_widgets.add(widget_key)
            self.report["matched_count"] += 1
            if len(self.report["dialogs"]) < 20:
                serializable = dict(snapshot)
                serializable.pop("normalized_text", None)
                serializable["handled_at"] = now()
                self.report["dialogs"].append(serializable)
            button.click()
            self.report["clicked_count"] += 1
            return


def load_file_with_known_cc_dialogs(
    path,
    label,
    require_character_preset=False,
    allow_character_preset=False,
    require_skin_material=False,
):
    if require_character_preset and require_skin_material:
        raise ReconstructionError(
            "Only one required CC dialog policy may be active"
        )
    character_preset_enabled = bool(
        require_character_preset or allow_character_preset
    )
    report = {
        "policy": (
            "character_preset_exact_dialog"
            if require_character_preset
            else (
                "optional_character_preset_exact_dialog"
                if allow_character_preset
                else (
                    "skin_material_exact_dialog"
                    if require_skin_material
                    else "optional_undo_warning_exact_dialog"
                )
            )
        ),
        "path": path,
        "undo_warning": {
            "required_text": UNDO_MANAGER_WARNING_TEXT,
            "matched_count": 0,
            "clicked_count": 0,
        },
        "character_preset": {
            "allowed": character_preset_enabled,
            "required": bool(require_character_preset),
            "required_title": CHARACTER_PRESET_DIALOG_TITLE,
            "required_checkboxes": list(
                CHARACTER_PRESET_CHECKBOX_TEXTS
            ),
            "target_button": "Apply",
            "matched_count": 0,
            "clicked_count": 0,
        },
        "skin_material": {
            "required": bool(require_skin_material),
            "required_title": SKIN_MATERIAL_DIALOG_TITLE,
            "required_checkbox_states": dict(
                SKIN_MATERIAL_CHECKBOX_STATES
            ),
            "target_button": "Apply",
            "matched_count": 0,
            "clicked_count": 0,
        },
        "poll_count": 0,
        "observed_dialogs": [],
        "fatal_unknown_dialog": None,
    }
    timer = QtCore.QTimer()
    timer.setInterval(100)
    handled_undo_widgets = set()
    character_preset_handled = [False]
    skin_material_handled = [False]
    unknown_poll_counts = {}

    def remember_snapshot(snapshot, is_active_modal):
        if len(report["observed_dialogs"]) >= 12:
            return
        serializable = dict(snapshot)
        serializable.pop("normalized_text", None)
        serializable["active_modal"] = bool(is_active_modal)
        if serializable not in report["observed_dialogs"]:
            report["observed_dialogs"].append(serializable)

    def cancel_unknown_dialog(widget, snapshot):
        if report["fatal_unknown_dialog"] is not None:
            return
        report["fatal_unknown_dialog"] = dict(snapshot)
        report["fatal_unknown_dialog"].pop("normalized_text", None)
        cancel_buttons = exact_dialog_buttons(
            widget, "Cancel", checkable=False
        )
        if len(cancel_buttons) == 1:
            cancel_buttons[0].click()
            report["fatal_unknown_dialog"]["close_action"] = (
                "exact_cancel_button"
            )
            return
        reject = getattr(widget, "reject", None)
        if callable(reject):
            reject()
            report["fatal_unknown_dialog"]["close_action"] = "reject"
            return
        widget.close()
        report["fatal_unknown_dialog"]["close_action"] = "close"

    def inspect_dialogs():
        report["poll_count"] += 1
        active = QtWidgets.QApplication.activeModalWidget()
        candidates = []
        if active is not None:
            candidates.append((active, True))
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if not widget.isVisible():
                continue
            if any(widget is item[0] for item in candidates):
                continue
            is_dialog = isinstance(widget, QtWidgets.QDialog)
            is_modal = False
            modal_method = getattr(widget, "isModal", None)
            if callable(modal_method):
                try:
                    is_modal = bool(modal_method())
                except Exception:
                    is_modal = False
            if not is_dialog and not is_modal:
                continue
            candidates.append((widget, False))

        for widget, is_active_modal in candidates:
            snapshot = cc_dialog_snapshot(widget)
            normalized = snapshot["normalized_text"]
            if (
                is_active_modal
                or normalized_dialog_text(
                    UNDO_MANAGER_WARNING_TEXT
                ) in normalized
                or normalized_dialog_text(
                    CHARACTER_PRESET_DIALOG_TITLE
                ) in normalized
                or normalized_dialog_text(
                    SKIN_MATERIAL_DIALOG_TITLE
                ) in normalized
            ):
                remember_snapshot(snapshot, is_active_modal)

            widget_key = id(widget)
            undo_button = exact_undo_warning_button(widget, snapshot)
            if undo_button is not None:
                if (
                    widget_key not in handled_undo_widgets
                ):
                    handled_undo_widgets.add(widget_key)
                    report["undo_warning"]["matched_count"] += 1
                    undo_button.click()
                    report["undo_warning"]["clicked_count"] += 1
                return

            has_character_preset_title = normalized_dialog_text(
                CHARACTER_PRESET_DIALOG_TITLE
            ) in normalized
            checkbox_matches = {}
            if has_character_preset_title:
                for checkbox_text in CHARACTER_PRESET_CHECKBOX_TEXTS:
                    checkbox_matches[checkbox_text] = (
                        exact_dialog_buttons(
                            widget,
                            checkbox_text,
                            checkable=True,
                        )
                    )
            apply_buttons = (
                exact_dialog_buttons(widget, "Apply", checkable=False)
                if has_character_preset_title
                else []
            )
            cancel_buttons = (
                exact_dialog_buttons(widget, "Cancel", checkable=False)
                if has_character_preset_title
                else []
            )
            exact_character_preset = (
                has_character_preset_title
                and all(
                    len(checkbox_matches[item]) == 1
                    for item in CHARACTER_PRESET_CHECKBOX_TEXTS
                )
                and len(apply_buttons) == 1
                and len(cancel_buttons) == 1
            )
            if (
                exact_character_preset
                and character_preset_enabled
                and not character_preset_handled[0]
            ):
                character_preset_handled[0] = True
                preset_report = report["character_preset"]
                preset_report["matched_count"] += 1
                preset_report["checkbox_state_before"] = {
                    item: bool(checkbox_matches[item][0].isChecked())
                    for item in CHARACTER_PRESET_CHECKBOX_TEXTS
                }
                for checkbox_text in CHARACTER_PRESET_CHECKBOX_TEXTS:
                    checkbox_matches[checkbox_text][0].setChecked(True)
                preset_report["checkbox_state_after"] = {
                    item: bool(checkbox_matches[item][0].isChecked())
                    for item in CHARACTER_PRESET_CHECKBOX_TEXTS
                }
                if not all(
                    preset_report["checkbox_state_after"].values()
                ):
                    preset_report["configuration_error"] = (
                        "A required checkbox could not be enabled"
                    )
                    cancel_buttons[0].click()
                    return
                apply_buttons[0].click()
                preset_report["clicked_count"] += 1
                return

            has_skin_material_title = normalized_dialog_text(
                SKIN_MATERIAL_DIALOG_TITLE
            ) in normalized
            skin_checkbox_matches = {}
            if has_skin_material_title:
                for checkbox_text, unused_state in (
                    SKIN_MATERIAL_CHECKBOX_STATES
                ):
                    skin_checkbox_matches[checkbox_text] = (
                        exact_dialog_buttons(
                            widget,
                            checkbox_text,
                            checkable=True,
                            visible_only=False,
                        )
                    )
            skin_apply_buttons = (
                exact_dialog_buttons(widget, "Apply", checkable=False)
                if has_skin_material_title
                else []
            )
            skin_cancel_buttons = (
                exact_dialog_buttons(widget, "Cancel", checkable=False)
                if has_skin_material_title
                else []
            )
            exact_skin_material = (
                has_skin_material_title
                and all(
                    len(skin_checkbox_matches[item]) == 1
                    for item, unused_state
                    in SKIN_MATERIAL_CHECKBOX_STATES
                )
                and len(skin_apply_buttons) == 1
                and len(skin_cancel_buttons) == 1
            )
            if (
                exact_skin_material
                and require_skin_material
                and not skin_material_handled[0]
            ):
                skin_material_handled[0] = True
                skin_report = report["skin_material"]
                skin_report["matched_count"] += 1
                skin_report["checkbox_state_before"] = {
                    item: bool(
                        skin_checkbox_matches[item][0].isChecked()
                    )
                    for item, unused_state
                    in SKIN_MATERIAL_CHECKBOX_STATES
                }
                for checkbox_text, target_state in (
                    SKIN_MATERIAL_CHECKBOX_STATES
                ):
                    skin_checkbox_matches[checkbox_text][0].setChecked(
                        bool(target_state)
                    )
                skin_report["checkbox_state_after"] = {
                    item: bool(
                        skin_checkbox_matches[item][0].isChecked()
                    )
                    for item, unused_state
                    in SKIN_MATERIAL_CHECKBOX_STATES
                }
                expected_states = dict(
                    SKIN_MATERIAL_CHECKBOX_STATES
                )
                if skin_report["checkbox_state_after"] != expected_states:
                    skin_report["configuration_error"] = (
                        "A required skin material checkbox state "
                        "could not be enforced"
                    )
                    skin_cancel_buttons[0].click()
                    return
                skin_apply_buttons[0].click()
                skin_report["clicked_count"] += 1
                return

            if not is_active_modal:
                continue
            unknown_key = (
                snapshot["window_title"],
                tuple(snapshot["labels"]),
                tuple(snapshot["direct_text"]),
                tuple(
                    item["text"] for item in snapshot["buttons"]
                ),
            )
            unknown_poll_counts[unknown_key] = (
                unknown_poll_counts.get(unknown_key, 0) + 1
            )
            if unknown_poll_counts[unknown_key] >= 15:
                cancel_unknown_dialog(widget, snapshot)
                return

    timer.timeout.connect(inspect_dialogs)
    timer.start()
    try:
        raw_status = RLPy.RFileIO.LoadFile(path)
    finally:
        timer.stop()
    report["load_returned"] = True

    if report["fatal_unknown_dialog"] is not None:
        raise ReconstructionError(
            "Unknown CC modal dialog cancelled while loading {}: {}".format(
                label,
                json.dumps(
                    report["fatal_unknown_dialog"],
                    sort_keys=True,
                    ensure_ascii=True,
                ),
            )
        )
    preset_report = report["character_preset"]
    if preset_report.get("configuration_error"):
        raise ReconstructionError(
            "Character preset dialog could not be configured safely"
        )
    if require_character_preset and (
        preset_report["matched_count"] != 1
        or preset_report["clicked_count"] != 1
    ):
        raise ReconstructionError(
            "Character preset load did not resolve the exact dialog"
        )
    if (
        allow_character_preset
        and preset_report["matched_count"]
        != preset_report["clicked_count"]
    ):
        raise ReconstructionError(
            "Optional Character Preset dialog was not resolved exactly"
        )
    skin_report = report["skin_material"]
    if skin_report.get("configuration_error"):
        raise ReconstructionError(
            "Skin material dialog could not be configured safely"
        )
    if require_skin_material and (
        skin_report["matched_count"] != 1
        or skin_report["clicked_count"] != 1
    ):
        raise ReconstructionError(
            "Skin material load did not resolve the exact dialog"
        )
    return checked(label, raw_status), report


def load_file_with_optional_undo_warning(path, label):
    return load_file_with_known_cc_dialogs(
        path,
        label,
        require_character_preset=False,
    )


def load_file_with_character_preset_dialog(path, label):
    return load_file_with_known_cc_dialogs(
        path,
        label,
        require_character_preset=True,
    )


def load_file_with_optional_character_preset_dialog(path, label):
    return load_file_with_known_cc_dialogs(
        path,
        label,
        allow_character_preset=True,
    )


def load_file_with_skin_material_dialog(path, label):
    return load_file_with_known_cc_dialogs(
        path,
        label,
        require_skin_material=True,
    )


def load_file_with_exact_replacement_dialog(
    path,
    label,
    target_button,
    policy,
):
    report = {
        "policy": policy,
        "expected_window_title": "Character Creator 5",
        "required_text": [
            "The target object layer already exists.",
            "Do you want to replace the object, or the material only?",
        ],
        "target_button": target_button,
        "poll_count": 0,
        "matched_count": 0,
        "clicked_count": 0,
        "observed_dialogs": [],
    }
    required_text = [
        normalized_dialog_text(item) for item in report["required_text"]
    ]
    target_button_text = normalized_dialog_text(
        report["target_button"]
    )
    timer = QtCore.QTimer()
    timer.setInterval(100)

    def inspect_dialogs():
        report["poll_count"] += 1
        candidates = []
        active = QtWidgets.QApplication.activeModalWidget()
        if active is not None:
            candidates.append(active)
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if widget not in candidates and widget.isVisible():
                candidates.append(widget)
        for widget in candidates:
            labels = []
            for label_widget in widget.findChildren(QtWidgets.QLabel):
                text = str(label_widget.text() or "")
                if text:
                    labels.append(text)
            direct_text = []
            for method_name in ("text", "informativeText", "detailedText"):
                method = getattr(widget, method_name, None)
                if not callable(method):
                    continue
                try:
                    value = str(method() or "")
                except Exception:
                    continue
                if value:
                    direct_text.append(value)
            all_text = labels + direct_text
            normalized = normalized_dialog_text(" ".join(all_text))
            buttons = list(widget.findChildren(QtWidgets.QPushButton))
            button_names = [
                str(button.text() or "") for button in buttons
            ]
            title = str(widget.windowTitle() or "")
            if (
                len(report["observed_dialogs"]) < 8
                and (all_text or button_names)
            ):
                snapshot = {
                    "window_title": title,
                    "text": all_text,
                    "buttons": button_names,
                }
                if snapshot not in report["observed_dialogs"]:
                    report["observed_dialogs"].append(snapshot)
            if normalized_dialog_text(title) != normalized_dialog_text(
                report["expected_window_title"]
            ):
                continue
            if not all(item in normalized for item in required_text):
                continue
            target = None
            for button in buttons:
                if normalized_dialog_text(
                    button.text()
                ) == target_button_text:
                    target = button
                    break
            if target is None:
                continue
            report["matched_count"] += 1
            target.click()
            report["clicked_count"] += 1
            report["matched_window_title"] = title
            report["matched_text"] = all_text
            report["matched_buttons"] = button_names
            timer.stop()
            return

    timer.timeout.connect(inspect_dialogs)
    timer.start()
    try:
        raw_status = RLPy.RFileIO.LoadFile(path)
    finally:
        timer.stop()
    report["load_returned"] = True
    status = checked(label, raw_status)
    if report["clicked_count"] != 1:
        raise ReconstructionError(
            "{} load did not resolve the exact replacement dialog".format(
                target_button
            )
        )
    return status, report


def load_file_with_material_only_dialog(path, label):
    return load_file_with_exact_replacement_dialog(
        path,
        label,
        "Material Only",
        "material_only_exact_dialog",
    )


def load_file_with_replace_dialog(path, label):
    if not os.path.isfile(REPLACE_DIALOG_GUARD_PATH):
        raise ReconstructionError(
            "Replace dialog guard is missing: {}".format(
                REPLACE_DIALOG_GUARD_PATH
            )
        )
    os.makedirs(REPLACE_DIALOG_GUARD_OUTPUT_ROOT, exist_ok=True)
    guard_id = "{}_{}".format(
        datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        hashlib.sha256(
            "{}|{}|{}".format(path, label, os.getpid()).encode("utf-8")
        ).hexdigest()[:12],
    )
    ready_path = os.path.join(
        REPLACE_DIALOG_GUARD_OUTPUT_ROOT,
        guard_id + ".ready.json",
    )
    log_path = os.path.join(
        REPLACE_DIALOG_GUARD_OUTPUT_ROOT,
        guard_id + ".jsonl",
    )
    report = {
        "policy": "replace_object_cc_spawned_dialog_guard",
        "expected_window_title": "Character Creator 5",
        "required_text": [
            "The target object layer already exists.",
            "Do you want to replace the object, or the material only?",
        ],
        "target_button": "Replace",
        "guard_path": REPLACE_DIALOG_GUARD_PATH,
        "guard_ready_path": ready_path,
        "guard_log_path": log_path,
        "guard_process_id": None,
        "guard_return_code": None,
        "guard_events": [],
    }
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        REPLACE_DIALOG_GUARD_PATH,
        "-TargetProcessId",
        str(os.getpid()),
        "-ReadyPath",
        ready_path,
        "-LogPath",
        log_path,
        "-TimeoutSeconds",
        "90",
        "-PollMilliseconds",
        "75",
    ]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    guard = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creation_flags,
    )
    report["guard_process_id"] = int(guard.pid)
    try:
        ready_deadline = time.time() + 12.0
        while not os.path.isfile(ready_path):
            return_code = guard.poll()
            if return_code is not None:
                raise ReconstructionError(
                    "Replace dialog guard exited before becoming ready: {}".format(
                        return_code
                    )
                )
            if time.time() >= ready_deadline:
                raise ReconstructionError(
                    "Timed out waiting for Replace dialog guard readiness"
                )
            time.sleep(0.05)

        raw_status = RLPy.RFileIO.LoadFile(path)
        report["load_returned"] = True
        try:
            report["guard_return_code"] = int(guard.wait(timeout=10.0))
        except subprocess.TimeoutExpired:
            guard.terminate()
            guard.wait(timeout=5.0)
            raise ReconstructionError(
                "Replace dialog guard did not finish after the load returned"
            )
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8-sig") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        report["guard_events"].append(json.loads(line))
                    except ValueError:
                        report["guard_events"].append({"raw": line})
        if report["guard_return_code"] != 0:
            raise ReconstructionError(
                "Replace dialog guard failed with code {}".format(
                    report["guard_return_code"]
                )
            )
        if not any(
            item.get("event") == "confirmed"
            for item in report["guard_events"]
            if isinstance(item, dict)
        ):
            raise ReconstructionError(
                "Replace dialog guard did not record a confirmed dialog"
            )
        status = checked(label, raw_status)
        return status, report
    finally:
        if guard.poll() is None:
            guard.terminate()
        try:
            if os.path.isfile(ready_path):
                os.remove(ready_path)
        except OSError:
            pass


def apply_appearance_assets(
    avatar,
    assets,
    cleanup_names=None,
    allow_missing_cleanup=False,
    progress_callback=None,
    asset_load_pacing=None,
):
    asset_load_pacing = asset_load_pacing or {
        "default_after_seconds": 0.0,
        "default_before_seconds": 0.0,
        "slots": {},
    }
    if progress_callback:
        progress_callback("appearance_cleanup")
    avatar, cleanup = remove_base_clothing(
        avatar,
        cleanup_names or [],
        allow_missing=allow_missing_cleanup,
    )
    initial = cleanup["after_inventory"]
    previous = initial
    avatar_id = scene_object_id(avatar)
    steps = []
    previous_material = None
    for item in assets:
        pacing = asset_load_pacing_for_slot(
            asset_load_pacing,
            item["slot"],
        )
        if progress_callback:
            progress_callback(
                "appearance_asset",
                {
                    "asset_id": item["asset_id"],
                    "display_name": item["display_name"],
                    "load_pacing": pacing,
                    "slot": item["slot"],
                },
            )
        verification_mode = item["verification_mode"]
        if verification_mode == "material_fingerprint" and previous_material is None:
            previous_material = avatar_material_fingerprint(avatar)
        replacement_preparation = None
        eye_support_before = None
        eye_support_restoration = None
        eye_part_before = None
        eye_part_after = None
        eye_geometry_preserved = None
        eye_support_preserved = None
        material_only_dialog = (
            item["slot"] in MATERIAL_ONLY_DIALOG_SLOTS
        )
        character_preset_dialog = (
            item["slot"] in CHARACTER_PRESET_DIALOG_SLOTS
        )
        dialog_policy = None
        if item["slot"] in ("eyes", "eyelashes"):
            eye_support_before = capture_eye_part_morph_weights(avatar)
            eye_part_type = avatar_part_type_for_slot("eyes")
            eye_part_before = [
                avatar_part_record(part)
                for part in avatar_parts_of_type(avatar, eye_part_type)
            ]
        replaceable_avatar_part = (
            item["slot"] in REPLACEABLE_AVATAR_PART_SLOTS
            and not material_only_dialog
            and not character_preset_dialog
        )
        if replaceable_avatar_part:
            avatar, replacement_preparation = remove_existing_avatar_part(
                avatar, item["slot"]
            )
        RLPy.RScene.SelectObject(avatar)
        settle_cc_ui(pacing["before_seconds"])
        load_label = "Load appearance {}".format(item["asset_id"])
        if item["slot"] in ("skin", "skin_preset"):
            status, dialog_policy = load_file_with_skin_material_dialog(
                item["path"],
                load_label,
            )
        elif material_only_dialog:
            status, dialog_policy = load_file_with_material_only_dialog(
                item["path"],
                load_label,
            )
        elif character_preset_dialog:
            status, dialog_policy = (
                load_file_with_character_preset_dialog(
                    item["path"],
                    load_label,
                )
            )
        else:
            status, dialog_policy = load_file_with_optional_undo_warning(
                item["path"],
                load_label,
            )
        settle_cc_ui(pacing["after_seconds"])
        current_avatars = list(RLPy.RScene.GetAvatars() or [])
        matches = [candidate for candidate in current_avatars if scene_object_id(candidate) == avatar_id]
        if len(matches) != 1:
            raise ReconstructionError(
                "Avatar identity changed while loading {}".format(item["asset_id"])
            )
        avatar = matches[0]
        if item["slot"] == "eyes" and replaceable_avatar_part:
            eye_support_restoration = restore_eye_part_morph_weights(
                avatar,
                eye_support_before,
            )
        if item["slot"] in ("eyes", "eyelashes"):
            eye_part_type = avatar_part_type_for_slot("eyes")
            eye_part_after = [
                avatar_part_record(part)
                for part in avatar_parts_of_type(avatar, eye_part_type)
            ]
            before_geometry = direct_avatar_part_signature(
                eye_part_before
            )
            after_geometry = direct_avatar_part_signature(
                eye_part_after
            )
            eye_geometry_preserved = (
                before_geometry == after_geometry
            )
            eye_support_after = capture_eye_part_morph_weights(avatar)
            before_support = dict(
                (entry["id"], float(entry["weight"]))
                for entry in eye_support_before
            )
            after_support = dict(
                (entry["id"], float(entry["weight"]))
                for entry in eye_support_after
            )
            eye_support_preserved = (
                set(before_support) == set(after_support)
                and all(
                    abs(after_support[morph_id] - weight) <= 1e-7
                    for morph_id, weight in before_support.items()
                )
            )
        character_preset_inventory = None
        character_preset_verified = None
        if character_preset_dialog:
            part_type = avatar_part_type_for_slot(item["slot"])
            character_preset_inventory = [
                avatar_part_record(part)
                for part in avatar_parts_of_type(avatar, part_type)
            ]
            preset_policy = (
                (dialog_policy or {}).get("character_preset") or {}
            )
            character_preset_verified = bool(
                preset_policy.get("matched_count") == 1
                and preset_policy.get("clicked_count") == 1
                and character_preset_inventory
                and eye_geometry_preserved is True
                and eye_support_preserved is True
            )
        replacement_inventory = None
        if replaceable_avatar_part:
            part_type = avatar_part_type_for_slot(item["slot"])
            replacement_parts = avatar_parts_of_type(avatar, part_type)
            replacement_inventory = [
                avatar_part_record(part) for part in replacement_parts
            ]
            if (
                not replacement_inventory
                and item["slot"]
                not in DUAL_REPRESENTATION_AVATAR_PART_SLOTS
            ):
                raise ReconstructionError(
                    "{} asset load did not create its avatar part".format(
                        item["slot"]
                    )
                )
        replacement_verified = bool(
            replaceable_avatar_part
            and replacement_preparation is not None
            and replacement_preparation["remaining_count"] == 0
            and replacement_inventory
        )
        current = avatar_asset_inventory(avatar)
        previous_by_id = dict((record["id"], record) for record in previous["objects"])
        current_by_id = dict((record["id"], record) for record in current["objects"])
        added = [current_by_id[key] for key in sorted(set(current_by_id) - set(previous_by_id))]
        removed = [previous_by_id[key] for key in sorted(set(previous_by_id) - set(current_by_id))]
        scene_changed = current["objects"] != previous["objects"]
        material_before = previous_material
        material_after = None
        material_changed = False
        material_changed_meshes = []
        if verification_mode == "material_fingerprint":
            material_after = avatar_material_fingerprint(avatar)
            material_changed = material_after["digest"] != material_before["digest"]
            before_mesh_digests = material_before.get("mesh_digests") or {}
            after_mesh_digests = material_after.get("mesh_digests") or {}
            material_changed_meshes = sorted(
                mesh_name
                for mesh_name in (
                    set(before_mesh_digests) | set(after_mesh_digests)
                )
                if before_mesh_digests.get(mesh_name)
                != after_mesh_digests.get(mesh_name)
            )
            previous_material = material_after
        material_only_verified = None
        if material_only_dialog:
            material_only_verified = bool(
                dialog_policy
                and dialog_policy.get("clicked_count") == 1
                and eye_geometry_preserved is True
                and eye_support_preserved is True
                and material_changed is True
                and material_changed_meshes == ["CC_Base_Eye"]
            )
        step = {
            "asset_id": item["asset_id"],
            "display_name": item["display_name"],
            "slot": item["slot"],
            "asset_form": item["asset_form"],
            "extension": item["extension"],
            "verification_mode": verification_mode,
            "resolved_path": item["path"],
            "load_status": status,
            "load_pacing": pacing,
            "replacement_preparation": replacement_preparation,
            "replacement_inventory": replacement_inventory,
            "replacement_verified": replacement_verified,
            "character_preset_dialog": character_preset_dialog,
            "character_preset_inventory": character_preset_inventory,
            "character_preset_verified": character_preset_verified,
            "eye_support_restoration": eye_support_restoration,
            "material_only_dialog": material_only_dialog,
            "replace_dialog": False,
            "dialog_policy": dialog_policy,
            "eye_part_before": eye_part_before,
            "eye_part_after": eye_part_after,
            "eye_geometry_preserved": eye_geometry_preserved,
            "eye_support_preserved": eye_support_preserved,
            "material_only_verified": material_only_verified,
            "scene_changed": scene_changed,
            "material_changed": material_changed,
            "material_changed_meshes": material_changed_meshes,
            "material_before": material_before,
            "material_after": material_after,
            "added_objects": added,
            "removed_objects": removed,
            "object_count_after": current["object_count"],
        }
        steps.append(step)
        if (
            verification_mode == "scene_inventory"
            and not scene_changed
            and replacement_verified is not True
            and character_preset_verified is not True
        ):
            if progress_callback:
                progress_callback(
                    "appearance_asset_verification_failed",
                    {
                        "asset_id": item["asset_id"],
                        "slot": item["slot"],
                        "scene_changed": scene_changed,
                        "replacement_verified": replacement_verified,
                        "character_preset_verified": (
                            character_preset_verified
                        ),
                        "character_preset_part_count": len(
                            character_preset_inventory or []
                        ),
                        "eye_geometry_preserved": (
                            eye_geometry_preserved
                        ),
                        "eye_support_preserved": eye_support_preserved,
                    },
                )
            raise ReconstructionError(
                "Appearance load produced no verified scene or avatar-part replacement: {}".format(
                    item["asset_id"]
                )
            )
        if (
            verification_mode == "material_fingerprint"
            and not material_changed
            and not replacement_verified
        ):
            raise ReconstructionError(
                "Appearance load produced no material fingerprint change: {}".format(
                    item["asset_id"]
                )
            )
        previous = current
    return avatar, {
        "asset_count": len(assets),
        "asset_ids": [item["asset_id"] for item in assets],
        "asset_load_pacing": asset_load_pacing,
        "preload_cleanup": cleanup,
        "initial_inventory": initial,
        "final_inventory": previous,
        "steps": steps,
    }


def set_dynamic_wrinkle_strength(avatar, strength):
    component = avatar.GetMaterialComponent()
    if component is None:
        raise ReconstructionError(
            "Avatar has no material component for dynamic wrinkles"
        )
    strength = float(strength)
    strength_results = []
    for constant_name in WRINKLE_FACE_PART_CONSTANTS:
        face_part = getattr(RLPy, constant_name, None)
        if face_part is None:
            raise ReconstructionError(
                "CC runtime lacks wrinkle face-part constant: {}".format(
                    constant_name
                )
            )
        strength_results.append(
            {
                "face_part": constant_name,
                "status": checked(
                    "Set dynamic wrinkle strength {}".format(
                        constant_name
                    ),
                    component.SetWrinkleDetailStrength(
                        face_part, strength
                    ),
                ),
            }
        )
    return {
        "strength": strength,
        "strength_results": strength_results,
    }


def apply_dynamic_wrinkle_strength(avatar, strength):
    before_material = avatar_material_fingerprint(avatar)
    before_vectors = capture_vectors(avatar)
    strength_application = set_dynamic_wrinkle_strength(
        avatar, strength
    )
    after_vectors = capture_vectors(avatar)
    morph_deltas = {
        classification: group_delta(
            before_vectors["groups"][classification]["entries"],
            after_vectors["groups"][classification]["entries"],
        )
        for classification in ("body", "junction", "face", "other")
    }
    if any(morph_deltas.values()):
        raise ReconstructionError(
            "Dynamic wrinkle profile changed protected Morph weights"
        )
    after_material = avatar_material_fingerprint(avatar)
    result = {
        "material_changed": (
            before_material["digest"] != after_material["digest"]
        ),
        "material_digest_after": after_material["digest"],
        "material_digest_before": before_material["digest"],
        "morph_deltas": morph_deltas,
        "strength": strength_application["strength"],
        "strength_results": strength_application["strength_results"],
    }
    return avatar, result


def apply_dynamic_wrinkle_profile(
    avatar,
    profile,
    strength,
):
    path = canonical_existing_file(
        profile.get("path"), "Dynamic wrinkle profile"
    )
    expected_sha256 = profile.get("sha256")
    if (
        isinstance(expected_sha256, str)
        and sha256_file(path) != expected_sha256
    ):
        raise ReconstructionError(
            "Dynamic wrinkle profile hash changed"
        )
    application_mode = profile.get("application_mode")
    if application_mode != (
        "inherit_neutral_bodyfit_profile_set_strength"
    ):
        raise ReconstructionError(
            "Unsupported dynamic wrinkle application mode: {}".format(
                application_mode
            )
        )
    avatar, result = apply_dynamic_wrinkle_strength(
        avatar, strength
    )
    result.update(
        {
            "application_mode": application_mode,
            "direct_rlwrinkle_load_supported": False,
            "profile_id": profile.get("asset_id"),
            "resolved_path": path,
            "source_asset_reference_only": bool(
                profile.get("source_asset_reference_only")
            ),
        }
    )
    return avatar, result


def facial_assembly_asset_ids(preset):
    keys = (
        "skin_asset_id",
        "teeth_asset_id",
        "eyebrow_asset_id",
        "eyelash_asset_id",
        "eye_asset_id",
        "facial_hair_asset_id",
        "scalp_hair_asset_id",
    )
    return [
        preset.get(key)
        for key in keys
        if preset.get(key) is not None
    ]


def apply_facial_assembly(
    avatar,
    preset,
    appearance_catalog,
    progress_callback=None,
    asset_load_pacing=None,
):
    assembly = preset.get("facial_assembly")
    if assembly is None:
        return avatar, None
    if not isinstance(assembly, dict):
        raise ReconstructionError("facial_assembly must be an object")
    application_order = assembly.get("application_order")
    if application_order != list(FACIAL_ASSEMBLY_ORDER):
        raise ReconstructionError(
            "facial_assembly application order differs from the "
            "canonical order"
        )
    expected_asset_ids = facial_assembly_asset_ids(preset)
    if assembly.get("asset_ids") != expected_asset_ids:
        raise ReconstructionError(
            "facial_assembly asset IDs differ from component fields"
        )
    if appearance_catalog is None:
        raise ReconstructionError(
            "facial_assembly requires appearance_catalog"
        )

    resolved_by_id = {}
    for asset_id in expected_asset_ids:
        resolved = resolve_appearance_assets(
            {
                "appearance_asset_ids": [asset_id],
                "sex": preset.get("sex"),
            },
            appearance_catalog,
        )
        if len(resolved) != 1:
            raise ReconstructionError(
                "Unable to resolve facial asset: {}".format(asset_id)
            )
        resolved_by_id[asset_id] = resolved[0]

    result = {
        "application_order": list(application_order),
        "asset_steps": [],
        "canonical_order_verified": True,
    }

    def apply_asset(field, expected_slot):
        nonlocal avatar
        asset_id = preset.get(field)
        if asset_id is None:
            return None
        asset = resolved_by_id[asset_id]
        if asset["slot"] != expected_slot:
            raise ReconstructionError(
                "{} resolves to {}, expected {}".format(
                    field, asset["slot"], expected_slot
                )
            )
        before = capture_vectors(avatar)
        avatar, application = apply_appearance_assets(
            avatar,
            [asset],
            cleanup_names=[],
            allow_missing_cleanup=True,
            progress_callback=progress_callback,
            asset_load_pacing=asset_load_pacing,
        )
        after = capture_vectors(avatar)
        deltas = {
            classification: group_delta(
                before["groups"][classification]["entries"],
                after["groups"][classification]["entries"],
            )
            for classification in ("body", "junction", "face", "other")
        }
        policy = evaluate_appearance_morph_policy(
            [asset],
            before,
            after,
            deltas,
        )
        if policy["status"] != "accepted":
            raise ReconstructionError(
                "Facial asset changed protected Morphs: {}".format(
                    asset_id
                )
            )
        step = {
            "application": application,
            "asset_id": asset_id,
            "morph_deltas": deltas,
            "morph_policy": policy,
            "slot": expected_slot,
        }
        result["asset_steps"].append(step)
        return step

    if progress_callback:
        progress_callback("facial_assembly_skin")
    apply_asset("skin_asset_id", "skin")

    if progress_callback:
        progress_callback("facial_assembly_age")
    age_morph_id = assembly.get("age_morph_id")
    result["age_morph"] = apply_single_morph_weight(
        avatar,
        age_morph_id,
        preset.get("full_face_elder_weight"),
        "age",
    )

    if progress_callback:
        progress_callback("facial_assembly_dynamic_wrinkles")
    avatar, result["dynamic_wrinkles"] = (
        apply_dynamic_wrinkle_profile(
            avatar,
            assembly.get("dynamic_wrinkle_profile") or {},
            preset.get("dynamic_wrinkle_strength"),
        )
    )

    if progress_callback:
        progress_callback("facial_assembly_teeth")
    apply_asset("teeth_asset_id", "teeth")
    if progress_callback:
        progress_callback("facial_assembly_eyebrows")
    apply_asset("eyebrow_asset_id", "eyebrows")
    if progress_callback:
        progress_callback("facial_assembly_eyelashes")
    apply_asset("eyelash_asset_id", "eyelashes")
    if progress_callback:
        progress_callback("facial_assembly_eyes")
    apply_asset("eye_asset_id", "eyes")
    if progress_callback:
        progress_callback("facial_assembly_facial_hair")
    apply_asset("facial_hair_asset_id", "facial_hair")
    if progress_callback:
        progress_callback("facial_assembly_scalp_hair")
    apply_asset("scalp_hair_asset_id", "scalp_hair")

    if progress_callback:
        progress_callback("facial_assembly_pigmentation")
    hair_color = assembly.get("hair_color")
    hair_asset_fields = (
        "eyebrow_asset_id",
        "facial_hair_asset_id",
        "scalp_hair_asset_id",
    )
    configured_hair_assets = [
        preset.get(field)
        for field in hair_asset_fields
        if preset.get(field) is not None
    ]
    if hair_color is None:
        if configured_hair_assets:
            raise ReconstructionError(
                "Shared hair pigmentation is required when facial hair "
                "assets are configured"
            )
        result["pigmentation"] = {
            "reason": "no_hair_assets",
            "status": "not_applicable",
        }
    else:
        result["pigmentation"] = apply_shared_hair_pigmentation(
            avatar,
            hair_color,
            preset.get("visible_gray_fraction"),
        )
    return avatar, result


def appearance_step_matches(step):
    verification_mode = step.get("verification_mode")
    if verification_mode == "material_fingerprint":
        if step.get("material_only_dialog") is True:
            return step.get("material_only_verified") is True
        return (
            step.get("material_changed") is True
            or step.get("replacement_verified") is True
        )
    if verification_mode == "scene_inventory":
        return (
            step.get("scene_changed") is True
            or step.get("replacement_verified") is True
            or step.get("character_preset_verified") is True
        )
    raise ReconstructionError(
        "Unsupported appearance verification mode: {}".format(
            verification_mode
        )
    )


def set_avatar_yaw(avatar, degrees):
    control = avatar.GetControl("Transform")
    if control is None:
        raise ReconstructionError("Avatar has no Transform control")
    data_block = control.GetDataBlock()
    if data_block is None:
        raise ReconstructionError("Avatar Transform control has no data block")
    time = RLPy.RGlobal.GetStartTime()
    checked(
        "Set avatar yaw {}".format(degrees),
        data_block.SetData(
            "Rotation/RotationZ", time, RLPy.RVariant(math.radians(degrees))
        ),
    )
    checked("Refresh avatar yaw", RLPy.RGlobal.SetTime(time, True))


def capture_bounds(scene_object):
    maximum = RLPy.RVector3()
    center = RLPy.RVector3()
    minimum = RLPy.RVector3()
    checked("Read object bounds", scene_object.GetBounds(maximum, center, minimum))
    return {
        "minimum": [float(minimum.x), float(minimum.y), float(minimum.z)],
        "center": [float(center.x), float(center.y), float(center.z)],
        "maximum": [float(maximum.x), float(maximum.y), float(maximum.z)],
    }


def resolve_face_subject_alignment(
    baseline_top_z,
    composed_top_z,
    camera_reference_top_z=None,
):
    if camera_reference_top_z is None:
        reference_top_z = float(baseline_top_z)
        reference_source = "source_project"
    else:
        if not isinstance(camera_reference_top_z, (int, float)):
            raise ReconstructionError(
                "face_camera_reference_top_z must be numeric"
            )
        reference_top_z = float(camera_reference_top_z)
        reference_source = "face_camera"
    return {
        "reference_source": reference_source,
        "reference_top_z": reference_top_z,
        "source_project_top_z": float(baseline_top_z),
        "composed_top_z": float(composed_top_z),
        "subject_z_offset": reference_top_z - float(composed_top_z),
    }


def set_avatar_position(avatar, position_x=None, position_y=None, position_z=None):
    control = avatar.GetControl("Transform")
    if control is None:
        raise ReconstructionError("Avatar has no Transform control")
    data_block = control.GetDataBlock()
    if data_block is None:
        raise ReconstructionError("Avatar Transform control has no data block")
    time = RLPy.RGlobal.GetStartTime()
    values = (
        ("Position/PositionX", position_x),
        ("Position/PositionY", position_y),
        ("Position/PositionZ", position_z),
    )
    for parameter_id, value in values:
        if value is None:
            continue
        checked(
            "Set avatar {} {}".format(parameter_id, value),
            data_block.SetData(
                parameter_id, time, RLPy.RVariant(float(value))
            ),
        )
    checked("Refresh avatar position", RLPy.RGlobal.SetTime(time, True))


def set_avatar_position_z(avatar, position_z):
    set_avatar_position(avatar, position_z=position_z)


def wait_for_rendered_preview(
    path,
    timeout_seconds=RENDER_PREVIEW_TIMEOUT_SECONDS,
    stable_seconds=RENDER_PREVIEW_STABLE_SECONDS,
):
    deadline = time.time() + float(timeout_seconds)
    stable_since = None
    last_signature = None
    while time.time() < deadline:
        QtWidgets.QApplication.processEvents()
        try:
            stat = os.stat(path)
            signature = (int(stat.st_size), int(stat.st_mtime_ns))
        except OSError:
            signature = None
        if signature is not None and signature[0] > 0:
            if signature == last_signature:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= float(stable_seconds):
                    return {
                        "bytes": signature[0],
                        "mtime_ns": signature[1],
                    }
            else:
                last_signature = signature
                stable_since = time.time()
        else:
            last_signature = None
            stable_since = None
        time.sleep(0.05)
    raise ReconstructionError(
        "Timed out waiting for rendered preview: {}".format(path)
    )


def render_preview(path, render_time=None):
    if render_time is None:
        render_time = RLPy.RGlobal.GetStartTime()
    if os.path.isfile(path):
        os.remove(path)
    original_view_size = current_view_size()
    try:
        checked(
            "Set deterministic render size",
            RLPy.RGlobal.SetViewSize(
                VIEWPORT_PREVIEW_WIDTH,
                VIEWPORT_PREVIEW_HEIGHT,
            ),
        )
        checked("Set render time", RLPy.RGlobal.SetTime(render_time, True))
        settle_cc_ui(RENDER_PREVIEW_SETTLE_SECONDS)
        checked("Render preview", RLPy.RGlobal.RenderImage(path))
        wait_for_rendered_preview(path)
        normalize_rendered_preview_image(path)
    finally:
        checked(
            "Restore render size",
            RLPy.RGlobal.SetViewSize(*original_view_size),
        )
        QtWidgets.QApplication.processEvents()


def normalize_rendered_preview_image(
    path,
    width=VIEWPORT_PREVIEW_WIDTH,
    height=VIEWPORT_PREVIEW_HEIGHT,
):
    from PySide2 import QtGui

    image = QtGui.QImage(path)
    if image.isNull():
        raise ReconstructionError(
            "Unable to read rendered preview for normalization: {}".format(
                path
            )
        )
    width = int(width)
    height = int(height)
    if image.width() == width and image.height() == height:
        return
    scaled = image.scaled(
        width,
        height,
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )
    canvas = QtGui.QImage(
        width,
        height,
        QtGui.QImage.Format_ARGB32,
    )
    canvas.fill(image.pixelColor(0, 0))
    painter = QtGui.QPainter(canvas)
    try:
        painter.drawImage(
            (width - scaled.width()) // 2,
            (height - scaled.height()) // 2,
            scaled,
        )
    finally:
        painter.end()
    temporary = path + ".normalize.tmp.png"
    if os.path.isfile(temporary):
        os.remove(temporary)
    if not canvas.save(temporary, "PNG"):
        raise ReconstructionError(
            "Unable to save normalized preview: {}".format(path)
        )
    os.replace(temporary, path)


def rendered_image_rmse(first_path, second_path, sample_size=128):
    from PySide2 import QtGui

    images = []
    for path in (first_path, second_path):
        image = QtGui.QImage(path)
        if image.isNull():
            raise ReconstructionError(
                "Unable to read evidence image: {}".format(path)
            )
        images.append(
            image.scaled(
                int(sample_size),
                int(sample_size),
                QtCore.Qt.IgnoreAspectRatio,
                QtCore.Qt.SmoothTransformation,
            ).convertToFormat(QtGui.QImage.Format_RGB32)
        )
    squared_error = 0.0
    channel_count = int(sample_size) * int(sample_size) * 3
    for y in range(int(sample_size)):
        for x in range(int(sample_size)):
            first_pixel = images[0].pixel(x, y)
            second_pixel = images[1].pixel(x, y)
            squared_error += (
                QtGui.qRed(first_pixel) - QtGui.qRed(second_pixel)
            ) ** 2
            squared_error += (
                QtGui.qGreen(first_pixel)
                - QtGui.qGreen(second_pixel)
            ) ** 2
            squared_error += (
                QtGui.qBlue(first_pixel) - QtGui.qBlue(second_pixel)
            ) ** 2
    return math.sqrt(squared_error / float(channel_count))


def current_native_cc_windows():
    import ctypes
    from ctypes import wintypes
    from shiboken2 import wrapInstance

    main_window = wrapInstance(
        int(RLPy.RUi.GetMainWindow()),
        QtWidgets.QMainWindow,
    )
    if main_window is None:
        raise ReconstructionError("Unable to wrap the CC main window")
    main_hwnd = int(main_window.winId())
    if main_hwnd <= 0:
        raise ReconstructionError("Unable to resolve the CC main HWND")

    user32 = ctypes.windll.user32

    class WindowRect(ctypes.Structure):
        _fields_ = (
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        )

    def window_record(hwnd):
        rectangle = WindowRect()
        if not user32.GetWindowRect(
            wintypes.HWND(hwnd),
            ctypes.byref(rectangle),
        ):
            return None
        width = int(rectangle.right - rectangle.left)
        height = int(rectangle.bottom - rectangle.top)
        class_buffer = ctypes.create_unicode_buffer(512)
        title_buffer = ctypes.create_unicode_buffer(1024)
        user32.GetClassNameW(
            wintypes.HWND(hwnd),
            class_buffer,
            len(class_buffer),
        )
        user32.GetWindowTextW(
            wintypes.HWND(hwnd),
            title_buffer,
            len(title_buffer),
        )
        return {
            "area": width * height,
            "class_name": class_buffer.value,
            "global_x": int(rectangle.left),
            "global_y": int(rectangle.top),
            "height": height,
            "hwnd": int(hwnd),
            "parent_hwnd": int(
                user32.GetParent(wintypes.HWND(hwnd)) or 0
            ),
            "title": title_buffer.value,
            "visible": bool(
                user32.IsWindowVisible(wintypes.HWND(hwnd))
            ),
            "width": width,
        }

    main_record = window_record(main_hwnd)
    if main_record is None:
        raise ReconstructionError("Unable to inspect the CC main HWND")
    hwnds = []
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @enum_proc_type
    def collect_window(hwnd, unused_lparam):
        hwnds.append(int(hwnd))
        return True

    if not user32.EnumChildWindows(
        wintypes.HWND(main_hwnd),
        collect_window,
        0,
    ):
        error_code = ctypes.get_last_error()
        if error_code:
            raise ReconstructionError(
                "EnumChildWindows failed with error {}".format(error_code)
            )
    records = []
    for hwnd in sorted(set(hwnds)):
        record = window_record(hwnd)
        if record is not None:
            records.append(record)
    return main_record, records


def select_native_viewport_record(main_record, records):
    main_x = int(main_record["global_x"])
    main_y = int(main_record["global_y"])
    main_width = int(main_record["width"])
    main_height = int(main_record["height"])
    main_right = main_x + main_width
    main_bottom = main_y + main_height
    candidates = []
    for record in records:
        width = int(record.get("width", 0))
        height = int(record.get("height", 0))
        if not record.get("visible") or width < 320 or height < 320:
            continue
        class_name = str(record.get("class_name", ""))
        if "QWindow" not in class_name or "OwnDC" in class_name:
            continue
        x = int(record.get("global_x", 0))
        y = int(record.get("global_y", 0))
        if (
            x < main_x - 32
            or y < main_y - 32
            or x + width > main_right + 32
            or y + height > main_bottom + 32
        ):
            continue
        center_x_ratio = (
            (x + (width / 2.0) - main_x) / float(main_width)
        )
        center_y_ratio = (
            (y + (height / 2.0) - main_y) / float(main_height)
        )
        aspect = width / float(height)
        if not 0.30 <= center_x_ratio <= 0.72:
            continue
        if not 0.20 <= center_y_ratio <= 0.82:
            continue
        if not 0.35 <= aspect <= 3.0:
            continue
        candidate = dict(record)
        candidate["center_x_ratio"] = center_x_ratio
        candidate["center_y_ratio"] = center_y_ratio
        candidates.append(candidate)
    if not candidates:
        raise ReconstructionError(
            "Unable to identify the native CC viewport HWND"
        )
    candidates.sort(
        key=lambda item: (
            int(item["area"]),
            abs(float(item["center_x_ratio"]) - 0.5),
            int(item["hwnd"]),
        )
    )
    return candidates[0]


def save_native_viewport_frame(
    path,
    pixmap,
    capture_mode="native_viewport_hwnd_v1",
):
    from PySide2 import QtGui

    if pixmap is None or pixmap.isNull():
        raise ReconstructionError(
            "Native viewport capture returned an empty pixmap"
        )
    image = pixmap.toImage()
    if image.isNull() or image.width() < 320 or image.height() < 320:
        raise ReconstructionError(
            "Native viewport capture returned invalid dimensions"
        )
    sample = image.scaled(
        32,
        32,
        QtCore.Qt.IgnoreAspectRatio,
        QtCore.Qt.FastTransformation,
    ).convertToFormat(QtGui.QImage.Format_RGB32)
    luminance = [
        QtGui.qGray(sample.pixel(x, y))
        for y in range(sample.height())
        for x in range(sample.width())
    ]
    color_range = max(luminance) - min(luminance)
    if color_range < 8:
        raise ReconstructionError(
            "Native viewport capture appears blank"
        )
    temporary = path + ".tmp.png"
    if os.path.isfile(temporary):
        os.remove(temporary)
    if not image.save(temporary, "PNG"):
        raise ReconstructionError(
            "Unable to save native viewport preview: {}".format(path)
        )
    os.replace(temporary, path)
    return {
        "bytes": os.path.getsize(path),
        "capture_mode": capture_mode,
        "color_range": color_range,
        "height": int(image.height()),
        "width": int(image.width()),
    }


def current_view_size():
    result = RLPy.RGlobal.GetViewSize(0, 0)
    if not isinstance(result, (list, tuple)) or len(result) < 3:
        raise ReconstructionError(
            "GetViewSize returned an unexpected result: {}".format(result)
        )
    width = int(result[-2])
    height = int(result[-1])
    if width <= 0 or height <= 0:
        raise ReconstructionError(
            "GetViewSize returned invalid dimensions: {}x{}".format(
                width,
                height,
            )
        )
    return width, height


def pixel_stream_frame(capture):
    candidates = (
        list(capture)
        if isinstance(capture, (list, tuple))
        else [capture]
    )
    for candidate in candidates:
        try:
            width = int(candidate.width)
            height = int(candidate.height)
            pointer = int(candidate.buffer_ptr)
        except Exception:
            continue
        if width > 0 and height > 0 and pointer > 0:
            return candidate, width, height, pointer
    raise ReconstructionError(
        "CapturePixelStream returned no valid viewport frame"
    )


def save_pixel_stream_frame(path, capture):
    import ctypes
    from PySide2 import QtGui

    unused_frame, width, height, pointer = pixel_stream_frame(capture)
    raw = ctypes.string_at(pointer, width * height * 4)
    if not any(raw):
        raise ReconstructionError(
            "CapturePixelStream returned an empty viewport frame"
        )
    image = QtGui.QImage(
        raw,
        width,
        height,
        width * 4,
        QtGui.QImage.Format_ARGB32,
    ).copy()
    if image.isNull():
        raise ReconstructionError(
            "Unable to construct the viewport preview image"
        )
    temporary = path + ".tmp.png"
    if os.path.isfile(temporary):
        os.remove(temporary)
    if not image.save(temporary, "PNG"):
        raise ReconstructionError(
            "Unable to save viewport preview: {}".format(path)
        )
    os.replace(temporary, path)
    return {
        "bytes": os.path.getsize(path),
        "capture_mode": "viewport_pixel_stream_v1",
        "height": height,
        "width": width,
    }


def render_viewport_preview(path, render_time=None):
    from PySide2 import QtGui

    if render_time is None:
        render_time = RLPy.RGlobal.GetTime()
    capture_errors = []
    for attempt in range(1, 4):
        checked(
            "Set native viewport preview time",
            RLPy.RGlobal.SetTime(render_time, True),
        )
        checked(
            "Force native viewport preview update",
            RLPy.RGlobal.ForceViewportUpdate(),
        )
        settle_cc_ui(RENDER_PREVIEW_SETTLE_SECONDS)
        try:
            main_record, records = current_native_cc_windows()
            viewport = select_native_viewport_record(
                main_record,
                records,
            )
            center = QtCore.QPoint(
                viewport["global_x"] + viewport["width"] // 2,
                viewport["global_y"] + viewport["height"] // 2,
            )
            screen = QtGui.QGuiApplication.screenAt(center)
            if screen is None:
                screen = QtGui.QGuiApplication.primaryScreen()
            if screen is None:
                raise ReconstructionError(
                    "No QScreen is available for native viewport capture"
                )
            device_pixel_ratio = float(screen.devicePixelRatio())
            if device_pixel_ratio <= 0.0:
                raise ReconstructionError(
                    "QScreen returned an invalid device pixel ratio"
                )
            screen_geometry = screen.geometry()
            logical_x = int(
                round(
                    screen_geometry.x()
                    + (
                        viewport["global_x"]
                        - (
                            screen_geometry.x()
                            * device_pixel_ratio
                        )
                    )
                    / device_pixel_ratio
                )
            )
            logical_y = int(
                round(
                    screen_geometry.y()
                    + (
                        viewport["global_y"]
                        - (
                            screen_geometry.y()
                            * device_pixel_ratio
                        )
                    )
                    / device_pixel_ratio
                )
            )
            logical_width = max(
                1,
                int(
                    round(
                        viewport["width"] / device_pixel_ratio
                    )
                ),
            )
            logical_height = max(
                1,
                int(
                    round(
                        viewport["height"] / device_pixel_ratio
                    )
                ),
            )
            result = save_native_viewport_frame(
                path,
                screen.grabWindow(
                    0,
                    logical_x,
                    logical_y,
                    logical_width,
                    logical_height,
                ),
                capture_mode="native_viewport_screen_rect_v1",
            )
            result["attempt"] = attempt
            result["device_pixel_ratio"] = device_pixel_ratio
            result["logical_capture_rect"] = {
                "height": logical_height,
                "width": logical_width,
                "x": logical_x,
                "y": logical_y,
            }
            result["viewport"] = dict(
                (
                    key,
                    viewport[key],
                )
                for key in (
                    "class_name",
                    "global_x",
                    "global_y",
                    "height",
                    "hwnd",
                    "parent_hwnd",
                    "title",
                    "width",
                )
            )
            return result
        except ReconstructionError as exc:
            capture_errors.append(str(exc))
            if attempt < 3:
                settle_cc_ui(1.0)
    raise ReconstructionError(
        "Native viewport capture failed after 3 attempts: {}".format(
            capture_errors
        )
    )


def face_identity_validation_timeline(start_frame, current_end_frame):
    start_frame = int(start_frame)
    current_end_frame = int(current_end_frame)
    clip_start_frame = current_end_frame + 1
    pose_frame = start_frame + FACE_IDENTITY_POSE_OFFSET_FRAMES
    if clip_start_frame > pose_frame:
        raise ReconstructionError(
            "The existing expression timeline reaches frame {}; "
            "the V1 evidence renderer requires a free pose frame at {}".format(
                current_end_frame,
                pose_frame,
            )
        )
    return {
        "clip_start_frame": clip_start_frame,
        "pose_frame": pose_frame,
        "validation_end_frame": (
            clip_start_frame + FACE_IDENTITY_CLIP_LENGTH_FRAMES
        ),
    }


def normalize_expression_name(name):
    return "".join(
        character.lower() for character in str(name) if character.isalnum()
    )


def first_expression_alias(expression_names, aliases):
    by_normalized = {}
    for name in expression_names:
        by_normalized.setdefault(normalize_expression_name(name), name)
    for alias in aliases:
        resolved = by_normalized.get(normalize_expression_name(alias))
        if resolved is not None:
            return resolved
    return None


def resolve_teeth_expression_targets(expression_names):
    expression_names = list(expression_names or [])
    if not expression_names:
        raise ReconstructionError("Character has no facial expression names")
    jaw_open = first_expression_alias(
        expression_names, TEETH_EXPRESSION_ALIASES["jaw_open"]
    )
    if jaw_open is None:
        raise ReconstructionError(
            "Unable to resolve a jaw-open expression for teeth validation"
        )
    smile = first_expression_alias(
        expression_names, TEETH_EXPRESSION_ALIASES["smile"]
    )
    if smile is not None:
        smile_targets = [smile]
    else:
        smile_left = first_expression_alias(
            expression_names, TEETH_EXPRESSION_ALIASES["smile_left"]
        )
        smile_right = first_expression_alias(
            expression_names, TEETH_EXPRESSION_ALIASES["smile_right"]
        )
        if smile_left is None or smile_right is None:
            raise ReconstructionError(
                "Unable to resolve bilateral smile expressions for teeth validation"
            )
        smile_targets = [smile_left, smile_right]
    oral_reveal = {}
    for target_id in (
        "upper_lip_raise_left",
        "upper_lip_raise_right",
        "lower_lip_depress_left",
        "lower_lip_depress_right",
        "stretch_left",
        "stretch_right",
    ):
        resolved = first_expression_alias(
            expression_names,
            TEETH_EXPRESSION_ALIASES[target_id],
        )
        if resolved is not None:
            oral_reveal[target_id] = resolved
    return {
        "jaw_open": jaw_open,
        "smile": smile_targets,
        "oral_reveal": oral_reveal,
    }


def render_teeth_visibility_previews(
    avatar,
    artifacts,
    mark_phase,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Character has no face component for teeth validation"
        )
    expression_names = list(face_component.GetExpressionNames("") or [])
    report = {
        "schema_version": 1,
        "profile": TEETH_VISIBILITY_PROFILE,
        "expression_set_uid": str(face_component.GetExpressionSetUid()),
        "expression_count": len(expression_names),
        "available_expression_names": expression_names,
        "resolved_targets": None,
        "poses": [],
    }
    write_json(report, artifacts["facial_pose_validation"])
    targets = resolve_teeth_expression_targets(expression_names)
    report["resolved_targets"] = targets
    write_json(report, artifacts["facial_pose_validation"])
    fps = RLPy.RGlobal.GetFps()
    clip_start = RLPy.IndexedFrameTime(0, fps)
    clip_length = RLPy.IndexedFrameTime(40, fps)
    interval = RLPy.IndexedFrameTime(0, fps)

    name_to_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )
    smile_weights = [0.0] * len(expression_names)
    for name in targets["smile"]:
        smile_weights[name_to_index[name]] = 0.8
    smile_weights[name_to_index[targets["jaw_open"]]] = 0.18
    jaw_open_weights = [0.0] * len(expression_names)
    jaw_open_weights[name_to_index[targets["jaw_open"]]] = 0.55
    reveal_strengths = {
        "upper_lip_raise_left": 0.25,
        "upper_lip_raise_right": 0.25,
        "lower_lip_depress_left": 0.35,
        "lower_lip_depress_right": 0.35,
        "stretch_left": 0.2,
        "stretch_right": 0.2,
    }
    for target_id, expression_name in targets["oral_reveal"].items():
        jaw_open_weights[name_to_index[expression_name]] = (
            reveal_strengths[target_id]
        )
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    pose_time = RLPy.IndexedFrameTime(10, fps)
    validation_end_time = RLPy.IndexedFrameTime(40, fps)
    report["timeline"] = {
        "initial_frame": int(fps.GetFrameIndex(initial_time)),
        "initial_end_frame": int(fps.GetFrameIndex(initial_end_time)),
        "initial_expression_clip_count": int(
            face_component.GetClipCount()
        ),
        "pose_frame": 10,
        "validation_end_frame": 40,
    }

    removed_clips = []
    for clip_index in range(
        int(face_component.GetClipCount()) - 1, -1, -1
    ):
        clip = face_component.GetClip(clip_index)
        removed_clips.append({"index": clip_index})
        checked(
            "Delete existing expression clip {}".format(clip_index),
            face_component.DeleteClip(clip),
        )
        QtWidgets.QApplication.processEvents()
    report["timeline"]["removed_expression_clips"] = removed_clips
    report["timeline"]["cleared_expression_clip_count"] = int(
        face_component.GetClipCount()
    )
    if report["timeline"]["cleared_expression_clip_count"] != 0:
        raise ReconstructionError(
            "Unable to clear existing expression clips for teeth validation"
        )

    def add_pose_clip(clip_name, weights):
        before_count = int(face_component.GetClipCount())
        checked(
            "Add {} expression clip".format(clip_name),
            face_component.AddClip(
                clip_start,
                clip_name,
                clip_length,
            ),
        )
        QtWidgets.QApplication.processEvents()
        after_count = int(face_component.GetClipCount())
        if after_count <= before_count:
            raise ReconstructionError(
                "Expression clip count did not increase for {}".format(
                    clip_name
                )
            )
        clip = face_component.GetClip(after_count - 1)
        checked(
            "Begin {} expression editing".format(clip_name),
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Add {} expression key".format(clip_name),
                face_component.AddExpressionKeys(
                    pose_time,
                    expression_names,
                    weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End {} expression editing".format(clip_name),
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate {} expression frame".format(clip_name),
            RLPy.RGlobal.SetTime(pose_time, True),
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        return clip

    active_clip = None
    try:
        if initial_end_time < validation_end_time:
            checked(
                "Extend teeth validation timeline",
                RLPy.RGlobal.SetEndTime(validation_end_time),
            )

        active_clip = add_pose_clip(
            "Lance_Teeth_Validation_Smile", smile_weights
        )
        set_avatar_yaw(avatar, 90.0)
        mark_phase("render_teeth_smile_front")
        render_preview(artifacts["teeth_smile_preview"], pose_time)
        checked(
            "Delete teeth smile validation clip",
            face_component.DeleteClip(active_clip),
        )
        active_clip = None

        active_clip = add_pose_clip(
            "Lance_Teeth_Validation_JawOpen", jaw_open_weights
        )
        set_avatar_yaw(avatar, 90.0)
        mark_phase("render_teeth_jaw_open_front")
        render_preview(artifacts["teeth_jaw_open_preview"], pose_time)
        set_avatar_yaw(avatar, 45.0)
        mark_phase("render_teeth_jaw_open_three_quarter")
        render_preview(
            artifacts["teeth_jaw_open_three_quarter_preview"],
            pose_time,
        )
        checked(
            "Delete teeth jaw-open validation clip",
            face_component.DeleteClip(active_clip),
        )
        active_clip = None
    finally:
        if active_clip is not None:
            face_component.DeleteClip(active_clip)
        RLPy.RGlobal.SetTime(initial_time, True)
        if initial_end_time < validation_end_time:
            RLPy.RGlobal.SetEndTime(initial_end_time)
        QtWidgets.QApplication.processEvents()

    report["poses"] = [
        {
            "pose_id": "smile_front",
            "frame": 10,
            "image": artifacts["teeth_smile_preview"],
        },
        {
            "pose_id": "jaw_open_front",
            "frame": 10,
            "image": artifacts["teeth_jaw_open_preview"],
        },
        {
            "pose_id": "jaw_open_three_quarter",
            "frame": 10,
            "image": artifacts[
                "teeth_jaw_open_three_quarter_preview"
            ],
        },
    ]
    write_json(report, artifacts["facial_pose_validation"])
    return report


def resolve_eye_expression_targets(expression_names):
    expression_names = list(expression_names or [])
    if not expression_names:
        raise ReconstructionError("Character has no facial expression names")
    resolved = {}
    for target_id, aliases in EYE_EXPRESSION_ALIASES.items():
        expression_name = first_expression_alias(expression_names, aliases)
        if expression_name is None:
            raise ReconstructionError(
                "Unable to resolve eye expression target: {}".format(
                    target_id
                )
            )
        resolved[target_id] = expression_name
    return {
        "look_left": [
            resolved["look_left_left"],
            resolved["look_left_right"],
        ],
        "look_right": [
            resolved["look_right_left"],
            resolved["look_right_right"],
        ],
        "look_up": [
            resolved["look_up_left"],
            resolved["look_up_right"],
        ],
        "look_down": [
            resolved["look_down_left"],
            resolved["look_down_right"],
        ],
    }


def render_eye_visibility_previews(
    avatar,
    artifacts,
    mark_phase,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Character has no face component for eye validation"
        )
    expression_names = list(face_component.GetExpressionNames("") or [])
    report = {
        "schema_version": 1,
        "profile": EYE_VISIBILITY_PROFILE,
        "expression_set_uid": str(face_component.GetExpressionSetUid()),
        "expression_count": len(expression_names),
        "available_expression_names": expression_names,
        "resolved_targets": None,
        "poses": [],
    }
    write_json(report, artifacts["facial_pose_validation"])
    targets = resolve_eye_expression_targets(expression_names)
    report["resolved_targets"] = targets
    write_json(report, artifacts["facial_pose_validation"])

    fps = RLPy.RGlobal.GetFps()
    clip_start = RLPy.IndexedFrameTime(0, fps)
    clip_length = RLPy.IndexedFrameTime(40, fps)
    interval = RLPy.IndexedFrameTime(0, fps)
    pose_time = RLPy.IndexedFrameTime(10, fps)
    validation_end_time = RLPy.IndexedFrameTime(40, fps)
    name_to_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )

    pose_specs = (
        (
            "look_left_front",
            "Lance_Eye_Validation_LookLeft",
            targets["look_left"],
            0.55,
            artifacts["eye_look_left_preview"],
        ),
        (
            "look_right_front",
            "Lance_Eye_Validation_LookRight",
            targets["look_right"],
            0.55,
            artifacts["eye_look_right_preview"],
        ),
        (
            "look_up_front",
            "Lance_Eye_Validation_LookUp",
            targets["look_up"],
            0.55,
            artifacts["eye_look_up_preview"],
        ),
        (
            "look_down_front",
            "Lance_Eye_Validation_LookDown",
            targets["look_down"],
            0.55,
            artifacts["eye_look_down_preview"],
        ),
    )
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    report["timeline"] = {
        "initial_frame": int(fps.GetFrameIndex(initial_time)),
        "initial_end_frame": int(fps.GetFrameIndex(initial_end_time)),
        "initial_expression_clip_count": int(
            face_component.GetClipCount()
        ),
        "pose_frame": 10,
        "validation_end_frame": 40,
    }

    removed_clips = []
    for clip_index in range(
        int(face_component.GetClipCount()) - 1, -1, -1
    ):
        clip = face_component.GetClip(clip_index)
        removed_clips.append({"index": clip_index})
        checked(
            "Delete existing expression clip {}".format(clip_index),
            face_component.DeleteClip(clip),
        )
        QtWidgets.QApplication.processEvents()
    report["timeline"]["removed_expression_clips"] = removed_clips
    report["timeline"]["cleared_expression_clip_count"] = int(
        face_component.GetClipCount()
    )
    if report["timeline"]["cleared_expression_clip_count"] != 0:
        raise ReconstructionError(
            "Unable to clear existing expression clips for eye validation"
        )

    def add_pose_clip(clip_name, target_names, weight):
        weights = [0.0] * len(expression_names)
        for name in target_names:
            weights[name_to_index[name]] = float(weight)
        before_count = int(face_component.GetClipCount())
        checked(
            "Add {} expression clip".format(clip_name),
            face_component.AddClip(
                clip_start,
                clip_name,
                clip_length,
            ),
        )
        QtWidgets.QApplication.processEvents()
        after_count = int(face_component.GetClipCount())
        if after_count <= before_count:
            raise ReconstructionError(
                "Expression clip count did not increase for {}".format(
                    clip_name
                )
            )
        clip = face_component.GetClip(after_count - 1)
        checked(
            "Begin {} expression editing".format(clip_name),
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Add {} expression key".format(clip_name),
                face_component.AddExpressionKeys(
                    pose_time,
                    expression_names,
                    weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End {} expression editing".format(clip_name),
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate {} expression frame".format(clip_name),
            RLPy.RGlobal.SetTime(pose_time, True),
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        return clip

    active_clip = None
    try:
        if initial_end_time < validation_end_time:
            checked(
                "Extend eye validation timeline",
                RLPy.RGlobal.SetEndTime(validation_end_time),
            )
        for pose_id, clip_name, target_names, weight, image_path in pose_specs:
            active_clip = add_pose_clip(
                clip_name,
                target_names,
                weight,
            )
            set_avatar_yaw(avatar, 90.0)
            mark_phase("render_eye_{}".format(pose_id))
            render_preview(image_path, pose_time)
            checked(
                "Delete {} validation clip".format(pose_id),
                face_component.DeleteClip(active_clip),
            )
            active_clip = None
    finally:
        if active_clip is not None:
            face_component.DeleteClip(active_clip)
        RLPy.RGlobal.SetTime(initial_time, True)
        if initial_end_time < validation_end_time:
            RLPy.RGlobal.SetEndTime(initial_end_time)
        QtWidgets.QApplication.processEvents()

    report["poses"] = [
        {
            "pose_id": pose_id,
            "frame": 10,
            "image": image_path,
        }
        for pose_id, unused_clip, unused_targets, unused_weight, image_path
        in pose_specs
    ]
    write_json(report, artifacts["facial_pose_validation"])
    return report


def resolve_eyebrow_expression_targets(expression_names):
    expression_names = list(expression_names or [])
    if not expression_names:
        raise ReconstructionError("Character has no facial expression names")
    resolved = {}
    for target_id, aliases in EYEBROW_EXPRESSION_ALIASES.items():
        expression_name = first_expression_alias(expression_names, aliases)
        if expression_name is None:
            raise ReconstructionError(
                "Unable to resolve eyebrow expression target: {}".format(
                    target_id
                )
            )
        resolved[target_id] = expression_name
    return {
        "raise_bilateral": [
            resolved["raise_inner_left"],
            resolved["raise_inner_right"],
            resolved["raise_outer_left"],
            resolved["raise_outer_right"],
        ],
        "down_bilateral": [
            resolved["down_left"],
            resolved["down_right"],
        ],
        "raise_left": [
            resolved["raise_inner_left"],
            resolved["raise_outer_left"],
        ],
    }


def render_eyebrow_visibility_previews(
    avatar,
    artifacts,
    mark_phase,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Character has no face component for eyebrow validation"
        )
    expression_names = list(face_component.GetExpressionNames("") or [])
    report = {
        "schema_version": 1,
        "profile": EYEBROW_VISIBILITY_PROFILE,
        "expression_set_uid": str(face_component.GetExpressionSetUid()),
        "expression_count": len(expression_names),
        "available_expression_names": expression_names,
        "resolved_targets": None,
        "poses": [],
    }
    write_json(report, artifacts["facial_pose_validation"])
    targets = resolve_eyebrow_expression_targets(expression_names)
    report["resolved_targets"] = targets
    write_json(report, artifacts["facial_pose_validation"])

    fps = RLPy.RGlobal.GetFps()
    clip_start = RLPy.IndexedFrameTime(0, fps)
    clip_length = RLPy.IndexedFrameTime(40, fps)
    interval = RLPy.IndexedFrameTime(0, fps)
    pose_time = RLPy.IndexedFrameTime(10, fps)
    validation_end_time = RLPy.IndexedFrameTime(40, fps)
    name_to_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )
    pose_specs = (
        (
            "raise_bilateral_front",
            "Lance_Eyebrow_Validation_Raise",
            targets["raise_bilateral"],
            0.65,
            artifacts["eyebrow_raise_preview"],
        ),
        (
            "down_bilateral_front",
            "Lance_Eyebrow_Validation_Down",
            targets["down_bilateral"],
            0.65,
            artifacts["eyebrow_down_preview"],
        ),
        (
            "raise_left_front",
            "Lance_Eyebrow_Validation_RaiseLeft",
            targets["raise_left"],
            0.65,
            artifacts["eyebrow_asymmetric_preview"],
        ),
    )
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    report["timeline"] = {
        "initial_frame": int(fps.GetFrameIndex(initial_time)),
        "initial_end_frame": int(fps.GetFrameIndex(initial_end_time)),
        "initial_expression_clip_count": int(
            face_component.GetClipCount()
        ),
        "pose_frame": 10,
        "validation_end_frame": 40,
    }

    removed_clips = []
    for clip_index in range(
        int(face_component.GetClipCount()) - 1, -1, -1
    ):
        clip = face_component.GetClip(clip_index)
        removed_clips.append({"index": clip_index})
        checked(
            "Delete existing expression clip {}".format(clip_index),
            face_component.DeleteClip(clip),
        )
        QtWidgets.QApplication.processEvents()
    report["timeline"]["removed_expression_clips"] = removed_clips
    if int(face_component.GetClipCount()) != 0:
        raise ReconstructionError(
            "Unable to clear existing expression clips for eyebrow validation"
        )

    def add_pose_clip(clip_name, target_names, weight):
        weights = [0.0] * len(expression_names)
        for name in target_names:
            weights[name_to_index[name]] = float(weight)
        before_count = int(face_component.GetClipCount())
        checked(
            "Add {} expression clip".format(clip_name),
            face_component.AddClip(
                clip_start,
                clip_name,
                clip_length,
            ),
        )
        QtWidgets.QApplication.processEvents()
        after_count = int(face_component.GetClipCount())
        if after_count <= before_count:
            raise ReconstructionError(
                "Expression clip count did not increase for {}".format(
                    clip_name
                )
            )
        clip = face_component.GetClip(after_count - 1)
        checked(
            "Begin {} expression editing".format(clip_name),
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Add {} expression key".format(clip_name),
                face_component.AddExpressionKeys(
                    pose_time,
                    expression_names,
                    weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End {} expression editing".format(clip_name),
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate {} expression frame".format(clip_name),
            RLPy.RGlobal.SetTime(pose_time, True),
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        return clip

    active_clip = None
    try:
        if initial_end_time < validation_end_time:
            checked(
                "Extend eyebrow validation timeline",
                RLPy.RGlobal.SetEndTime(validation_end_time),
            )
        for pose_id, clip_name, target_names, weight, image_path in pose_specs:
            active_clip = add_pose_clip(
                clip_name,
                target_names,
                weight,
            )
            set_avatar_yaw(avatar, 90.0)
            mark_phase("render_eyebrow_{}".format(pose_id))
            render_preview(image_path, pose_time)
            checked(
                "Delete {} validation clip".format(pose_id),
                face_component.DeleteClip(active_clip),
            )
            active_clip = None
    finally:
        if active_clip is not None:
            face_component.DeleteClip(active_clip)
        RLPy.RGlobal.SetTime(initial_time, True)
        if initial_end_time < validation_end_time:
            RLPy.RGlobal.SetEndTime(initial_end_time)
        QtWidgets.QApplication.processEvents()

    report["poses"] = [
        {
            "pose_id": pose_id,
            "frame": 10,
            "weight": weight,
            "image": image_path,
        }
        for pose_id, unused_clip, unused_targets, weight, image_path
        in pose_specs
    ]
    write_json(report, artifacts["facial_pose_validation"])
    return report


def resolve_eyelash_expression_targets(expression_names):
    expression_names = list(expression_names or [])
    if not expression_names:
        raise ReconstructionError("Character has no facial expression names")
    resolved = {}
    for target_id, aliases in EYELASH_EXPRESSION_ALIASES.items():
        expression_name = first_expression_alias(expression_names, aliases)
        if expression_name is None:
            raise ReconstructionError(
                "Unable to resolve eyelash expression target: {}".format(
                    target_id
                )
            )
        resolved[target_id] = expression_name
    blink_left = [
        resolved["blink_left"],
        resolved["blink_corrective_left"],
        resolved["lash_down_inner_left"],
        resolved["lash_down_outer_left"],
    ]
    blink_right = [
        resolved["blink_right"],
        resolved["blink_corrective_right"],
        resolved["lash_down_inner_right"],
        resolved["lash_down_outer_right"],
    ]
    widen_left = [
        resolved["widen_left"],
        resolved["lash_up_inner_left"],
        resolved["lash_up_outer_left"],
    ]
    widen_right = [
        resolved["widen_right"],
        resolved["lash_up_inner_right"],
        resolved["lash_up_outer_right"],
    ]
    return {
        "blink_bilateral": blink_left + blink_right,
        "blink_left": blink_left,
        "blink_right": blink_right,
        "widen_bilateral": widen_left + widen_right,
        "widen_left": widen_left,
        "widen_right": widen_right,
    }


def render_eyelash_visibility_previews(
    avatar,
    artifacts,
    mark_phase,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Character has no face component for eyelash validation"
        )
    expression_names = list(face_component.GetExpressionNames("") or [])
    report = {
        "schema_version": 1,
        "profile": EYELASH_VISIBILITY_PROFILE,
        "expression_set_uid": str(face_component.GetExpressionSetUid()),
        "expression_count": len(expression_names),
        "available_expression_names": expression_names,
        "resolved_targets": None,
        "poses": [],
    }
    write_json(report, artifacts["facial_pose_validation"])
    targets = resolve_eyelash_expression_targets(expression_names)
    report["resolved_targets"] = targets
    report["correction_mode"] = (
        "base_eye_expression_plus_cc_blink_and_eyelash_corrections"
    )
    write_json(report, artifacts["facial_pose_validation"])

    fps = RLPy.RGlobal.GetFps()
    clip_start = RLPy.IndexedFrameTime(0, fps)
    clip_length = RLPy.IndexedFrameTime(40, fps)
    interval = RLPy.IndexedFrameTime(0, fps)
    pose_time = RLPy.IndexedFrameTime(10, fps)
    validation_end_time = RLPy.IndexedFrameTime(40, fps)
    name_to_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )
    pose_specs = (
        (
            "blink_bilateral_front",
            "Lance_Eyelash_Validation_Blink",
            targets["blink_bilateral"],
            1.0,
            artifacts["eyelash_blink_preview"],
        ),
        (
            "blink_left_front",
            "Lance_Eyelash_Validation_BlinkLeft",
            targets["blink_left"],
            1.0,
            artifacts["eyelash_asymmetric_preview"],
        ),
        (
            "widen_bilateral_front",
            "Lance_Eyelash_Validation_Widen",
            targets["widen_bilateral"],
            0.65,
            artifacts["eyelash_wide_preview"],
        ),
    )
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    validation_camera = RLPy.RScene.GetCurrentCamera()
    if validation_camera is None:
        raise ReconstructionError(
            "Eyelash validation has no active face camera"
        )
    validation_camera_id = scene_object_id(validation_camera)
    neutral_bounds = capture_bounds(avatar)
    report["validation_camera"] = camera_state(validation_camera)
    report["neutral_bounds"] = neutral_bounds
    report["timeline"] = {
        "initial_frame": int(fps.GetFrameIndex(initial_time)),
        "initial_end_frame": int(fps.GetFrameIndex(initial_end_time)),
        "initial_expression_clip_count": int(
            face_component.GetClipCount()
        ),
        "pose_frame": 10,
        "validation_end_frame": 40,
    }

    removed_clips = []
    for clip_index in range(
        int(face_component.GetClipCount()) - 1, -1, -1
    ):
        clip = face_component.GetClip(clip_index)
        removed_clips.append({"index": clip_index})
        checked(
            "Delete existing expression clip {}".format(clip_index),
            face_component.DeleteClip(clip),
        )
        QtWidgets.QApplication.processEvents()
    report["timeline"]["removed_expression_clips"] = removed_clips
    if int(face_component.GetClipCount()) != 0:
        raise ReconstructionError(
            "Unable to clear existing expression clips for eyelash validation"
        )

    def add_pose_clip(clip_name, target_names, weight):
        weights = [0.0] * len(expression_names)
        for name in target_names:
            weights[name_to_index[name]] = float(weight)
        before_count = int(face_component.GetClipCount())
        checked(
            "Add {} expression clip".format(clip_name),
            face_component.AddClip(
                clip_start,
                clip_name,
                clip_length,
            ),
        )
        QtWidgets.QApplication.processEvents()
        after_count = int(face_component.GetClipCount())
        if after_count <= before_count:
            raise ReconstructionError(
                "Expression clip count did not increase for {}".format(
                    clip_name
                )
            )
        clip = face_component.GetClip(after_count - 1)
        checked(
            "Begin {} expression editing".format(clip_name),
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Add {} expression key".format(clip_name),
                face_component.AddExpressionKeys(
                    pose_time,
                    expression_names,
                    weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End {} expression editing".format(clip_name),
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate {} expression frame".format(clip_name),
            RLPy.RGlobal.SetTime(pose_time, True),
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        return clip

    active_clip = None
    pose_records = []
    try:
        if initial_end_time < validation_end_time:
            checked(
                "Extend eyelash validation timeline",
                RLPy.RGlobal.SetEndTime(validation_end_time),
            )
        for pose_id, clip_name, target_names, weight, image_path in pose_specs:
            active_clip = add_pose_clip(
                clip_name,
                target_names,
                weight,
            )
            checked(
                "Restore eyelash validation camera",
                RLPy.RScene.SetCurrentCamera(validation_camera),
            )
            set_avatar_yaw(avatar, 90.0)
            checked(
                "Re-evaluate {} after camera reset".format(pose_id),
                RLPy.RGlobal.SetTime(pose_time, True),
            )
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()
            current_camera = RLPy.RScene.GetCurrentCamera()
            if (
                current_camera is None
                or scene_object_id(current_camera) != validation_camera_id
            ):
                raise ReconstructionError(
                    "Active camera changed during eyelash validation"
                )
            pose_bounds = capture_bounds(avatar)
            mark_phase("render_eyelash_{}".format(pose_id))
            render_preview(image_path, pose_time)
            pose_records.append(
                {
                    "pose_id": pose_id,
                    "frame": 10,
                    "weight": weight,
                    "targets": list(target_names),
                    "image": image_path,
                    "avatar_bounds": pose_bounds,
                    "camera": camera_state(current_camera),
                }
            )
            checked(
                "Delete {} validation clip".format(pose_id),
                face_component.DeleteClip(active_clip),
            )
            active_clip = None
            checked(
                "Reset expression state after {}".format(pose_id),
                RLPy.RGlobal.SetTime(clip_start, True),
            )
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()
    finally:
        if active_clip is not None:
            face_component.DeleteClip(active_clip)
        RLPy.RGlobal.SetTime(initial_time, True)
        if initial_end_time < validation_end_time:
            RLPy.RGlobal.SetEndTime(initial_end_time)
        QtWidgets.QApplication.processEvents()

    report["poses"] = pose_records
    write_json(report, artifacts["facial_pose_validation"])
    return report


def resolve_face_identity_safety_targets(expression_names):
    expression_names = list(expression_names or [])
    eyelash = resolve_eyelash_expression_targets(expression_names)
    gaze = resolve_eye_expression_targets(expression_names)
    eyebrow = resolve_eyebrow_expression_targets(expression_names)
    teeth = resolve_teeth_expression_targets(expression_names)
    squint_left = first_expression_alias(
        expression_names,
        ("Eye_Squint_Inner_L", "Eye_Squint_L"),
    )
    squint_right = first_expression_alias(
        expression_names,
        ("Eye_Squint_Inner_R", "Eye_Squint_R"),
    )
    if squint_left is None or squint_right is None:
        raise ReconstructionError(
            "Unable to resolve bilateral eye squint expressions"
        )
    return {
        "blink_bilateral": eyelash["blink_bilateral"],
        "blink_left": eyelash["blink_left"],
        "blink_right": eyelash["blink_right"],
        "brow_down": eyebrow["down_bilateral"],
        "brow_raise": eyebrow["raise_bilateral"],
        "brow_raise_left": eyebrow["raise_left"],
        "gaze_down": gaze["look_down"],
        "gaze_left": gaze["look_left"],
        "gaze_right": gaze["look_right"],
        "gaze_up": gaze["look_up"],
        "jaw_open": teeth["jaw_open"],
        "oral_reveal": teeth["oral_reveal"],
        "smile": teeth["smile"],
        "squint_bilateral": [squint_left, squint_right],
        "widen_bilateral": eyelash["widen_bilateral"],
    }


def expression_weights_at(face_component, time_value, expression_names):
    expression_names = list(expression_names)
    raw = face_component.GetExpressionWeights(
        time_value,
        expression_names,
    )
    candidates = [raw]
    if isinstance(raw, (list, tuple)):
        candidates.extend(
            item
            for item in raw
            if isinstance(item, (list, tuple))
        )
    for candidate in candidates:
        if not isinstance(candidate, (list, tuple)):
            continue
        if len(candidate) != len(expression_names):
            continue
        try:
            return [float(item) for item in candidate]
        except (TypeError, ValueError):
            continue
    raise ReconstructionError(
        "GetExpressionWeights returned an unexpected result for {} "
        "expressions: {}".format(
            len(expression_names),
            repr(raw)[:500],
        )
    )


def render_face_identity_safety_previews(
    avatar,
    artifacts,
    mark_phase,
    profile=FACE_IDENTITY_SAFETY_PROFILE,
    pose_ids=None,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Character has no face component for identity safety validation"
        )
    expression_names = list(
        face_component.GetExpressionNames("") or []
    )
    targets = resolve_face_identity_safety_targets(
        expression_names
    )
    report = {
        "available_expression_names": expression_names,
        "expression_count": len(expression_names),
        "expression_set_uid": str(
            face_component.GetExpressionSetUid()
        ),
        "poses": [],
        "profile": profile,
        "resolved_targets": targets,
        "schema_version": 1,
    }
    write_json(report, artifacts["facial_pose_validation"])

    def uniform_weights(names, value):
        return dict((name, float(value)) for name in names)

    smile_weights = uniform_weights(targets["smile"], 0.8)
    smile_weights[targets["jaw_open"]] = 0.18
    jaw_weights = {targets["jaw_open"]: 0.55}
    reveal_strengths = {
        "upper_lip_raise_left": 0.25,
        "upper_lip_raise_right": 0.25,
        "lower_lip_depress_left": 0.35,
        "lower_lip_depress_right": 0.35,
        "stretch_left": 0.2,
        "stretch_right": 0.2,
    }
    for target_id, expression_name in targets[
        "oral_reveal"
    ].items():
        jaw_weights[expression_name] = reveal_strengths[target_id]

    pose_specs = (
        (
            "blink_bilateral_front",
            uniform_weights(targets["blink_bilateral"], 1.0),
            90.0,
            artifacts["face_blink_bilateral_preview"],
        ),
        (
            "blink_left_front",
            uniform_weights(targets["blink_left"], 1.0),
            90.0,
            artifacts["face_blink_left_preview"],
        ),
        (
            "blink_right_front",
            uniform_weights(targets["blink_right"], 1.0),
            90.0,
            artifacts["face_blink_right_preview"],
        ),
        (
            "look_left_front",
            uniform_weights(targets["gaze_left"], 0.55),
            90.0,
            artifacts["face_look_left_preview"],
        ),
        (
            "look_right_front",
            uniform_weights(targets["gaze_right"], 0.55),
            90.0,
            artifacts["face_look_right_preview"],
        ),
        (
            "look_up_front",
            uniform_weights(targets["gaze_up"], 0.55),
            90.0,
            artifacts["face_look_up_preview"],
        ),
        (
            "look_down_front",
            uniform_weights(targets["gaze_down"], 0.55),
            90.0,
            artifacts["face_look_down_preview"],
        ),
        (
            "squint_bilateral_front",
            uniform_weights(targets["squint_bilateral"], 0.65),
            90.0,
            artifacts["face_squint_preview"],
        ),
        (
            "widen_bilateral_front",
            uniform_weights(targets["widen_bilateral"], 0.65),
            90.0,
            artifacts["face_widen_preview"],
        ),
        (
            "brow_raise_front",
            uniform_weights(targets["brow_raise"], 0.65),
            90.0,
            artifacts["face_brow_raise_preview"],
        ),
        (
            "brow_down_front",
            uniform_weights(targets["brow_down"], 0.65),
            90.0,
            artifacts["face_brow_down_preview"],
        ),
        (
            "brow_raise_left_front",
            uniform_weights(targets["brow_raise_left"], 0.65),
            90.0,
            artifacts["face_brow_raise_left_preview"],
        ),
        (
            "smile_front",
            smile_weights,
            90.0,
            artifacts["face_smile_preview"],
        ),
        (
            "jaw_open_front",
            jaw_weights,
            90.0,
            artifacts["face_jaw_open_preview"],
        ),
        (
            "jaw_open_three_quarter",
            jaw_weights,
            45.0,
            artifacts["face_jaw_open_three_quarter_preview"],
        ),
    )
    if pose_ids is not None:
        requested_pose_ids = tuple(pose_ids)
        available_pose_ids = {
            item[0] for item in pose_specs
        }
        unknown_pose_ids = sorted(
            set(requested_pose_ids) - available_pose_ids
        )
        if unknown_pose_ids:
            raise ReconstructionError(
                "Unknown face safety pose IDs: {}".format(
                    unknown_pose_ids
                )
            )
        pose_specs = tuple(
            item
            for item in pose_specs
            if item[0] in requested_pose_ids
        )

    force_avatar_scene_evaluation(avatar)
    neutral_eye_state_before = capture_eye_integrity_state(avatar)
    fps = RLPy.RGlobal.GetFps()
    initial_time = RLPy.RGlobal.GetTime()
    project_start_time = RLPy.RGlobal.GetStartTime()
    baseline_clip_count = int(face_component.GetClipCount())
    if baseline_clip_count < 1:
        raise ReconstructionError(
            "Face identity validation requires an existing Facial "
            "Profile expression clip"
        )
    baseline_clip = face_component.GetClipByTime(project_start_time)
    if baseline_clip is None or not baseline_clip.IsValid():
        raise ReconstructionError(
            "No Facial Profile expression clip covers the project "
            "start frame"
        )
    validation_expression_names = sorted(
        {
            expression_name
            for unused_pose_id, target_weights, unused_yaw, unused_path
            in pose_specs
            for expression_name in target_weights
        }
    )
    baseline_weights = expression_weights_at(
        face_component,
        project_start_time,
        validation_expression_names,
    )
    baseline_by_name = dict(
        zip(validation_expression_names, baseline_weights)
    )
    interval = RLPy.IndexedFrameTime(0, fps)
    start_frame = int(fps.GetFrameIndex(project_start_time))
    snapshot_path = os.path.join(
        os.path.dirname(artifacts["facial_pose_validation"]),
        "_face_identity_validation_snapshot.ccProject",
    )
    if os.path.isfile(snapshot_path):
        os.remove(snapshot_path)
    report["timeline"] = {
        "baseline_expression_clip_count": baseline_clip_count,
        "capture_frame": start_frame,
        "capture_strategy": (
            "facial_profile_start_frame_snapshot_restore_v1"
        ),
        "initial_frame": int(fps.GetFrameIndex(initial_time)),
        "preserved_existing_expression_clips": True,
        "removed_expression_clips": [],
        "validation_expression_names": validation_expression_names,
        "validation_expression_weights_before": dict(
            sorted(baseline_by_name.items())
        ),
    }

    snapshot_saved = False
    snapshot_restored = False
    try:
        mark_phase("save_face_identity_validation_snapshot")
        checked(
            "Save face identity validation snapshot",
            RLPy.RFileIO.SaveProject(snapshot_path),
        )
        snapshot_stat = wait_for_rendered_preview(
            snapshot_path,
            timeout_seconds=180.0,
            stable_seconds=1.0,
        )
        snapshot_saved = True
        report["snapshot"] = {
            "path": snapshot_path,
            "saved": True,
            "size": snapshot_stat,
        }
        warmup_path = os.path.join(
            os.path.dirname(artifacts["facial_pose_validation"]),
            "_face_render_warmup.png",
        )
        mark_phase("warmup_face_identity_render")
        set_avatar_yaw(avatar, 90.0)
        render_preview(warmup_path, project_start_time)
        report["render_warmup"] = {
            "bytes": os.path.getsize(warmup_path),
            "sha256": sha256_file(warmup_path),
        }
        os.remove(warmup_path)
        report["render_warmup"]["deleted"] = True
        for pose_id, target_weights, yaw, image_path in pose_specs:
            pose_by_name = dict(baseline_by_name)
            for expression_name, weight in target_weights.items():
                if expression_name not in pose_by_name:
                    raise ReconstructionError(
                        "Face identity expression disappeared: {}".format(
                            expression_name
                        )
                    )
                pose_by_name[expression_name] = float(weight)
            pose_weights = [
                pose_by_name[name]
                for name in validation_expression_names
            ]
            checked(
                "Begin {} expression editing".format(pose_id),
                face_component.BeginKeyEditing(),
            )
            try:
                checked(
                    "Write {} expression key".format(pose_id),
                    face_component.AddExpressionKeys(
                        project_start_time,
                        validation_expression_names,
                        pose_weights,
                        interval,
                    ),
                )
            finally:
                checked(
                    "End {} expression editing".format(pose_id),
                    face_component.EndKeyEditing(),
                )
            checked(
                "Evaluate {} expression frame".format(pose_id),
                RLPy.RGlobal.SetTime(project_start_time, True),
            )
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()
            evaluated_weights = expression_weights_at(
                face_component,
                project_start_time,
                validation_expression_names,
            )
            set_avatar_yaw(avatar, yaw)
            mark_phase("render_face_identity_{}".format(pose_id))
            render_preview(image_path, project_start_time)
            report["poses"].append(
                {
                    "capture": {
                        "bytes": os.path.getsize(image_path),
                        "capture_mode": (
                            "render_image_start_frame_snapshot_restore_v1"
                        ),
                        "sha256": sha256_file(image_path),
                    },
                    "evaluated_expression_weights": dict(
                        sorted(
                            zip(
                                validation_expression_names,
                                evaluated_weights,
                            )
                        )
                    ),
                    "frame": start_frame,
                    "image": image_path,
                    "pose_id": pose_id,
                    "target_weights": dict(
                        sorted(target_weights.items())
                    ),
                    "yaw_degrees": yaw,
                }
            )
        post_pose_neutral_path = artifacts.get(
            "face_post_pose_neutral_preview"
        )
        if not post_pose_neutral_path:
            raise ReconstructionError(
                "Face identity validation requires a post-pose "
                "neutral evidence path"
            )
        checked(
            "Begin post-pose neutral expression editing",
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Restore post-pose neutral expression weights",
                face_component.AddExpressionKeys(
                    project_start_time,
                    validation_expression_names,
                    baseline_weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End post-pose neutral expression editing",
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate post-pose neutral expression frame",
            RLPy.RGlobal.SetTime(project_start_time, True),
        )
        set_avatar_yaw(avatar, 90.0)
        mark_phase("render_face_post_pose_neutral")
        render_preview(
            post_pose_neutral_path,
            project_start_time,
        )
        report["post_pose_neutral_capture"] = {
            "bytes": os.path.getsize(post_pose_neutral_path),
            "capture_mode": (
                "render_image_same_scene_restored_neutral_v1"
            ),
            "sha256": sha256_file(post_pose_neutral_path),
        }
        report["post_pose_neutral_image"] = post_pose_neutral_path
        report["post_pose_neutral_expression_weights"] = dict(
            sorted(
                zip(
                    validation_expression_names,
                    expression_weights_at(
                        face_component,
                        project_start_time,
                        validation_expression_names,
                    ),
                )
            )
        )
    finally:
        if snapshot_saved:
            mark_phase("restore_face_identity_validation_snapshot")
            unused_status, restore_dialogs = (
                load_file_with_optional_undo_warning(
                    snapshot_path,
                    "Restore face identity validation snapshot",
                )
            )
            settle_cc_ui(1.0)
            avatar, avatars = resolve_avatar()
            if len(avatars) != 1:
                raise ReconstructionError(
                    "Face validation snapshot restore expected one avatar"
                )
            face_component = avatar.GetFaceComponent()
            if face_component is None:
                raise ReconstructionError(
                    "Restored character has no face component"
                )
            force_avatar_scene_evaluation(avatar)
            snapshot_restored = True
            report["snapshot"]["restored"] = True
            report["snapshot"]["restore_dialogs"] = restore_dialogs
            try:
                os.remove(snapshot_path)
            except OSError as exc:
                report["snapshot"]["cleanup_error"] = str(exc)
            else:
                report["snapshot"]["deleted"] = True

    if not snapshot_restored:
        raise ReconstructionError(
            "Face identity validation snapshot was not restored"
        )
    report["final_expression_clip_count"] = int(face_component.GetClipCount())
    if report["final_expression_clip_count"] != baseline_clip_count:
        raise ReconstructionError(
            "Face identity validation changed the baseline expression clips"
        )
    neutral_eye_state_after = capture_eye_integrity_state(avatar)
    report["neutral_eye_integrity"] = compare_neutral_eye_states(
        neutral_eye_state_before,
        neutral_eye_state_after,
        include_world=True,
        include_runtime_ids=False,
        t_pose_tolerance=0.5,
    )
    report["neutral_eye_reload_strict_observation"] = (
        compare_neutral_eye_states(
            neutral_eye_state_before,
            neutral_eye_state_after,
            include_world=True,
        )
    )
    report["neutral_eye_world_observation"] = report[
        "neutral_eye_integrity"
    ]
    if not report["neutral_eye_integrity"]["matches"]:
        write_json(report, artifacts["facial_pose_validation"])
        raise ReconstructionError(
            "Face identity validation changed neutral eye bone state: "
            "{}".format(
                report["neutral_eye_integrity"]["differences"]
            )
        )
    post_pose_neutral_path = report.get("post_pose_neutral_image")
    if post_pose_neutral_path:
        liveness_records = []
        for pose_record in report["poses"]:
            if float(pose_record["yaw_degrees"]) != 90.0:
                continue
            rmse = rendered_image_rmse(
                pose_record["image"],
                post_pose_neutral_path,
            )
            liveness_records.append(
                {
                    "matches": rmse >= FACE_EVIDENCE_MIN_RMSE,
                    "pose_id": pose_record["pose_id"],
                    "rmse": rmse,
                }
            )
        report["evidence_liveness"] = {
            "minimum_rmse": FACE_EVIDENCE_MIN_RMSE,
            "poses": liveness_records,
            "reference_image": post_pose_neutral_path,
            "status": (
                "passed"
                if liveness_records
                and all(
                    item["matches"]
                    for item in liveness_records
                )
                else "failed"
            ),
        }
        if report["evidence_liveness"]["status"] != "passed":
            write_json(report, artifacts["facial_pose_validation"])
            raise ReconstructionError(
                "Face expression evidence did not differ from the "
                "restored neutral frame"
            )
    write_json(report, artifacts["facial_pose_validation"])
    return report


def render_dynamic_wrinkle_strength_pair(
    avatar,
    artifacts,
    mark_phase,
    validation,
):
    pose_ids = validation["pose_ids"]
    baseline_artifacts = dict(artifacts)
    baseline_artifacts["facial_pose_validation"] = artifacts[
        "dynamic_wrinkle_baseline_pose_validation"
    ]
    for pose_id in pose_ids:
        target_key, baseline_key = (
            DYNAMIC_WRINKLE_POSE_ARTIFACT_KEYS[pose_id]
        )
        baseline_artifacts[target_key] = artifacts[baseline_key]

    report = {
        "baseline": None,
        "pairs": [],
        "profile": "dynamic_wrinkle_strength_pair_v1",
        "schema_version": 1,
        "target": None,
        "target_restore": None,
    }
    target_strength = validation["target_strength"]
    baseline_strength = validation["baseline_strength"]
    mark_phase(
        "dynamic_wrinkle_target_strength",
        {"strength": target_strength},
    )
    avatar, target_application = apply_dynamic_wrinkle_strength(
        avatar, target_strength
    )
    target_pose_report = render_face_identity_safety_previews(
        avatar,
        artifacts,
        mark_phase,
        pose_ids=pose_ids,
    )
    avatar, unused_avatars = resolve_avatar()
    report["target"] = {
        "application": target_application,
        "neutral_image": artifacts["face_front_preview"],
        "pose_report": artifacts["facial_pose_validation"],
        "strength": target_strength,
    }

    try:
        mark_phase(
            "dynamic_wrinkle_baseline_strength",
            {"strength": baseline_strength},
        )
        avatar, baseline_application = apply_dynamic_wrinkle_strength(
            avatar, baseline_strength
        )
        set_avatar_yaw(avatar, 90.0)
        mark_phase("render_dynamic_wrinkle_baseline_neutral")
        render_preview(
            artifacts["dynamic_wrinkle_baseline_neutral_preview"]
        )
        baseline_pose_report = render_face_identity_safety_previews(
            avatar,
            baseline_artifacts,
            mark_phase,
            profile="dynamic_wrinkle_baseline_v1",
            pose_ids=pose_ids,
        )
        avatar, unused_avatars = resolve_avatar()
        report["baseline"] = {
            "application": baseline_application,
            "neutral_image": artifacts[
                "dynamic_wrinkle_baseline_neutral_preview"
            ],
            "pose_report": artifacts[
                "dynamic_wrinkle_baseline_pose_validation"
            ],
            "strength": baseline_strength,
        }
        target_poses = dict(
            (item["pose_id"], item)
            for item in target_pose_report["poses"]
        )
        baseline_poses = dict(
            (item["pose_id"], item)
            for item in baseline_pose_report["poses"]
        )
        report["pairs"].append(
            {
                "baseline_image": artifacts[
                    "dynamic_wrinkle_baseline_neutral_preview"
                ],
                "pose_id": "neutral_front",
                "target_image": artifacts["face_front_preview"],
            }
        )
        for pose_id in pose_ids:
            report["pairs"].append(
                {
                    "baseline_image": baseline_poses[pose_id]["image"],
                    "pose_id": pose_id,
                    "target_image": target_poses[pose_id]["image"],
                }
            )
    finally:
        mark_phase(
            "dynamic_wrinkle_restore_target_strength",
            {"strength": target_strength},
        )
        avatar, restore_application = apply_dynamic_wrinkle_strength(
            avatar, target_strength
        )
        report["target_restore"] = restore_application
        write_json(
            report,
            artifacts["dynamic_wrinkle_validation"],
        )
    return target_pose_report, report


def direct_avatar_part_records(avatar, slot):
    part_type = avatar_part_type_for_slot(slot)
    return [
        avatar_part_record(part)
        for part in avatar_parts_of_type(avatar, part_type)
    ]


def direct_avatar_part_signature(records):
    return sorted(
        (
            item.get("id"),
            item.get("name"),
            item.get("python_type"),
            item.get("avatar_part_type"),
            tuple(item.get("mesh_names") or []),
            json.dumps(
                (item.get("geometry") or {}).get("local_transform"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ),
        )
        for item in records
    )


def direct_morph_weight(avatar, morph_id):
    component = avatar.GetAvatarShapingComponent()
    if component is None:
        raise ReconstructionError("Avatar has no shaping component")
    try:
        return float(component.GetShapingMorphWeight(morph_id))
    except Exception as exc:
        raise ReconstructionError(
            "Unable to read morph {}: {}".format(morph_id, exc)
        )


def direct_eyelash_artifacts(case_dir):
    return {
        "face_front_preview": os.path.join(case_dir, "face_front.png"),
        "face_three_quarter_preview": os.path.join(
            case_dir, "face_three_quarter.png"
        ),
        "face_profile_preview": os.path.join(
            case_dir, "face_profile.png"
        ),
        "facial_pose_validation": os.path.join(
            case_dir, "facial_pose_validation.json"
        ),
        "eyelash_blink_preview": os.path.join(
            case_dir, "eyelash_blink_front.png"
        ),
        "eyelash_asymmetric_preview": os.path.join(
            case_dir, "eyelash_blink_left_front.png"
        ),
        "eyelash_wide_preview": os.path.join(
            case_dir, "eyelash_wide_front.png"
        ),
    }


def render_direct_eyelash_case(avatar, case_dir, progress_callback):
    os.makedirs(case_dir, exist_ok=False)
    artifacts = direct_eyelash_artifacts(case_dir)
    initial_position = {
        "x": _transform_float(avatar, "Position/PositionX"),
        "y": _transform_float(avatar, "Position/PositionY"),
        "z": _transform_float(avatar, "Position/PositionZ"),
    }
    initial_yaw = _transform_float(avatar, "Rotation/RotationZ")
    try:
        set_avatar_yaw(avatar, 0.0)
        progress_callback("render_face_profile")
        render_preview(artifacts["face_profile_preview"])
        set_avatar_yaw(avatar, 45.0)
        progress_callback("render_face_three_quarter")
        render_preview(artifacts["face_three_quarter_preview"])
        set_avatar_yaw(avatar, 90.0)
        progress_callback("render_face_front")
        render_preview(artifacts["face_front_preview"])
        pose_report = render_eyelash_visibility_previews(
            avatar,
            artifacts,
            progress_callback,
        )
    finally:
        set_avatar_yaw(avatar, math.degrees(initial_yaw))
        set_avatar_position(
            avatar,
            position_x=initial_position["x"],
            position_y=initial_position["y"],
            position_z=initial_position["z"],
        )
        checked(
            "Restore start time after direct eyelash validation",
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime()),
        )
        QtWidgets.QApplication.processEvents()
    return {
        "artifacts": artifacts,
        "facial_pose_validation": pose_report,
    }


def probe_direct_eyelash_matrix(
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    os.makedirs(output_dir, exist_ok=True)
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [
            item["preset_id"]
            for item in all_presets
            if not item.get("appearance_asset_ids")
        ]
    )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown direct eyelash baseline IDs: {}".format(missing)
        )
    selected = [by_id[item_id] for item_id in selected_ids]
    selected_sexes = sorted(set(item.get("sex") for item in selected))
    if (
        not selected_sexes
        or any(sex not in ("male", "female") for sex in selected_sexes)
    ):
        raise ReconstructionError(
            "Direct eyelash matrix requires male or female baselines"
        )

    appearance_catalog = load_appearance_catalog(library)
    if appearance_catalog is None:
        raise ReconstructionError(
            "Direct eyelash matrix requires an appearance catalog"
        )

    progress_path = os.path.join(output_dir, "progress.json")
    summary_path = os.path.join(output_dir, "validation_result.json")

    def mark_progress(sex, case_id, phase, detail=None):
        write_json(
            {
                "schema_version": 1,
                "updated_at": now(),
                "sex": sex,
                "case_id": case_id,
                "phase": phase,
                "detail": detail,
            },
            progress_path,
        )

    started_at = now()
    sex_results = []
    requested_asset_count = 0
    for sex in selected_sexes:
        baselines = [
            item
            for item in all_presets
            if item.get("sex") == sex
            and not item.get("appearance_asset_ids")
        ]
        if len(baselines) != 1:
            raise ReconstructionError(
                "Expected one {} direct eyelash baseline, found {}".format(
                    sex, len(baselines)
                )
            )
        baseline = baselines[0]
        asset_presets = [
            item
            for item in all_presets
            if item.get("sex") == sex
            and item.get("appearance_asset_ids")
        ]
        if not asset_presets:
            raise ReconstructionError(
                "Expected at least one {} eyelash asset".format(
                    sex
                )
            )
        expected_asset_count = len(asset_presets)
        requested_asset_count += expected_asset_count
        source_project = canonical_existing_file(
            (baseline.get("source_project") or {}).get("path"),
            "{} direct eyelash source project".format(sex),
        )
        camera_path = canonical_existing_file(
            baseline.get("face_camera"),
            "{} direct eyelash face camera".format(sex),
        )
        mark_progress(
            sex,
            baseline["preset_id"],
            "load_source_project",
            {"path": source_project},
        )
        source_load_status, source_dialog_policy = (
            load_file_with_optional_undo_warning(
                source_project,
                "Load {} direct eyelash source project".format(sex),
            )
        )
        QtWidgets.QApplication.processEvents()
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Expected one {} source avatar, found {}".format(
                    sex, len(avatars)
                )
            )

        lightroom = library.get("preview_lightroom")
        if lightroom:
            lightroom = canonical_existing_file(
                lightroom,
                "Direct eyelash preview Lightroom",
            )
            mark_progress(
                sex,
                baseline["preset_id"],
                "load_preview_lightroom",
                {"path": lightroom},
            )
            checked(
                "Load direct eyelash preview Lightroom",
                RLPy.RFileIO.LoadFile(lightroom),
            )
            QtWidgets.QApplication.processEvents()
        checked(
            "Load {} direct eyelash face camera".format(sex),
            RLPy.RFileIO.LoadFile(camera_path),
        )
        QtWidgets.QApplication.processEvents()
        if RLPy.RScene.GetCurrentCamera() is None:
            raise ReconstructionError(
                "{} direct eyelash validation has no active camera".format(
                    sex
                )
            )

        initial_eye_parts = direct_avatar_part_records(avatar, "eyes")
        initial_eyeball_move = direct_morph_weight(
            avatar, EYEBALL_MOVE_MORPH_ID
        )
        sex_dir = os.path.join(output_dir, sex)
        os.makedirs(sex_dir, exist_ok=False)
        baseline_dir = os.path.join(sex_dir, "baseline")
        mark_progress(
            sex,
            baseline["preset_id"],
            "render_baseline",
        )
        baseline_render = render_direct_eyelash_case(
            avatar,
            baseline_dir,
            lambda phase, detail=None: mark_progress(
                sex,
                baseline["preset_id"],
                phase,
                detail,
            ),
        )
        baseline_result = {
            "case_id": baseline["preset_id"],
            "source_project": source_project,
            "source_load_status": source_load_status,
            "source_dialog_policy": source_dialog_policy,
            "eye_parts": initial_eye_parts,
            "eyelash_parts": direct_avatar_part_records(
                avatar, "eyelashes"
            ),
            "eyeball_move": initial_eyeball_move,
            "render": baseline_render,
        }
        write_json(
            baseline_result,
            os.path.join(baseline_dir, "result.json"),
        )

        cases = []
        for index, preset in enumerate(asset_presets, 1):
            assets = resolve_appearance_assets(
                preset, appearance_catalog
            )
            if len(assets) != 1 or assets[0]["slot"] != "eyelashes":
                raise ReconstructionError(
                    "{} must resolve exactly one eyelash asset".format(
                        preset["preset_id"]
                    )
                )
            asset = assets[0]
            case_dir = os.path.join(
                sex_dir,
                "{:02d}_{}".format(index, preset["preset_id"]),
            )
            mark_progress(
                sex,
                preset["preset_id"],
                "load_eyelash",
                {
                    "asset_id": asset["asset_id"],
                    "display_name": asset["display_name"],
                    "path": asset["path"],
                },
            )
            eye_parts_before = direct_avatar_part_records(
                avatar, "eyes"
            )
            eye_signature_before = direct_avatar_part_signature(
                eye_parts_before
            )
            eyeball_move_before = direct_morph_weight(
                avatar, EYEBALL_MOVE_MORPH_ID
            )
            RLPy.RScene.SelectObject(avatar)
            load_status, dialog_policy = (
                load_file_with_character_preset_dialog(
                    asset["path"],
                    "Load direct eyelash {}".format(asset["asset_id"]),
                )
            )
            QtWidgets.QApplication.processEvents()
            current_avatar, current_avatars = resolve_avatar()
            if (
                len(current_avatars) != 1
                or scene_object_id(current_avatar)
                != scene_object_id(avatar)
            ):
                raise ReconstructionError(
                    "Avatar changed while loading {}".format(
                        asset["asset_id"]
                    )
                )
            avatar = current_avatar
            eye_parts = direct_avatar_part_records(avatar, "eyes")
            eye_signature = direct_avatar_part_signature(eye_parts)
            eyelash_parts = direct_avatar_part_records(
                avatar, "eyelashes"
            )
            if not eyelash_parts:
                raise ReconstructionError(
                    "No eyelash AvatarPart after {}".format(
                        asset["asset_id"]
                    )
                )
            eyeball_move = direct_morph_weight(
                avatar, EYEBALL_MOVE_MORPH_ID
            )
            render_result = render_direct_eyelash_case(
                avatar,
                case_dir,
                lambda phase, detail=None, active_id=preset[
                    "preset_id"
                ]: mark_progress(
                    sex,
                    active_id,
                    phase,
                    detail,
                ),
            )
            case_result = {
                "case_id": preset["preset_id"],
                "asset": asset,
                "load_status": load_status,
                "dialog_policy": dialog_policy,
                "eye_parts_before": eye_parts_before,
                "eye_parts": eye_parts,
                "eye_geometry_preserved": (
                    eye_signature == eye_signature_before
                ),
                "eyelash_parts": eyelash_parts,
                "eyeball_move_before": eyeball_move_before,
                "eyeball_move": eyeball_move,
                "eyeball_move_preserved": (
                    abs(eyeball_move - eyeball_move_before) <= 1e-7
                ),
                "render": render_result,
            }
            write_json(
                case_result,
                os.path.join(case_dir, "result.json"),
            )
            if not case_result["eye_geometry_preserved"]:
                raise ReconstructionError(
                    "Eye geometry changed while loading {}".format(
                        asset["asset_id"]
                    )
                )
            if not case_result["eyeball_move_preserved"]:
                raise ReconstructionError(
                    "Eyeball Move changed while loading {}".format(
                        asset["asset_id"]
                    )
                )
            cases.append(case_result)
            log(
                "DIRECT EYELASH {}/{} {} {}".format(
                    index,
                    expected_asset_count,
                    sex,
                    asset["display_name"],
                )
            )

        sex_result = {
            "sex": sex,
            "source_project": source_project,
            "camera": camera_path,
            "baseline": baseline_result,
            "asset_count": len(cases),
            "cases": cases,
            "success": len(cases) == expected_asset_count,
        }
        write_json(
            sex_result,
            os.path.join(sex_dir, "result.json"),
        )
        sex_results.append(sex_result)

    success_count = sum(
        item.get("asset_count", 0) for item in sex_results
    )
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "diagnostic_mode": "eyelash_direct_matrix",
        "requested_sexes": selected_sexes,
        "requested_asset_count": requested_asset_count,
        "success_count": success_count,
        "failure_count": requested_asset_count - success_count,
        "success": (
            len(sex_results) == len(selected_sexes)
            and all(item.get("success") for item in sex_results)
        ),
        "appearance_catalog": {
            "path": appearance_catalog["path"],
            "catalog_id": appearance_catalog["catalog_id"],
        },
        "sex_results": sex_results,
    }
    write_json(summary, summary_path)
    summary["summary_path"] = summary_path
    mark_progress(None, None, "complete")
    return summary


def compact_material_fingerprint(fingerprint):
    return {
        "digest": fingerprint.get("digest"),
        "mesh_digests": fingerprint.get("mesh_digests") or {},
        "mesh_names": fingerprint.get("mesh_names") or [],
        "observation_error_count": fingerprint.get(
            "observation_error_count"
        ),
        "texture_count": fingerprint.get("texture_count"),
    }


def evaluate_skin_material_change(before, after):
    before_meshes = before.get("mesh_digests") or {}
    after_meshes = after.get("mesh_digests") or {}
    changed_meshes = sorted(
        mesh_name
        for mesh_name in (set(before_meshes) | set(after_meshes))
        if before_meshes.get(mesh_name) != after_meshes.get(mesh_name)
    )
    material_changed = before.get("digest") != after.get("digest")
    texture_observable = bool(
        int(before.get("texture_count") or 0)
        or int(after.get("texture_count") or 0)
    )
    if material_changed and "CC_Base_Body" in changed_meshes:
        status = "verified_by_material_api"
        reason = "CC_Base_Body material fingerprint changed"
    elif material_changed:
        status = "failed"
        reason = "Material changed outside CC_Base_Body"
    elif not texture_observable:
        status = "render_confirmation_required"
        reason = (
            "RLPy exposed no skin texture samples; material API "
            "fingerprint is inconclusive"
        )
    else:
        status = "failed"
        reason = "Observable skin material fingerprint did not change"
    return {
        "changed_meshes": changed_meshes,
        "material_changed": material_changed,
        "reason": reason,
        "status": status,
        "texture_observable": texture_observable,
    }


def compact_vector_fingerprints(vectors):
    return {
        "body_and_junction_fingerprint_sha256": vectors.get(
            "body_and_junction_fingerprint_sha256"
        ),
        "body_and_junction_nonzero_count": vectors.get(
            "body_and_junction_nonzero_count"
        ),
        "groups": dict(
            (
                name,
                {
                    "fingerprint_sha256": group.get(
                        "fingerprint_sha256"
                    ),
                    "nonzero_count": group.get("nonzero_count"),
                },
            )
            for name, group in sorted(
                (vectors.get("groups") or {}).items()
            )
        ),
    }


def vector_weight_map(vectors):
    result = {}
    for group in (vectors.get("groups") or {}).values():
        for item in group.get("entries") or []:
            result[item["id"]] = {
                "classification": item.get("classification"),
                "display": item.get("display"),
                "weight": float(item["weight"]),
            }
    return result


def vector_differences(before, after):
    before_map = vector_weight_map(before)
    after_map = vector_weight_map(after)
    differences = []
    for morph_id in sorted(set(before_map) | set(after_map)):
        before_item = before_map.get(morph_id)
        after_item = after_map.get(morph_id)
        before_weight = (
            float(before_item["weight"]) if before_item else 0.0
        )
        after_weight = (
            float(after_item["weight"]) if after_item else 0.0
        )
        if abs(after_weight - before_weight) <= 1e-7:
            continue
        source = after_item or before_item
        differences.append(
            {
                "after": after_weight,
                "before": before_weight,
                "classification": source.get("classification"),
                "display": source.get("display"),
                "id": morph_id,
            }
        )
    return differences


def vectors_match(before, after):
    return compact_vector_fingerprints(
        before
    ) == compact_vector_fingerprints(after)


def set_direct_morph_weight(avatar, morph_id, target, label):
    component = avatar.GetAvatarShapingComponent()
    if component is None:
        raise ReconstructionError("Avatar has no shaping component")
    bounds = component.GetShapingMorphMinMax(morph_id)
    minimum = float(bounds.first)
    maximum = float(bounds.second)
    target = float(target)
    if target < minimum - 1e-7 or target > maximum + 1e-7:
        raise ReconstructionError(
            "{} target {} is outside [{}, {}]".format(
                label, target, minimum, maximum
            )
        )
    previous = float(component.GetShapingMorphWeight(morph_id))
    if abs(previous - target) > 1e-7:
        checked(
            "Set {}".format(label),
            component.SetShapingMorphWeight(morph_id, target),
        )
        checked(
            "Refresh {}".format(label),
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        checked(
            "Evaluate {}".format(label),
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
    actual = float(component.GetShapingMorphWeight(morph_id))
    if abs(actual - target) > 1e-7:
        raise ReconstructionError(
            "{} did not reach target {}: {}".format(
                label, target, actual
            )
        )
    return {
        "actual": actual,
        "bounds": {"maximum": maximum, "minimum": minimum},
        "previous": previous,
        "target": target,
    }


def skin_age_artifacts(age_dir):
    return {
        "face_front_preview": os.path.join(
            age_dir, "face_front.png"
        ),
        "face_profile_preview": os.path.join(
            age_dir, "face_profile.png"
        ),
        "face_three_quarter_preview": os.path.join(
            age_dir, "face_three_quarter.png"
        ),
    }


def render_skin_age_views(avatar, age_dir, progress_callback):
    os.makedirs(age_dir, exist_ok=False)
    artifacts = skin_age_artifacts(age_dir)
    initial_position = {
        "x": _transform_float(avatar, "Position/PositionX"),
        "y": _transform_float(avatar, "Position/PositionY"),
        "z": _transform_float(avatar, "Position/PositionZ"),
    }
    initial_yaw_radians = _transform_float(
        avatar, "Rotation/RotationZ"
    )
    try:
        set_avatar_yaw(avatar, 0.0)
        progress_callback("render_face_profile")
        render_preview(artifacts["face_profile_preview"])
        set_avatar_yaw(avatar, 45.0)
        progress_callback("render_face_three_quarter")
        render_preview(artifacts["face_three_quarter_preview"])
        set_avatar_yaw(avatar, 90.0)
        progress_callback("render_face_front")
        render_preview(artifacts["face_front_preview"])
    finally:
        set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
        set_avatar_position(
            avatar,
            position_x=initial_position["x"],
            position_y=initial_position["y"],
            position_z=initial_position["z"],
        )
        checked(
            "Restore start time after skin age validation",
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
        )
        QtWidgets.QApplication.processEvents()
    return artifacts


def probe_direct_skin_age_matrix(
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    os.makedirs(output_dir, exist_ok=True)
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "Skin age preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown skin age preset IDs: {}".format(missing)
        )
    selected = [by_id[item_id] for item_id in selected_ids]
    if any(item.get("sex") not in ("male", "female") for item in selected):
        raise ReconstructionError("Skin age presets have invalid sex")

    age_morph = library.get("age_morph") or {}
    age_morph_id = age_morph.get("id")
    age_levels = library.get("age_levels") or []
    if (
        not isinstance(age_morph_id, str)
        or not age_morph_id
        or [item.get("label") for item in age_levels]
        != ["young", "middle", "older"]
        or [float(item.get("weight")) for item in age_levels]
        != [0.0, 0.5, 1.0]
    ):
        raise ReconstructionError("Skin age controls are invalid")

    progress_path = os.path.join(output_dir, "progress.json")
    summary_path = os.path.join(output_dir, "validation_result.json")

    def mark_progress(sex, case_id, phase, detail=None):
        write_json(
            {
                "case_id": case_id,
                "detail": detail,
                "phase": phase,
                "schema_version": 1,
                "sex": sex,
                "updated_at": now(),
            },
            progress_path,
        )

    started_at = now()
    sex_results = []
    for sex in ("female", "male"):
        sex_presets = [
            item for item in selected if item.get("sex") == sex
        ]
        if not sex_presets:
            continue
        source_paths = {
            canonical_existing_file(
                (item.get("source_project") or {}).get("path"),
                "{} skin source project".format(sex),
            )
            for item in sex_presets
        }
        camera_paths = {
            canonical_existing_file(
                item.get("face_camera"),
                "{} skin face camera".format(sex),
            )
            for item in sex_presets
        }
        if len(source_paths) != 1 or len(camera_paths) != 1:
            raise ReconstructionError(
                "{} skin presets do not share one source and camera".format(
                    sex
                )
            )
        source_project = next(iter(source_paths))
        camera_path = next(iter(camera_paths))
        mark_progress(
            sex,
            None,
            "load_source_project",
            {"path": source_project},
        )
        source_status, source_dialog_policy = (
            load_file_with_optional_undo_warning(
                source_project,
                "Load {} skin source project".format(sex),
            )
        )
        QtWidgets.QApplication.processEvents()
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Expected one {} source avatar, found {}".format(
                    sex, len(avatars)
                )
            )
        avatar_id = scene_object_id(avatar)

        lightroom = canonical_existing_file(
            library.get("preview_lightroom"),
            "Skin preview Lightroom",
        )
        mark_progress(
            sex, None, "load_preview_lightroom", {"path": lightroom}
        )
        checked(
            "Load skin preview Lightroom",
            RLPy.RFileIO.LoadFile(lightroom),
        )
        checked(
            "Load {} skin face camera".format(sex),
            RLPy.RFileIO.LoadFile(camera_path),
        )
        QtWidgets.QApplication.processEvents()
        if RLPy.RScene.GetCurrentCamera() is None:
            raise ReconstructionError(
                "{} skin validation has no active camera".format(sex)
            )

        component, morphs, unused_categories = morph_catalog(avatar)
        if age_morph_id not in morphs:
            raise ReconstructionError(
                "Age morph is unavailable: {}".format(age_morph_id)
            )
        if morphs[age_morph_id]["display"] != age_morph.get("display"):
            raise ReconstructionError(
                "Age morph display changed: {}".format(
                    morphs[age_morph_id]["display"]
                )
            )
        age_zero = set_direct_morph_weight(
            avatar,
            age_morph_id,
            0.0,
            "Full Face Elder young baseline",
        )
        baseline_vectors = capture_vectors(avatar)
        baseline_vector_summary = compact_vector_fingerprints(
            baseline_vectors
        )
        initial_eye_parts = direct_avatar_part_records(avatar, "eyes")
        initial_eye_signature = direct_avatar_part_signature(
            initial_eye_parts
        )
        initial_eyeball_move = direct_morph_weight(
            avatar, EYEBALL_MOVE_MORPH_ID
        )
        previous_material = avatar_material_fingerprint(avatar)
        sex_dir = os.path.join(output_dir, sex)
        os.makedirs(sex_dir, exist_ok=False)
        cases = []

        for index, preset in enumerate(sex_presets, 1):
            asset = preset.get("skin_asset") or {}
            asset_path = canonical_existing_file(
                asset.get("path"),
                "{} skin asset".format(preset["preset_id"]),
            )
            case_dir = os.path.join(
                sex_dir,
                "{:02d}_{}".format(index, preset["preset_id"]),
            )
            os.makedirs(case_dir, exist_ok=False)
            case_result = {
                "age_from_filename": preset.get("age_from_filename"),
                "age_levels": [],
                "asset": asset,
                "case_id": preset["preset_id"],
                "group": preset.get("group"),
                "region_label": preset.get("region_label"),
                "sex": sex,
                "source_preset_id": preset.get("source_preset_id"),
            }
            try:
                set_direct_morph_weight(
                    avatar,
                    age_morph_id,
                    0.0,
                    "Reset Full Face Elder before skin load",
                )
                mark_progress(
                    sex,
                    preset["preset_id"],
                    "load_skin",
                    {
                        "asset_id": asset.get("asset_id"),
                        "display_name": asset.get("display_name"),
                        "path": asset_path,
                    },
                )
                RLPy.RScene.SelectObject(avatar)
                load_status, dialog_policy = (
                    load_file_with_skin_material_dialog(
                        asset_path,
                        "Load skin {}".format(asset.get("asset_id")),
                    )
                )
                QtWidgets.QApplication.processEvents()
                current_avatar, current_avatars = resolve_avatar()
                if (
                    len(current_avatars) != 1
                    or scene_object_id(current_avatar) != avatar_id
                ):
                    raise ReconstructionError(
                        "Avatar changed while loading {}".format(
                            asset.get("asset_id")
                        )
                    )
                avatar = current_avatar
                material_after = avatar_material_fingerprint(avatar)
                material_verification = evaluate_skin_material_change(
                    previous_material,
                    material_after,
                )
                changed_meshes = material_verification["changed_meshes"]
                vectors_after_skin = capture_vectors(avatar)
                morph_differences = vector_differences(
                    baseline_vectors, vectors_after_skin
                )
                eye_parts_after = direct_avatar_part_records(
                    avatar, "eyes"
                )
                eyeball_move_after = direct_morph_weight(
                    avatar, EYEBALL_MOVE_MORPH_ID
                )
                case_result.update(
                    {
                        "dialog_policy": dialog_policy,
                        "eye_geometry_preserved": (
                            direct_avatar_part_signature(
                                eye_parts_after
                            )
                            == initial_eye_signature
                        ),
                        "eyeball_move": eyeball_move_after,
                        "eyeball_move_preserved": (
                            abs(
                                eyeball_move_after
                                - initial_eyeball_move
                            )
                            <= 1e-7
                        ),
                        "load_status": load_status,
                        "material_after": (
                            compact_material_fingerprint(material_after)
                        ),
                        "material_before": (
                            compact_material_fingerprint(
                                previous_material
                            )
                        ),
                        "material_changed": material_verification[
                            "material_changed"
                        ],
                        "material_changed_meshes": changed_meshes,
                        "material_verification": material_verification,
                        "morph_differences_after_skin": morph_differences,
                        "morphs_preserved_after_skin": (
                            not morph_differences
                            and vectors_match(
                                baseline_vectors,
                                vectors_after_skin,
                            )
                        ),
                    }
                )
                if material_verification["status"] == "failed":
                    raise ReconstructionError(
                        material_verification["reason"]
                    )
                if not case_result["morphs_preserved_after_skin"]:
                    raise ReconstructionError(
                        "Skin changed morph weights: {}".format(
                            morph_differences
                        )
                    )
                if not case_result["eye_geometry_preserved"]:
                    raise ReconstructionError(
                        "Skin changed eye AvatarPart identity"
                    )
                if not case_result["eyeball_move_preserved"]:
                    raise ReconstructionError(
                        "Skin changed Eyeball Move"
                    )

                for age_level in age_levels:
                    age_label = age_level["label"]
                    age_dir = os.path.join(case_dir, age_label)
                    age_apply = set_direct_morph_weight(
                        avatar,
                        age_morph_id,
                        float(age_level["weight"]),
                        "Full Face Elder {}".format(age_label),
                    )
                    mark_progress(
                        sex,
                        preset["preset_id"],
                        "render_age",
                        {
                            "age_label": age_label,
                            "weight": age_level["weight"],
                        },
                    )
                    artifacts = render_skin_age_views(
                        avatar,
                        age_dir,
                        lambda phase, detail=None, active_age=age_label: (
                            mark_progress(
                                sex,
                                preset["preset_id"],
                                "{}_{}".format(active_age, phase),
                                detail,
                            )
                        ),
                    )
                    case_result["age_levels"].append(
                        {
                            "application": age_apply,
                            "artifacts": artifacts,
                            "label": age_label,
                            "ui_value": age_level.get("ui_value"),
                            "weight": float(age_level["weight"]),
                        }
                    )

                age_reset = set_direct_morph_weight(
                    avatar,
                    age_morph_id,
                    0.0,
                    "Reset Full Face Elder after skin validation",
                )
                vectors_after_age_cycle = capture_vectors(avatar)
                age_cycle_differences = vector_differences(
                    baseline_vectors, vectors_after_age_cycle
                )
                case_result.update(
                    {
                        "age_cycle_differences": age_cycle_differences,
                        "age_cycle_reset": age_reset,
                        "age_cycle_restored": (
                            not age_cycle_differences
                            and vectors_match(
                                baseline_vectors,
                                vectors_after_age_cycle,
                            )
                        ),
                        "success": True,
                    }
                )
                if not case_result["age_cycle_restored"]:
                    raise ReconstructionError(
                        "Age cycle did not restore the morph baseline"
                    )
                previous_material = material_after
                cases.append(case_result)
                write_json(
                    case_result,
                    os.path.join(case_dir, "result.json"),
                )
                log(
                    "DIRECT SKIN {}/{} {} {}".format(
                        index,
                        len(sex_presets),
                        sex,
                        asset.get("display_name"),
                    )
                )
            except Exception as exc:
                case_result["error"] = {
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                    "type": type(exc).__name__,
                }
                case_result["success"] = False
                write_json(
                    case_result,
                    os.path.join(case_dir, "result.json"),
                )
                raise

        sex_result = {
            "age_morph": {
                "baseline_application": age_zero,
                "display": age_morph.get("display"),
                "id": age_morph_id,
            },
            "asset_count": len(cases),
            "baseline_vectors": baseline_vector_summary,
            "camera": camera_path,
            "cases": cases,
            "sex": sex,
            "source_dialog_policy": source_dialog_policy,
            "source_load_status": source_status,
            "source_project": source_project,
            "success": len(cases) == len(sex_presets),
        }
        write_json(
            sex_result, os.path.join(sex_dir, "result.json")
        )
        sex_results.append(sex_result)

    success_count = sum(
        item.get("asset_count", 0) for item in sex_results
    )
    requested_count = len(selected)
    summary = {
        "age_state_count": success_count * len(age_levels),
        "diagnostic_mode": "skin_age_direct_matrix",
        "failure_count": requested_count - success_count,
        "finished_at": now(),
        "library_id": library.get("library_id"),
        "requested_asset_count": requested_count,
        "requested_age_state_count": requested_count
        * len(age_levels),
        "schema_version": 1,
        "sex_results": sex_results,
        "started_at": started_at,
        "success": (
            success_count == requested_count
            and all(item.get("success") for item in sex_results)
        ),
        "success_count": success_count,
    }
    write_json(summary, summary_path)
    summary["summary_path"] = summary_path
    mark_progress(None, None, "complete")
    return summary


def probe_current_official_expression(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("official_expression_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError(
            "official_expression_probe must be an object"
        )
    expression_path = canonical_existing_file(
        probe.get("path"),
        "Official expression probe",
    )
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Official expression probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Current avatar has no face component for expression probe"
        )
    camera_path = probe.get("camera_path")
    if camera_path:
        camera_path = canonical_existing_file(
            camera_path,
            "Official expression probe camera",
        )
        checked(
            "Load official expression probe camera",
            RLPy.RFileIO.LoadFile(camera_path),
        )
        QtWidgets.QApplication.processEvents()
    camera = RLPy.RScene.GetCurrentCamera()
    if camera is None:
        raise ReconstructionError(
            "Official expression probe has no active camera"
        )

    fps = RLPy.RGlobal.GetFps()
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    camera_reference_time = RLPy.RGlobal.GetStartTime()
    checked(
        "Set official expression camera reference time",
        RLPy.RGlobal.SetTime(camera_reference_time, True),
    )
    camera_transform = RLPy.RTransform(camera.LocalTransform())
    camera_focal_length = float(
        camera.GetFocalLength(camera_reference_time)
    )
    camera_transform_control = camera.GetControl("Transform")
    camera_can_be_frozen = camera_transform_control is not None
    initial_clip_count = int(face_component.GetClipCount())
    replace_existing_clips = bool(
        probe.get("replace_existing_expression_clips", True)
    )
    removed_expression_clips = 0
    if replace_existing_clips:
        for clip_index in range(initial_clip_count - 1, -1, -1):
            checked(
                "Delete existing official expression probe clip {}".format(
                    clip_index
                ),
                face_component.DeleteClip(
                    face_component.GetClip(clip_index)
                ),
            )
            removed_expression_clips += 1
            QtWidgets.QApplication.processEvents()
    probe_baseline_clip_count = int(face_component.GetClipCount())
    RLPy.RScene.SelectObject(avatar)
    checked(
        "Apply official expression probe",
        RLPy.RFileIO.LoadFile(expression_path),
    )
    QtWidgets.QApplication.processEvents()
    QtWidgets.QApplication.processEvents()

    current_time = RLPy.RGlobal.GetTime()
    end_time = RLPy.RGlobal.GetEndTime()
    current_frame = int(fps.GetFrameIndex(current_time))
    end_frame = int(fps.GetFrameIndex(end_time))
    after_clip_count = int(face_component.GetClipCount())
    if after_clip_count <= probe_baseline_clip_count:
        raise ReconstructionError(
            "Official expression did not add a facial expression clip"
        )

    clip_records = []
    observed_clip_frames = [current_frame, end_frame]
    for clip_index in range(probe_baseline_clip_count, after_clip_count):
        clip = face_component.GetClip(clip_index)
        record = {
            "index": clip_index,
            "python_type": type(clip).__name__,
            "methods": _callable_names(
                clip,
                ("time", "start", "end", "length", "name"),
            ),
        }
        for label, method_name in (
            ("name", "GetName"),
            ("start_time", "GetStartTime"),
            ("end_time", "GetEndTime"),
            ("length", "GetLength"),
            ("clip_length", "GetClipLength"),
            ("last_key_time", "GetLastKeyTime"),
            ("start_offset", "GetStartOffset"),
        ):
            method = getattr(clip, method_name, None)
            if not callable(method):
                continue
            try:
                value = method()
                if "time" in label or label == "length":
                    record[label] = str(value)
                    record[label + "_frame"] = int(
                        fps.GetFrameIndex(value)
                    )
                    observed_clip_frames.append(
                        record[label + "_frame"]
                    )
                elif label in ("clip_length", "start_offset"):
                    record[label] = str(value)
                    record[label + "_frame"] = int(
                        fps.GetFrameIndex(value)
                    )
                    observed_clip_frames.append(
                        record[label + "_frame"]
                    )
                else:
                    record[label] = str(value)
            except Exception as exc:
                record[label + "_error"] = str(exc)
        clip_records.append(record)

    clip_end_frame = max([0] + observed_clip_frames)
    candidate_frames = [
        current_frame,
        0,
        1,
        5,
        10,
        clip_end_frame // 4,
        clip_end_frame // 2,
        (clip_end_frame * 3) // 4,
        max(0, clip_end_frame - 1),
        clip_end_frame,
    ]
    requested_frames = probe.get("frames")
    if requested_frames is not None:
        if (
            not isinstance(requested_frames, list)
            or any(not isinstance(item, int) for item in requested_frames)
        ):
            raise ReconstructionError(
                "official_expression_probe.frames must be an integer list"
            )
        candidate_frames.extend(requested_frames)
    render_frames = []
    for frame in candidate_frames:
        frame = max(0, min(int(frame), clip_end_frame))
        if frame not in render_frames:
            render_frames.append(frame)

    pose_records = []
    try:
        if clip_end_frame > end_frame:
            checked(
                "Extend official expression probe timeline",
                RLPy.RGlobal.SetEndTime(
                    RLPy.IndexedFrameTime(clip_end_frame, fps)
                ),
            )
        set_avatar_yaw(avatar, 90.0)
        for frame in render_frames:
            render_time = RLPy.IndexedFrameTime(frame, fps)
            image_path = os.path.join(
                output_dir,
                "official_expression_frame_{:04d}.png".format(frame),
            )
            if camera_can_be_frozen:
                checked(
                    "Freeze official expression camera at frame {}".format(
                        frame
                    ),
                    camera_transform_control.SetValue(
                        render_time,
                        camera_transform,
                    ),
                )
                checked(
                    (
                        "Freeze official expression focal length at frame {}"
                    ).format(frame),
                    camera.SetFocalLength(
                        render_time,
                        camera_focal_length,
                    ),
                )
                camera.Update()
            checked(
                "Restore official expression camera at frame {}".format(
                    frame
                ),
                RLPy.RScene.SetCurrentCamera(camera),
            )
            render_preview(image_path, render_time)
            pose_records.append(
                {
                    "frame": frame,
                    "image": image_path,
                    "avatar_bounds": capture_bounds(avatar),
                    "camera": camera_state(RLPy.RScene.GetCurrentCamera()),
                }
            )
    finally:
        for clip_index in range(
            int(face_component.GetClipCount()) - 1,
            probe_baseline_clip_count - 1,
            -1,
        ):
            face_component.DeleteClip(face_component.GetClip(clip_index))
            QtWidgets.QApplication.processEvents()
        RLPy.RGlobal.SetTime(initial_time, True)
        if RLPy.RGlobal.GetEndTime() != initial_end_time:
            RLPy.RGlobal.SetEndTime(initial_end_time)
        QtWidgets.QApplication.processEvents()

    report = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "official_expression_probe",
        "expression_path": expression_path,
        "camera_path": camera_path,
        "camera_can_be_frozen": camera_can_be_frozen,
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "timeline": {
            "initial_frame": int(fps.GetFrameIndex(initial_time)),
            "initial_end_frame": int(fps.GetFrameIndex(initial_end_time)),
            "post_load_current_frame": current_frame,
            "post_load_end_frame": end_frame,
            "observed_clip_end_frame": clip_end_frame,
        },
        "initial_expression_clip_count": initial_clip_count,
        "replace_existing_expression_clips": replace_existing_clips,
        "removed_expression_clip_count": removed_expression_clips,
        "probe_baseline_expression_clip_count": probe_baseline_clip_count,
        "post_load_expression_clip_count": after_clip_count,
        "new_clips": clip_records,
        "poses": pose_records,
        "scene_restored": {
            "expression_clip_count": int(face_component.GetClipCount()),
            "frame": int(fps.GetFrameIndex(RLPy.RGlobal.GetTime())),
            "end_frame": int(fps.GetFrameIndex(RLPy.RGlobal.GetEndTime())),
        },
    }
    report_path = os.path.join(
        output_dir,
        "official_expression_probe.json",
    )
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "official_expression_probe",
        "official_expression_probe_path": report_path,
        "summary_path": report_path,
    }


def _callable_names(value, terms=None):
    terms = tuple(item.lower() for item in (terms or ()))
    names = []
    for name in dir(value):
        lowered = name.lower()
        if terms and not any(term in lowered for term in terms):
            continue
        try:
            member = getattr(value, name)
        except Exception:
            continue
        if callable(member):
            names.append(name)
    return sorted(names)


def _vector3_data(value):
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def _quaternion_data(value):
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
        "w": float(value.w),
    }


def _transform_data(value):
    data = {
        "translation": _vector3_data(value.T()),
        "rotation": _quaternion_data(value.R()),
    }
    for name in ("D", "S", "U"):
        try:
            candidate = getattr(value, name)()
            if hasattr(candidate, "X"):
                data[name.lower()] = _vector3_data(candidate)
            else:
                data[name.lower()] = float(candidate)
        except Exception as exc:
            data[name.lower() + "_error"] = str(exc)
    return data


def _variant_data(value):
    if value is None:
        return None
    result = {"type": int(value.GetType())}
    conversions = (
        ("float", "ToFloat"),
        ("int32", "ToInt32"),
        ("uint32", "ToUInt32"),
        ("bool", "ToBool"),
        ("string", "ToString"),
    )
    for label, method_name in conversions:
        try:
            converted = getattr(value, method_name)()
            if label == "float":
                converted = float(converted)
            elif label in ("int32", "uint32"):
                converted = int(converted)
            elif label == "bool":
                converted = bool(converted)
            else:
                converted = str(converted)
            result[label] = converted
        except Exception:
            continue
    return result


def _data_block_probe(block, time):
    if block is None:
        return None
    result = {
        "type": type(block).__name__,
        "attributes": [],
    }
    try:
        attributes = list(block.GetAttributes() or [])
    except Exception as exc:
        result["attributes_error"] = str(exc)
        attributes = []
    for attribute in attributes:
        item = {}
        try:
            item["name"] = str(attribute.GetName())
        except Exception as exc:
            item["name_error"] = str(exc)
        try:
            item["type"] = int(attribute.GetType())
        except Exception as exc:
            item["type_error"] = str(exc)
        try:
            item["flag"] = int(attribute.GetFlag())
        except Exception as exc:
            item["flag_error"] = str(exc)
        if item.get("name"):
            try:
                item["data"] = _variant_data(block.GetData(item["name"], time))
            except Exception as exc:
                item["data_error"] = str(exc)
        result["attributes"].append(item)
    return result


def _capture_eye_bones(skeleton):
    eye_bones = []
    for bone in list(skeleton.GetSkinBones() or []):
        name = str(bone.GetName())
        if "eye" not in name.lower():
            continue
        bone.Update()
        item = {
            "name": name,
            "id": str(bone.GetID()),
            "local_transform": _transform_data(bone.LocalTransform()),
            "basis_transform": _transform_data(bone.BasisTransform()),
            "world_transform": _transform_data(bone.WorldTransform()),
        }
        try:
            item["t_pose_position"] = _vector3_data(
                skeleton.GetBoneTPosePosition(bone)
            )
        except Exception as exc:
            item["t_pose_position_error"] = str(exc)
        try:
            item["is_animated"] = bool(skeleton.IsBoneAnimated(bone))
        except Exception as exc:
            item["is_animated_error"] = str(exc)
        eye_bones.append(item)
    return eye_bones


def capture_eye_integrity_state(avatar):
    component, catalog, unused_categories = morph_catalog(avatar)
    morph = catalog.get(EYEBALL_MOVE_MORPH_ID)
    skeleton = avatar.GetSkeletonComponent()
    if skeleton is None:
        raise ReconstructionError("Avatar has no skeleton component")
    look_at = skeleton.GetLookAtComponent()
    eye_part_type = getattr(RLPy, "EAvatarPartType_Eyes", None)
    eye_parts = (
        [
            avatar_part_record(part)
            for part in avatar_parts_of_type(avatar, eye_part_type)
        ]
        if eye_part_type is not None
        else []
    )
    state = {
        "eyeball_move": {
            "id": EYEBALL_MOVE_MORPH_ID,
            "available": morph is not None,
            "display": morph["display"] if morph else None,
            "weight": (
                float(component.GetShapingMorphWeight(EYEBALL_MOVE_MORPH_ID))
                if morph
                else None
            ),
        },
        "avatar_parts": eye_parts,
        "avatar_part_count": len(eye_parts),
        "avatar_part_type_available": eye_part_type is not None,
        "eye_bones": _capture_eye_bones(skeleton),
        "look_at": {
            "available": look_at is not None,
            "valid": bool(look_at.IsValid()) if look_at is not None else None,
        },
    }
    return state


def force_avatar_scene_evaluation(avatar, settle_seconds=1.0):
    time_value = RLPy.RGlobal.GetStartTime()
    checked(
        "Refresh avatar Morph evaluation",
        RLPy.RGlobal.ObjectModified(
            avatar,
            RLPy.EObjectModifiedType_MorphWeight,
        ),
    )
    checked(
        "Force avatar scene evaluation",
        RLPy.RGlobal.SetTime(time_value, True),
    )
    settle_cc_ui(settle_seconds)


def stabilize_neutral_eye_state(
    avatar,
    expected_state,
    attempts=4,
    settle_seconds=1.0,
):
    records = []
    actual_state = None
    comparison = None
    for attempt_index in range(1, int(attempts) + 1):
        force_avatar_scene_evaluation(
            avatar,
            settle_seconds=settle_seconds,
        )
        actual_state = capture_eye_integrity_state(avatar)
        comparison = compare_neutral_eye_states(
            expected_state,
            actual_state,
        )
        records.append(
            {
                "attempt": attempt_index,
                "differences": comparison["differences"],
                "matches": comparison["matches"],
            }
        )
        if comparison["matches"]:
            break
    return actual_state, comparison, records


def compare_neutral_eye_states(
    before,
    after,
    tolerance=2e-3,
    include_world=True,
    include_runtime_ids=True,
    t_pose_tolerance=None,
):
    differences = []
    before_signature = eye_integrity_structure_signature(
        before,
        include_runtime_ids=include_runtime_ids,
    )
    after_signature = eye_integrity_structure_signature(
        after,
        include_runtime_ids=include_runtime_ids,
    )
    if before_signature != after_signature:
        differences.append(
            {
                "field": "structure_signature",
                "before": before_signature,
                "after": after_signature,
            }
        )
    if t_pose_tolerance is None:
        t_pose_tolerance = tolerance
    if float(t_pose_tolerance) < float(tolerance):
        raise ReconstructionError(
            "t_pose_tolerance cannot be smaller than tolerance"
        )
    before_weight = before.get("eyeball_move", {}).get("weight")
    after_weight = after.get("eyeball_move", {}).get("weight")
    if (
        before_weight is None
        or after_weight is None
        or abs(float(before_weight) - float(after_weight)) > 1e-7
    ):
        differences.append(
            {
                "field": "eyeball_move.weight",
                "before": before_weight,
                "after": after_weight,
            }
        )
    before_bones = dict(
        (item.get("name"), item)
        for item in (before.get("eye_bones") or [])
    )
    after_bones = dict(
        (item.get("name"), item)
        for item in (after.get("eye_bones") or [])
    )
    if set(before_bones) != set(after_bones):
        differences.append(
            {
                "field": "eye_bone_names",
                "before": sorted(before_bones),
                "after": sorted(after_bones),
            }
        )

    vector_paths = [
        (("local_transform", "s"), ("x", "y", "z")),
        (("local_transform", "translation"), ("x", "y", "z")),
        (("local_transform", "rotation"), ("w", "x", "y", "z")),
        (("basis_transform", "s"), ("x", "y", "z")),
        (("basis_transform", "translation"), ("x", "y", "z")),
        (("basis_transform", "rotation"), ("w", "x", "y", "z")),
        (("t_pose_position",), ("x", "y", "z")),
    ]
    if include_world:
        vector_paths.extend(
            [
                (("world_transform", "s"), ("x", "y", "z")),
                (
                    ("world_transform", "translation"),
                    ("x", "y", "z"),
                ),
                (
                    ("world_transform", "rotation"),
                    ("w", "x", "y", "z"),
                ),
            ]
        )
    for name in sorted(set(before_bones) & set(after_bones)):
        before_bone = before_bones[name]
        after_bone = after_bones[name]
        for path, axes in vector_paths:
            before_value = before_bone
            after_value = after_bone
            for key in path:
                before_value = (
                    before_value.get(key)
                    if isinstance(before_value, dict)
                    else None
                )
                after_value = (
                    after_value.get(key)
                    if isinstance(after_value, dict)
                    else None
                )
            for axis in axes:
                before_axis = (
                    before_value.get(axis)
                    if isinstance(before_value, dict)
                    else None
                )
                after_axis = (
                    after_value.get(axis)
                    if isinstance(after_value, dict)
                    else None
                )
                axis_tolerance = (
                    max(tolerance, 2e-2)
                    if path == ("world_transform", "translation")
                    else (
                        float(t_pose_tolerance)
                        if path == ("t_pose_position",)
                        else tolerance
                    )
                )
                if (
                    before_axis is None
                    or after_axis is None
                    or abs(float(before_axis) - float(after_axis))
                    > axis_tolerance
                ):
                    differences.append(
                        {
                            "field": "{}.{}.{}".format(
                                name,
                                ".".join(path),
                                axis,
                            ),
                            "before": before_axis,
                            "after": after_axis,
                        }
                    )
    return {
        "differences": differences,
        "include_world": include_world,
        "include_runtime_ids": include_runtime_ids,
        "matches": not differences,
        "t_pose_tolerance": float(t_pose_tolerance),
        "tolerance": tolerance,
        "world_translation_tolerance": max(tolerance, 2e-2),
    }


def eye_integrity_structure_signature(
    state,
    include_runtime_ids=True,
):
    return {
        "avatar_parts": sorted(
            (
                item.get("id") if include_runtime_ids else None,
                item.get("name"),
                item.get("python_type"),
                item.get("avatar_part_type"),
                tuple(item.get("mesh_names") or []),
            )
            for item in (state.get("avatar_parts") or [])
        ),
        "eye_bones": sorted(
            (
                item.get("id") if include_runtime_ids else None,
                item.get("name"),
            )
            for item in (state.get("eye_bones") or [])
        ),
        "look_at": {
            "available": (state.get("look_at") or {}).get("available"),
            "valid": (state.get("look_at") or {}).get("valid"),
        },
    }


def probe_current_head_preset(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("head_preset_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError("head_preset_probe must be an object")
    preset_path = canonical_existing_file(
        probe.get("path"),
        "Head preset probe",
    )
    seed_id = probe.get("seed_id", "HEAD_PRESET_PROBE")
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Head preset probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    before_state = capture_eye_integrity_state(avatar)
    avatar, application = load_primary_head_preset(
        avatar,
        {
            "primary_seed_id": seed_id,
            "source_head_preset": {
                "path": preset_path,
                "sha256": probe.get("sha256"),
            },
        },
    )
    after_state = capture_eye_integrity_state(avatar)
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "head_preset_probe",
        "seed_id": seed_id,
        "preset_path": preset_path,
        "application": application,
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "eye_integrity": {
            "before": before_state,
            "after": after_state,
        },
    }
    report_path = os.path.join(output_dir, "head_preset_probe.json")
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "head_preset_probe",
        "head_preset_probe_path": report_path,
        "summary_path": report_path,
    }


def probe_source_project_load(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("source_project_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError("source_project_probe must be an object")
    source_project = canonical_existing_file(
        probe.get("path"),
        "Source project probe",
    )
    progress_path = os.path.join(output_dir, "progress.json")
    result_path = os.path.join(output_dir, "source_project_load_result.json")

    def mark_phase(phase):
        write_json(
            {
                "schema_version": 1,
                "updated_at": now(),
                "phase": phase,
                "source_project": source_project,
            },
            progress_path,
        )

    started_at = now()
    mark_phase("before_load")
    load_status = checked(
        "Load source project probe",
        RLPy.RFileIO.LoadFile(source_project),
    )
    mark_phase("load_returned")
    QtWidgets.QApplication.processEvents()
    avatar, avatars = resolve_avatar()
    vectors = capture_vectors(avatar)
    result = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "source_project_load",
        "source_project": source_project,
        "load_status": load_status,
        "avatar_count": len(avatars),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "body_and_junction_fingerprint_sha256": vectors[
            "body_and_junction_fingerprint_sha256"
        ],
        "progress_path": progress_path,
        "summary_path": result_path,
    }
    write_json(result, result_path)
    mark_phase("complete")
    return result


def probe_avatar_preset_save(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("avatar_preset_save_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError("avatar_preset_save_probe must be an object")
    source_project = canonical_existing_file(
        probe.get("source_project"),
        "Avatar preset source project",
    )
    base_avatar = canonical_existing_file(
        probe.get("base_avatar"),
        "Avatar preset neutral base",
    )
    preset_name = probe.get("preset_name", "Body_Morph_Save_Pilot")
    if (
        not isinstance(preset_name, str)
        or not preset_name
        or any(char in preset_name for char in '<>:"/\\|?*')
    ):
        raise ReconstructionError("avatar preset_name is invalid")

    progress_path = os.path.join(output_dir, "progress.json")
    result_path = os.path.join(output_dir, "avatar_preset_save_result.json")
    preset_path = os.path.join(output_dir, preset_name + ".ccAvatarPreset")
    source_vectors_path = os.path.join(output_dir, "source_vectors.json")
    baseline_vectors_path = os.path.join(output_dir, "baseline_vectors.json")
    applied_vectors_path = os.path.join(output_dir, "applied_vectors.json")

    def mark_phase(phase):
        write_json(
            {
                "schema_version": 1,
                "updated_at": now(),
                "phase": phase,
                "source_project": source_project,
                "preset_path": preset_path,
            },
            progress_path,
        )

    started_at = now()
    mark_phase("load_source_project")
    checked(
        "Load avatar preset source project",
        RLPy.RFileIO.LoadFile(source_project),
    )
    source_avatar, source_avatars = resolve_avatar()
    if len(source_avatars) != 1:
        raise ReconstructionError(
            "Expected one source avatar, found {}".format(len(source_avatars))
        )
    source_vectors = capture_vectors(source_avatar)
    write_json(source_vectors, source_vectors_path)

    mark_phase("save_avatar_preset_all")
    save_setting = RLPy.RSaveFileSetting()
    save_setting.SetSaveType(RLPy.ESaveFileType_AvatarPresetAll)
    save_status = checked(
        "Save AvatarPresetAll pilot",
        RLPy.RFileIO.SaveFile(source_avatar, save_setting, preset_path),
    )
    if not os.path.isfile(preset_path) or os.path.getsize(preset_path) <= 0:
        raise ReconstructionError(
            "Avatar preset save returned without a non-empty file"
        )

    mark_phase("load_neutral_base")
    neutral_avatar, base_attempts = load_base(base_avatar)
    baseline_vectors = capture_vectors(neutral_avatar)
    write_json(baseline_vectors, baseline_vectors_path)

    mark_phase("apply_saved_avatar_preset")
    neutral_id = scene_object_id(neutral_avatar)
    RLPy.RScene.SelectObject(neutral_avatar)
    apply_status = checked(
        "Apply saved AvatarPresetAll pilot",
        RLPy.RFileIO.LoadFile(preset_path),
    )
    current_avatars = list(RLPy.RScene.GetAvatars() or [])
    matches = [
        avatar
        for avatar in current_avatars
        if scene_object_id(avatar) == neutral_id
    ]
    if len(matches) != 1:
        raise ReconstructionError(
            "Avatar identity changed while applying saved avatar preset"
        )
    applied_avatar = matches[0]
    applied_vectors = capture_vectors(applied_avatar)
    write_json(applied_vectors, applied_vectors_path)

    deltas = {
        "body_from_source": group_delta(
            source_vectors["groups"]["body"]["entries"],
            applied_vectors["groups"]["body"]["entries"],
        ),
        "junction_from_source": group_delta(
            source_vectors["groups"]["junction"]["entries"],
            applied_vectors["groups"]["junction"]["entries"],
        ),
        "face_from_neutral": group_delta(
            baseline_vectors["groups"]["face"]["entries"],
            applied_vectors["groups"]["face"]["entries"],
        ),
        "other_from_neutral": group_delta(
            baseline_vectors["groups"]["other"]["entries"],
            applied_vectors["groups"]["other"]["entries"],
        ),
    }
    body_matches_source = not bool(
        deltas["body_from_source"] or deltas["junction_from_source"]
    )
    face_unchanged_from_neutral = not bool(deltas["face_from_neutral"])
    other_unchanged_from_neutral = not bool(deltas["other_from_neutral"])
    result = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "avatar_preset_save",
        "source_project": source_project,
        "base_avatar": base_avatar,
        "base_load_attempts": base_attempts,
        "save_type": "ESaveFileType_AvatarPresetAll",
        "save_status": save_status,
        "apply_status": apply_status,
        "preset_path": preset_path,
        "preset_bytes": os.path.getsize(preset_path),
        "body_matches_source": body_matches_source,
        "face_unchanged_from_neutral": face_unchanged_from_neutral,
        "other_unchanged_from_neutral": other_unchanged_from_neutral,
        "body_only_qualified": (
            body_matches_source
            and face_unchanged_from_neutral
            and other_unchanged_from_neutral
        ),
        "deltas": deltas,
        "artifacts": {
            "progress": progress_path,
            "source_vectors": source_vectors_path,
            "baseline_vectors": baseline_vectors_path,
            "applied_vectors": applied_vectors_path,
            "saved_preset": preset_path,
        },
        "summary_path": result_path,
    }
    write_json(result, result_path)
    mark_phase("complete")
    return result


def validate_expected_eye_integrity(
    state,
    expected_weight,
    phase,
    tolerance=1e-7,
):
    morph = state["eyeball_move"]
    if not morph["available"]:
        raise ReconstructionError(
            "{} is unavailable during {}".format(EYEBALL_MOVE_MORPH_ID, phase)
        )
    actual = float(morph["weight"])
    if abs(actual - float(expected_weight)) > tolerance:
        raise ReconstructionError(
            "Eyeball Move changed during {}: expected={} actual={}".format(
                phase, expected_weight, actual
            )
        )


def probe_current_eye_state(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    time = RLPy.RGlobal.GetStartTime()
    checked("Set eye probe time", RLPy.RGlobal.SetTime(time))
    skeleton = avatar.GetSkeletonComponent()
    if skeleton is None:
        raise ReconstructionError("Current avatar has no skeleton component")
    eye_bones = _capture_eye_bones(skeleton)
    vectors = capture_vectors(avatar)
    vectors_path = os.path.join(output_dir, "current_vectors.json")
    write_json(vectors, vectors_path)
    look_at = skeleton.GetLookAtComponent()
    look_at_data = None
    if look_at is not None:
        look_at_data = {
            "type": type(look_at).__name__,
            "valid": bool(look_at.IsValid()),
            "methods": _callable_names(look_at),
        }
        look_at_blocks = (
            ("offset", lambda: look_at.GetLookAtOffsetDataBlock()),
            ("eye_weight", lambda: look_at.GetLookAtWeightDataBlock(False)),
            ("body_weight", lambda: look_at.GetLookAtWeightDataBlock(True)),
        )
        for label, getter in look_at_blocks:
            try:
                look_at_data[label] = _data_block_probe(getter(), time)
            except Exception as exc:
                look_at_data[label + "_error"] = str(exc)

    face = avatar.GetFaceComponent()
    low_level = getattr(RLPy, "_RLPy", None)
    avatar_parts = {}
    for slot in ("eyes", "eyelashes"):
        try:
            part_type = avatar_part_type_for_slot(slot)
            avatar_parts[slot] = [
                avatar_part_record(part)
                for part in avatar_parts_of_type(avatar, part_type)
            ]
        except Exception as exc:
            avatar_parts[slot] = {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            }
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar_count": len(avatars),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
            "bounds": capture_bounds(avatar),
        },
        "time": str(time),
        "eye_bones": eye_bones,
        "morph_vectors": {
            "path": vectors_path,
            "catalog_morph_count": vectors["catalog_morph_count"],
            "groups": dict(
                (
                    name,
                    {
                        "nonzero_count": group["nonzero_count"],
                        "fingerprint_sha256": group["fingerprint_sha256"],
                    },
                )
                for name, group in vectors["groups"].items()
            ),
        },
        "avatar_parts": avatar_parts,
        "eye_support_morphs": capture_eye_part_morph_weights(avatar),
        "look_at": look_at_data,
        "face_component": {
            "type": type(face).__name__ if face is not None else None,
            "valid": bool(face.IsValid()) if face is not None else False,
            "methods": _callable_names(
                face, ("eye", "key", "pose", "expression")
            )
            if face is not None
            else [],
        },
        "low_level_eye_api": _callable_names(
            low_level, ("facecomponent", "lookat", "eye")
        )
        if low_level is not None
        else [],
    }
    report_path = os.path.join(output_dir, "eye_state.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "eye_state",
        "eye_state_path": report_path,
        "summary_path": summary_path,
    }


def probe_current_eye_state_refresh(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Eye refresh probe expected one avatar"
        )
    time = RLPy.RGlobal.GetStartTime()
    checked(
        "Set eye refresh probe time",
        RLPy.RGlobal.SetTime(time, True),
    )
    QtWidgets.QApplication.processEvents()
    before = capture_eye_integrity_state(avatar)
    skeleton = avatar.GetSkeletonComponent()
    eye_bone_api = []
    for bone in list(skeleton.GetSkinBones() or []):
        if "eye" not in str(bone.GetName()).lower():
            continue
        eye_bone_api.append(
            {
                "methods": _callable_names(
                    bone,
                    (
                        "basis",
                        "local",
                        "set",
                        "transform",
                        "world",
                    ),
                ),
                "name": str(bone.GetName()),
                "python_type": type(bone).__name__,
            }
        )
    before_path = os.path.join(output_dir, "before_refresh.png")
    render_preview(before_path, time)

    checked(
        "Refresh current Morph weights",
        RLPy.RGlobal.ObjectModified(
            avatar,
            RLPy.EObjectModifiedType_MorphWeight,
        ),
    )
    for unused_index in range(4):
        QtWidgets.QApplication.processEvents()
    checked(
        "Re-evaluate current avatar after Morph refresh",
        RLPy.RGlobal.SetTime(time, True),
    )
    for unused_index in range(4):
        QtWidgets.QApplication.processEvents()
    after = capture_eye_integrity_state(avatar)
    after_path = os.path.join(output_dir, "after_refresh.png")
    render_preview(after_path, time)

    report = {
        "after": after,
        "after_image": after_path,
        "before": before,
        "before_image": before_path,
        "captured_at": now(),
        "eye_bone_api": eye_bone_api,
        "schema_version": 1,
    }
    report_path = os.path.join(output_dir, "eye_state_refresh.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    return {
        "diagnostic_mode": "eye_state_refresh",
        "eye_state_refresh_path": report_path,
        "failure_count": 0,
        "finished_at": now(),
        "requested_count": 1,
        "run_id": os.path.basename(output_dir),
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def probe_current_eye_tpose_restore(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("eye_tpose_restore_probe") or {}
    expected_bones = probe.get("eye_bones") or []
    if not expected_bones:
        raise ReconstructionError(
            "eye_tpose_restore_probe.eye_bones is required"
        )
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Eye T-pose restore probe expected one avatar"
        )
    time = RLPy.RGlobal.GetStartTime()
    checked(
        "Set eye T-pose restore probe time",
        RLPy.RGlobal.SetTime(time, True),
    )
    QtWidgets.QApplication.processEvents()
    skeleton = avatar.GetSkeletonComponent()
    if skeleton is None:
        raise ReconstructionError("Avatar has no skeleton component")
    bones_by_name = dict(
        (str(bone.GetName()), bone)
        for bone in list(skeleton.GetSkinBones() or [])
    )
    before = capture_eye_integrity_state(avatar)
    before_path = os.path.join(output_dir, "before_tpose_restore.png")
    render_preview(before_path, time)

    applications = []
    for item in expected_bones:
        name = item.get("name")
        position = item.get("t_pose_position")
        if name not in bones_by_name:
            raise ReconstructionError(
                "Eye T-pose restore bone is missing: {}".format(name)
            )
        if not isinstance(position, dict):
            raise ReconstructionError(
                "Eye T-pose restore position is missing for {}".format(name)
            )
        bone = bones_by_name[name]
        target = RLPy.RVector3(
            float(position["x"]),
            float(position["y"]),
            float(position["z"]),
        )
        status = checked(
            "Restore {} T-pose position".format(name),
            skeleton.SetBoneTPosePosition(bone, target),
        )
        bone.Update()
        applications.append(
            {
                "name": name,
                "status": status,
                "target": dict(position),
            }
        )
    for unused_index in range(4):
        QtWidgets.QApplication.processEvents()
    checked(
        "Re-evaluate current avatar after eye T-pose restore",
        RLPy.RGlobal.SetTime(time, True),
    )
    for unused_index in range(4):
        QtWidgets.QApplication.processEvents()
    after = capture_eye_integrity_state(avatar)
    after_path = os.path.join(output_dir, "after_tpose_restore.png")
    render_preview(after_path, time)

    report = {
        "after": after,
        "after_image": after_path,
        "applications": applications,
        "before": before,
        "before_image": before_path,
        "captured_at": now(),
        "schema_version": 1,
    }
    report_path = os.path.join(output_dir, "eye_tpose_restore.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    return {
        "diagnostic_mode": "eye_tpose_restore",
        "eye_tpose_restore_path": report_path,
        "failure_count": 0,
        "finished_at": now(),
        "requested_count": 1,
        "run_id": os.path.basename(output_dir),
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def probe_current_neutral_face_clip(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Neutral face clip probe expected one avatar"
        )
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError("Avatar has no face component")
    expression_names = list(
        face_component.GetExpressionNames("") or []
    )
    if not expression_names:
        raise ReconstructionError(
            "Neutral face clip probe found no expressions"
        )
    fps = RLPy.RGlobal.GetFps()
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    initial_end_frame = int(fps.GetFrameIndex(initial_end_time))
    clip_start_frame = initial_end_frame + 1
    clip_start = RLPy.IndexedFrameTime(clip_start_frame, fps)
    clip_length = RLPy.IndexedFrameTime(40, fps)
    interval = RLPy.IndexedFrameTime(0, fps)
    neutral_time = RLPy.IndexedFrameTime(clip_start_frame + 10, fps)
    validation_end_time = RLPy.IndexedFrameTime(
        clip_start_frame + 40, fps
    )
    before = capture_eye_integrity_state(avatar)
    before_path = os.path.join(output_dir, "before_neutral_clip.png")
    render_preview(before_path, initial_time)

    clip = None
    try:
        if initial_end_time < validation_end_time:
            checked(
                "Extend neutral face clip probe timeline",
                RLPy.RGlobal.SetEndTime(validation_end_time),
            )
        before_count = int(face_component.GetClipCount())
        checked(
            "Add neutral face probe clip",
            face_component.AddClip(
                clip_start,
                "Lance_Neutral_Face_Probe",
                clip_length,
            ),
        )
        QtWidgets.QApplication.processEvents()
        after_count = int(face_component.GetClipCount())
        if after_count <= before_count:
            raise ReconstructionError(
                "Neutral face probe clip count did not increase"
            )
        clip = face_component.GetClip(after_count - 1)
        checked(
            "Begin neutral face probe key editing",
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Add neutral face probe expression key",
                face_component.AddExpressionKeys(
                    neutral_time,
                    expression_names,
                    [0.0] * len(expression_names),
                    interval,
                ),
            )
        finally:
            checked(
                "End neutral face probe key editing",
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate neutral face probe frame",
            RLPy.RGlobal.SetTime(neutral_time, True),
        )
        for unused_index in range(4):
            QtWidgets.QApplication.processEvents()
        during = capture_eye_integrity_state(avatar)
        during_path = os.path.join(output_dir, "during_neutral_clip.png")
        render_preview(during_path, neutral_time)
    finally:
        if clip is not None:
            face_component.DeleteClip(clip)
        checked(
            "Restore neutral face probe start time",
            RLPy.RGlobal.SetTime(initial_time, True),
        )
        if RLPy.RGlobal.GetEndTime() != initial_end_time:
            RLPy.RGlobal.SetEndTime(initial_end_time)
        for unused_index in range(4):
            QtWidgets.QApplication.processEvents()
    after = capture_eye_integrity_state(avatar)
    after_path = os.path.join(output_dir, "after_neutral_clip_delete.png")
    render_preview(after_path, initial_time)
    RLPy.RGlobal.SetTime(initial_time, True)

    report = {
        "after": after,
        "after_image": after_path,
        "before": before,
        "before_image": before_path,
        "captured_at": now(),
        "during": during,
        "during_image": during_path,
        "expression_count": len(expression_names),
        "final_expression_clip_count": int(
            face_component.GetClipCount()
        ),
        "schema_version": 1,
    }
    report_path = os.path.join(output_dir, "neutral_face_clip.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    return {
        "diagnostic_mode": "neutral_face_clip",
        "failure_count": 0,
        "finished_at": now(),
        "neutral_face_clip_path": report_path,
        "requested_count": 1,
        "run_id": os.path.basename(output_dir),
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def probe_current_face_pose_mode_refresh(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Face pose mode refresh expected one avatar"
        )
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError("Avatar has no face component")
    time = RLPy.RGlobal.GetStartTime()
    checked(
        "Set face pose mode refresh start time",
        RLPy.RGlobal.SetTime(time, True),
    )
    for unused_index in range(4):
        QtWidgets.QApplication.processEvents()
    before = capture_eye_integrity_state(avatar)
    before_path = os.path.join(output_dir, "before_pose_mode_refresh.png")
    render_preview(before_path, time)
    status = checked(
        "Set current face pose mode",
        face_component.SetCurrentPoseMode(),
    )
    checked(
        "Re-evaluate current face pose mode",
        RLPy.RGlobal.SetTime(time, True),
    )
    for unused_index in range(6):
        QtWidgets.QApplication.processEvents()
    after = capture_eye_integrity_state(avatar)
    after_path = os.path.join(output_dir, "after_pose_mode_refresh.png")
    render_preview(after_path, time)
    comparison = compare_neutral_eye_states(before, after)
    report = {
        "after": after,
        "after_image": after_path,
        "before": before,
        "before_image": before_path,
        "captured_at": now(),
        "comparison": comparison,
        "is_current_pose_mode": bool(
            face_component.IsCurrentPoseMode()
        ),
        "schema_version": 1,
        "status": status,
    }
    report_path = os.path.join(output_dir, "face_pose_mode_refresh.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    return {
        "diagnostic_mode": "face_pose_mode_refresh",
        "face_pose_mode_refresh_path": report_path,
        "failure_count": 0,
        "finished_at": now(),
        "requested_count": 1,
        "run_id": os.path.basename(output_dir),
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def probe_current_face_safety_cleanup(output_dir, pose_ids=None):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Face safety cleanup probe expected one avatar"
        )
    filenames = {
        "facial_pose_validation": "facial_pose_validation.json",
        "face_blink_bilateral_preview": "face_blink_bilateral.png",
        "face_blink_left_preview": "face_blink_left.png",
        "face_blink_right_preview": "face_blink_right.png",
        "face_look_left_preview": "face_look_left.png",
        "face_look_right_preview": "face_look_right.png",
        "face_look_up_preview": "face_look_up.png",
        "face_look_down_preview": "face_look_down.png",
        "face_squint_preview": "face_squint.png",
        "face_widen_preview": "face_widen.png",
        "face_brow_raise_preview": "face_brow_raise.png",
        "face_brow_down_preview": "face_brow_down.png",
        "face_brow_raise_left_preview": "face_brow_raise_left.png",
        "face_smile_preview": "face_smile.png",
        "face_jaw_open_preview": "face_jaw_open.png",
        "face_jaw_open_three_quarter_preview": (
            "face_jaw_open_three_quarter.png"
        ),
        "face_post_pose_neutral_preview": "face_post_pose_neutral.png",
    }
    artifacts = dict(
        (key, os.path.join(output_dir, filename))
        for key, filename in filenames.items()
    )
    force_avatar_scene_evaluation(avatar)
    before = capture_eye_integrity_state(avatar)
    report = render_face_identity_safety_previews(
        avatar,
        artifacts,
        lambda unused_phase: None,
        pose_ids=pose_ids,
    )
    settle_cc_ui(1.0)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Face safety cleanup restore expected one avatar"
        )
    force_avatar_scene_evaluation(avatar)
    after = capture_eye_integrity_state(avatar)
    post_cleanup_world_observation = compare_neutral_eye_states(
        before,
        after,
        include_world=True,
        include_runtime_ids=False,
        t_pose_tolerance=0.5,
    )
    post_cleanup_comparison = report["neutral_eye_integrity"]
    report_path = artifacts["facial_pose_validation"]
    summary_path = os.path.join(output_dir, "validation_result.json")
    return {
        "diagnostic_mode": "face_safety_cleanup",
        "face_safety_cleanup_path": report_path,
        "failure_count": 0,
        "finished_at": now(),
        "neutral_eye_integrity": report["neutral_eye_integrity"],
        "post_pose_neutral_image": report.get(
            "post_pose_neutral_image"
        ),
        "post_cleanup_comparison": post_cleanup_comparison,
        "post_cleanup_world_observation": (
            post_cleanup_world_observation
        ),
        "requested_count": 1,
        "run_id": os.path.basename(output_dir),
        "schema_version": 1,
        "started_at": now(),
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def apply_current_eye_expression_pose(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Eye expression pose expected one avatar, found {}".format(
                len(avatars)
            )
        )

    pose = library.get("eye_expression_pose") or {}
    direction = pose.get("direction", "look_down")
    weight = float(pose.get("weight", 0.55))
    pose_frame = int(pose.get("frame", 10))
    clip_length_frames = int(pose.get("clip_length_frames", 40))
    replace_existing_clips = bool(
        pose.get("replace_existing_expression_clips", False)
    )
    base_clip_name = pose.get(
        "clip_name", "Lance_Eye_Sclera_Demo_LookDown"
    )
    if direction not in (
        "look_left",
        "look_right",
        "look_up",
        "look_down",
    ):
        raise ReconstructionError(
            "Unsupported eye expression direction: {}".format(direction)
        )
    if not 0.0 <= weight <= 1.0:
        raise ReconstructionError("Eye expression weight must be within [0, 1]")
    if pose_frame < 0 or clip_length_frames <= pose_frame:
        raise ReconstructionError(
            "Eye expression clip must extend beyond the pose frame"
        )
    if not isinstance(base_clip_name, str) or not base_clip_name:
        raise ReconstructionError(
            "Eye expression clip_name must be a non-empty string"
        )

    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Current avatar has no face component for eye pose"
        )
    expression_names = list(face_component.GetExpressionNames("") or [])
    targets = resolve_eye_expression_targets(expression_names)
    target_names = targets[direction]
    name_to_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )
    weights = [0.0] * len(expression_names)
    for name in target_names:
        weights[name_to_index[name]] = weight

    fps = RLPy.RGlobal.GetFps()
    initial_time = RLPy.RGlobal.GetTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    initial_end_frame = int(fps.GetFrameIndex(initial_end_time))
    initial_clip_count = int(face_component.GetClipCount())
    removed_clip_count = 0
    if replace_existing_clips:
        for clip_index in range(initial_clip_count - 1, -1, -1):
            checked(
                "Delete existing eye demonstration clip {}".format(
                    clip_index
                ),
                face_component.DeleteClip(
                    face_component.GetClip(clip_index)
                ),
            )
            removed_clip_count += 1
            QtWidgets.QApplication.processEvents()
        clip_start_frame = 0
    else:
        clip_start_frame = initial_end_frame + 1
    global_pose_frame = clip_start_frame + pose_frame
    required_end_frame = clip_start_frame + clip_length_frames
    clip_start = RLPy.IndexedFrameTime(clip_start_frame, fps)
    clip_length = RLPy.IndexedFrameTime(clip_length_frames, fps)
    key_interval = RLPy.IndexedFrameTime(0, fps)
    pose_time = RLPy.IndexedFrameTime(global_pose_frame, fps)
    required_end_time = RLPy.IndexedFrameTime(required_end_frame, fps)
    clip_name = "{}_{}".format(
        base_clip_name,
        datetime.datetime.now().strftime("%H%M%S%f"),
    )
    before_count = int(face_component.GetClipCount())
    clip = None
    try:
        checked(
            "Extend timeline for current-scene eye pose",
            RLPy.RGlobal.SetEndTime(required_end_time),
        )
        checked(
            "Add current-scene eye expression clip",
            face_component.AddClip(
                clip_start,
                clip_name,
                clip_length,
            ),
        )
        QtWidgets.QApplication.processEvents()
        after_count = int(face_component.GetClipCount())
        if after_count <= before_count:
            raise ReconstructionError(
                "Expression clip count did not increase for {}".format(
                    clip_name
                )
            )
        clip = face_component.GetClip(after_count - 1)
        checked(
            "Begin current-scene eye expression editing",
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Add current-scene eye expression key",
                face_component.AddExpressionKeys(
                    pose_time,
                    expression_names,
                    weights,
                    key_interval,
                ),
            )
        finally:
            checked(
                "End current-scene eye expression editing",
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate current-scene eye expression pose",
            RLPy.RGlobal.SetTime(pose_time, True),
        )
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
    except Exception:
        if clip is not None:
            face_component.DeleteClip(clip)
        RLPy.RGlobal.SetTime(initial_time, True)
        RLPy.RGlobal.SetEndTime(initial_end_time)
        QtWidgets.QApplication.processEvents()
        raise

    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "scene_preserved": True,
        "expression_set_uid": str(face_component.GetExpressionSetUid()),
        "direction": direction,
        "resolved_targets": target_names,
        "weight": weight,
        "relative_pose_frame": pose_frame,
        "pose_frame": global_pose_frame,
        "clip_start_frame": clip_start_frame,
        "clip_length_frames": clip_length_frames,
        "clip_name": clip_name,
        "initial_frame": int(fps.GetFrameIndex(initial_time)),
        "replace_existing_expression_clips": replace_existing_clips,
        "removed_expression_clip_count": removed_clip_count,
        "pre_operation_expression_clip_count": initial_clip_count,
        "final_frame": int(fps.GetFrameIndex(RLPy.RGlobal.GetTime())),
        "initial_expression_clip_count": before_count,
        "final_expression_clip_count": int(face_component.GetClipCount()),
    }
    report_path = os.path.join(output_dir, "eye_expression_pose_result.json")
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "eye_expression_pose_apply",
        "eye_expression_pose_result_path": report_path,
        "summary_path": report_path,
    }


def _transform_float(avatar, parameter_id):
    control = avatar.GetControl("Transform")
    if control is None:
        raise ReconstructionError("Avatar has no Transform control")
    data_block = control.GetDataBlock()
    if data_block is None:
        raise ReconstructionError("Avatar Transform control has no data block")
    value = data_block.GetData(parameter_id, RLPy.RGlobal.GetStartTime())
    if value is None:
        raise ReconstructionError(
            "Avatar Transform parameter is unavailable: {}".format(parameter_id)
        )
    return float(value.ToFloat())


def camera_state(camera):
    if camera is None:
        return None
    time = RLPy.RGlobal.GetStartTime()
    state = {
        "id": scene_object_id(camera),
        "name": scene_object_name(camera),
        "python_type": type(camera).__name__,
        "local_transform": _transform_data(camera.LocalTransform()),
        "world_transform": _transform_data(camera.WorldTransform()),
    }
    observations = (
        ("focal_length", lambda: float(camera.GetFocalLength(time))),
        ("angle_of_view", lambda: float(camera.GetAngleOfView(time))),
        ("fit_render_region_type", lambda: int(camera.GetFitRenderRegionType())),
        ("fit_fov_type", lambda: int(camera.GetFitFovType())),
    )
    for key, reader in observations:
        try:
            state[key] = reader()
        except Exception as exc:
            state[key + "_error"] = str(exc)
    return state


def probe_face_camera_sweep(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Face camera sweep expected one avatar, found {}".format(
                len(avatars)
            )
        )
    camera_path = library.get("camera_path")
    if not isinstance(camera_path, str) or not os.path.isfile(camera_path):
        raise ReconstructionError("Face camera sweep camera is missing")
    positions = library.get("positions")
    if not isinstance(positions, list) or not positions:
        raise ReconstructionError("Face camera sweep positions are missing")
    yaw_degrees = float(library.get("yaw_degrees", 90.0))
    initial_position = {
        "x": _transform_float(avatar, "Position/PositionX"),
        "y": _transform_float(avatar, "Position/PositionY"),
        "z": _transform_float(avatar, "Position/PositionZ"),
    }
    initial_yaw_radians = _transform_float(avatar, "Rotation/RotationZ")
    initial_camera = RLPy.RScene.GetCurrentCamera()
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "camera_path": camera_path,
        "initial_camera": camera_state(initial_camera),
        "initial_position": initial_position,
        "yaw_degrees": yaw_degrees,
        "candidates": [],
    }
    try:
        checked(
            "Load face camera sweep camera",
            RLPy.RFileIO.LoadFile(camera_path),
        )
        report["loaded_camera"] = camera_state(
            RLPy.RScene.GetCurrentCamera()
        )
        set_avatar_yaw(avatar, yaw_degrees)
        for item in positions:
            candidate_id = item.get("id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ReconstructionError(
                    "Face camera sweep candidate has no ID"
                )
            position = {
                axis: float(item.get(axis, 0.0))
                for axis in ("x", "y", "z")
            }
            set_avatar_position(
                avatar,
                position_x=position["x"],
                position_y=position["y"],
                position_z=position["z"],
            )
            image_path = os.path.join(
                output_dir, "camera_{}.png".format(candidate_id)
            )
            render_preview(image_path)
            report["candidates"].append(
                {
                    "id": candidate_id,
                    "position": position,
                    "image": image_path,
                }
            )
    finally:
        set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
        set_avatar_position(
            avatar,
            position_x=initial_position["x"],
            position_y=initial_position["y"],
            position_z=initial_position["z"],
        )
        if initial_camera is not None:
            checked(
                "Restore camera after face camera sweep",
                RLPy.RScene.SetCurrentCamera(initial_camera),
            )
        QtWidgets.QApplication.processEvents()

    report_path = os.path.join(output_dir, "camera_sweep.json")
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": len(report["candidates"]),
        "success_count": len(report["candidates"]),
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "face_camera_sweep",
        "camera_sweep_path": report_path,
        "summary_path": report_path,
    }


def probe_current_eye_morph_sweep(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Eye morph sweep expected one avatar, found {}".format(len(avatars))
        )
    morph_id = library.get("eye_morph_id")
    values = library.get("eye_morph_values")
    camera_path = library.get("face_camera")
    subject_z_offset = float(library.get("subject_z_offset", 0.0))
    if not isinstance(morph_id, str) or not morph_id:
        raise ReconstructionError("eye_morph_id must be a non-empty string")
    if not isinstance(values, list) or not values:
        raise ReconstructionError("eye_morph_values must be a non-empty list")
    values = [float(value) for value in values]
    if not isinstance(camera_path, str) or not os.path.isfile(camera_path):
        raise ReconstructionError("Eye sweep face camera is missing")

    component, catalog, unused_categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "Eye sweep morph is unavailable: {}".format(morph_id)
        )
    initial_weight = float(component.GetShapingMorphWeight(morph_id))
    initial_z = _transform_float(avatar, "Position/PositionZ")
    initial_yaw = _transform_float(avatar, "Rotation/RotationZ")
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "morph": catalog[morph_id],
        "initial_weight": initial_weight,
        "subject_z_offset": subject_z_offset,
        "candidates": [],
    }
    try:
        checked("Load eye sweep camera", RLPy.RFileIO.LoadFile(camera_path))
        set_avatar_position_z(avatar, subject_z_offset)
        set_avatar_yaw(avatar, 90.0)
        for index, value in enumerate(values):
            checked(
                "Set eye sweep morph {}".format(value),
                component.SetShapingMorphWeight(morph_id, value),
            )
            checked(
                "Refresh eye sweep morph",
                RLPy.RGlobal.ObjectModified(
                    avatar, RLPy.EObjectModifiedType_MorphWeight
                ),
            )
            QtWidgets.QApplication.processEvents()
            image_path = os.path.join(
                output_dir,
                "eye_move_{:02d}_{:+.2f}.png".format(index, value),
            )
            render_preview(image_path)
            report["candidates"].append(
                {
                    "value": value,
                    "image": image_path,
                    "eye_bones": _capture_eye_bones(
                        avatar.GetSkeletonComponent()
                    ),
                }
            )
    finally:
        checked(
            "Restore eye sweep morph",
            component.SetShapingMorphWeight(morph_id, initial_weight),
        )
        checked(
            "Refresh restored eye sweep morph",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        set_avatar_position_z(avatar, initial_z)
        set_avatar_yaw(avatar, math.degrees(initial_yaw))
        QtWidgets.QApplication.processEvents()

    report_path = os.path.join(output_dir, "eye_morph_sweep.json")
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "eye_morph_sweep",
        "eye_morph_sweep_path": report_path,
        "summary_path": report_path,
    }


def apply_current_eye_alignment(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Eye alignment expected one avatar, found {}".format(len(avatars))
        )
    morph_id = library.get("eye_morph_id")
    target = float(library.get("eye_morph_target"))
    camera_path = library.get("face_camera")
    subject_z_offset = float(library.get("subject_z_offset", 0.0))
    if not isinstance(morph_id, str) or not morph_id:
        raise ReconstructionError("eye_morph_id must be a non-empty string")
    if not isinstance(camera_path, str) or not os.path.isfile(camera_path):
        raise ReconstructionError("Eye alignment face camera is missing")

    component, catalog, unused_categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "Eye alignment morph is unavailable: {}".format(morph_id)
        )
    initial_weight = float(component.GetShapingMorphWeight(morph_id))
    initial_z = _transform_float(avatar, "Position/PositionZ")
    initial_yaw = _transform_float(avatar, "Rotation/RotationZ")
    image_path = os.path.join(output_dir, "eye_alignment_final.png")
    report_path = os.path.join(output_dir, "eye_alignment_result.json")
    applied = False
    try:
        checked(
            "Set final eye alignment morph",
            component.SetShapingMorphWeight(morph_id, target),
        )
        checked(
            "Refresh final eye alignment morph",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        QtWidgets.QApplication.processEvents()
        applied = True
        checked("Load final eye alignment camera", RLPy.RFileIO.LoadFile(camera_path))
        set_avatar_position_z(avatar, subject_z_offset)
        set_avatar_yaw(avatar, 90.0)
        render_preview(image_path)
    except Exception:
        if applied:
            component.SetShapingMorphWeight(morph_id, initial_weight)
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            )
        raise
    finally:
        set_avatar_position_z(avatar, initial_z)
        set_avatar_yaw(avatar, math.degrees(initial_yaw))
        QtWidgets.QApplication.processEvents()

    final_weight = float(component.GetShapingMorphWeight(morph_id))
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "morph": catalog[morph_id],
        "initial_weight": initial_weight,
        "target_weight": target,
        "final_weight": final_weight,
        "image": image_path,
    }
    write_json(report, report_path)
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "eye_morph_apply",
        "eye_alignment_result_path": report_path,
        "summary_path": report_path,
    }


def validate_preset(
    library,
    preset,
    preset_dir,
    log,
    body_catalog_path=None,
    face_catalog_path=None,
    appearance_catalog=None,
):
    os.makedirs(preset_dir, exist_ok=False)
    result_path = os.path.join(preset_dir, "result.json")
    appearance_validation_plan = resolve_appearance_validation_plan(preset)
    dynamic_wrinkle_validation = resolve_dynamic_wrinkle_validation(
        appearance_validation_plan
    )
    render_static_hair_views = render_static_hair_views_enabled(
        appearance_validation_plan
    )
    asset_load_pacing = resolve_asset_load_pacing(preset)
    artifacts = {
        "source_preview": os.path.join(preset_dir, "source_preview.png"),
        "reconstructed_preview": os.path.join(preset_dir, "reconstructed_preview.png"),
        "source_vectors": os.path.join(preset_dir, "source_vectors.json"),
        "baseline_vectors": os.path.join(preset_dir, "baseline_vectors.json"),
        "reconstructed_vectors": os.path.join(preset_dir, "reconstructed_vectors.json"),
        "head_preset_vectors": os.path.join(preset_dir, "head_preset_vectors.json"),
        "head_preset_supported_vectors": os.path.join(
            preset_dir,
            "head_preset_supported_vectors.json",
        ),
        "facial_profile_vectors": os.path.join(
            preset_dir,
            "facial_profile_vectors.json",
        ),
        "composed_vectors": os.path.join(preset_dir, "composed_vectors.json"),
        "morph_delta": os.path.join(preset_dir, "morph_delta.json"),
        "face_front_preview": os.path.join(preset_dir, "face_front.png"),
        "face_three_quarter_preview": os.path.join(
            preset_dir, "face_three_quarter.png"
        ),
        "face_profile_preview": os.path.join(preset_dir, "face_profile.png"),
        "appearance_inventory": os.path.join(preset_dir, "appearance_inventory.json"),
        "facial_assembly": os.path.join(
            preset_dir, "facial_assembly.json"
        ),
        "eye_integrity": os.path.join(preset_dir, "eye_integrity.json"),
        "progress": os.path.join(preset_dir, "progress.json"),
        "body_catalog": body_catalog_path,
        "face_catalog": face_catalog_path,
    }
    if (
        appearance_validation_plan
        and appearance_validation_plan.get("pose_profile")
        == TEETH_VISIBILITY_PROFILE
    ):
        artifacts.update(
            {
                "facial_pose_validation": os.path.join(
                    preset_dir, "facial_pose_validation.json"
                ),
                "teeth_smile_preview": os.path.join(
                    preset_dir, "teeth_smile_front.png"
                ),
                "teeth_jaw_open_preview": os.path.join(
                    preset_dir, "teeth_jaw_open_front.png"
                ),
                "teeth_jaw_open_three_quarter_preview": os.path.join(
                    preset_dir, "teeth_jaw_open_three_quarter.png"
                ),
            }
        )
    if (
        appearance_validation_plan
        and appearance_validation_plan.get("pose_profile")
        == EYE_VISIBILITY_PROFILE
    ):
        artifacts.update(
            {
                "facial_pose_validation": os.path.join(
                    preset_dir, "facial_pose_validation.json"
                ),
                "eye_look_left_preview": os.path.join(
                    preset_dir, "eye_look_left_front.png"
                ),
                "eye_look_right_preview": os.path.join(
                    preset_dir, "eye_look_right_front.png"
                ),
                "eye_look_up_preview": os.path.join(
                    preset_dir, "eye_look_up_front.png"
                ),
                "eye_look_down_preview": os.path.join(
                    preset_dir, "eye_look_down_front.png"
                ),
            }
        )
    if (
        appearance_validation_plan
        and appearance_validation_plan.get("pose_profile")
        == EYEBROW_VISIBILITY_PROFILE
    ):
        artifacts.update(
            {
                "facial_pose_validation": os.path.join(
                    preset_dir, "facial_pose_validation.json"
                ),
                "eyebrow_raise_preview": os.path.join(
                    preset_dir, "eyebrow_raise_front.png"
                ),
                "eyebrow_down_preview": os.path.join(
                    preset_dir, "eyebrow_down_front.png"
                ),
                "eyebrow_asymmetric_preview": os.path.join(
                    preset_dir, "eyebrow_raise_left_front.png"
                ),
            }
        )
    if (
        appearance_validation_plan
        and appearance_validation_plan.get("pose_profile")
        == EYELASH_VISIBILITY_PROFILE
    ):
        artifacts.update(
            {
                "facial_pose_validation": os.path.join(
                    preset_dir, "facial_pose_validation.json"
                ),
                "eyelash_blink_preview": os.path.join(
                    preset_dir, "eyelash_blink_front.png"
                ),
                "eyelash_asymmetric_preview": os.path.join(
                    preset_dir, "eyelash_blink_left_front.png"
                ),
                "eyelash_wide_preview": os.path.join(
                    preset_dir, "eyelash_wide_front.png"
                ),
            }
        )
    if (
        appearance_validation_plan
        and appearance_validation_plan.get("pose_profile")
        == FACE_IDENTITY_SAFETY_PROFILE
    ):
        artifacts.update(
            {
                "facial_pose_validation": os.path.join(
                    preset_dir, "facial_pose_validation.json"
                ),
                "face_blink_bilateral_preview": os.path.join(
                    preset_dir, "face_blink_bilateral_front.png"
                ),
                "face_blink_left_preview": os.path.join(
                    preset_dir, "face_blink_left_front.png"
                ),
                "face_blink_right_preview": os.path.join(
                    preset_dir, "face_blink_right_front.png"
                ),
                "face_look_left_preview": os.path.join(
                    preset_dir, "face_look_left_front.png"
                ),
                "face_look_right_preview": os.path.join(
                    preset_dir, "face_look_right_front.png"
                ),
                "face_look_up_preview": os.path.join(
                    preset_dir, "face_look_up_front.png"
                ),
                "face_look_down_preview": os.path.join(
                    preset_dir, "face_look_down_front.png"
                ),
                "face_squint_preview": os.path.join(
                    preset_dir, "face_squint_front.png"
                ),
                "face_widen_preview": os.path.join(
                    preset_dir, "face_widen_front.png"
                ),
                "face_brow_raise_preview": os.path.join(
                    preset_dir, "face_brow_raise_front.png"
                ),
                "face_brow_down_preview": os.path.join(
                    preset_dir, "face_brow_down_front.png"
                ),
                "face_brow_raise_left_preview": os.path.join(
                    preset_dir, "face_brow_raise_left_front.png"
                ),
                "face_smile_preview": os.path.join(
                    preset_dir, "face_smile_front.png"
                ),
                "face_jaw_open_preview": os.path.join(
                    preset_dir, "face_jaw_open_front.png"
                ),
                "face_jaw_open_three_quarter_preview": os.path.join(
                    preset_dir, "face_jaw_open_three_quarter.png"
                ),
                "face_post_pose_neutral_preview": os.path.join(
                    preset_dir, "face_post_pose_neutral_front.png"
                ),
            }
        )
    if (
        appearance_validation_plan
        and appearance_validation_plan.get("pose_profile")
        == FACIAL_HAIR_VISIBILITY_PROFILE
    ):
        artifacts.update(
            {
                "facial_pose_validation": os.path.join(
                    preset_dir, "facial_pose_validation.json"
                ),
                "face_blink_bilateral_preview": os.path.join(
                    preset_dir, "face_blink_bilateral_front.png"
                ),
                "face_blink_left_preview": os.path.join(
                    preset_dir, "face_blink_left_front.png"
                ),
                "face_blink_right_preview": os.path.join(
                    preset_dir, "face_blink_right_front.png"
                ),
                "face_look_left_preview": os.path.join(
                    preset_dir, "face_look_left_front.png"
                ),
                "face_look_right_preview": os.path.join(
                    preset_dir, "face_look_right_front.png"
                ),
                "face_look_up_preview": os.path.join(
                    preset_dir, "face_look_up_front.png"
                ),
                "face_look_down_preview": os.path.join(
                    preset_dir, "face_look_down_front.png"
                ),
                "face_squint_preview": os.path.join(
                    preset_dir, "face_squint_front.png"
                ),
                "face_widen_preview": os.path.join(
                    preset_dir, "face_widen_front.png"
                ),
                "face_brow_raise_preview": os.path.join(
                    preset_dir, "face_brow_raise_front.png"
                ),
                "face_brow_down_preview": os.path.join(
                    preset_dir, "face_brow_down_front.png"
                ),
                "face_brow_raise_left_preview": os.path.join(
                    preset_dir, "face_brow_raise_left_front.png"
                ),
                "face_smile_preview": os.path.join(
                    preset_dir, "face_smile_front.png"
                ),
                "face_jaw_open_preview": os.path.join(
                    preset_dir, "face_jaw_open_front.png"
                ),
                "face_jaw_open_three_quarter_preview": os.path.join(
                    preset_dir, "face_jaw_open_three_quarter.png"
                ),
                "face_post_pose_neutral_preview": os.path.join(
                    preset_dir, "face_post_pose_neutral_front.png"
                ),
            }
        )
    if dynamic_wrinkle_validation is not None:
        artifacts.update(
            {
                "dynamic_wrinkle_validation": os.path.join(
                    preset_dir, "dynamic_wrinkle_validation.json"
                ),
                "dynamic_wrinkle_baseline_pose_validation": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_pose_validation.json",
                ),
                "dynamic_wrinkle_baseline_neutral_preview": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_neutral_front.png",
                ),
                "dynamic_wrinkle_baseline_blink_bilateral_preview": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_blink_bilateral_front.png",
                ),
                "dynamic_wrinkle_baseline_brow_raise_preview": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_brow_raise_front.png",
                ),
                "dynamic_wrinkle_baseline_brow_down_preview": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_brow_down_front.png",
                ),
                "dynamic_wrinkle_baseline_squint_preview": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_squint_front.png",
                ),
                "dynamic_wrinkle_baseline_smile_preview": os.path.join(
                    preset_dir,
                    "dynamic_wrinkle_baseline_smile_front.png",
                ),
            }
        )
    if render_static_hair_views:
        artifacts.update(
            {
                "hair_rear_preview": os.path.join(
                    preset_dir, "hair_rear.png"
                ),
                "hair_rear_three_quarter_preview": os.path.join(
                    preset_dir, "hair_rear_three_quarter.png"
                ),
            }
        )

    def mark_phase(phase, detail=None):
        write_json(
            {
                "schema_version": 1,
                "preset_id": preset["preset_id"],
                "updated_at": now(),
                "phase": phase,
                "detail": detail,
            },
            artifacts["progress"],
        )

    body_application_mode = resolve_body_application_mode(library, preset)
    expected_eyeball_move_weight = library.get(
        "expected_eyeball_move_weight"
    )
    result = {
        "schema_version": 1,
        "preset_id": preset["preset_id"],
        "sex": preset["sex"],
        "success": False,
        "source_matches_library": None,
        "reconstruction_matches_library": None,
        "face_unchanged": None,
        "other_unchanged": None,
        "application": None,
        "body_application_mode": body_application_mode,
        "face_recipe_id": preset.get("face_recipe_id"),
        "face_generation": preset.get("face_generation"),
        "face_context": None,
        "face_head_preset_application": None,
        "face_support_application": None,
        "face_facial_profile_application": None,
        "face_facial_profile_morph_delta": None,
        "face_facial_profile_morphs_unchanged": None,
        "face_facial_profile_eye_structure_unchanged": None,
        "face_application": None,
        "file_load_dialogs": {},
        "face_primary_matches_seed": None,
        "face_primary_seed_delta": None,
        "face_support_preserved_after_preset": None,
        "face_support_matches_primary_after_preset": None,
        "face_matches_recipe": None,
        "body_unchanged_after_face": None,
        "junction_unchanged_after_face": None,
        "face_support_changes_after_preset": None,
        "face_support_delta_from_primary": None,
        "face_support_changes_after_identity": None,
        "face_support_preserved_after_identity": None,
        "eye_structure_preserved_after_identity": None,
        "appearance_asset_ids": preset.get("appearance_asset_ids"),
        "appearance_recipe_id": preset.get("appearance_recipe_id"),
        "appearance_validation_plan": appearance_validation_plan,
        "appearance_application": None,
        "appearance_matches_recipe": None,
        "morphs_unchanged_after_appearance": None,
        "appearance_morphs_within_policy": None,
        "appearance_morph_policy": None,
        "face_view_y_offsets": None,
        "scalp_hair_view_y_offsets": None,
        "hair_motion_validation": None,
        "facial_pose_validation": None,
        "dynamic_wrinkle_validation": None,
        "eye_integrity": {
            "morph_id": EYEBALL_MOVE_MORPH_ID,
            "expected_weight": expected_eyeball_move_weight,
            "identity_write_attempted": None,
            "phases": {},
        },
        "artifacts": artifacts,
        "error": None,
    }
    write_json(result, result_path)
    mark_phase("initializing")
    try:
        source_project = preset["source_project"]["path"]
        if not os.path.isfile(source_project):
            raise ReconstructionError("Source project is missing: {}".format(source_project))
        mark_phase(
            "load_source_project",
            {"path": source_project},
        )
        source_load_status, source_load_dialogs = (
            load_file_with_optional_undo_warning(
                source_project,
                "Load source project",
            )
        )
        result["file_load_dialogs"]["source_project"] = {
            "status": source_load_status,
            "dialogs": source_load_dialogs,
        }
        mark_phase("source_project_loaded")
        source_avatar, source_avatars = resolve_avatar()
        if len(source_avatars) != 1:
            raise ReconstructionError(
                "Expected one source avatar, found {}".format(len(source_avatars))
            )
        source_vectors = capture_vectors(source_avatar)
        result["eye_integrity"]["phases"]["source_project"] = (
            capture_eye_integrity_state(source_avatar)
        )
        if expected_eyeball_move_weight is not None:
            validate_expected_eye_integrity(
                result["eye_integrity"]["phases"]["source_project"],
                expected_eyeball_move_weight,
                "source project",
            )
        write_json(source_vectors, artifacts["source_vectors"])
        source_body_delta = group_delta(
            preset["target_body_morphs"], source_vectors["groups"]["body"]["entries"]
        )
        source_junction_delta = group_delta(
            preset["target_junction_morphs"],
            source_vectors["groups"]["junction"]["entries"],
        )
        result["source_matches_library"] = not bool(
            source_body_delta or source_junction_delta
        )
        if not result["source_matches_library"]:
            raise ReconstructionError("Source project no longer matches BodyFit library")

        lightroom = library.get("preview_lightroom")
        if lightroom:
            if not os.path.isfile(lightroom):
                raise ReconstructionError("Preview Lightroom is missing: {}".format(lightroom))
            mark_phase(
                "load_preview_lightroom",
                {"path": lightroom},
            )
            lightroom_status, lightroom_dialogs = (
                load_file_with_optional_undo_warning(
                    lightroom,
                    "Load preview Lightroom",
                )
            )
            result["file_load_dialogs"]["preview_lightroom"] = {
                "status": lightroom_status,
                "dialogs": lightroom_dialogs,
            }
        mark_phase("render_source_preview")
        render_preview(artifacts["source_preview"])

        if body_application_mode == "source_project":
            mark_phase("retain_source_project_body")
            avatar, current_avatars = resolve_avatar()
            if len(current_avatars) != 1:
                raise ReconstructionError(
                    "Expected one canonical body avatar, found {}".format(
                        len(current_avatars)
                    )
                )
            baseline = capture_vectors(avatar)
            baseline_bounds = capture_bounds(avatar)
            result["application"] = {
                "mode": "source_project",
                "source_project": source_project,
                "changed": [],
            }
            log(
                "{} canonical source project body retained".format(
                    preset["preset_id"]
                )
            )
        else:
            base_path = preset["base_avatar"]["path"]
            if not os.path.isfile(base_path):
                raise ReconstructionError(
                    "Neutral base is missing: {}".format(base_path)
                )
            mark_phase(
                "load_neutral_base",
                {"path": base_path},
            )
            avatar, attempts = load_base(base_path)
            log("{} base loaded: {}".format(preset["preset_id"], attempts))
            baseline = capture_vectors(avatar)
            baseline_bounds = capture_bounds(avatar)
        write_json(baseline, artifacts["baseline_vectors"])
        if body_application_mode == "raw_morph_weights":
            if body_catalog_path and not os.path.isfile(body_catalog_path):
                write_json(
                    capture_body_catalog(avatar, preset["base_avatar"]),
                    body_catalog_path,
                )
            if face_catalog_path and not os.path.isfile(face_catalog_path):
                write_json(
                    capture_face_catalog(avatar, preset["base_avatar"]),
                    face_catalog_path,
                )
            mark_phase("apply_raw_body_morphs")
            result["application"] = apply_bodyfit(
                avatar,
                preset["target_body_morphs"],
                preset["target_junction_morphs"],
            )
        after_body = capture_vectors(avatar)
        result["eye_integrity"]["phases"]["after_body"] = (
            capture_eye_integrity_state(avatar)
        )
        if expected_eyeball_move_weight is not None:
            validate_expected_eye_integrity(
                result["eye_integrity"]["phases"]["after_body"],
                expected_eyeball_move_weight,
                "body application",
            )
        write_json(after_body, artifacts["reconstructed_vectors"])

        deltas = {
            "source_body": source_body_delta,
            "source_junction": source_junction_delta,
            "reconstructed_body": group_delta(
                preset["target_body_morphs"],
                after_body["groups"]["body"]["entries"],
            ),
            "reconstructed_junction": group_delta(
                preset["target_junction_morphs"],
                after_body["groups"]["junction"]["entries"],
            ),
            "face": group_delta(
                baseline["groups"]["face"]["entries"],
                after_body["groups"]["face"]["entries"],
            ),
            "other": group_delta(
                baseline["groups"]["other"]["entries"],
                after_body["groups"]["other"]["entries"],
            ),
        }
        write_json(deltas, artifacts["morph_delta"])
        result["reconstruction_matches_library"] = not bool(
            deltas["reconstructed_body"] or deltas["reconstructed_junction"]
        )
        result["face_unchanged"] = not bool(deltas["face"])
        result["other_unchanged"] = not bool(deltas["other"])
        result["reconstructed_fingerprint"] = after_body[
            "body_and_junction_fingerprint_sha256"
        ]
        result["expected_fingerprint"] = preset[
            "body_and_junction_fingerprint"
        ]
        if not result["reconstruction_matches_library"]:
            raise ReconstructionError("Reconstructed BodyFit differs from target values")
        if result["reconstructed_fingerprint"] != result["expected_fingerprint"]:
            raise ReconstructionError("Reconstructed BodyFit fingerprint mismatch")
        if not result["face_unchanged"]:
            raise ReconstructionError("Applying BodyFit changed face morphs")
        if not result["other_unchanged"]:
            raise ReconstructionError("Applying BodyFit changed unowned morphs")

        target_face = preset.get("target_face_morphs")
        local_face = preset.get("local_face_morphs")
        if target_face is not None and local_face is not None:
            raise ReconstructionError(
                "Face recipe cannot contain both legacy and V3 Morph fields"
            )
        has_face_recipe = (
            target_face is not None or local_face is not None
        )
        if has_face_recipe:
            if target_face is not None and (
                not isinstance(target_face, list) or not target_face
            ):
                raise ReconstructionError(
                    "target_face_morphs must be a non-empty list"
                )
            if local_face is not None and not isinstance(local_face, list):
                raise ReconstructionError(
                    "local_face_morphs must be a list"
                )
            face_context = resolve_face_application_context(library, preset)
            v3_face_pipeline = (
                face_context["mode"]
                == COMPLETE_PRIMARY_FACE_PIPELINE
            )
            if v3_face_pipeline:
                support_exclusion_ids = face_context[
                    "modified_morph_ids"
                ]
                modifiable_face_ids = face_context[
                    "modifiable_morph_ids"
                ]
                recipe_targets = [
                    {"id": item["id"], "weight": item["weight"]}
                    for item in local_face
                ]
            else:
                support_exclusion_ids = face_context[
                    "owned_morph_ids"
                ]
                modifiable_face_ids = support_exclusion_ids
                recipe_targets = target_face
            if EYEBALL_MOVE_MORPH_ID in modifiable_face_ids:
                raise ReconstructionError(
                    "Identity policy must not own {}".format(
                        EYEBALL_MOVE_MORPH_ID
                    )
                )
            if any(
                item.get("id") == EYEBALL_MOVE_MORPH_ID
                for item in recipe_targets
            ):
                raise ReconstructionError(
                    "Face recipe must not target {}".format(
                        EYEBALL_MOVE_MORPH_ID
                    )
                )
            hidden_context_keys = {
                "owned_morph_ids",
                "primary_expected_head_morphs",
                "primary_support_target_morphs",
            }
            result["face_context"] = dict(
                (key, value)
                for key, value in face_context.items()
                if key not in hidden_context_keys
            )
            if v3_face_pipeline:
                primary_targets = face_context[
                    "primary_expected_head_morphs"
                ]
                primary_support_targets = face_context[
                    "primary_support_target_morphs"
                ]
                result["face_context"][
                    "primary_target_face_morph_count"
                ] = len(primary_targets)
                result["face_context"][
                    "primary_target_face_fingerprint"
                ] = runtime_target_fingerprint(primary_targets)
                result["face_context"][
                    "primary_support_target_morph_count"
                ] = len(primary_support_targets)
                result["face_context"][
                    "primary_support_target_fingerprint"
                ] = runtime_target_fingerprint(
                    primary_support_targets
                )
            else:
                result["face_context"]["owned_morph_ids"] = (
                    support_exclusion_ids
                )

            support_before_preset = (
                head_preset_support_entries(after_body)
                if v3_face_pipeline
                else unowned_entries(
                    after_body,
                    support_exclusion_ids,
                    ("face", "other"),
                )
            )
            mark_phase(
                "load_primary_head_preset",
                {
                    "primary_seed_id": face_context["primary_seed_id"],
                    "path": face_context["source_head_preset"]["path"],
                },
            )
            avatar, result["face_head_preset_application"] = (
                load_primary_head_preset(avatar, face_context)
            )
            after_head_preset = capture_vectors(avatar)
            result["eye_integrity"]["phases"]["after_head_preset"] = (
                capture_eye_integrity_state(avatar)
            )
            if expected_eyeball_move_weight is not None:
                validate_expected_eye_integrity(
                    result["eye_integrity"]["phases"]["after_head_preset"],
                    expected_eyeball_move_weight,
                    "primary head preset",
                )
            write_json(after_head_preset, artifacts["head_preset_vectors"])
            support_after_preset = (
                head_preset_support_entries(after_head_preset)
                if v3_face_pipeline
                else unowned_entries(
                    after_head_preset,
                    support_exclusion_ids,
                    ("face", "other"),
                )
            )
            deltas["body_after_head_preset"] = group_delta(
                preset["target_body_morphs"],
                after_head_preset["groups"]["body"]["entries"],
            )
            deltas["junction_after_head_preset"] = group_delta(
                preset["target_junction_morphs"],
                after_head_preset["groups"]["junction"]["entries"],
            )
            deltas["face_support_after_preset"] = group_delta(
                support_before_preset,
                support_after_preset,
            )
            result["face_support_changes_after_preset"] = deltas[
                "face_support_after_preset"
            ]
            result["face_support_preserved_after_preset"] = not bool(
                deltas["face_support_after_preset"]
            )
            if deltas["body_after_head_preset"]:
                raise ReconstructionError(
                    "Loading primary head preset changed BodyFit morphs"
                )
            if deltas["junction_after_head_preset"]:
                raise ReconstructionError(
                    "Loading primary head preset changed junction morphs"
                )
            if v3_face_pipeline:
                before_identity = head_preset_identity_entries(after_body)
                after_identity = head_preset_identity_entries(
                    after_head_preset
                )
                primary_expected_map = {
                    item["id"]: float(item["weight"])
                    for item in primary_targets
                }
                primary_domain_ids = sorted(
                    set(primary_expected_map)
                    | {item["id"] for item in before_identity}
                    | {item["id"] for item in after_identity}
                )
                primary_expected_domain = [
                    {
                        "id": morph_id,
                        "weight": primary_expected_map.get(
                            morph_id, 0.0
                        ),
                    }
                    for morph_id in primary_domain_ids
                ]
                primary_actual = vector_entries_for_ids(
                    after_head_preset,
                    primary_domain_ids,
                )
                deltas["primary_head_preset_identity"] = group_delta(
                    primary_expected_domain,
                    primary_actual,
                    tolerance=1e-6,
                )
                result["face_primary_seed_delta"] = deltas[
                    "primary_head_preset_identity"
                ]
                result["face_primary_matches_seed"] = not bool(
                    deltas["primary_head_preset_identity"]
                )
                if not result["face_primary_matches_seed"]:
                    raise ReconstructionError(
                        "Loaded primary Head Preset differs from its "
                        "validated head-identity vector"
                    )

                mark_phase(
                    "apply_primary_head_support",
                    {
                        "primary_seed_id": face_context[
                            "primary_seed_id"
                        ],
                        "target_count": len(primary_support_targets),
                    },
                )
                result["face_support_application"] = (
                    apply_primary_head_support(
                        avatar,
                        primary_support_targets,
                        support_after_preset,
                    )
                )
                supported_head_preset = capture_vectors(avatar)
                write_json(
                    supported_head_preset,
                    artifacts["head_preset_supported_vectors"],
                )
                result["eye_integrity"]["phases"][
                    "after_primary_support"
                ] = capture_eye_integrity_state(avatar)
                if expected_eyeball_move_weight is not None:
                    validate_expected_eye_integrity(
                        result["eye_integrity"]["phases"][
                            "after_primary_support"
                        ],
                        expected_eyeball_move_weight,
                        "primary head support application",
                    )

                deltas["body_after_primary_support"] = group_delta(
                    preset["target_body_morphs"],
                    supported_head_preset["groups"]["body"]["entries"],
                )
                deltas["junction_after_primary_support"] = group_delta(
                    preset["target_junction_morphs"],
                    supported_head_preset["groups"]["junction"][
                        "entries"
                    ],
                )
                supported_entries = head_preset_support_entries(
                    supported_head_preset
                )
                primary_support_map = {
                    item["id"]: float(item["weight"])
                    for item in primary_support_targets
                }
                actor_part_domain_ids = sorted(
                    set(primary_support_map)
                    | {
                        item["id"]
                        for item in support_before_preset
                        if is_head_geometry_actor_part_morph_entry(item)
                    }
                    | {
                        item["id"]
                        for item in support_after_preset
                        if is_head_geometry_actor_part_morph_entry(item)
                    }
                    | {
                        item["id"]
                        for item in supported_entries
                        if is_head_geometry_actor_part_morph_entry(item)
                    }
                )
                primary_support_expected_domain = [
                    {
                        "id": morph_id,
                        "weight": primary_support_map.get(
                            morph_id,
                            0.0,
                        ),
                    }
                    for morph_id in actor_part_domain_ids
                ]
                primary_support_actual = vector_entries_for_ids(
                    supported_head_preset,
                    actor_part_domain_ids,
                )
                deltas["primary_head_support"] = group_delta(
                    primary_support_expected_domain,
                    primary_support_actual,
                    tolerance=1e-6,
                )
                result["face_support_delta_from_primary"] = deltas[
                    "primary_head_support"
                ]
                result[
                    "face_support_matches_primary_after_preset"
                ] = not bool(deltas["primary_head_support"])
                if deltas["body_after_primary_support"]:
                    raise ReconstructionError(
                        "Applying primary Head support changed BodyFit "
                        "Morphs"
                    )
                if deltas["junction_after_primary_support"]:
                    raise ReconstructionError(
                        "Applying primary Head support changed junction "
                        "Morphs"
                    )
                if not result[
                    "face_support_matches_primary_after_preset"
                ]:
                    raise ReconstructionError(
                        "Primary Head support differs from its validated "
                        "Actor Parts vector"
                    )
                after_head_preset = supported_head_preset

                mark_phase(
                    "load_primary_facial_profile",
                    {
                        "path": face_context[
                            "source_facial_profile"
                        ]["path"],
                        "primary_seed_id": face_context[
                            "primary_seed_id"
                        ],
                    },
                )
                avatar, result[
                    "face_facial_profile_application"
                ] = load_primary_facial_profile(
                    avatar,
                    face_context,
                )
                after_facial_profile = capture_vectors(avatar)
                write_json(
                    after_facial_profile,
                    artifacts["facial_profile_vectors"],
                )
                result["eye_integrity"]["phases"][
                    "after_facial_profile"
                ] = capture_eye_integrity_state(avatar)
                if expected_eyeball_move_weight is not None:
                    validate_expected_eye_integrity(
                        result["eye_integrity"]["phases"][
                            "after_facial_profile"
                        ],
                        expected_eyeball_move_weight,
                        "primary Facial Profile application",
                    )
                profile_morph_delta = {
                    classification: group_delta(
                        after_head_preset["groups"][classification][
                            "entries"
                        ],
                        after_facial_profile["groups"][classification][
                            "entries"
                        ],
                    )
                    for classification in (
                        "body",
                        "junction",
                        "face",
                        "other",
                    )
                }
                result["face_facial_profile_morph_delta"] = (
                    profile_morph_delta
                )
                result[
                    "face_facial_profile_morphs_unchanged"
                ] = not any(profile_morph_delta.values())
                result[
                    "face_facial_profile_eye_structure_unchanged"
                ] = (
                    eye_integrity_structure_signature(
                        result["eye_integrity"]["phases"][
                            "after_primary_support"
                        ]
                    )
                    == eye_integrity_structure_signature(
                        result["eye_integrity"]["phases"][
                            "after_facial_profile"
                        ]
                    )
                )
                if not result[
                    "face_facial_profile_morphs_unchanged"
                ]:
                    raise ReconstructionError(
                        "Loading primary Facial Profile changed static "
                        "Body, Head, or support Morphs"
                    )
                if not result[
                    "face_facial_profile_eye_structure_unchanged"
                ]:
                    raise ReconstructionError(
                        "Loading primary Facial Profile changed eye "
                        "object or eye-bone identity"
                    )
                after_head_preset = after_facial_profile

            support_before_identity = unowned_entries(
                after_head_preset,
                support_exclusion_ids,
                ("face", "other"),
            )
            mark_phase(
                "apply_face_identity_morphs",
                {
                    "mode": face_context["mode"],
                    "target_count": len(recipe_targets),
                },
            )
            if v3_face_pipeline:
                result["face_application"] = apply_local_face_morphs(
                    avatar,
                    local_face,
                    modifiable_face_ids,
                )
            else:
                result["face_application"] = apply_target_face(
                    avatar,
                    target_face,
                    support_exclusion_ids,
                )
            result["eye_integrity"]["identity_write_attempted"] = any(
                item["id"] == EYEBALL_MOVE_MORPH_ID
                for item in result["face_application"]["changed"]
            )
            if result["eye_integrity"]["identity_write_attempted"]:
                raise ReconstructionError(
                    "Identity application wrote {}".format(
                        EYEBALL_MOVE_MORPH_ID
                    )
                )
            composed = capture_vectors(avatar)
            result["eye_integrity"]["phases"]["after_face_identity"] = (
                capture_eye_integrity_state(avatar)
            )
            if expected_eyeball_move_weight is not None:
                validate_expected_eye_integrity(
                    result["eye_integrity"]["phases"]["after_face_identity"],
                    expected_eyeball_move_weight,
                    "face identity application",
                )
            write_json(composed, artifacts["composed_vectors"])
            composed_identity = vector_entries_for_ids(
                composed,
                [item["id"] for item in recipe_targets],
            )
            support_after_identity = unowned_entries(
                composed,
                support_exclusion_ids,
                ("face", "other"),
            )
            deltas["face_target"] = group_delta(
                recipe_targets,
                composed_identity,
                tolerance=1e-6,
            )
            deltas["body_after_face"] = group_delta(
                preset["target_body_morphs"],
                composed["groups"]["body"]["entries"],
            )
            deltas["junction_after_face"] = group_delta(
                preset["target_junction_morphs"],
                composed["groups"]["junction"]["entries"],
            )
            deltas["other_after_face"] = group_delta(
                baseline["groups"]["other"]["entries"],
                composed["groups"]["other"]["entries"],
            )
            deltas["face_support_after_identity"] = group_delta(
                support_before_identity,
                support_after_identity,
            )
            write_json(deltas, artifacts["morph_delta"])
            result["face_matches_recipe"] = not bool(deltas["face_target"])
            result["body_unchanged_after_face"] = not bool(
                deltas["body_after_face"]
            )
            result["junction_unchanged_after_face"] = not bool(
                deltas["junction_after_face"]
            )
            result["face_support_changes_after_identity"] = deltas[
                "face_support_after_identity"
            ]
            result["face_support_preserved_after_identity"] = not bool(
                deltas["face_support_after_identity"]
            )
            result["eye_structure_preserved_after_identity"] = (
                eye_integrity_structure_signature(
                    result["eye_integrity"]["phases"][
                        (
                            "after_facial_profile"
                            if v3_face_pipeline
                            else "after_head_preset"
                        )
                    ]
                )
                == eye_integrity_structure_signature(
                    result["eye_integrity"]["phases"][
                        "after_face_identity"
                    ]
                )
            )
            result["expected_face_fingerprint"] = preset.get(
                "local_morph_fingerprint"
                if v3_face_pipeline
                else "target_face_fingerprint"
            )
            result["expected_runtime_face_fingerprint"] = (
                runtime_target_fingerprint(recipe_targets)
            )
            result["reconstructed_face_fingerprint"] = vector_fingerprint(
                composed_identity
            )
            result["exact_runtime_face_fingerprint_matches"] = (
                result["reconstructed_face_fingerprint"]
                == result["expected_runtime_face_fingerprint"]
            )
            result["face_max_abs_error"] = maximum_abs_delta(
                recipe_targets,
                composed_identity,
            )
            if not result["face_matches_recipe"]:
                raise ReconstructionError("Composed face differs from target recipe")
            if not result["body_unchanged_after_face"]:
                raise ReconstructionError("Applying face recipe changed body morphs")
            if not result["junction_unchanged_after_face"]:
                raise ReconstructionError("Applying face recipe changed junction morphs")
            if (
                v3_face_pipeline
                and not result[
                    "face_support_preserved_after_identity"
                ]
            ):
                raise ReconstructionError(
                    "V3 local Morph application changed unlisted "
                    "face/support Morphs"
                )
            if (
                v3_face_pipeline
                and not result[
                    "eye_structure_preserved_after_identity"
                ]
            ):
                raise ReconstructionError(
                    "V3 local Morph application changed eye object "
                    "or eye-bone identity"
                )

        face_alignment_bounds = capture_bounds(avatar)
        avatar, facial_assembly_result = apply_facial_assembly(
            avatar,
            preset,
            appearance_catalog,
            progress_callback=mark_phase,
            asset_load_pacing=asset_load_pacing,
        )
        if facial_assembly_result is not None:
            result["facial_assembly"] = facial_assembly_result
            write_json(
                facial_assembly_result,
                artifacts["facial_assembly"],
            )
            result["eye_integrity"]["phases"][
                "after_facial_assembly"
            ] = capture_eye_integrity_state(avatar)
            if expected_eyeball_move_weight is not None:
                validate_expected_eye_integrity(
                    result["eye_integrity"]["phases"][
                        "after_facial_assembly"
                    ],
                    expected_eyeball_move_weight,
                    "facial assembly",
                )
        appearance_assets = resolve_appearance_assets(preset, appearance_catalog)
        if appearance_assets:
            before_appearance = capture_vectors(avatar)
            avatar, result["appearance_application"] = apply_appearance_assets(
                avatar,
                appearance_assets,
                resolve_appearance_cleanup(preset),
                allow_missing_cleanup=(
                    body_application_mode == "source_project"
                ),
                progress_callback=mark_phase,
                asset_load_pacing=asset_load_pacing,
            )
            write_json(
                result["appearance_application"], artifacts["appearance_inventory"]
            )
            after_appearance = capture_vectors(avatar)
            appearance_deltas = {
                classification: group_delta(
                    before_appearance["groups"][classification]["entries"],
                    after_appearance["groups"][classification]["entries"],
                )
                for classification in ("body", "junction", "face", "other")
            }
            deltas["appearance"] = appearance_deltas
            write_json(deltas, artifacts["morph_delta"])
            result["appearance_matches_recipe"] = all(
                appearance_step_matches(step)
                for step in result["appearance_application"]["steps"]
            )
            result["morphs_unchanged_after_appearance"] = not any(
                appearance_deltas.values()
            )
            result["appearance_morph_policy"] = (
                evaluate_appearance_morph_policy(
                    appearance_assets,
                    before_appearance,
                    after_appearance,
                    appearance_deltas,
                )
            )
            result["appearance_morphs_within_policy"] = (
                result["appearance_morph_policy"]["status"] == "accepted"
            )
            if not result["appearance_matches_recipe"]:
                raise ReconstructionError("Appearance recipe did not change the scene")
            if not result["appearance_morphs_within_policy"]:
                raise ReconstructionError(
                    "Applying appearance assets changed protected avatar morphs"
                )

        force_avatar_scene_evaluation(avatar)
        result["eye_integrity"]["phases"]["final"] = (
            capture_eye_integrity_state(avatar)
        )
        if expected_eyeball_move_weight is not None:
            validate_expected_eye_integrity(
                result["eye_integrity"]["phases"]["final"],
                expected_eyeball_move_weight,
                "final character",
            )
        write_json(result["eye_integrity"], artifacts["eye_integrity"])
        mark_phase("render_reconstructed_preview")
        render_preview(artifacts["reconstructed_preview"])
        requires_face_validation = bool(
            has_face_recipe
            or (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                in (
                    TEETH_VISIBILITY_PROFILE,
                    EYE_VISIBILITY_PROFILE,
                    EYEBROW_VISIBILITY_PROFILE,
                    EYELASH_VISIBILITY_PROFILE,
                    FACIAL_HAIR_VISIBILITY_PROFILE,
                    SCALP_HAIR_VISIBILITY_PROFILE,
                    FACE_IDENTITY_SAFETY_PROFILE,
                )
            )
        )
        if requires_face_validation:
            camera_path = preset.get("face_camera")
            if not isinstance(camera_path, str) or not os.path.isfile(camera_path):
                raise ReconstructionError(
                    "Face preview camera is missing: {}".format(camera_path)
                )
            camera_status, camera_dialogs = (
                load_file_with_optional_undo_warning(
                    camera_path,
                    "Load face preview camera",
                )
            )
            result["file_load_dialogs"]["face_preview_camera"] = {
                "status": camera_status,
                "dialogs": camera_dialogs,
            }
            face_subject_alignment = resolve_face_subject_alignment(
                baseline_bounds["maximum"][2],
                face_alignment_bounds["maximum"][2],
                (
                    appearance_validation_plan.get(
                        "face_camera_reference_top_z"
                    )
                    if appearance_validation_plan
                    else None
                ),
            )
            subject_z_offset = face_subject_alignment[
                "subject_z_offset"
            ]
            initial_position = {
                "x": _transform_float(avatar, "Position/PositionX"),
                "y": _transform_float(avatar, "Position/PositionY"),
                "z": _transform_float(avatar, "Position/PositionZ"),
            }
            initial_yaw_radians = _transform_float(
                avatar, "Rotation/RotationZ"
            )
            subject_position_offset = (
                appearance_validation_plan.get("subject_position_offset", {})
                if appearance_validation_plan
                else {}
            )
            validation_position = {
                "x": float(subject_position_offset.get("x", 0.0)),
                "y": float(subject_position_offset.get("y", 0.0)),
                "z": subject_z_offset
                + float(subject_position_offset.get("z", 0.0)),
            }
            result["face_subject_alignment"] = dict(
                face_subject_alignment
            )
            result["face_subject_alignment"].update(
                {
                    "initial_position": initial_position,
                    "subject_position_offset": subject_position_offset,
                    "validation_position": validation_position,
                }
            )
            set_avatar_position(
                avatar,
                position_x=validation_position["x"],
                position_y=validation_position["y"],
                position_z=validation_position["z"],
            )
            scalp_hair_profile = bool(
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == SCALP_HAIR_VISIBILITY_PROFILE
            )
            compensate_face_views = bool(
                scalp_hair_profile or facial_assembly_result is not None
            )
            if compensate_face_views:
                result["face_view_y_offsets"] = dict(
                    SCALP_HAIR_VIEW_Y_OFFSETS
                )
            if render_static_hair_views:
                result["scalp_hair_view_y_offsets"] = dict(
                    SCALP_HAIR_VIEW_Y_OFFSETS
                )
            if compensate_face_views:
                set_avatar_position(
                    avatar,
                    position_y=(
                        validation_position["y"]
                        + SCALP_HAIR_VIEW_Y_OFFSETS["profile"]
                    ),
                )
            set_avatar_yaw(avatar, 0.0)
            mark_phase("render_face_profile")
            render_preview(artifacts["face_profile_preview"])
            if compensate_face_views:
                set_avatar_position(
                    avatar,
                    position_y=(
                        validation_position["y"]
                        + SCALP_HAIR_VIEW_Y_OFFSETS["three_quarter"]
                    ),
                )
            set_avatar_yaw(avatar, 45.0)
            mark_phase("render_face_three_quarter")
            render_preview(artifacts["face_three_quarter_preview"])
            if compensate_face_views:
                set_avatar_position(
                    avatar,
                    position_y=(
                        validation_position["y"]
                        + SCALP_HAIR_VIEW_Y_OFFSETS["front"]
                    ),
                )
            set_avatar_yaw(avatar, 90.0)
            mark_phase("render_face_front")
            render_preview(artifacts["face_front_preview"])
            if render_static_hair_views:
                set_avatar_position(
                    avatar,
                    position_y=(
                        validation_position["y"]
                        + SCALP_HAIR_VIEW_Y_OFFSETS[
                            "rear_three_quarter"
                        ]
                    ),
                )
                set_avatar_yaw(avatar, -45.0)
                mark_phase("render_hair_rear_three_quarter")
                render_preview(
                    artifacts["hair_rear_three_quarter_preview"]
                )
                set_avatar_position(
                    avatar,
                    position_y=(
                        validation_position["y"]
                        + SCALP_HAIR_VIEW_Y_OFFSETS["rear"]
                    ),
                )
                set_avatar_yaw(avatar, -90.0)
                mark_phase("render_hair_rear")
                render_preview(artifacts["hair_rear_preview"])
            hair_motion_plan = (
                appearance_validation_plan.get(
                    "hair_motion_validation"
                )
                if appearance_validation_plan
                else None
            )
            if hair_motion_plan is not None:
                if not isinstance(hair_motion_plan, dict):
                    raise ReconstructionError(
                        "hair_motion_validation must be an object"
                    )
                mark_phase("validate_hair_motion")
                result["hair_motion_validation"] = (
                    probe_current_hair_motion(
                        {
                            "hair_motion_probe": hair_motion_plan,
                        },
                        os.path.join(
                            preset_dir,
                            "hair_motion",
                        ),
                    )
                )
            if compensate_face_views:
                set_avatar_position(
                    avatar,
                    position_y=(
                        validation_position["y"]
                        + SCALP_HAIR_VIEW_Y_OFFSETS["front"]
                    ),
                )
            set_avatar_yaw(avatar, 90.0)
            if (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == TEETH_VISIBILITY_PROFILE
            ):
                result["facial_pose_validation"] = (
                    render_teeth_visibility_previews(
                        avatar,
                        artifacts,
                        mark_phase,
                    )
                )
            elif (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == EYE_VISIBILITY_PROFILE
            ):
                result["facial_pose_validation"] = (
                    render_eye_visibility_previews(
                        avatar,
                        artifacts,
                        mark_phase,
                    )
                )
            elif (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == EYEBROW_VISIBILITY_PROFILE
            ):
                result["facial_pose_validation"] = (
                    render_eyebrow_visibility_previews(
                        avatar,
                        artifacts,
                        mark_phase,
                    )
                )
            elif (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == EYELASH_VISIBILITY_PROFILE
            ):
                result["facial_pose_validation"] = (
                    render_eyelash_visibility_previews(
                        avatar,
                        artifacts,
                        mark_phase,
                    )
                )
            elif (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == FACIAL_HAIR_VISIBILITY_PROFILE
            ):
                result["facial_pose_validation"] = (
                    render_face_identity_safety_previews(
                        avatar,
                        artifacts,
                        mark_phase,
                        profile=FACIAL_HAIR_VISIBILITY_PROFILE,
                        pose_ids=(
                            "smile_front",
                            "jaw_open_front",
                            "jaw_open_three_quarter",
                        ),
                    )
                )
            elif (
                appearance_validation_plan
                and appearance_validation_plan.get("pose_profile")
                == FACE_IDENTITY_SAFETY_PROFILE
            ):
                if dynamic_wrinkle_validation is not None:
                    (
                        result["facial_pose_validation"],
                        result["dynamic_wrinkle_validation"],
                    ) = render_dynamic_wrinkle_strength_pair(
                        avatar,
                        artifacts,
                        mark_phase,
                        dynamic_wrinkle_validation,
                    )
                else:
                    result["facial_pose_validation"] = (
                        render_face_identity_safety_previews(
                            avatar,
                            artifacts,
                            mark_phase,
                        )
                    )
            avatar, unused_avatars = resolve_avatar()
            post_face_validation_expected = result[
                "eye_integrity"
            ]["phases"]["final"]
            facial_pose_timeline = (
                (result.get("facial_pose_validation") or {}).get(
                    "timeline"
                )
                or {}
            )
            if facial_pose_timeline.get("capture_strategy") == (
                "facial_profile_start_frame_snapshot_restore_v1"
            ):
                post_face_validation_expected = (
                    capture_eye_integrity_state(avatar)
                )
                result["eye_integrity"]["phases"][
                    "post_face_validation_snapshot_restore"
                ] = post_face_validation_expected
            set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
            set_avatar_position(
                avatar,
                position_x=initial_position["x"],
                position_y=initial_position["y"],
                position_z=initial_position["z"],
            )
            (
                result["eye_integrity"]["phases"][
                    "post_face_validation"
                ],
                result["eye_integrity"][
                    "post_face_validation_comparison"
                ],
                result["eye_integrity"][
                    "post_face_validation_refresh_attempts"
                ],
            ) = stabilize_neutral_eye_state(
                avatar,
                post_face_validation_expected,
            )
            write_json(result["eye_integrity"], artifacts["eye_integrity"])
            if not result["eye_integrity"][
                "post_face_validation_comparison"
            ]["matches"]:
                raise ReconstructionError(
                    "Face validation changed final eye state: {}".format(
                        result["eye_integrity"][
                            "post_face_validation_comparison"
                        ]["differences"]
                    )
                )
        result["success"] = True
        mark_phase("complete")
    except Exception as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        log("FAILED {}: {}".format(preset["preset_id"], exc))
        mark_phase(
            "failed",
            {"type": type(exc).__name__, "message": str(exc)},
        )
    write_json(result, result_path)
    return result


def probe_current_hair_shaders(output_dir):
    avatar, unused_avatars = resolve_avatar()
    records = current_hair_shader_records(avatar)
    signatures = collections.Counter(
        (
            item.get("domain"),
            item.get("shader"),
            tuple(sorted((item.get("parameters") or {}).keys())),
        )
        for item in records
        if not item.get("error")
    )
    report = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "captured_at": now(),
        "material_record_count": len(records),
        "records": records,
        "schema_version": 1,
        "signatures": [
            {
                "count": count,
                "domain": key[0],
                "parameter_names": list(key[2]),
                "shader": key[1],
            }
            for key, count in sorted(
                signatures.items(),
                key=lambda item: (
                    str(item[0][0]),
                    str(item[0][1]),
                    item[0][2],
                ),
            )
        ],
    }
    report_path = os.path.join(output_dir, "hair_shader_probe.json")
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir, "hair_shader_probe_summary.json"
    )
    return {
        "diagnostic_mode": "hair_shader_probe",
        "failure_count": 0,
        "finished_at": now(),
        "hair_shader_probe_path": report_path,
        "requested_count": 1,
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def capture_current_hair_physics(avatar):
    hair_records = []
    for hair in list(avatar.GetHairs() or []):
        record = {
            "bounds": None,
            "id": scene_object_id(hair),
            "name": scene_object_name(hair),
            "physics_active": None,
            "physics_component_present": False,
            "soft_material_count": 0,
            "soft_meshes": [],
        }
        try:
            component = hair.GetPhysicsComponent()
            record["physics_component_present"] = component is not None
            if component is None:
                hair_records.append(record)
                continue
            record["physics_active"] = bool(
                component.IsActivatePhysicsEnable()
            )
            mesh_names = list(
                component.GetSoftPhysicsMeshNameList()
            )
            for mesh_name in mesh_names:
                material_names = list(
                    component.GetSoftPhysicsMaterialNameList(
                        mesh_name
                    )
                )
                record["soft_meshes"].append(
                    {
                        "material_names": material_names,
                        "mesh_name": mesh_name,
                    }
                )
                record["soft_material_count"] += len(
                    material_names
                )
            try:
                record["bounds"] = capture_bounds(hair)
            except Exception as exc:
                record["bounds_error"] = str(exc)
        except Exception as exc:
            record["error"] = {
                "message": str(exc),
                "type": type(exc).__name__,
            }
        hair_records.append(record)
    if not hair_records:
        raise ReconstructionError(
            "Hair physics probe found no RIHair objects"
        )
    eligible_records = [
        item for item in hair_records if not item.get("error")
    ]
    return {
        "all_hair_parts_physics_enabled": bool(
            eligible_records
            and len(eligible_records) == len(hair_records)
            and all(
                item["physics_component_present"]
                and item["physics_active"]
                for item in eligible_records
            )
        ),
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "captured_at": now(),
        "global_physics_simulation_loop": bool(
            RLPy.RGlobal.IsPhysicsSimulationLoop()
        ),
        "hair_part_count": len(hair_records),
        "hair_parts": hair_records,
        "physics_active_count": sum(
            1
            for item in hair_records
            if item.get("physics_active") is True
        ),
        "physics_component_count": sum(
            1
            for item in hair_records
            if item.get("physics_component_present")
        ),
        "soft_material_count": sum(
            int(item.get("soft_material_count", 0))
            for item in hair_records
        ),
    }


def probe_current_hair_physics(output_dir):
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Hair physics probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    report = capture_current_hair_physics(avatar)
    report.update(
        {
            "avatar": {
                "id": scene_object_id(avatar),
                "name": scene_object_name(avatar),
            },
            "captured_at": now(),
            "global_physics_simulation_loop": bool(
                RLPy.RGlobal.IsPhysicsSimulationLoop()
            ),
            "schema_version": 1,
        }
    )
    report_path = os.path.join(
        output_dir, "hair_physics_probe.json"
    )
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir, "hair_physics_probe_summary.json"
    )
    write_json(
        {
            "all_hair_parts_physics_enabled": report[
                "all_hair_parts_physics_enabled"
            ],
            "diagnostic_mode": "hair_physics_probe",
            "failure_count": 0,
            "finished_at": now(),
            "hair_part_count": report["hair_part_count"],
            "hair_physics_probe_path": report_path,
            "physics_active_count": report[
                "physics_active_count"
            ],
            "physics_component_count": report[
                "physics_component_count"
            ],
            "requested_count": 1,
            "schema_version": 1,
            "soft_material_count": report[
                "soft_material_count"
            ],
            "started_at": report["captured_at"],
            "success": True,
            "success_count": 1,
            "summary_path": summary_path,
        },
        summary_path,
    )
    return read_json(summary_path)


def probe_current_hair_motion(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Hair motion probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    probe = library.get("hair_motion_probe") or {}
    motion_path = canonical_existing_file(
        probe.get("motion_path"),
        "Hair motion probe",
    )
    camera_path = canonical_existing_file(
        probe.get("camera_path"),
        "Hair motion probe camera",
    )
    sample_frames = probe.get("sample_frames") or [
        0,
        30,
        60,
        90,
        120,
    ]
    if (
        not isinstance(sample_frames, list)
        or not sample_frames
        or any(
            not isinstance(item, int) or item < 0
            for item in sample_frames
        )
    ):
        raise ReconstructionError(
            "hair_motion_probe.sample_frames must contain "
            "non-negative integers"
        )
    sample_frames = sorted(set(sample_frames))
    subject_position = probe.get("subject_position") or {}
    yaw_degrees = float(probe.get("yaw_degrees", 90.0))
    segment_timeout_seconds = float(
        probe.get("segment_timeout_seconds", 20.0)
    )
    if segment_timeout_seconds <= 0.0:
        raise ReconstructionError(
            "hair_motion_probe.segment_timeout_seconds must be positive"
        )

    skeleton = avatar.GetSkeletonComponent()
    if skeleton is None:
        raise ReconstructionError(
            "Hair motion probe avatar has no skeleton component"
        )
    face_component = avatar.GetFaceComponent()
    initial_clip_count = int(skeleton.GetClipCount())
    initial_face_clip_count = (
        int(face_component.GetClipCount())
        if face_component is not None
        else 0
    )
    initial_time = RLPy.RGlobal.GetTime()
    initial_start_time = RLPy.RGlobal.GetStartTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    initial_physics_loop = bool(
        RLPy.RGlobal.IsPhysicsSimulationLoop()
    )
    initial_camera = RLPy.RScene.GetCurrentCamera()
    initial_position = {
        "x": _transform_float(avatar, "Position/PositionX"),
        "y": _transform_float(avatar, "Position/PositionY"),
        "z": _transform_float(avatar, "Position/PositionZ"),
    }
    initial_yaw_radians = _transform_float(
        avatar, "Rotation/RotationZ"
    )
    fps = RLPy.RGlobal.GetFps()
    clip_start = RLPy.IndexedFrameTime(0, fps)
    report = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "captured_at": now(),
        "camera_path": camera_path,
        "initial_hair_physics": capture_current_hair_physics(
            avatar
        ),
        "motion_path": motion_path,
        "samples": [],
        "schema_version": 1,
    }
    baseline_clip_count = initial_clip_count
    baseline_face_clip_count = initial_face_clip_count
    try:
        if bool(probe.get("replace_existing_motion_clips", True)):
            for clip_index in range(
                int(skeleton.GetClipCount()) - 1,
                -1,
                -1,
            ):
                checked(
                    "Delete existing hair motion probe clip {}".format(
                        clip_index
                    ),
                    skeleton.DeleteClip(
                        skeleton.GetClip(clip_index)
                    ),
                )
                QtWidgets.QApplication.processEvents()
            baseline_clip_count = int(skeleton.GetClipCount())
            if face_component is not None:
                for clip_index in range(
                    int(face_component.GetClipCount()) - 1,
                    -1,
                    -1,
                ):
                    checked(
                        (
                            "Delete existing hair motion face clip {}"
                        ).format(clip_index),
                        face_component.DeleteClip(
                            face_component.GetClip(clip_index)
                        ),
                    )
                    QtWidgets.QApplication.processEvents()
                baseline_face_clip_count = int(
                    face_component.GetClipCount()
                )

        checked(
            "Load hair motion probe camera",
            RLPy.RFileIO.LoadFile(camera_path),
        )
        motion_camera = RLPy.RScene.GetCurrentCamera()
        if motion_camera is None:
            raise ReconstructionError(
                "Hair motion probe has no active camera"
            )
        report["camera"] = camera_state(motion_camera)
        RLPy.RScene.SelectObject(avatar)
        checked(
            "Load hair motion probe",
            RLPy.RFileIO.LoadFile(motion_path),
        )
        QtWidgets.QApplication.processEvents()
        clip_count = int(skeleton.GetClipCount())
        if clip_count <= baseline_clip_count:
            raise ReconstructionError(
                "Hair motion probe did not add a skeleton clip"
            )
        clip = skeleton.GetClip(clip_count - 1)
        clip_length = clip.GetLength()
        clip_length_frame = int(
            fps.GetFrameIndex(clip_length)
        )
        if clip_length_frame <= 0:
            clip_length = clip.GetClipLength()
            clip_length_frame = int(
                fps.GetFrameIndex(clip_length)
            )
        if clip_length_frame <= 0:
            raise ReconstructionError(
                "Hair motion probe clip has no positive length"
            )
        bounded_frames = sorted(
            set(
                min(frame, clip_length_frame)
                for frame in sample_frames
            )
        )
        report["clip"] = {
            "clip_count_after_load": clip_count,
            "face_clip_count_after_load": (
                int(face_component.GetClipCount())
                if face_component is not None
                else 0
            ),
            "length_frame": clip_length_frame,
            "load_method": "RFileIO.LoadFile",
            "python_type": type(clip).__name__,
            "sample_frames": bounded_frames,
        }
        set_avatar_position(
            avatar,
            position_x=float(
                subject_position.get(
                    "x", initial_position["x"]
                )
            ),
            position_y=float(
                subject_position.get(
                    "y", initial_position["y"]
                )
            ),
            position_z=float(
                subject_position.get(
                    "z", initial_position["z"]
                )
            ),
        )
        set_avatar_yaw(avatar, yaw_degrees)
        checked(
            "Enable hair motion physics simulation loop",
            RLPy.RGlobal.SetPhysicsSimulationLoop(True),
        )
        end_time = RLPy.IndexedFrameTime(
            max(bounded_frames),
            fps,
        )
        checked(
            "Set hair motion probe start time",
            RLPy.RGlobal.SetStartTime(clip_start),
        )
        checked(
            "Set hair motion probe end time",
            RLPy.RGlobal.SetEndTime(end_time),
        )
        checked(
            "Initialize hair motion probe time",
            RLPy.RGlobal.SetTime(clip_start, True),
        )
        previous_frame = 0
        for frame in bounded_frames:
            target_time = RLPy.IndexedFrameTime(frame, fps)
            if frame > previous_frame:
                segment_start = RLPy.IndexedFrameTime(
                    previous_frame,
                    fps,
                )
                checked(
                    "Play hair motion probe to frame {}".format(
                        frame
                    ),
                    RLPy.RGlobal.Play(
                        segment_start,
                        target_time,
                    ),
                )
                deadline = time.time() + segment_timeout_seconds
                while RLPy.RGlobal.IsPlaying():
                    QtWidgets.QApplication.processEvents()
                    if time.time() >= deadline:
                        raise ReconstructionError(
                            "Hair motion playback timed out at "
                            "frame {}".format(frame)
                        )
                    time.sleep(0.01)
            checked(
                "Set hair motion sample frame {}".format(frame),
                RLPy.RGlobal.SetTime(target_time, True),
            )
            checked(
                (
                    "Restore hair motion camera at frame {}"
                ).format(frame),
                RLPy.RScene.SetCurrentCamera(motion_camera),
            )
            QtWidgets.QApplication.processEvents()
            image_path = os.path.join(
                output_dir,
                "hair_motion_frame_{:04d}.png".format(frame),
            )
            render_preview(image_path, target_time)
            report["samples"].append(
                {
                    "frame": frame,
                    "hair_physics": capture_current_hair_physics(
                        avatar
                    ),
                    "image": image_path,
                }
            )
            previous_frame = frame
    finally:
        if RLPy.RGlobal.IsPlaying():
            RLPy.RGlobal.Stop()
        for clip_index in range(
            int(skeleton.GetClipCount()) - 1,
            baseline_clip_count - 1,
            -1,
        ):
            skeleton.DeleteClip(skeleton.GetClip(clip_index))
            QtWidgets.QApplication.processEvents()
        if face_component is not None:
            for clip_index in range(
                int(face_component.GetClipCount()) - 1,
                baseline_face_clip_count - 1,
                -1,
            ):
                face_component.DeleteClip(
                    face_component.GetClip(clip_index)
                )
                QtWidgets.QApplication.processEvents()
        set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
        set_avatar_position(
            avatar,
            position_x=initial_position["x"],
            position_y=initial_position["y"],
            position_z=initial_position["z"],
        )
        RLPy.RGlobal.SetPhysicsSimulationLoop(
            initial_physics_loop
        )
        RLPy.RGlobal.SetStartTime(initial_start_time)
        RLPy.RGlobal.SetEndTime(initial_end_time)
        RLPy.RGlobal.SetTime(initial_time, True)
        if initial_camera is not None:
            RLPy.RScene.SetCurrentCamera(initial_camera)
        QtWidgets.QApplication.processEvents()

    report["finished_at"] = now()
    report_path = os.path.join(
        output_dir, "hair_motion_probe.json"
    )
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir, "hair_motion_probe_summary.json"
    )
    summary = {
        "diagnostic_mode": "hair_motion_probe",
        "failure_count": 0,
        "finished_at": report["finished_at"],
        "hair_motion_probe_path": report_path,
        "motion_length_frame": report["clip"][
            "length_frame"
        ],
        "requested_count": 1,
        "sample_count": len(report["samples"]),
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def apply_current_hair_pigmentation(library, output_dir):
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Hair pigmentation probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    payload = library.get("hair_pigmentation") or {}
    hair_color = payload.get("hair_color")
    visible_gray_fraction = payload.get(
        "visible_gray_fraction"
    )
    before = current_hair_shader_records(avatar)
    application = apply_shared_hair_pigmentation(
        avatar,
        hair_color,
        visible_gray_fraction,
    )
    after = current_hair_shader_records(avatar)
    report = {
        "application": application,
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "before": before,
        "after": after,
        "captured_at": now(),
        "requested": {
            "hair_color": hair_color,
            "visible_gray_fraction": visible_gray_fraction,
        },
        "schema_version": 1,
    }
    report_path = os.path.join(
        output_dir, "hair_pigmentation_apply.json"
    )
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir, "hair_pigmentation_apply_summary.json"
    )
    return {
        "diagnostic_mode": "hair_pigmentation_apply",
        "failure_count": 0,
        "finished_at": now(),
        "hair_pigmentation_apply_path": report_path,
        "requested_count": 1,
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }


def probe_current_wrinkle_profile(library, output_dir):
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Wrinkle profile probe expected one avatar"
        )
    path = canonical_existing_file(
        library.get("wrinkle_profile_path"),
        "Wrinkle profile probe",
    )
    require_file_extension(
        path,
        ".rlWrinkle",
        "Wrinkle profile probe",
    )
    profile_component = avatar.GetFacialProfileComponent()
    if profile_component is None:
        raise ReconstructionError(
            "Avatar has no facial profile component"
        )
    before_vectors = capture_vectors(avatar)
    before_material = avatar_material_fingerprint(avatar)
    RLPy.RScene.SelectObject(avatar)
    status = checked(
        "Load wrinkle profile through facial profile component",
        profile_component.LoadProfile(path),
    )
    QtWidgets.QApplication.processEvents()
    after_vectors = capture_vectors(avatar)
    after_material = avatar_material_fingerprint(avatar)
    morph_deltas = {
        classification: group_delta(
            before_vectors["groups"][classification]["entries"],
            after_vectors["groups"][classification]["entries"],
        )
        for classification in ("body", "junction", "face", "other")
    }
    report = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "captured_at": now(),
        "load_status": status,
        "material_changed": (
            before_material["digest"] != after_material["digest"]
        ),
        "material_digest_after": after_material["digest"],
        "material_digest_before": before_material["digest"],
        "morph_deltas": morph_deltas,
        "path": path,
        "schema_version": 1,
    }
    report_path = os.path.join(
        output_dir, "wrinkle_profile_probe.json"
    )
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir, "wrinkle_profile_probe_summary.json"
    )
    return {
        "diagnostic_mode": "wrinkle_profile_probe",
        "failure_count": 0,
        "finished_at": now(),
        "requested_count": 1,
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
        "wrinkle_profile_probe_path": report_path,
    }


def probe_current_pixel_stream(output_dir):
    import ctypes
    from PySide2 import QtGui

    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Pixel stream probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    report = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "captured_at": now(),
        "diagnostic_mode": "pixel_stream_probe",
        "frame_candidates": [],
        "schema_version": 1,
    }
    original_view_size = None
    try:
        try:
            view_size = RLPy.RGlobal.GetViewSize(0, 0)
            if (
                isinstance(view_size, (list, tuple))
                and len(view_size) >= 3
            ):
                original_view_size = (
                    int(view_size[-2]),
                    int(view_size[-1]),
                )
                report["original_view_size"] = list(original_view_size)
        except Exception as exc:
            report["original_view_size_error"] = str(exc)
        report["set_view_size_status"] = checked(
            "Set pixel stream view size",
            RLPy.RGlobal.SetViewSize(512, 512),
        )
        report["enable_status"] = checked(
            "Enable viewport pixel stream",
            RLPy.RGlobal.EnablePixelStream(True),
        )
        try:
            report["render_preview_status"] = checked(
                "Render viewport pixel stream",
                RLPy.RGlobal.RenderPreview(),
            )
        except Exception as exc:
            report["render_preview_error"] = {
                "message": str(exc),
                "type": type(exc).__name__,
            }
        captured_images = []
        for capture_index in range(3):
            report.setdefault("viewport_update_statuses", []).append(
                checked(
                    "Force viewport update",
                    RLPy.RGlobal.ForceViewportUpdate(),
                )
            )
            settle_cc_ui(1.0)
            capture = RLPy.RGlobal.CapturePixelStream()
            candidates = (
                list(capture)
                if isinstance(capture, (list, tuple))
                else [capture]
            )
            for candidate_index, candidate in enumerate(candidates):
                index = len(report["frame_candidates"])
                record = {
                    "capture_index": capture_index,
                    "candidate_index": candidate_index,
                    "index": index,
                    "python_type": type(candidate).__name__,
                    "repr": repr(candidate)[:500],
                }
                for attribute in (
                    "width",
                    "height",
                    "buffer_ptr",
                    "buffer",
                ):
                    try:
                        value = getattr(candidate, attribute)
                    except Exception as exc:
                        record[attribute + "_error"] = str(exc)
                        continue
                    if attribute == "buffer":
                        record["buffer_type"] = type(value).__name__
                        try:
                            record["buffer_length"] = len(value)
                        except Exception as exc:
                            record["buffer_length_error"] = str(exc)
                        continue
                    try:
                        record[attribute] = int(value)
                    except Exception:
                        record[attribute] = str(value)
                width = record.get("width")
                height = record.get("height")
                pointer = record.get("buffer_ptr")
                if (
                    isinstance(width, int)
                    and isinstance(height, int)
                    and isinstance(pointer, int)
                    and width > 0
                    and height > 0
                    and pointer > 0
                ):
                    byte_count = width * height * 4
                    raw = ctypes.string_at(pointer, byte_count)
                    record["buffer_sha256"] = hashlib.sha256(raw).hexdigest()
                    record["buffer_prefix_hex"] = raw[:64].hex()
                    image = QtGui.QImage(
                        raw,
                        width,
                        height,
                        width * 4,
                        QtGui.QImage.Format_ARGB32,
                    ).copy()
                    for suffix, candidate_image in (
                        ("argb32", image),
                        (
                            "argb32_vertical_flip",
                            image.mirrored(False, True),
                        ),
                    ):
                        image_path = os.path.join(
                            output_dir,
                            "pixel_stream_{}_{}.png".format(
                                index,
                                suffix,
                            )
                        )
                        if not candidate_image.save(image_path, "PNG"):
                            raise ReconstructionError(
                                "Unable to save pixel stream image: {}".format(
                                    image_path
                                )
                            )
                        captured_images.append(image_path)
                report["frame_candidates"].append(record)
        report["captured_images"] = captured_images
        report["success"] = bool(captured_images)
        if not report["success"]:
            raise ReconstructionError(
                "CapturePixelStream returned no convertible frame"
            )
    finally:
        report["disable_status"] = checked(
            "Disable viewport pixel stream",
            RLPy.RGlobal.EnablePixelStream(False),
        )
        if original_view_size is not None:
            report["restore_view_size_status"] = checked(
                "Restore pixel stream view size",
                RLPy.RGlobal.SetViewSize(*original_view_size),
            )
    report_path = os.path.join(output_dir, "pixel_stream_probe.json")
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir,
        "pixel_stream_probe_summary.json",
    )
    summary = {
        "diagnostic_mode": "pixel_stream_probe",
        "failure_count": 0,
        "finished_at": now(),
        "pixel_stream_probe_path": report_path,
        "requested_count": 1,
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def probe_current_viewport_widgets(output_dir):
    from shiboken2 import wrapInstance

    os.makedirs(output_dir, exist_ok=True)
    main_window = wrapInstance(
        int(RLPy.RUi.GetMainWindow()),
        QtWidgets.QMainWindow,
    )
    if main_window is None:
        raise ReconstructionError("Unable to wrap the CC main window")
    widgets = [main_window]
    central = main_window.centralWidget()
    if central is not None:
        widgets.append(central)
    widgets.extend(main_window.findChildren(QtWidgets.QWidget))
    records = []
    seen = set()
    for widget in widgets:
        try:
            width = int(widget.width())
            height = int(widget.height())
            visible = bool(widget.isVisible())
            class_name = str(widget.metaObject().className())
            object_name = str(widget.objectName())
            global_top_left = widget.mapToGlobal(QtCore.QPoint(0, 0))
        except Exception:
            continue
        if not visible or width < 200 or height < 200:
            continue
        key = (
            class_name,
            object_name,
            int(global_top_left.x()),
            int(global_top_left.y()),
            width,
            height,
        )
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "area": width * height,
                "class_name": class_name,
                "global_x": int(global_top_left.x()),
                "global_y": int(global_top_left.y()),
                "height": height,
                "object_name": object_name,
                "widget": widget,
                "width": width,
            }
        )
    records.sort(
        key=lambda item: (
            -item["area"],
            item["class_name"],
            item["object_name"],
        )
    )
    output_records = []
    for index, record in enumerate(records[:30]):
        widget = record.pop("widget")
        output = dict(record)
        output["index"] = index
        base = "widget_{:02d}_{}".format(
            index,
            "".join(
                character if character.isalnum() else "_"
                for character in record["class_name"]
            )[:60],
        )
        grab_path = os.path.join(output_dir, base + "_grab.png")
        pixmap = widget.grab()
        output["grab_is_null"] = bool(pixmap.isNull())
        if not pixmap.isNull() and pixmap.save(grab_path, "PNG"):
            output["grab_path"] = grab_path
        grab_framebuffer = getattr(widget, "grabFramebuffer", None)
        if callable(grab_framebuffer):
            framebuffer_path = os.path.join(
                output_dir,
                base + "_framebuffer.png",
            )
            try:
                image = grab_framebuffer()
                output["framebuffer_is_null"] = bool(image.isNull())
                if (
                    not image.isNull()
                    and image.save(framebuffer_path, "PNG")
                ):
                    output["framebuffer_path"] = framebuffer_path
            except Exception as exc:
                output["framebuffer_error"] = str(exc)
        output_records.append(output)
    report = {
        "captured_at": now(),
        "candidate_count": len(output_records),
        "diagnostic_mode": "viewport_widget_probe",
        "schema_version": 1,
        "widgets": output_records,
    }
    report_path = os.path.join(output_dir, "viewport_widget_probe.json")
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir,
        "viewport_widget_probe_summary.json",
    )
    summary = {
        "diagnostic_mode": "viewport_widget_probe",
        "failure_count": 0,
        "finished_at": now(),
        "requested_count": 1,
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
        "viewport_widget_probe_path": report_path,
    }
    write_json(summary, summary_path)
    return summary


def probe_current_native_windows(output_dir):
    import ctypes
    from ctypes import wintypes
    from PySide2 import QtGui
    from shiboken2 import wrapInstance

    os.makedirs(output_dir, exist_ok=True)
    main_window = wrapInstance(
        int(RLPy.RUi.GetMainWindow()),
        QtWidgets.QMainWindow,
    )
    if main_window is None:
        raise ReconstructionError("Unable to wrap the CC main window")
    main_hwnd = int(main_window.winId())
    if main_hwnd <= 0:
        raise ReconstructionError("Unable to resolve the CC main window")

    user32 = ctypes.windll.user32

    class WindowRect(ctypes.Structure):
        _fields_ = (
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        )

    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )
    hwnds = [main_hwnd]

    @enum_proc_type
    def collect_window(hwnd, unused_lparam):
        hwnds.append(int(hwnd))
        return True

    if not user32.EnumChildWindows(
        wintypes.HWND(main_hwnd),
        collect_window,
        0,
    ):
        error_code = ctypes.get_last_error()
        if error_code:
            raise ReconstructionError(
                "EnumChildWindows failed with error {}".format(error_code)
            )

    records = []
    seen = set()
    for hwnd in hwnds:
        if hwnd in seen:
            continue
        seen.add(hwnd)
        if not user32.IsWindow(wintypes.HWND(hwnd)):
            continue
        rectangle = WindowRect()
        if not user32.GetWindowRect(
            wintypes.HWND(hwnd),
            ctypes.byref(rectangle),
        ):
            continue
        width = int(rectangle.right - rectangle.left)
        height = int(rectangle.bottom - rectangle.top)
        visible = bool(user32.IsWindowVisible(wintypes.HWND(hwnd)))
        if not visible or width < 160 or height < 160:
            continue
        class_buffer = ctypes.create_unicode_buffer(512)
        title_buffer = ctypes.create_unicode_buffer(1024)
        user32.GetClassNameW(
            wintypes.HWND(hwnd),
            class_buffer,
            len(class_buffer),
        )
        user32.GetWindowTextW(
            wintypes.HWND(hwnd),
            title_buffer,
            len(title_buffer),
        )
        records.append(
            {
                "area": width * height,
                "class_name": class_buffer.value,
                "global_x": int(rectangle.left),
                "global_y": int(rectangle.top),
                "height": height,
                "hwnd": hwnd,
                "title": title_buffer.value,
                "width": width,
            }
        )

    records.sort(
        key=lambda item: (
            -item["area"],
            item["class_name"],
            item["hwnd"],
        )
    )
    output_records = []
    for index, record in enumerate(records[:40]):
        output = dict(record)
        center = QtCore.QPoint(
            record["global_x"] + record["width"] // 2,
            record["global_y"] + record["height"] // 2,
        )
        screen = QtGui.QGuiApplication.screenAt(center)
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            output["capture_error"] = "No QScreen is available"
            output_records.append(output)
            continue

        safe_class_name = "".join(
            character if character.isalnum() else "_"
            for character in record["class_name"]
        )[:60]
        base = "native_{:02d}_{}".format(index, safe_class_name)

        window_path = os.path.join(
            output_dir,
            base + "_window.png",
        )
        window_pixmap = screen.grabWindow(record["hwnd"])
        output["window_grab_is_null"] = bool(window_pixmap.isNull())
        if (
            not window_pixmap.isNull()
            and window_pixmap.save(window_path, "PNG")
        ):
            output["window_grab_path"] = window_path

        geometry = screen.geometry()
        screen_path = os.path.join(
            output_dir,
            base + "_screen_rect.png",
        )
        screen_pixmap = screen.grabWindow(
            0,
            record["global_x"] - int(geometry.x()),
            record["global_y"] - int(geometry.y()),
            record["width"],
            record["height"],
        )
        output["screen_grab_is_null"] = bool(screen_pixmap.isNull())
        if (
            not screen_pixmap.isNull()
            and screen_pixmap.save(screen_path, "PNG")
        ):
            output["screen_grab_path"] = screen_path
        output["screen_name"] = str(screen.name())
        output_records.append(output)

    report = {
        "captured_at": now(),
        "candidate_count": len(output_records),
        "diagnostic_mode": "native_window_probe",
        "main_hwnd": main_hwnd,
        "schema_version": 1,
        "windows": output_records,
    }
    report_path = os.path.join(output_dir, "native_window_probe.json")
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir,
        "native_window_probe_summary.json",
    )
    summary = {
        "diagnostic_mode": "native_window_probe",
        "failure_count": 0,
        "finished_at": now(),
        "native_window_probe_path": report_path,
        "requested_count": 1,
        "schema_version": 1,
        "started_at": report["captured_at"],
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def validate_library_document(library):
    if int(library.get("schema_version", -1)) != 1:
        raise ReconstructionError("Unsupported BodyFit library schema")
    presets = library.get("presets")
    if not isinstance(presets, list) or not presets:
        raise ReconstructionError("BodyFit library has no presets")
    ids = [item.get("preset_id") for item in presets]
    if len(ids) != len(set(ids)):
        raise ReconstructionError("BodyFit preset IDs are not unique")
    return presets


def _run_library_without_dialog_guard(
    library_path,
    output_dir,
    log,
    preset_ids=None,
):
    library_path = os.path.realpath(os.path.abspath(library_path))
    output_dir = os.path.realpath(os.path.abspath(output_dir))
    if not os.path.isfile(library_path):
        raise ReconstructionError("BodyFit library is missing: {}".format(library_path))
    if os.path.isdir(output_dir) and os.listdir(output_dir):
        raise ReconstructionError("Output directory exists and is not empty")
    os.makedirs(output_dir, exist_ok=True)
    library = read_json(library_path)
    all_presets = validate_library_document(library)
    if library.get("diagnostic_mode") == "source_project_load":
        log("Loading one source project without face or appearance operations")
        return probe_source_project_load(library, output_dir)
    if library.get("diagnostic_mode") == "avatar_preset_save":
        log("Saving and reapplying one AvatarPresetAll pilot")
        return probe_avatar_preset_save(library, output_dir)
    if library.get("diagnostic_mode") == "eye_state":
        log("Capturing current eye state without replacing the scene")
        return probe_current_eye_state(output_dir)
    if library.get("diagnostic_mode") == "eye_state_refresh":
        log("Refreshing and recapturing the current eye state")
        return probe_current_eye_state_refresh(output_dir)
    if library.get("diagnostic_mode") == "eye_tpose_restore":
        log("Restoring and recapturing current eye T-pose positions")
        return probe_current_eye_tpose_restore(library, output_dir)
    if library.get("diagnostic_mode") == "neutral_face_clip":
        log("Testing a reversible neutral face expression clip")
        return probe_current_neutral_face_clip(output_dir)
    if library.get("diagnostic_mode") == "face_pose_mode_refresh":
        log("Refreshing the current facial pose solver mode")
        return probe_current_face_pose_mode_refresh(output_dir)
    if library.get("diagnostic_mode") == "face_safety_cleanup":
        log("Testing current facial gaze cleanup and neutral recovery")
        return probe_current_face_safety_cleanup(
            output_dir,
            library.get("pose_ids"),
        )
    if library.get("diagnostic_mode") == "eye_expression_pose_apply":
        log("Applying an eye expression pose to the current scene")
        return apply_current_eye_expression_pose(library, output_dir)
    if library.get("diagnostic_mode") == "eye_morph_sweep":
        log("Rendering a reversible eye morph sweep on the current scene")
        return probe_current_eye_morph_sweep(library, output_dir)
    if library.get("diagnostic_mode") == "eye_morph_apply":
        log("Applying one eye alignment correction to the current scene")
        return apply_current_eye_alignment(library, output_dir)
    if library.get("diagnostic_mode") == "face_camera_sweep":
        log("Rendering a reversible face camera position sweep")
        return probe_face_camera_sweep(library, output_dir)
    if library.get("diagnostic_mode") == "official_expression_probe":
        log("Rendering an official CC expression on the current scene")
        return probe_current_official_expression(library, output_dir)
    if library.get("diagnostic_mode") == "head_preset_probe":
        log("Applying one head preset to the current scene")
        return probe_current_head_preset(library, output_dir)
    if library.get("diagnostic_mode") == "hair_shader_probe":
        log("Capturing current scalp-hair, brow, and beard shader signatures")
        return probe_current_hair_shaders(output_dir)
    if library.get("diagnostic_mode") == "hair_physics_probe":
        log("Capturing current scalp-hair physics state")
        return probe_current_hair_physics(output_dir)
    if library.get("diagnostic_mode") == "hair_motion_probe":
        log("Playing one official motion with scalp-hair physics")
        return probe_current_hair_motion(library, output_dir)
    if library.get("diagnostic_mode") == "hair_pigmentation_apply":
        log(
            "Applying and verifying shared scalp-hair, brow, and "
            "beard pigmentation"
        )
        return apply_current_hair_pigmentation(
            library, output_dir
        )
    if library.get("diagnostic_mode") == "wrinkle_profile_probe":
        log("Loading one wrinkle asset through the facial profile component")
        return probe_current_wrinkle_profile(library, output_dir)
    if library.get("diagnostic_mode") == "pixel_stream_probe":
        log("Capturing the current evaluated viewport pixel stream")
        return probe_current_pixel_stream(output_dir)
    if library.get("diagnostic_mode") == "viewport_widget_probe":
        log("Capturing candidate CC viewport widgets")
        return probe_current_viewport_widgets(output_dir)
    if library.get("diagnostic_mode") == "native_window_probe":
        log("Capturing candidate native CC viewport windows")
        return probe_current_native_windows(output_dir)
    if library.get("diagnostic_mode") == "skin_age_direct_matrix":
        log("Running the direct-source skin and age compatibility matrix")
        return probe_direct_skin_age_matrix(
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == "eyelash_direct_matrix":
        log("Running the direct-source eyelash compatibility matrix")
        return probe_direct_eyelash_matrix(
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    appearance_catalog = load_appearance_catalog(library)
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(preset_ids or [item["preset_id"] for item in all_presets])
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError("Selected preset IDs must be non-empty and unique")
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError("Unknown BodyFit preset IDs: {}".format(missing))

    started_at = now()
    results = []
    body_catalog_paths = {
        "male": os.path.join(output_dir, "catalogs", "male_body_catalog.json"),
        "female": os.path.join(output_dir, "catalogs", "female_body_catalog.json"),
    }
    face_catalog_paths = {
        "male": os.path.join(output_dir, "catalogs", "male_face_catalog.json"),
        "female": os.path.join(output_dir, "catalogs", "female_face_catalog.json"),
    }
    for index, preset_id in enumerate(selected_ids):
        log("START {}/{} {}".format(index + 1, len(selected_ids), preset_id))
        results.append(
            validate_preset(
                library,
                by_id[preset_id],
                os.path.join(output_dir, preset_id),
                log,
                body_catalog_paths.get(by_id[preset_id].get("sex")),
                face_catalog_paths.get(by_id[preset_id].get("sex")),
                appearance_catalog,
            )
        )
        QtWidgets.QApplication.processEvents()
    failures = [item for item in results if not item["success"]]
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "started_from_library": library_path,
        "library_id": library.get("library_id"),
        "appearance_catalog": {
            "path": appearance_catalog["path"],
            "catalog_id": appearance_catalog["catalog_id"],
        }
        if appearance_catalog
        else None,
        "requested_count": len(selected_ids),
        "success_count": len(results) - len(failures),
        "failure_count": len(failures),
        "success": not bool(failures) and len(results) == len(selected_ids),
        "body_catalogs": dict(
            (sex, path)
            for sex, path in body_catalog_paths.items()
            if os.path.isfile(path)
        ),
        "face_catalogs": dict(
            (sex, path)
            for sex, path in face_catalog_paths.items()
            if os.path.isfile(path)
        ),
        "results": results,
    }
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(summary, summary_path)
    summary["summary_path"] = summary_path
    return summary


def run_library(library_path, output_dir, log, preset_ids=None):
    undo_guard = ExactUndoWarningGuard()
    undo_guard.start()
    try:
        summary = _run_library_without_dialog_guard(
            library_path,
            output_dir,
            log,
            preset_ids,
        )
    finally:
        undo_guard.stop()
    if isinstance(summary, dict):
        summary["undo_warning_guard"] = undo_guard.report
        summary_path = summary.get("summary_path")
        if isinstance(summary_path, str) and os.path.isfile(summary_path):
            write_json(summary, summary_path)
    return summary


def main():
    answer = QtWidgets.QMessageBox.question(
        None,
        "Validate BodyFit Reconstruction",
        (
            "This replaces the current CC scene while rebuilding all BodyFit "
            "presets from parameters. Save unrelated work before continuing."
        ),
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
        QtWidgets.QMessageBox.Cancel,
    )
    if answer != QtWidgets.QMessageBox.Yes:
        return
    run_id = datetime.datetime.now().strftime(
        "adult_body_reconstruction_%Y%m%d_%H%M%S_%f"
    )
    output_dir = os.path.join(OUTPUT_ROOT, run_id)

    def log(message):
        print("[{}] {}".format(now(), message))
        QtWidgets.QApplication.processEvents()

    summary = run_library(DEFAULT_LIBRARY, output_dir, log)
    QtWidgets.QMessageBox.information(
        None,
        "BodyFit Reconstruction Finished",
        "success={}\n\n{}".format(summary["success"], summary["summary_path"]),
    )


if os.environ.get("CC_BODY_RECONSTRUCTOR_IMPORT_ONLY") != "1":
    main()
