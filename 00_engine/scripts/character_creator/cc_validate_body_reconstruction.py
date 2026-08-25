"""Rebuild canonical BodyFit presets on clean CC5 neutral bases and validate them."""

import collections
import copy
import datetime
import gc
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import time
import traceback

import RLPy
from PySide2 import QtCore, QtGui, QtWidgets


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DEFAULT_LIBRARY = os.path.join(SCRIPT_DIR, "cc_body_preset_library_v2.json")
DEFAULT_FACE_SEED_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_face_seed_library_v1.json"
)
DEFAULT_FACE_IDENTITY_POLICY = os.path.join(
    SCRIPT_DIR, "cc_face_identity_policy_v1.json"
)
OUTPUT_ROOT = (
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_body_reconstruction"
)
BODYFIT_STANDARD_PROJECT_ROOT = (
    r"D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project"
)
BODYFIT_HEAD_SCALE_MORPH_ID = "cc embed morphs/embed_full_head9"
REPLACE_DIALOG_GUARD_PATH = os.path.join(
    ENGINE_ROOT,
    "character_creator_bridge",
    "cc_replace_dialog_once.ps1",
)
UNDO_DIALOG_GUARD_PATH = os.path.join(
    ENGINE_ROOT,
    "character_creator_bridge",
    "cc_undo_dialog_guard.ps1",
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
DEFAULT_VIEWPORT_PREVIEW_WIDTH = 512
DEFAULT_VIEWPORT_PREVIEW_HEIGHT = 512
VIEWPORT_PREVIEW_WIDTH = DEFAULT_VIEWPORT_PREVIEW_WIDTH
VIEWPORT_PREVIEW_HEIGHT = DEFAULT_VIEWPORT_PREVIEW_HEIGHT
PIXEL_STREAM_PREVIEW_SIZE = 1024
PREVIEW_CAPTURE_MODE = "render_image"
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
NATURAL_SMILE_SUPPORT_ALIASES = {
    "cheek_raise_left": (
        "Eye_Cheek_Raise_L",
        "Eye_CheekRaise_L",
        "Cheek_Raise_L",
    ),
    "cheek_raise_right": (
        "Eye_Cheek_Raise_R",
        "Eye_CheekRaise_R",
        "Cheek_Raise_R",
    ),
    "squint_inner_left": (
        "Eye_Squint_Inner_L",
        "Eye_SquintInner_L",
        "Eye_Squint_L",
    ),
    "squint_inner_right": (
        "Eye_Squint_Inner_R",
        "Eye_SquintInner_R",
        "Eye_Squint_R",
    ),
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
    "face_material_quality_profile",
)
BODYFIT_PROPORTION_APPLICATION_ORDER = (
    "head_scale",
    "neck_height",
)
KNOWN_SIGNED_RUNTIME_MORPH_IDS = frozenset(
    (
        "2019-08-30-20-14-55_neck height",
        "2019-08-13-15-33-14_head width",
        "2019-08-13-16-00-36_head depth",
        "2019-08-13-15-25-44_skull height",
        "2019-08-13-15-26-49_skull width",
        "2019-08-13-15-27-43_skull depth",
        "2019-08-21-13-57-18_skull back depth",
        "2019-08-21-14-02-10_skull peak",
    )
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


class BlockingDialogError(ReconstructionError):
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
    for attempt in range(10):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.2 * (attempt + 1))


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


def capture_filtered_morph_catalog(avatar, terms):
    if not isinstance(terms, list) or any(
        not isinstance(item, str) or not item.strip() for item in terms
    ):
        raise ReconstructionError(
            "Morph catalog terms must be a list of non-empty strings"
        )
    normalized_terms = [item.strip().lower() for item in terms]
    component, catalog, categories = morph_catalog(avatar)
    entries = []
    for morph_id in sorted(catalog):
        source = catalog[morph_id]
        searchable = " ".join(
            [morph_id, source["display"]] + list(source["categories"])
        ).lower()
        if normalized_terms and not any(
            term in searchable for term in normalized_terms
        ):
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
                "default_weight": float(
                    component.GetShapingMorphWeight(morph_id)
                ),
            }
        )
    return {
        "schema_version": 1,
        "captured_at": now(),
        "catalog_morph_count": len(catalog),
        "category_count": len(categories),
        "filter_terms": terms,
        "matched_morph_count": len(entries),
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


def probe_resource_release(library, output_dir, log):
    """Release disposable scene/Python resources without restarting CC."""
    clear_scene = bool(library.get("clear_current_scene", False))
    before_avatars = list(RLPy.RScene.GetAvatars() or [])
    before = [
        {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
            "python_type": type(avatar).__name__,
        }
        for avatar in before_avatars
    ]

    if clear_scene:
        log("Removing {} disposable avatar(s) from the current scene".format(
            len(before_avatars)
        ))
        remove_current_avatars()
        for _ in range(5):
            QtWidgets.QApplication.processEvents()
            time.sleep(0.1)

    QtGui.QPixmapCache.clear()
    collected = []
    for _ in range(3):
        collected.append(int(gc.collect()))
        QtWidgets.QApplication.processEvents()
        time.sleep(0.1)

    after_avatars = list(RLPy.RScene.GetAvatars() or [])
    api_candidates = {}
    for owner_name in ("RGlobal", "RScene"):
        owner = getattr(RLPy, owner_name, None)
        api_candidates[owner_name] = sorted(
            name
            for name in dir(owner)
            if any(
                token in name.lower()
                for token in ("cache", "garbage", "memory", "purge", "release")
            )
        ) if owner is not None else []

    success = not clear_scene or not after_avatars
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "resource_release_probe",
        "success": success,
        "clear_current_scene": clear_scene,
        "before_avatars": before,
        "after_avatar_count": len(after_avatars),
        "removed_avatar_count": len(before_avatars) - len(after_avatars),
        "qt_pixmap_cache_cleared": True,
        "python_gc_collected_per_pass": collected,
        "public_release_api_candidates": api_candidates,
        "scope_note": (
            "This clears active scene references and Python/Qt caches only. "
            "CC renderer or asset-manager native caches may remain allocated."
        ),
    }
    report_path = os.path.join(output_dir, "resource_release_report.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    summary = {
        "schema_version": 1,
        "diagnostic_mode": "resource_release_probe",
        "phase": "complete" if success else "failed",
        "success": success,
        "failure_count": 0 if success else 1,
        "success_count": 1 if success else 0,
        "report_path": report_path,
        "summary_path": summary_path,
        "resource_release": report,
    }
    write_json(summary, summary_path)
    return summary


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


def allows_reported_bounds_probe(morph_id):
    return (
        morph_id.lower().startswith("cc embed morphs/")
        or morph_id in KNOWN_SIGNED_RUNTIME_MORPH_IDS
    )


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
    reported_out_of_bounds = (
        target < minimum - 1e-7 or target > maximum + 1e-7
    )
    if reported_out_of_bounds and not allows_reported_bounds_probe(morph_id):
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
        "reported_bounds_override": (
            reported_out_of_bounds
            and allows_reported_bounds_probe(morph_id)
        ),
        "previous": previous,
        "target": target,
    }


def apply_bodyfit_proportion_adjustment(
    avatar,
    preset,
    progress_callback=None,
):
    adjustment = preset.get("bodyfit_proportion_adjustment")
    if adjustment is None:
        return avatar, None
    if not isinstance(adjustment, dict):
        raise ReconstructionError(
            "bodyfit_proportion_adjustment must be an object"
        )
    decision_set_id = adjustment.get("decision_set_id")
    if not isinstance(decision_set_id, str) or not decision_set_id:
        raise ReconstructionError(
            "bodyfit_proportion_adjustment decision_set_id is missing"
        )
    application_order = adjustment.get("application_order")
    if application_order != list(BODYFIT_PROPORTION_APPLICATION_ORDER):
        raise ReconstructionError(
            "BodyFit proportion application order is not canonical"
        )
    targets = adjustment.get("targets")
    if not isinstance(targets, list) or len(targets) != len(
        BODYFIT_PROPORTION_APPLICATION_ORDER
    ):
        raise ReconstructionError(
            "BodyFit proportion adjustment requires two targets"
        )
    if [item.get("role") for item in targets] != list(
        BODYFIT_PROPORTION_APPLICATION_ORDER
    ):
        raise ReconstructionError(
            "BodyFit proportion targets differ from canonical order"
        )
    controlled_ids = []
    for item in targets:
        morph_id = item.get("id")
        target = item.get("target")
        if not isinstance(morph_id, str) or not morph_id:
            raise ReconstructionError(
                "BodyFit proportion target Morph ID is missing"
            )
        if (
            isinstance(target, bool)
            or not isinstance(target, (int, float))
            or not math.isfinite(float(target))
        ):
            raise ReconstructionError(
                "BodyFit proportion target must be finite"
            )
        controlled_ids.append(morph_id)
    if len(controlled_ids) != len(set(controlled_ids)):
        raise ReconstructionError(
            "BodyFit proportion target Morph IDs are duplicated"
        )

    component, catalog, unused_categories = morph_catalog(avatar)
    missing_ids = sorted(set(controlled_ids) - set(catalog))
    if missing_ids:
        raise ReconstructionError(
            "BodyFit proportion Morphs are unavailable: {}".format(
                missing_ids
            )
        )
    before_vectors = capture_vectors(avatar)
    protected_before = vectors_excluding_morphs_fingerprint(
        before_vectors,
        controlled_ids,
    )
    eye_before = capture_eye_integrity_state(avatar)
    applications = []
    for item in targets:
        role = item["role"]
        if progress_callback is not None:
            progress_callback(
                "bodyfit_proportion_{}".format(role),
                {
                    "bodyfit_id": preset.get("bodyfit_id"),
                    "target": float(item["target"]),
                },
            )
        applications.append(
            dict(
                apply_single_morph_weight(
                    avatar,
                    item["id"],
                    item["target"],
                    "BodyFit proportion {}".format(role),
                ),
                role=role,
                ui_value=item.get("ui_value"),
            )
        )
    force_avatar_scene_evaluation(avatar)
    after_vectors = capture_vectors(avatar)
    protected_after = vectors_excluding_morphs_fingerprint(
        after_vectors,
        controlled_ids,
    )
    eye_after = capture_eye_integrity_state(avatar)
    eye_structure_preserved = (
        eye_integrity_structure_signature(eye_before)
        == eye_integrity_structure_signature(eye_after)
    )
    if protected_after != protected_before:
        raise ReconstructionError(
            "BodyFit proportion adjustment changed protected Morphs"
        )
    if not eye_structure_preserved:
        raise ReconstructionError(
            "BodyFit proportion adjustment changed eye structure"
        )
    return avatar, {
        "application_order": list(application_order),
        "applications": applications,
        "bodyfit_id": preset.get("bodyfit_id"),
        "canonical_order_verified": True,
        "controlled_morph_ids": controlled_ids,
        "decision_set_id": decision_set_id,
        "eye_structure_preserved": True,
        "protected_morph_fingerprint_after": protected_after,
        "protected_morph_fingerprint_before": protected_before,
        "protected_morphs_unchanged": True,
        "targets_match": all(
            abs(float(item["actual"]) - float(item["target"])) <= 1e-6
            for item in applications
        ),
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


def avatar_material_structure(avatar):
    component = avatar.GetMaterialComponent()
    if component is None:
        raise ReconstructionError("Avatar has no material component")
    mesh_names = sorted(str(name) for name in (avatar.GetMeshNames() or []))
    records = []
    for mesh_name in mesh_names:
        material_names = sorted(
            str(name)
            for name in (component.GetMaterialNames(mesh_name) or [])
        )
        for material_name in material_names:
            records.append(
                {
                    "material": material_name,
                    "mesh": mesh_name,
                    "shader": str(
                        component.GetShader(mesh_name, material_name)
                    ),
                }
            )
    encoded = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return {
        "digest": hashlib.sha256(encoded).hexdigest(),
        "material_count": len(records),
        "mesh_count": len(mesh_names),
        "mesh_names": mesh_names,
        "records": records,
    }


def face_material_domain(mesh_name, material_name):
    mesh = str(mesh_name).lower()
    material = str(material_name).lower()
    if mesh == "cc_base_eye":
        return "cornea" if "cornea" in material else "eye_base"
    if mesh == "cc_base_eyeocclusion":
        return "eye_occlusion"
    if mesh == "cc_base_tearline":
        return "tearline"
    if mesh == "cc_base_body":
        body_domains = {
            "std_skin_head": "skin_head",
            "std_skin_body": "skin_body",
            "std_skin_arm": "skin_arm",
            "std_skin_leg": "skin_leg",
        }
        return body_domains.get(material)
    return None


def probe_current_face_material_parameters(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Face material probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    component = avatar.GetMaterialComponent()
    if component is None:
        raise ReconstructionError("Face material probe found no material component")
    property_methods = (
        "GetAmbientColor",
        "GetDiffuseColor",
        "GetSpecularColor",
        "GetGlossinessWeight",
        "GetSpecularWeight",
        "GetSelfIlluminationWeight",
        "GetOpacity",
        "GetRefraction",
        "GetReflection",
    )
    records = []
    observation_errors = []
    mesh_names = sorted(set(str(name) for name in (avatar.GetMeshNames() or [])))
    for mesh_name in mesh_names:
        material_names = sorted(
            set(
                str(name)
                for name in (component.GetMaterialNames(mesh_name) or [])
            )
        )
        for material_name in material_names:
            domain = face_material_domain(mesh_name, material_name)
            if domain is None:
                continue
            record = {
                "domain": domain,
                "mesh": mesh_name,
                "material": material_name,
                "shader": str(component.GetShader(mesh_name, material_name)),
                "properties": {},
                "shader_parameters": {},
            }
            for method_name in property_methods:
                try:
                    record["properties"][method_name] = material_call(
                        component,
                        method_name,
                        mesh_name,
                        material_name,
                    )
                except Exception as exc:
                    observation_errors.append(
                        {
                            "domain": domain,
                            "mesh": mesh_name,
                            "material": material_name,
                            "stage": method_name,
                            "error": str(exc),
                        }
                    )
            try:
                parameter_names = sorted(
                    set(
                        str(name)
                        for name in (
                            component.GetShaderParameterNames(
                                mesh_name,
                                material_name,
                            )
                            or []
                        )
                    )
                )
            except Exception as exc:
                parameter_names = []
                observation_errors.append(
                    {
                        "domain": domain,
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
                            mesh_name,
                            material_name,
                            parameter_name,
                        )
                    )
                except Exception as exc:
                    observation_errors.append(
                        {
                            "domain": domain,
                            "mesh": mesh_name,
                            "material": material_name,
                            "stage": "shader_parameter:{}".format(parameter_name),
                            "error": str(exc),
                        }
                    )
            records.append(record)
    required_domains = {
        "cornea",
        "eye_base",
        "eye_occlusion",
        "tearline",
        "skin_head",
        "skin_body",
        "skin_arm",
        "skin_leg",
    }
    observed_domains = set(record["domain"] for record in records)
    missing_domains = sorted(required_domains - observed_domains)
    if missing_domains:
        raise ReconstructionError(
            "Face material probe is missing domains: {}".format(missing_domains)
        )
    payload = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "face_material_parameter_probe",
        "scene_policy": "read_only",
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
            "python_type": type(avatar).__name__,
        },
        "domain_count": len(observed_domains),
        "domains": sorted(observed_domains),
        "record_count": len(records),
        "records": records,
        "observation_error_count": len(observation_errors),
        "observation_errors": observation_errors,
        "eye_integrity": capture_eye_integrity_state(avatar),
    }
    inventory_path = os.path.join(
        output_dir,
        "face_material_parameters.json",
    )
    write_json(payload, inventory_path)
    summary_path = os.path.join(output_dir, "validation_result.json")
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": payload["captured_at"],
        "finished_at": now(),
        "requested_count": len(required_domains),
        "success_count": len(required_domains),
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "face_material_parameter_probe",
        "face_material_parameters_path": inventory_path,
        "summary_path": summary_path,
        "scene_policy": "read_only",
    }
    write_json(summary, summary_path)
    return summary


def face_material_numeric_value(component, mesh_name, material_name, parameter_name):
    value = material_value(
        component.GetShaderParameter(
            mesh_name,
            material_name,
            parameter_name,
        )
    )
    if (
        not isinstance(value, list)
        or not value
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        raise ReconstructionError(
            "Face material parameter is not numeric: {} {} {} {}".format(
                mesh_name,
                material_name,
                parameter_name,
                value,
            )
        )
    return [float(item) for item in value]


def face_material_values_match(left, right, tolerance=1e-5):
    return len(left) == len(right) and all(
        abs(float(a) - float(b)) <= tolerance
        for a, b in zip(left, right)
    )


def apply_face_material_quality_profile(avatar, reference):
    if not isinstance(reference, dict):
        raise ReconstructionError(
            "Face material quality profile reference must be an object"
        )
    profile_path = canonical_existing_file(
        reference.get("path"),
        "Face material quality profile",
    )
    actual_sha256 = sha256_file(profile_path)
    expected_sha256 = reference.get("sha256")
    if expected_sha256 and actual_sha256 != expected_sha256:
        raise ReconstructionError("Face material quality profile hash changed")
    profile = read_json(profile_path)
    expected_profile_id = reference.get("profile_id")
    required_status = reference.get("required_status")
    if profile.get("profile_id") != expected_profile_id:
        raise ReconstructionError("Face material quality profile ID changed")
    if profile.get("status") != required_status:
        raise ReconstructionError("Face material quality profile status changed")
    changes = profile.get("recommended_changes")
    if not isinstance(changes, list) or not changes:
        raise ReconstructionError(
            "Face material quality profile has no recommended changes"
        )

    component = avatar.GetMaterialComponent()
    if component is None:
        raise ReconstructionError(
            "Face material quality application found no material component"
        )
    material_slots = []
    for mesh_name in sorted(set(str(name) for name in (avatar.GetMeshNames() or []))):
        for material_name in sorted(
            set(str(name) for name in (component.GetMaterialNames(mesh_name) or []))
        ):
            domain = face_material_domain(mesh_name, material_name)
            if domain is None:
                continue
            material_slots.append(
                {
                    "domain": domain,
                    "mesh": mesh_name,
                    "material": material_name,
                    "parameter_names": set(
                        str(name)
                        for name in (
                            component.GetShaderParameterNames(
                                mesh_name, material_name
                            )
                            or []
                        )
                    ),
                }
            )

    normalized_changes = []
    seen_changes = set()
    touched = {}
    for change in changes:
        domain = change.get("domain") if isinstance(change, dict) else None
        parameter = (
            change.get("parameter") if isinstance(change, dict) else None
        )
        value = (
            change.get("recommended_value")
            if isinstance(change, dict)
            else None
        )
        if (
            not isinstance(domain, str)
            or not domain
            or not isinstance(parameter, str)
            or not parameter
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ReconstructionError(
                "Face material quality change is invalid"
            )
        key = (domain, parameter)
        if key in seen_changes:
            raise ReconstructionError(
                "Face material quality change is duplicated: {} {}".format(
                    domain, parameter
                )
            )
        seen_changes.add(key)
        matching_slots = [
            slot
            for slot in material_slots
            if slot["domain"] == domain
            and parameter in slot["parameter_names"]
        ]
        if not matching_slots:
            raise ReconstructionError(
                "No face material slot matches {} {}".format(
                    domain, parameter
                )
            )
        normalized_changes.append(
            {
                "domain": domain,
                "parameter": parameter,
                "value": [float(value)],
                "documented_baseline": change.get("baseline_value"),
                "matching_slots": matching_slots,
            }
        )
        for slot in matching_slots:
            material_key = (slot["mesh"], slot["material"], parameter)
            if material_key not in touched:
                touched[material_key] = face_material_numeric_value(
                    component,
                    material_key[0],
                    material_key[1],
                    material_key[2],
                )

    eye_before = capture_eye_integrity_state(avatar)
    applied = []

    def restore_touched():
        for material_key, before in sorted(touched.items()):
            checked(
                "Restore failed face quality application {} {} {}".format(
                    *material_key
                ),
                component.SetShaderParameter(
                    material_key[0],
                    material_key[1],
                    material_key[2],
                    tuple(before),
                ),
            )

    try:
        for change in normalized_changes:
            for slot in change["matching_slots"]:
                checked(
                    "Apply face quality {} {}".format(
                        slot["material"], change["parameter"]
                    ),
                    component.SetShaderParameter(
                        slot["mesh"],
                        slot["material"],
                        change["parameter"],
                        tuple(change["value"]),
                    ),
                )
                actual = face_material_numeric_value(
                    component,
                    slot["mesh"],
                    slot["material"],
                    change["parameter"],
                )
                if not face_material_values_match(actual, change["value"]):
                    raise ReconstructionError(
                        "Face material quality write did not round-trip: "
                        "{} {}".format(
                            slot["material"], change["parameter"]
                        )
                    )
                material_key = (
                    slot["mesh"],
                    slot["material"],
                    change["parameter"],
                )
                applied.append(
                    {
                        "after": actual,
                        "before": touched[material_key],
                        "documented_baseline": change[
                            "documented_baseline"
                        ],
                        "domain": change["domain"],
                        "material": slot["material"],
                        "mesh": slot["mesh"],
                        "parameter": change["parameter"],
                    }
                )
        force_avatar_scene_evaluation(avatar)
        eye_after = capture_eye_integrity_state(avatar)
        eye_integrity = compare_neutral_eye_states(
            eye_before,
            eye_after,
            include_world=True,
        )
        if not eye_integrity.get("matches"):
            raise ReconstructionError(
                "Face material quality application changed eye geometry"
            )
    except Exception:
        restore_touched()
        force_avatar_scene_evaluation(avatar)
        raise

    return {
        "application_order": profile.get("application_order"),
        "applied": applied,
        "applied_slot_count": len(applied),
        "eye_integrity": eye_integrity,
        "profile_id": profile["profile_id"],
        "profile_path": profile_path,
        "profile_sha256": actual_sha256,
        "profile_status": profile["status"],
        "success": True,
    }


def probe_current_face_material_visual_matrix(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    config = library.get("face_material_visual_matrix") or {}
    if not isinstance(config, dict):
        raise ReconstructionError("face_material_visual_matrix must be an object")
    camera_path = canonical_existing_file(
        config.get("camera_path"),
        "Face material matrix camera",
    )
    restore_lightroom = canonical_existing_file(
        config.get("restore_lightroom"),
        "Face material matrix restore Lightroom",
    )
    lights = config.get("lights")
    profiles = config.get("profiles")
    if not isinstance(lights, list) or not lights:
        raise ReconstructionError("Face material matrix lights are missing")
    if not isinstance(profiles, list) or not profiles:
        raise ReconstructionError("Face material matrix profiles are missing")
    normalized_lights = []
    seen_ids = set()
    for item in lights:
        light_id = item.get("id") if isinstance(item, dict) else None
        if (
            not isinstance(light_id, str)
            or not light_id
            or light_id in seen_ids
        ):
            raise ReconstructionError("Face material matrix light IDs must be unique")
        seen_ids.add(light_id)
        normalized_lights.append(
            {
                "id": light_id,
                "path": canonical_existing_file(
                    item.get("path"),
                    "Face material matrix light {}".format(light_id),
                ),
            }
        )
    normalized_profiles = []
    seen_ids = set()
    for item in profiles:
        profile_id = item.get("id") if isinstance(item, dict) else None
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id in seen_ids
        ):
            raise ReconstructionError("Face material matrix profile IDs must be unique")
        seen_ids.add(profile_id)
        changes = item.get("changes", [])
        if not isinstance(changes, list):
            raise ReconstructionError(
                "Face material profile changes must be a list: {}".format(profile_id)
            )
        normalized_changes = []
        for change in changes:
            domain = change.get("domain") if isinstance(change, dict) else None
            parameter = change.get("parameter") if isinstance(change, dict) else None
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(domain, str) or not domain:
                raise ReconstructionError("Face material change has no domain")
            if not isinstance(parameter, str) or not parameter:
                raise ReconstructionError("Face material change has no parameter")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = [float(value)]
            if (
                not isinstance(value, list)
                or not value
                or any(
                    isinstance(number, bool) or not isinstance(number, (int, float))
                    for number in value
                )
            ):
                raise ReconstructionError(
                    "Face material change value must be numeric: {} {}".format(
                        profile_id,
                        parameter,
                    )
                )
            normalized_changes.append(
                {
                    "domain": domain,
                    "parameter": parameter,
                    "value": [float(number) for number in value],
                }
            )
        normalized_profiles.append(
            {
                "id": profile_id,
                "label": str(item.get("label") or profile_id),
                "changes": normalized_changes,
            }
        )
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Face material matrix expected one avatar, found {}".format(len(avatars))
        )
    component = avatar.GetMaterialComponent()
    if component is None:
        raise ReconstructionError("Face material matrix found no material component")
    face_position = _quality_benchmark_position(
        config.get("face_position", [0.0, 8.0, 6.0]),
        "face_material_visual_matrix.face_position",
    )
    yaw_degrees = float(config.get("yaw_degrees", 90.0))
    settle_seconds = float(config.get("light_settle_seconds", 1.0))
    if settle_seconds < 0.0 or settle_seconds > 30.0:
        raise ReconstructionError("Face material matrix settle time is invalid")
    initial_position = {
        "x": _transform_float(avatar, "Position/PositionX"),
        "y": _transform_float(avatar, "Position/PositionY"),
        "z": _transform_float(avatar, "Position/PositionZ"),
    }
    initial_yaw_radians = _transform_float(avatar, "Rotation/RotationZ")
    initial_camera = RLPy.RScene.GetCurrentCamera()
    initial_eye_integrity = capture_eye_integrity_state(avatar)
    material_slots = []
    for mesh_name in sorted(set(str(name) for name in (avatar.GetMeshNames() or []))):
        for material_name in sorted(
            set(str(name) for name in (component.GetMaterialNames(mesh_name) or []))
        ):
            domain = face_material_domain(mesh_name, material_name)
            if domain is None:
                continue
            parameter_names = set(
                str(name)
                for name in (
                    component.GetShaderParameterNames(mesh_name, material_name) or []
                )
            )
            material_slots.append(
                {
                    "domain": domain,
                    "mesh": mesh_name,
                    "material": material_name,
                    "parameter_names": parameter_names,
                }
            )
    touched = {}
    for profile in normalized_profiles:
        for change in profile["changes"]:
            matching_slots = [
                slot
                for slot in material_slots
                if slot["domain"] == change["domain"]
                and change["parameter"] in slot["parameter_names"]
            ]
            if not matching_slots:
                raise ReconstructionError(
                    "No face material slot matches {} {}".format(
                        change["domain"],
                        change["parameter"],
                    )
                )
            for slot in matching_slots:
                key = (slot["mesh"], slot["material"], change["parameter"])
                if key not in touched:
                    touched[key] = face_material_numeric_value(
                        component,
                        key[0],
                        key[1],
                        key[2],
                    )

    def restore_touched_parameters():
        for key, before in sorted(touched.items()):
            checked(
                "Restore face material {} {} {}".format(*key),
                component.SetShaderParameter(key[0], key[1], key[2], tuple(before)),
            )

    report = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "face_material_visual_matrix",
        "scene_policy": "reversible_material_and_light_matrix",
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "camera_path": camera_path,
        "restore_lightroom": restore_lightroom,
        "face_position": face_position,
        "yaw_degrees": yaw_degrees,
        "initial_position": initial_position,
        "initial_eye_integrity": initial_eye_integrity,
        "lights": normalized_lights,
        "profiles": [],
        "touched_parameter_count": len(touched),
        "touched_before": [
            {
                "mesh": key[0],
                "material": key[1],
                "parameter": key[2],
                "value": value,
            }
            for key, value in sorted(touched.items())
        ],
    }
    try:
        checked("Load face material matrix camera", RLPy.RFileIO.LoadFile(camera_path))
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1],
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, yaw_degrees)
        checked(
            "Set face material matrix start time",
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
        )
        for profile in normalized_profiles:
            restore_touched_parameters()
            applied = []
            for change in profile["changes"]:
                for slot in material_slots:
                    if (
                        slot["domain"] != change["domain"]
                        or change["parameter"] not in slot["parameter_names"]
                    ):
                        continue
                    checked(
                        "Apply face material {} {} {}".format(
                            profile["id"],
                            slot["material"],
                            change["parameter"],
                        ),
                        component.SetShaderParameter(
                            slot["mesh"],
                            slot["material"],
                            change["parameter"],
                            tuple(change["value"]),
                        ),
                    )
                    actual = face_material_numeric_value(
                        component,
                        slot["mesh"],
                        slot["material"],
                        change["parameter"],
                    )
                    if not face_material_values_match(actual, change["value"]):
                        raise ReconstructionError(
                            "Face material write did not round-trip: {} {} {} {}".format(
                                profile["id"],
                                slot["material"],
                                change["parameter"],
                                actual,
                            )
                        )
                    applied.append(
                        {
                            "domain": change["domain"],
                            "mesh": slot["mesh"],
                            "material": slot["material"],
                            "parameter": change["parameter"],
                            "value": actual,
                        }
                    )
            profile_record = {
                "id": profile["id"],
                "label": profile["label"],
                "changes": profile["changes"],
                "applied": applied,
                "captures": [],
            }
            for light in normalized_lights:
                checked(
                    "Load face material matrix light {}".format(light["id"]),
                    RLPy.RFileIO.LoadFile(light["path"]),
                )
                settle_cc_ui(settle_seconds)
                checked(
                    "Reload face material matrix camera for {}".format(
                        light["id"]
                    ),
                    RLPy.RFileIO.LoadFile(camera_path),
                )
                set_avatar_position(
                    avatar,
                    position_x=face_position[0],
                    position_y=face_position[1],
                    position_z=face_position[2],
                )
                set_avatar_yaw(avatar, yaw_degrees)
                checked(
                    "Reset face material matrix time for {}".format(
                        light["id"]
                    ),
                    RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
                )
                force_avatar_scene_evaluation(avatar)
                image_path = os.path.join(
                    output_dir,
                    "{}_{}.png".format(profile["id"], light["id"]),
                )
                render_preview(image_path, RLPy.RGlobal.GetStartTime())
                profile_record["captures"].append(
                    {
                        "light_id": light["id"],
                        "path": image_path,
                        "bytes": os.path.getsize(image_path),
                    }
                )
            report["profiles"].append(profile_record)
    finally:
        restore_touched_parameters()
        checked(
            "Restore face material matrix Lightroom",
            RLPy.RFileIO.LoadFile(restore_lightroom),
        )
        settle_cc_ui(settle_seconds)
        set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
        set_avatar_position(
            avatar,
            position_x=initial_position["x"],
            position_y=initial_position["y"],
            position_z=initial_position["z"],
        )
        if initial_camera is not None:
            checked(
                "Restore camera after face material matrix",
                RLPy.RScene.SetCurrentCamera(initial_camera),
            )
        force_avatar_scene_evaluation(avatar)
    restoration_mismatches = []
    for key, before in sorted(touched.items()):
        actual = face_material_numeric_value(
            component,
            key[0],
            key[1],
            key[2],
        )
        if not face_material_values_match(actual, before):
            restoration_mismatches.append(
                {
                    "mesh": key[0],
                    "material": key[1],
                    "parameter": key[2],
                    "expected": before,
                    "actual": actual,
                }
            )
    report["restoration"] = {
        "material_mismatches": restoration_mismatches,
        "materials_restored": not restoration_mismatches,
        "eye_integrity": compare_neutral_eye_states(
            initial_eye_integrity,
            capture_eye_integrity_state(avatar),
            include_world=True,
        ),
    }
    report["success"] = (
        not restoration_mismatches
        and report["restoration"]["eye_integrity"]["matches"]
    )
    report["finished_at"] = now()
    report_path = os.path.join(output_dir, "face_material_visual_matrix.json")
    write_json(report, report_path)
    summary_path = os.path.join(output_dir, "validation_result.json")
    capture_count = sum(len(item["captures"]) for item in report["profiles"])
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": report["finished_at"],
        "requested_count": capture_count,
        "success_count": capture_count if report["success"] else 0,
        "failure_count": 0 if report["success"] else capture_count,
        "success": report["success"],
        "diagnostic_mode": "face_material_visual_matrix",
        "face_material_visual_matrix_path": report_path,
        "summary_path": summary_path,
        "scene_policy": report["scene_policy"],
    }
    write_json(summary, summary_path)
    return summary


def probe_face_material_cross_skin_matrix(library, output_dir, log):
    os.makedirs(output_dir, exist_ok=True)
    config = library.get("face_material_cross_skin_matrix") or {}
    if not isinstance(config, dict):
        raise ReconstructionError(
            "face_material_cross_skin_matrix must be an object"
        )
    subjects = config.get("subjects")
    views = config.get("views")
    matrix_template = config.get("matrix")
    if not isinstance(subjects, list) or not subjects:
        raise ReconstructionError("Cross-skin subjects are missing")
    if not isinstance(views, list) or not views:
        raise ReconstructionError("Cross-skin views are missing")
    if not isinstance(matrix_template, dict):
        raise ReconstructionError("Cross-skin material matrix is missing")

    expected_subject_ids = {
        "female_light",
        "female_dark",
        "male_light",
        "male_dark",
    }
    subject_ids = [
        item.get("id") if isinstance(item, dict) else None
        for item in subjects
    ]
    if (
        len(subject_ids) != len(set(subject_ids))
        or set(subject_ids) != expected_subject_ids
    ):
        raise ReconstructionError(
            "Cross-skin subjects must be female_light, female_dark, "
            "male_light, and male_dark exactly once"
        )
    normalized_views = []
    seen_view_ids = set()
    for item in views:
        view_id = item.get("id") if isinstance(item, dict) else None
        yaw_degrees = item.get("yaw_degrees") if isinstance(item, dict) else None
        if (
            not isinstance(view_id, str)
            or not view_id
            or view_id in seen_view_ids
            or isinstance(yaw_degrees, bool)
            or not isinstance(yaw_degrees, (int, float))
        ):
            raise ReconstructionError("Cross-skin view definition is invalid")
        seen_view_ids.add(view_id)
        normalized_views.append(
            {"id": view_id, "yaw_degrees": float(yaw_degrees)}
        )

    restore_project = canonical_existing_file(
        config.get("restore_project"),
        "Cross-skin restore project",
    )
    load_settle_seconds = float(config.get("load_settle_seconds", 8.0))
    skin_settle_seconds = float(config.get("skin_settle_seconds", 3.0))
    if not 0.0 <= load_settle_seconds <= 60.0:
        raise ReconstructionError("Cross-skin project settle time is invalid")
    if not 0.0 <= skin_settle_seconds <= 60.0:
        raise ReconstructionError("Cross-skin asset settle time is invalid")

    normalized_subjects = []
    for item in subjects:
        subject_id = item["id"]
        sex = item.get("sex")
        tone_class = item.get("tone_class")
        if sex not in ("female", "male"):
            raise ReconstructionError(
                "Cross-skin subject has invalid sex: {}".format(subject_id)
            )
        if tone_class not in ("light", "dark"):
            raise ReconstructionError(
                "Cross-skin subject has invalid tone class: {}".format(
                    subject_id
                )
            )
        if subject_id != "{}_{}".format(sex, tone_class):
            raise ReconstructionError(
                "Cross-skin subject ID does not match its labels: {}".format(
                    subject_id
                )
            )
        source_project = canonical_existing_file(
            item.get("source_project"),
            "Cross-skin source project {}".format(subject_id),
        )
        skin_asset = canonical_existing_file(
            item.get("skin_asset"),
            "Cross-skin asset {}".format(subject_id),
        )
        camera_path = canonical_existing_file(
            item.get("camera_path"),
            "Cross-skin camera {}".format(subject_id),
        )
        expected_source_sha256 = item.get("source_project_sha256")
        expected_skin_sha256 = item.get("skin_asset_sha256")
        actual_source_sha256 = sha256_file(source_project)
        actual_skin_sha256 = sha256_file(skin_asset)
        if (
            expected_source_sha256
            and actual_source_sha256 != expected_source_sha256
        ):
            raise ReconstructionError(
                "Cross-skin source project hash changed: {}".format(subject_id)
            )
        if expected_skin_sha256 and actual_skin_sha256 != expected_skin_sha256:
            raise ReconstructionError(
                "Cross-skin asset hash changed: {}".format(subject_id)
            )
        normalized_subjects.append(
            {
                "camera_path": camera_path,
                "id": subject_id,
                "sex": sex,
                "skin_asset": skin_asset,
                "skin_asset_sha256": actual_skin_sha256,
                "skin_display_name": str(
                    item.get("skin_display_name") or os.path.basename(skin_asset)
                ),
                "source_project": source_project,
                "source_project_sha256": actual_source_sha256,
                "tone_class": tone_class,
            }
        )

    started_at = now()
    report_path = os.path.join(
        output_dir, "face_material_cross_skin_matrix.json"
    )
    summary_path = os.path.join(output_dir, "validation_result.json")
    progress_path = os.path.join(output_dir, "progress.json")
    cases = []
    run_error = None
    restoration = {
        "attempted": False,
        "project": restore_project,
        "success": False,
    }

    def mark(subject_id, phase, detail=None):
        write_json(
            {
                "detail": detail,
                "phase": phase,
                "schema_version": 1,
                "subject_id": subject_id,
                "updated_at": now(),
            },
            progress_path,
        )

    try:
        for index, subject in enumerate(normalized_subjects, 1):
            subject_id = subject["id"]
            log(
                "CROSS SKIN {}/{} {}".format(
                    index, len(normalized_subjects), subject_id
                )
            )
            case_dir = os.path.join(output_dir, subject_id)
            os.makedirs(case_dir, exist_ok=False)
            case = {
                "id": subject_id,
                "sex": subject["sex"],
                "tone_class": subject["tone_class"],
                "source_project": subject["source_project"],
                "source_project_sha256": subject["source_project_sha256"],
                "skin_asset": subject["skin_asset"],
                "skin_asset_sha256": subject["skin_asset_sha256"],
                "skin_display_name": subject["skin_display_name"],
                "views": [],
                "success": False,
            }
            try:
                mark(subject_id, "load_source_project")
                source_status, source_dialogs = load_file_with_optional_undo_warning(
                    subject["source_project"],
                    "Load cross-skin source {}".format(subject_id),
                )
                settle_cc_ui(load_settle_seconds)
                avatar, avatars = resolve_avatar()
                if len(avatars) != 1:
                    raise ReconstructionError(
                        "Cross-skin {} expected one avatar, found {}".format(
                            subject_id, len(avatars)
                        )
                    )
                avatar_id = scene_object_id(avatar)
                vectors_before_skin = capture_vectors(avatar)
                eye_before_skin = capture_eye_integrity_state(avatar)
                eye_parts_before_skin = direct_avatar_part_signature(
                    direct_avatar_part_records(avatar, "eyes")
                )
                material_before_skin = avatar_material_fingerprint(avatar)

                mark(subject_id, "load_skin", {"path": subject["skin_asset"]})
                RLPy.RScene.SelectObject(avatar)
                skin_status, skin_dialogs = load_file_with_skin_material_dialog(
                    subject["skin_asset"],
                    "Load cross-skin asset {}".format(subject_id),
                )
                settle_cc_ui(skin_settle_seconds)
                avatar_after_skin, avatars_after_skin = resolve_avatar()
                if (
                    len(avatars_after_skin) != 1
                    or scene_object_id(avatar_after_skin) != avatar_id
                ):
                    raise ReconstructionError(
                        "Avatar changed while applying cross-skin asset {}".format(
                            subject_id
                        )
                    )
                avatar = avatar_after_skin
                material_after_skin = avatar_material_fingerprint(avatar)
                material_verification = evaluate_skin_material_change(
                    material_before_skin,
                    material_after_skin,
                )
                vectors_after_skin = capture_vectors(avatar)
                morph_differences = vector_differences(
                    vectors_before_skin,
                    vectors_after_skin,
                )
                eye_parts_after_skin = direct_avatar_part_signature(
                    direct_avatar_part_records(avatar, "eyes")
                )
                eye_after_skin = capture_eye_integrity_state(avatar)
                eye_geometry = compare_neutral_eye_states(
                    eye_before_skin,
                    eye_after_skin,
                    include_world=True,
                )
                case["source_load"] = {
                    "dialogs": source_dialogs,
                    "status": source_status,
                }
                case["skin_load"] = {
                    "dialogs": skin_dialogs,
                    "status": skin_status,
                }
                case["skin_verification"] = {
                    "eye_avatar_parts_preserved": (
                        eye_parts_after_skin == eye_parts_before_skin
                    ),
                    "eye_geometry": eye_geometry,
                    "material": material_verification,
                    "morph_differences": morph_differences,
                    "morphs_preserved": (
                        not morph_differences
                        and vectors_match(vectors_before_skin, vectors_after_skin)
                    ),
                }
                if material_verification["status"] == "failed":
                    raise ReconstructionError(material_verification["reason"])
                if not case["skin_verification"]["morphs_preserved"]:
                    raise ReconstructionError(
                        "Cross-skin asset changed Morph weights: {}".format(
                            subject_id
                        )
                    )
                if not case["skin_verification"][
                    "eye_avatar_parts_preserved"
                ]:
                    raise ReconstructionError(
                        "Cross-skin asset changed eye AvatarParts: {}".format(
                            subject_id
                        )
                    )
                if not eye_geometry.get("matches"):
                    raise ReconstructionError(
                        "Cross-skin asset changed eye geometry: {}".format(
                            subject_id
                        )
                    )

                for view in normalized_views:
                    view_id = view["id"]
                    mark(subject_id, "render_{}".format(view_id))
                    view_dir = os.path.join(case_dir, view_id)
                    view_matrix = copy.deepcopy(matrix_template)
                    view_matrix["camera_path"] = subject["camera_path"]
                    view_matrix["yaw_degrees"] = view["yaw_degrees"]
                    view_summary = probe_current_face_material_visual_matrix(
                        {"face_material_visual_matrix": view_matrix},
                        view_dir,
                    )
                    case["views"].append(
                        {
                            "id": view_id,
                            "matrix_path": view_summary[
                                "face_material_visual_matrix_path"
                            ],
                            "success": bool(view_summary.get("success")),
                            "summary_path": view_summary["summary_path"],
                            "yaw_degrees": view["yaw_degrees"],
                        }
                    )
                    if not view_summary.get("success"):
                        raise ReconstructionError(
                            "Cross-skin material view failed: {} {}".format(
                                subject_id, view_id
                            )
                        )
                case["success"] = all(
                    item.get("success") for item in case["views"]
                )
            except Exception as exc:
                case["error"] = {
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                    "type": type(exc).__name__,
                }
                run_error = case["error"]
            cases.append(case)
            write_json(case, os.path.join(case_dir, "result.json"))
            if run_error is not None:
                break
    finally:
        restoration["attempted"] = True
        try:
            mark(None, "restore_project", {"path": restore_project})
            restore_status, restore_dialogs = load_file_with_optional_undo_warning(
                restore_project,
                "Restore project after cross-skin matrix",
            )
            settle_cc_ui(load_settle_seconds)
            restored_avatar, restored_avatars = resolve_avatar()
            restoration.update(
                {
                    "avatar_count": len(restored_avatars),
                    "avatar_id": scene_object_id(restored_avatar),
                    "dialogs": restore_dialogs,
                    "status": restore_status,
                    "success": len(restored_avatars) == 1,
                }
            )
        except Exception as exc:
            restoration["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "type": type(exc).__name__,
            }
            if run_error is None:
                run_error = restoration["error"]

    success_count = sum(1 for item in cases if item.get("success"))
    report = {
        "schema_version": 1,
        "captured_at": started_at,
        "diagnostic_mode": "face_material_cross_skin_matrix",
        "expected_subject_ids": sorted(expected_subject_ids),
        "subjects": cases,
        "restoration": restoration,
        "success": (
            run_error is None
            and success_count == len(normalized_subjects)
            and restoration.get("success")
        ),
        "finished_at": now(),
    }
    write_json(report, report_path)
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": report["finished_at"],
        "requested_count": len(normalized_subjects),
        "success_count": success_count,
        "failure_count": len(normalized_subjects) - success_count,
        "success": report["success"],
        "diagnostic_mode": "face_material_cross_skin_matrix",
        "face_material_cross_skin_matrix_path": report_path,
        "restoration": restoration,
        "run_error": run_error,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    mark(None, "complete", {"success": summary["success"]})
    return summary


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


def remove_source_accessories_for_outfit_gate(avatar):
    before = avatar_asset_inventory(avatar)
    avatar_id = scene_object_id(avatar)
    accessories = list(avatar.GetAccessories() or [])
    removals = []
    for item in accessories:
        record = {
            "id": scene_object_id(item),
            "name": scene_object_name(item),
            "python_type": type(item).__name__,
            "collection": "GetAccessories",
        }
        record["remove_status"] = checked(
            "Remove source accessory before outfit gate {}".format(
                record["name"]
            ),
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
        raise ReconstructionError(
            "Avatar identity changed during source accessory cleanup"
        )
    avatar = matches[0]
    after = avatar_asset_inventory(avatar)
    remaining_ids = {
        item["id"]
        for item in after["objects"]
        if item["collection"] == "GetAccessories"
    }
    failed_removals = [
        item["id"] for item in removals if item["id"] in remaining_ids
    ]
    if failed_removals:
        raise ReconstructionError(
            "Source accessory cleanup did not remove objects: {}".format(
                failed_removals
            )
        )
    return avatar, {
        "before_inventory": before,
        "after_inventory": after,
        "removed_objects": removals,
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
EXPORT_LICENSE_BLOCKER_TEXT = (
    "You must first purchase the content licenses in order to export FBX files."
)
FATAL_DIALOG_FILENAME = "fatal_dialog.json"


def raise_if_fatal_cc_dialog(output_dir):
    fatal_path = os.path.join(output_dir, FATAL_DIALOG_FILENAME)
    if not os.path.isfile(fatal_path):
        return
    try:
        with open(fatal_path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise ReconstructionError(
            "CC recorded a fatal dialog, but its evidence is unreadable: {} ({})"
            .format(fatal_path, exc)
        )
    message = str(payload.get("message") or "unknown fatal CC dialog")
    raise ReconstructionError(
        "CC blocked the operation with a fatal dialog: {} Evidence: {}".format(
            message,
            fatal_path,
        )
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
APPLY_CLOTH_OPTIONS_DIALOG_TITLE = "Apply Cloth Options"
APPLY_CLOTH_OPTIONS_REQUIRED_TEXT = (
    "The cloth was not made for this character generation.",
    "Please select one of the following options:",
)
APPLY_CLOTH_OPTIONS_POLICIES = {
    "keep_cloth_shape": "Keep Cloth Shape",
    "fit_body_shape": "Fit Body Shape",
}


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


def is_known_cc_progress_dialog(widget, snapshot=None):
    snapshot = snapshot or cc_dialog_snapshot(widget)
    if type(widget).__name__ != "QProgressDialog":
        return False
    if normalized_dialog_text(snapshot["window_title"]) != (
        normalized_dialog_text("Character Creator 5")
    ):
        return False
    if snapshot["direct_text"]:
        return False
    if not any(
        normalized_dialog_text(text)
        == normalized_dialog_text("Character Creator 5")
        for text in snapshot["labels"]
    ):
        return False
    button_texts = {
        normalized_dialog_text(item["text"])
        for item in snapshot["buttons"]
    }
    return button_texts.issubset({"", "cancel"})


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

    def __init__(self, output_dir=None):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.inspect)
        self.handled_widgets = set()
        self.output_dir = output_dir
        self.native_process = None
        self.native_stop_path = None
        self.native_fatal_dialog_path = (
            os.path.join(output_dir, FATAL_DIALOG_FILENAME)
            if output_dir
            else None
        )
        self.report = {
            "policy": "exact_undo_warning_whole_run",
            "required_text": UNDO_MANAGER_WARNING_TEXT,
            "poll_count": 0,
            "matched_count": 0,
            "clicked_count": 0,
            "dialogs": [],
            "native_guard": None,
        }

    def start(self):
        self.timer.start()
        if not self.output_dir or not os.path.isfile(
            UNDO_DIALOG_GUARD_PATH
        ):
            return
        os.makedirs(self.output_dir, exist_ok=True)
        if (
            self.native_fatal_dialog_path
            and os.path.isfile(self.native_fatal_dialog_path)
        ):
            os.remove(self.native_fatal_dialog_path)
        self.native_stop_path = os.path.join(
            self.output_dir,
            "_undo_warning_guard.stop",
        )
        if os.path.isfile(self.native_stop_path):
            os.remove(self.native_stop_path)
        log_path = os.path.join(
            self.output_dir,
            "undo_warning_guard_native.jsonl",
        )
        result_path = os.path.join(
            self.output_dir,
            "validation_result.json",
        )
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            UNDO_DIALOG_GUARD_PATH,
            "-TargetProcessId",
            str(os.getpid()),
            "-ResultPath",
            result_path,
            "-LogPath",
            log_path,
            "-ProgressRoot",
            self.output_dir,
            "-StopPath",
            self.native_stop_path,
            "-TimeoutSeconds",
            "43200",
        ]
        try:
            self.native_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
            )
            self.report["native_guard"] = {
                "enabled": True,
                "guard_path": UNDO_DIALOG_GUARD_PATH,
                "fatal_dialog_path": self.native_fatal_dialog_path,
                "log_path": log_path,
                "process_id": self.native_process.pid,
                "stop_path": self.native_stop_path,
            }
        except Exception as exc:
            self.report["native_guard"] = {
                "enabled": False,
                "error_message": str(exc),
                "error_type": type(exc).__name__,
                "guard_path": UNDO_DIALOG_GUARD_PATH,
            }

    def stop(self):
        self.timer.stop()
        if self.native_stop_path:
            try:
                with open(self.native_stop_path, "w", encoding="utf-8") as handle:
                    handle.write(now() + "\n")
            except Exception as exc:
                if self.report.get("native_guard") is not None:
                    self.report["native_guard"]["stop_error"] = str(exc)
        if self.native_process is not None:
            deadline = time.time() + 3.0
            while self.native_process.poll() is None and time.time() < deadline:
                QtWidgets.QApplication.processEvents()
                time.sleep(0.05)
            native_report = self.report.get("native_guard") or {}
            native_report["exit_code"] = self.native_process.poll()
            if (
                self.native_fatal_dialog_path
                and os.path.isfile(self.native_fatal_dialog_path)
            ):
                try:
                    native_report["fatal_dialog"] = read_json(
                        self.native_fatal_dialog_path
                    )
                except Exception as exc:
                    native_report["fatal_dialog_read_error"] = str(exc)

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
    allow_skin_material=False,
    character_preset_checkbox_states=None,
):
    if (require_character_preset or allow_character_preset) and (
        require_skin_material or allow_skin_material
    ):
        raise ReconstructionError(
            "Only one CC dialog policy may be active"
        )
    character_preset_enabled = bool(
        require_character_preset or allow_character_preset
    )
    if character_preset_checkbox_states is None:
        character_preset_checkbox_states = {
            item: True for item in CHARACTER_PRESET_CHECKBOX_TEXTS
        }
    else:
        character_preset_checkbox_states = dict(
            character_preset_checkbox_states
        )
        if set(character_preset_checkbox_states) != set(
            CHARACTER_PRESET_CHECKBOX_TEXTS
        ):
            raise ReconstructionError(
                "Character preset checkbox policy must define exactly {}"
                .format(", ".join(CHARACTER_PRESET_CHECKBOX_TEXTS))
            )
        character_preset_checkbox_states = {
            item: bool(character_preset_checkbox_states[item])
            for item in CHARACTER_PRESET_CHECKBOX_TEXTS
        }
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
                    else (
                        "optional_skin_material_exact_dialog"
                        if allow_skin_material
                        else "optional_undo_warning_exact_dialog"
                    )
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
            "required_checkbox_states": dict(
                character_preset_checkbox_states
            ),
            "target_button": "Apply",
            "matched_count": 0,
            "clicked_count": 0,
        },
        "skin_material": {
            "allowed": bool(
                require_skin_material or allow_skin_material
            ),
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
            if is_known_cc_progress_dialog(widget, snapshot):
                continue
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
                    checkbox_matches[checkbox_text][0].setChecked(
                        character_preset_checkbox_states[checkbox_text]
                    )
                preset_report["checkbox_state_after"] = {
                    item: bool(checkbox_matches[item][0].isChecked())
                    for item in CHARACTER_PRESET_CHECKBOX_TEXTS
                }
                if (
                    preset_report["checkbox_state_after"]
                    != character_preset_checkbox_states
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
                and (require_skin_material or allow_skin_material)
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
    if (
        allow_skin_material
        and skin_report["matched_count"]
        != skin_report["clicked_count"]
    ):
        raise ReconstructionError(
            "Optional skin material dialog was not resolved exactly"
        )
    return checked(label, raw_status), report


def load_file_with_optional_undo_warning(path, label):
    return load_file_with_known_cc_dialogs(
        path,
        label,
        require_character_preset=False,
    )


def load_clothing_asset_with_known_dialogs(
    path,
    label,
    cloth_options_policy,
    record_step=True,
    load_mode="file",
):
    if cloth_options_policy not in APPLY_CLOTH_OPTIONS_POLICIES:
        raise ReconstructionError(
            "Unsupported cloth options policy: {}".format(
                cloth_options_policy
            )
        )
    if not isinstance(record_step, bool):
        raise ReconstructionError(
            "record_step must be a boolean for clothing asset loads"
        )
    if load_mode not in ("file", "object"):
        raise ReconstructionError(
            "Unsupported clothing asset load mode: {}".format(load_mode)
        )

    target_choice_text = APPLY_CLOTH_OPTIONS_POLICIES[
        cloth_options_policy
    ]
    report = {
        "policy": "exact_apply_cloth_options_dialog_v1",
        "path": path,
        "cloth_options_policy": cloth_options_policy,
        "record_step": record_step,
        "load_mode": load_mode,
        "target_choice": target_choice_text,
        "undo_warning": {
            "required_text": UNDO_MANAGER_WARNING_TEXT,
            "matched_count": 0,
            "clicked_count": 0,
        },
        "cloth_options": {
            "required_title": APPLY_CLOTH_OPTIONS_DIALOG_TITLE,
            "required_text": list(APPLY_CLOTH_OPTIONS_REQUIRED_TEXT),
            "required_choices": dict(APPLY_CLOTH_OPTIONS_POLICIES),
            "target_button": "OK",
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
    handled_cloth_widgets = set()
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
        fatal = dict(snapshot)
        fatal.pop("normalized_text", None)
        cancel_buttons = exact_dialog_buttons(
            widget,
            "Cancel",
            checkable=False,
        )
        if len(cancel_buttons) == 1:
            cancel_buttons[0].click()
            fatal["close_action"] = "exact_cancel_button"
        else:
            reject = getattr(widget, "reject", None)
            if callable(reject):
                reject()
                fatal["close_action"] = "reject"
            else:
                widget.close()
                fatal["close_action"] = "close"
        report["fatal_unknown_dialog"] = fatal

    def choice_buttons(widget, choice_text):
        target = normalized_dialog_text(choice_text)
        matches = []
        for button in widget.findChildren(QtWidgets.QAbstractButton):
            if (
                not button.isVisible()
                or not button.isEnabled()
                or not button.isCheckable()
            ):
                continue
            text = normalized_dialog_text(button.text())
            if text == target or text.startswith(target + " "):
                matches.append(button)
        return matches

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
            if is_known_cc_progress_dialog(widget, snapshot):
                continue
            normalized = snapshot["normalized_text"]
            if (
                is_active_modal
                or normalized_dialog_text(UNDO_MANAGER_WARNING_TEXT)
                in normalized
                or normalized_dialog_text(
                    APPLY_CLOTH_OPTIONS_DIALOG_TITLE
                ) in normalized
            ):
                remember_snapshot(snapshot, is_active_modal)

            widget_key = id(widget)
            undo_button = exact_undo_warning_button(widget, snapshot)
            if undo_button is not None:
                if widget_key not in handled_undo_widgets:
                    handled_undo_widgets.add(widget_key)
                    report["undo_warning"]["matched_count"] += 1
                    undo_button.click()
                    report["undo_warning"]["clicked_count"] += 1
                return

            title_matches = normalized_dialog_text(
                snapshot["window_title"]
            ) == normalized_dialog_text(APPLY_CLOTH_OPTIONS_DIALOG_TITLE)
            body_matches = all(
                normalized_dialog_text(required) in normalized
                for required in APPLY_CLOTH_OPTIONS_REQUIRED_TEXT
            )
            keep_buttons = choice_buttons(widget, "Keep Cloth Shape")
            fit_buttons = choice_buttons(widget, "Fit Body Shape")
            ok_buttons = exact_dialog_buttons(
                widget,
                "OK",
                checkable=False,
            )
            cancel_buttons = exact_dialog_buttons(
                widget,
                "Cancel",
                checkable=False,
            )
            more_buttons = exact_dialog_buttons(
                widget,
                "More",
                checkable=False,
            )
            visible_buttons = [
                button
                for button in widget.findChildren(
                    QtWidgets.QAbstractButton
                )
                if button.isVisible() and button.isEnabled()
            ]
            expected_button_count = (
                len(keep_buttons)
                + len(fit_buttons)
                + len(ok_buttons)
                + len(cancel_buttons)
                + len(more_buttons)
            )
            exact_cloth_dialog = (
                title_matches
                and body_matches
                and len(keep_buttons) == 1
                and len(fit_buttons) == 1
                and len(ok_buttons) == 1
                and len(cancel_buttons) == 1
                and len(more_buttons) <= 1
                and expected_button_count == len(visible_buttons)
            )
            if exact_cloth_dialog:
                if widget_key in handled_cloth_widgets:
                    return
                handled_cloth_widgets.add(widget_key)
                cloth_report = report["cloth_options"]
                cloth_report["matched_count"] += 1
                cloth_report["choice_state_before"] = {
                    "keep_cloth_shape": bool(
                        keep_buttons[0].isChecked()
                    ),
                    "fit_body_shape": bool(
                        fit_buttons[0].isChecked()
                    ),
                }
                target = (
                    keep_buttons[0]
                    if cloth_options_policy == "keep_cloth_shape"
                    else fit_buttons[0]
                )
                target.setChecked(True)
                QtWidgets.QApplication.processEvents()
                cloth_report["choice_state_after"] = {
                    "keep_cloth_shape": bool(
                        keep_buttons[0].isChecked()
                    ),
                    "fit_body_shape": bool(
                        fit_buttons[0].isChecked()
                    ),
                }
                if not target.isChecked():
                    cloth_report["configuration_error"] = (
                        "Target cloth option could not be selected"
                    )
                    cancel_buttons[0].click()
                    return
                ok_buttons[0].click()
                cloth_report["clicked_count"] += 1
                return

            if not is_active_modal:
                continue
            unknown_key = (
                snapshot["window_title"],
                tuple(snapshot["labels"]),
                tuple(snapshot["direct_text"]),
                tuple(item["text"] for item in snapshot["buttons"]),
            )
            unknown_poll_counts[unknown_key] = (
                unknown_poll_counts.get(unknown_key, 0) + 1
            )
            if unknown_poll_counts[unknown_key] >= 20:
                cancel_unknown_dialog(widget, snapshot)
                return

    timer.timeout.connect(inspect_dialogs)
    timer.start()
    try:
        if load_mode == "object":
            loaded_object = RLPy.RFileIO.LoadObject(path, record_step)
            raw_status = None
            report["loaded_object"] = (
                {
                    "id": scene_object_id(loaded_object),
                    "name": scene_object_name(loaded_object),
                    "python_type": type(loaded_object).__name__,
                }
                if loaded_object is not None
                else None
            )
        else:
            raw_status = RLPy.RFileIO.LoadFile(path, record_step)
    finally:
        timer.stop()
    report["load_returned"] = True

    if report["fatal_unknown_dialog"] is not None:
        raise BlockingDialogError(
            "Unknown CC modal dialog cancelled while loading {}: {}".format(
                label,
                json.dumps(
                    report["fatal_unknown_dialog"],
                    sort_keys=True,
                    ensure_ascii=True,
                ),
            )
        )
    cloth_report = report["cloth_options"]
    if cloth_report.get("configuration_error"):
        raise BlockingDialogError(
            "Apply Cloth Options dialog could not be configured safely"
        )
    if (
        cloth_report["matched_count"]
        != cloth_report["clicked_count"]
    ):
        raise BlockingDialogError(
            "Apply Cloth Options dialog was not resolved exactly"
        )
    return checked(label, raw_status), report


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


def load_file_with_optional_skin_material_dialog(path, label):
    return load_file_with_known_cc_dialogs(
        path,
        label,
        allow_skin_material=True,
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
            status, dialog_policy = (
                load_file_with_optional_skin_material_dialog(
                    item["path"],
                    load_label,
                )
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


def render_pixel_stream_preview(path, render_time=None):
    import ctypes
    from PySide2 import QtGui

    if render_time is None:
        render_time = RLPy.RGlobal.GetStartTime()
    if os.path.isfile(path):
        os.remove(path)
    original_view_size = current_view_size()
    enabled = False
    try:
        checked(
            "Set deterministic pixel-stream size",
            RLPy.RGlobal.SetViewSize(
                PIXEL_STREAM_PREVIEW_SIZE,
                PIXEL_STREAM_PREVIEW_SIZE,
            ),
        )
        checked("Set pixel-stream time", RLPy.RGlobal.SetTime(render_time, True))
        checked(
            "Enable viewport pixel stream",
            RLPy.RGlobal.EnablePixelStream(True),
        )
        enabled = True
        try:
            checked(
                "Start viewport pixel stream",
                RLPy.RGlobal.RenderPreview(),
            )
        except Exception:
            pass
        image = None
        for unused_index in range(3):
            checked(
                "Force viewport update",
                RLPy.RGlobal.ForceViewportUpdate(),
            )
            settle_cc_ui(0.35)
            captured = RLPy.RGlobal.CapturePixelStream()
            candidates = (
                list(captured)
                if isinstance(captured, (list, tuple))
                else [captured]
            )
            for candidate in candidates:
                try:
                    width = int(candidate.width)
                    height = int(candidate.height)
                    pointer = int(candidate.buffer_ptr)
                except Exception:
                    continue
                if width <= 0 or height <= 0 or pointer <= 0:
                    continue
                raw = ctypes.string_at(pointer, width * height * 4)
                image = QtGui.QImage(
                    raw,
                    width,
                    height,
                    width * 4,
                    QtGui.QImage.Format_ARGB32,
                ).copy()
        if image is None or image.isNull():
            raise ReconstructionError(
                "Viewport pixel stream returned no convertible frame"
            )
        if not image.save(path, "PNG"):
            raise ReconstructionError(
                "Unable to save viewport pixel-stream image: {}".format(path)
            )
    finally:
        if enabled:
            checked(
                "Disable viewport pixel stream",
                RLPy.RGlobal.EnablePixelStream(False),
            )
        checked(
            "Restore pixel-stream view size",
            RLPy.RGlobal.SetViewSize(*original_view_size),
        )
        QtWidgets.QApplication.processEvents()


def render_preview(path, render_time=None):
    if PREVIEW_CAPTURE_MODE == "pixel_stream":
        return render_pixel_stream_preview(path, render_time)
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
    width=None,
    height=None,
):
    from PySide2 import QtGui

    image = QtGui.QImage(path)
    if image.isNull():
        raise ReconstructionError(
            "Unable to read rendered preview for normalization: {}".format(
                path
            )
        )
    width = VIEWPORT_PREVIEW_WIDTH if width is None else int(width)
    height = VIEWPORT_PREVIEW_HEIGHT if height is None else int(height)
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

    (
        neutral_eye_state_before,
        neutral_eye_capture_before,
    ) = capture_stable_neutral_eye_state(avatar)
    report["neutral_eye_capture_stabilization_before"] = (
        neutral_eye_capture_before
    )
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
    (
        neutral_eye_state_after,
        neutral_eye_capture_after,
    ) = capture_stable_neutral_eye_state(avatar)
    report["neutral_eye_capture_stabilization_after"] = (
        neutral_eye_capture_after
    )
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
        preset_ids
        if preset_ids is not None
        else [item["preset_id"] for item in all_presets]
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
    bones = [
        bone
        for bone in list(skeleton.GetSkinBones() or [])
        if "eye" in str(bone.GetName()).lower()
    ]
    # The first bone update can flush a stale root-transform cache. Refresh
    # every eye bone once before sampling either side.
    for bone in bones:
        bone.Update()

    eye_bones = []
    for bone in bones:
        name = str(bone.GetName())
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


def capture_stable_neutral_eye_state(
    avatar,
    attempts=6,
    settle_seconds=0.5,
):
    previous_state = None
    records = []
    for attempt_index in range(1, int(attempts) + 1):
        force_avatar_scene_evaluation(
            avatar,
            settle_seconds=settle_seconds,
        )
        current_state = capture_eye_integrity_state(avatar)
        if previous_state is None:
            records.append(
                {
                    "attempt": attempt_index,
                    "differences": [],
                    "matches": None,
                }
            )
        else:
            comparison = compare_neutral_eye_states(
                previous_state,
                current_state,
                include_world=True,
            )
            records.append(
                {
                    "attempt": attempt_index,
                    "differences": comparison["differences"],
                    "matches": comparison["matches"],
                }
            )
            if comparison["matches"]:
                return current_state, records
        previous_state = current_state
    raise ReconstructionError(
        "Neutral eye state did not stabilize after {} captures: {}".format(
            attempts,
            records[-1]["differences"] if records else [],
        )
    )


def compare_neutral_eye_states(
    before,
    after,
    tolerance=2e-3,
    include_world=True,
    include_runtime_ids=True,
    t_pose_tolerance=None,
    world_translation_tolerance=None,
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
    if world_translation_tolerance is None:
        world_translation_tolerance = max(tolerance, 2e-2)
    world_translation_tolerance = float(world_translation_tolerance)
    if world_translation_tolerance < float(tolerance):
        raise ReconstructionError(
            "world_translation_tolerance cannot be smaller than tolerance"
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
                    world_translation_tolerance
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
        "world_translation_tolerance": world_translation_tolerance,
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


def bodyfit_height_cm(bounds):
    return float(bounds["maximum"][2] - bounds["minimum"][2])


def avatar_motion_inventory(avatar):
    skeleton = avatar.GetSkeletonComponent()
    face_component = avatar.GetFaceComponent()
    return {
        "skeleton_clip_count": (
            int(skeleton.GetClipCount()) if skeleton is not None else 0
        ),
        "face_clip_count": (
            int(face_component.GetClipCount())
            if face_component is not None
            else 0
        ),
    }


def clear_avatar_motion(avatar):
    before = avatar_motion_inventory(avatar)
    skeleton = avatar.GetSkeletonComponent()
    face_component = avatar.GetFaceComponent()
    removed_skeleton_clips = 0
    removed_face_clips = 0
    if skeleton is not None:
        for clip_index in range(
            int(skeleton.GetClipCount()) - 1,
            -1,
            -1,
        ):
            checked(
                "Delete BodyFit skeleton clip {}".format(clip_index),
                skeleton.DeleteClip(skeleton.GetClip(clip_index)),
            )
            removed_skeleton_clips += 1
            QtWidgets.QApplication.processEvents()
    if face_component is not None:
        for clip_index in range(
            int(face_component.GetClipCount()) - 1,
            -1,
            -1,
        ):
            checked(
                "Delete BodyFit face clip {}".format(clip_index),
                face_component.DeleteClip(face_component.GetClip(clip_index)),
            )
            removed_face_clips += 1
            QtWidgets.QApplication.processEvents()
    checked(
        "Evaluate neutral BodyFit timeline",
        RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
    )
    after = avatar_motion_inventory(avatar)
    if after["skeleton_clip_count"] or after["face_clip_count"]:
        raise ReconstructionError("BodyFit animation cleanup was incomplete")
    return {
        "before": before,
        "after": after,
        "removed_skeleton_clip_count": removed_skeleton_clips,
        "removed_face_clip_count": removed_face_clips,
    }


def clear_avatar_skeleton_motion(avatar):
    before = avatar_motion_inventory(avatar)
    skeleton = avatar.GetSkeletonComponent()
    removed_skeleton_clips = 0
    if skeleton is not None:
        for clip_index in range(
            int(skeleton.GetClipCount()) - 1,
            -1,
            -1,
        ):
            checked(
                "Delete quality benchmark skeleton clip {}".format(
                    clip_index
                ),
                skeleton.DeleteClip(skeleton.GetClip(clip_index)),
            )
            removed_skeleton_clips += 1
            QtWidgets.QApplication.processEvents()
    checked(
        "Evaluate quality benchmark body-neutral timeline",
        RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
    )
    after = avatar_motion_inventory(avatar)
    if after["skeleton_clip_count"]:
        raise ReconstructionError(
            "Quality benchmark skeleton animation cleanup was incomplete"
        )
    if after["face_clip_count"] != before["face_clip_count"]:
        raise ReconstructionError(
            "Quality benchmark changed the existing face clips"
        )
    return {
        "before": before,
        "after": after,
        "removed_skeleton_clip_count": removed_skeleton_clips,
        "removed_face_clip_count": 0,
        "face_clip_policy": "preserve_existing_facial_profile_clip",
    }


def remove_all_attached_avatar_assets(avatar):
    before = avatar_asset_inventory(avatar)
    removed = []
    seen = set()
    for getter_name in ("GetClothes", "GetAccessories", "GetHairs"):
        for scene_object in list(getattr(avatar, getter_name)() or []):
            object_id = scene_object_id(scene_object)
            if object_id in seen:
                continue
            seen.add(object_id)
            record = {
                "collection": getter_name,
                "id": object_id,
                "name": scene_object_name(scene_object),
                "python_type": type(scene_object).__name__,
            }
            record["remove_status"] = checked(
                "Remove BodyFit attached asset {}".format(record["name"]),
                RLPy.RScene.RemoveObject(scene_object),
            )
            removed.append(record)
            QtWidgets.QApplication.processEvents()
    after = avatar_asset_inventory(avatar)
    if after["object_count"]:
        raise ReconstructionError(
            "Standard BodyFit still contains clothing, hair, or accessories"
        )
    return {"before": before, "after": after, "removed": removed}


def avatar_part_inventory(avatar):
    parts = []
    try:
        avatar_parts = list(avatar.GetAvatarParts() or [])
    except Exception:
        avatar_parts = []
    for part in avatar_parts:
        parts.append(
            {
                "avatar_part_type": str(part.GetAvatarPartType()),
                "id": scene_object_id(part),
                "name": scene_object_name(part),
                "python_type": type(part).__name__,
            }
        )
    parts.sort(
        key=lambda item: (
            item["avatar_part_type"],
            item["name"],
            item["id"],
        )
    )
    return {"part_count": len(parts), "parts": parts}


def bodyfit_freeze_file_record(path):
    return {
        "bytes": os.path.getsize(path),
        "path": path,
        "sha256": sha256_file(path),
    }


def save_bodyfit_project(path, label):
    path = os.path.realpath(os.path.abspath(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.isfile(path):
        raise ReconstructionError(
            "Refusing to save BodyFit over an existing staging file: {}".format(
                path
            )
        )
    checked(label, RLPy.RFileIO.SaveProject(path))
    wait_for_rendered_preview(
        path,
        timeout_seconds=600.0,
        stable_seconds=2.0,
    )
    return bodyfit_freeze_file_record(path)


def bodyfit_source_targets(vectors):
    return {
        classification: [
            dict(item)
            for item in vectors["groups"][classification]["entries"]
        ]
        for classification in ("body", "junction")
    }


def split_portable_bodyfit_targets(avatar, source_targets):
    component, catalog, unused_categories = morph_catalog(avatar)
    portable = {"body": [], "junction": []}
    unavailable = []
    for classification in ("body", "junction"):
        for source in source_targets[classification]:
            morph_id = source["id"]
            target = catalog.get(morph_id)
            if target is None:
                unavailable.append(
                    dict(source, unavailable_reason="missing_from_neutral_base")
                )
                continue
            if target["classification"] != classification:
                unavailable.append(
                    dict(
                        source,
                        neutral_classification=target["classification"],
                        unavailable_reason="classification_changed",
                    )
                )
                continue
            bounds = component.GetShapingMorphMinMax(morph_id)
            portable[classification].append(
                dict(
                    source,
                    categories=list(target["categories"]),
                    display=target["display"],
                    minimum=float(bounds.first),
                    maximum=float(bounds.second),
                )
            )
    return portable, unavailable


def validate_standard_bodyfit_state(
    avatar,
    expected_targets,
    expected_head_scale,
):
    vectors = capture_vectors(avatar)
    deltas = {
        classification: group_delta(
            expected_targets[classification],
            vectors["groups"][classification]["entries"],
        )
        for classification in ("body", "junction")
    }
    component, catalog, unused_categories = morph_catalog(avatar)
    if BODYFIT_HEAD_SCALE_MORPH_ID not in catalog:
        raise ReconstructionError("Standard BodyFit has no Head Scale Morph")
    head_scale = float(
        component.GetShapingMorphWeight(BODYFIT_HEAD_SCALE_MORPH_ID)
    )
    assets = avatar_asset_inventory(avatar)
    motion = avatar_motion_inventory(avatar)
    valid = (
        not deltas["body"]
        and not deltas["junction"]
        and abs(head_scale - float(expected_head_scale)) <= 1e-6
        and assets["object_count"] == 0
        and motion["skeleton_clip_count"] == 0
        and motion["face_clip_count"] == 0
    )
    return {
        "asset_inventory": assets,
        "avatar_part_inventory": avatar_part_inventory(avatar),
        "body_and_junction_fingerprint_sha256": vectors[
            "body_and_junction_fingerprint_sha256"
        ],
        "deltas": deltas,
        "head_scale": head_scale,
        "motion_inventory": motion,
        "valid": valid,
        "vectors": vectors,
    }


def install_standard_bodyfit_project(staging_path, formal_path, output_dir):
    formal_path = os.path.realpath(os.path.abspath(formal_path))
    if not path_is_within(formal_path, [BODYFIT_STANDARD_PROJECT_ROOT]):
        raise ReconstructionError(
            "Formal BodyFit path is outside the approved project root"
        )
    require_file_extension(
        formal_path,
        ".ccProject",
        "Formal BodyFit project",
    )
    os.makedirs(os.path.dirname(formal_path), exist_ok=True)
    previous = None
    if os.path.isfile(formal_path):
        previous_path = os.path.join(
            output_dir,
            "previous_formal_{}".format(os.path.basename(formal_path)),
        )
        shutil.copy2(formal_path, previous_path)
        previous = bodyfit_freeze_file_record(previous_path)
    temporary = formal_path + ".lance_install_tmp"
    if os.path.isfile(temporary):
        os.remove(temporary)
    try:
        shutil.copy2(staging_path, temporary)
        if sha256_file(temporary) != sha256_file(staging_path):
            raise ReconstructionError("BodyFit staging copy hash mismatch")
        os.replace(temporary, formal_path)
    finally:
        if os.path.isfile(temporary):
            os.remove(temporary)
    installed = bodyfit_freeze_file_record(formal_path)
    if installed["sha256"] != sha256_file(staging_path):
        raise ReconstructionError("Installed BodyFit hash differs from staging")
    return {"installed": installed, "previous": previous}


def probe_current_scene_bodyfit_freeze(library, output_dir, log):
    os.makedirs(output_dir, exist_ok=True)
    config = library.get("current_scene_bodyfit_freeze") or {}
    if not isinstance(config, dict):
        raise ReconstructionError(
            "current_scene_bodyfit_freeze must be an object"
        )
    operation = config.get("operation")
    if operation not in ("capture_only", "standardize_and_install"):
        raise ReconstructionError("Unsupported BodyFit freeze operation")
    base_avatar_path = canonical_existing_file(
        config.get("base_avatar_path"),
        "BodyFit neutral base",
    )
    formal_project_path = os.path.realpath(
        os.path.abspath(config.get("formal_project_path") or "")
    )
    if not path_is_within(
        formal_project_path,
        [BODYFIT_STANDARD_PROJECT_ROOT],
    ):
        raise ReconstructionError(
            "Formal BodyFit project path is outside the approved root"
        )
    source_head_scale = float(config.get("source_head_scale", 0.0))
    production_head_scale = float(
        config.get("production_head_scale", -0.1)
    )
    expected_source_fingerprint = config.get(
        "expected_source_body_and_junction_fingerprint"
    )
    allowed_unavailable_ids = set(
        config.get("allowed_unavailable_source_morph_ids") or []
    )
    progress_path = os.path.join(output_dir, "progress.json")
    report_path = os.path.join(output_dir, "bodyfit_freeze_report.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    backup_path = os.path.join(output_dir, "current_scene_backup.ccProject")
    source_preview_path = os.path.join(output_dir, "current_scene.png")

    def mark(phase, extra=None):
        payload = {
            "operation": operation,
            "phase": phase,
            "schema_version": 1,
            "updated_at": now(),
        }
        if extra:
            payload.update(extra)
        write_json(payload, progress_path)
        log("F05 FREEZE {}".format(phase))
        QtWidgets.QApplication.processEvents()

    started_at = now()
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Current-scene BodyFit freeze expected exactly one avatar"
        )
    RLPy.RScene.SelectObject(avatar)
    mark("capture_current_scene")
    source_vectors = capture_vectors(avatar)
    if (
        expected_source_fingerprint is not None
        and source_vectors["body_and_junction_fingerprint_sha256"]
        != expected_source_fingerprint
    ):
        raise ReconstructionError(
            "Current F05 body fingerprint changed before standardization"
        )
    source_targets = bodyfit_source_targets(source_vectors)
    source_state = {
        "asset_inventory": avatar_asset_inventory(avatar),
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "avatar_bounds": capture_bounds(avatar),
        "avatar_part_inventory": avatar_part_inventory(avatar),
        "motion_inventory": avatar_motion_inventory(avatar),
        "targets": source_targets,
        "vectors": source_vectors,
    }
    write_json(source_state, os.path.join(output_dir, "current_scene_state.json"))
    render_preview(source_preview_path)
    mark("save_current_scene_backup")
    backup = save_bodyfit_project(
        backup_path,
        "Save current F05 scene backup",
    )
    report = {
        "backup": backup,
        "base_avatar_path": base_avatar_path,
        "formal_project_path": formal_project_path,
        "operation": operation,
        "schema_version": 1,
        "source_preview": source_preview_path,
        "source_state": source_state,
        "started_at": started_at,
    }
    write_json(report, report_path)

    if operation == "capture_only":
        report["finished_at"] = now()
        report["success"] = True
        write_json(report, report_path)
        summary = {
            "diagnostic_mode": "current_scene_bodyfit_freeze",
            "failure_count": 0,
            "finished_at": report["finished_at"],
            "freeze_report_path": report_path,
            "operation": operation,
            "requested_count": 1,
            "schema_version": 1,
            "started_at": started_at,
            "success": True,
            "success_count": 1,
            "summary_path": summary_path,
        }
        write_json(summary, summary_path)
        mark("complete")
        return summary

    formal_install = None
    formal_replaced = False
    try:
        mark("load_neutral_base")
        avatar, base_load_attempts = load_base(base_avatar_path)
        if len(list(RLPy.RScene.GetAvatars() or [])) != 1:
            raise ReconstructionError(
                "Neutral BodyFit reconstruction expected one avatar"
        )
        RLPy.RScene.SelectObject(avatar)
        asset_cleanup = remove_all_attached_avatar_assets(avatar)
        base_motion_cleanup = clear_avatar_motion(avatar)
        neutral_material = avatar_material_fingerprint(avatar)
        neutral_material_structure = avatar_material_structure(avatar)
        portable_targets, unavailable = split_portable_bodyfit_targets(
            avatar,
            source_targets,
        )
        unavailable_ids = set(item["id"] for item in unavailable)
        if unavailable_ids != allowed_unavailable_ids:
            raise ReconstructionError(
                "Unavailable source Morph IDs differ from the approved set: "
                "actual={} approved={}".format(
                    sorted(unavailable_ids),
                    sorted(allowed_unavailable_ids),
                )
            )

        mark(
            "apply_body_targets",
            {
                "body_target_count": len(portable_targets["body"]),
                "junction_target_count": len(portable_targets["junction"]),
            },
        )
        application = apply_bodyfit(
            avatar,
            portable_targets["body"],
            portable_targets["junction"],
        )
        head_application = apply_single_morph_weight(
            avatar,
            BODYFIT_HEAD_SCALE_MORPH_ID,
            source_head_scale,
            "standard BodyFit Head Scale",
        )
        force_avatar_scene_evaluation(avatar)
        motion_cleanup = clear_avatar_motion(avatar)
        standardized_state = validate_standard_bodyfit_state(
            avatar,
            portable_targets,
            source_head_scale,
        )
        write_json(
            {
                "asset_cleanup": asset_cleanup,
                "base_motion_cleanup": base_motion_cleanup,
                "motion_cleanup": motion_cleanup,
                "portable_targets": portable_targets,
                "standardized_state": standardized_state,
                "unavailable_source_morphs": unavailable,
            },
            os.path.join(output_dir, "pre_save_standard_state.json"),
        )
        if not standardized_state["valid"]:
            raise ReconstructionError(
                "Rebuilt standard BodyFit failed pre-save validation"
            )
        standardized_material = avatar_material_fingerprint(avatar)
        standardized_material_structure = avatar_material_structure(avatar)
        if (
            standardized_material_structure["digest"]
            != neutral_material_structure["digest"]
        ):
            raise ReconstructionError(
                "BodyFit reconstruction changed the neutral material layout"
            )

        source_bounds = capture_bounds(avatar)
        source_height = bodyfit_height_cm(source_bounds)
        source_standard_preview = os.path.join(
            output_dir,
            "standard_source_head_scale.png",
        )
        render_preview(source_standard_preview)
        protected_fingerprint = standardized_state[
            "body_and_junction_fingerprint_sha256"
        ]
        mark("measure_production_head_scale")
        production_application = apply_single_morph_weight(
            avatar,
            BODYFIT_HEAD_SCALE_MORPH_ID,
            production_head_scale,
            "production BodyFit Head Scale",
        )
        force_avatar_scene_evaluation(avatar)
        production_bounds = capture_bounds(avatar)
        production_height = bodyfit_height_cm(production_bounds)
        production_preview = os.path.join(
            output_dir,
            "production_head_scale.png",
        )
        render_preview(production_preview)
        production_vectors = capture_vectors(avatar)
        if production_vectors[
            "body_and_junction_fingerprint_sha256"
        ] != protected_fingerprint:
            raise ReconstructionError(
                "Production Head Scale changed body or junction Morphs"
            )
        restore_head_application = apply_single_morph_weight(
            avatar,
            BODYFIT_HEAD_SCALE_MORPH_ID,
            source_head_scale,
            "restore source BodyFit Head Scale",
        )
        force_avatar_scene_evaluation(avatar)
        post_measurement_motion_cleanup = clear_avatar_motion(avatar)
        post_measurement_state = validate_standard_bodyfit_state(
            avatar,
            portable_targets,
            source_head_scale,
        )
        if not post_measurement_state["valid"]:
            raise ReconstructionError(
                "BodyFit state was not clean after height measurement"
            )

        staging_path = os.path.join(
            output_dir,
            "staging",
            os.path.basename(formal_project_path),
        )
        mark("save_standard_staging_project")
        staging = save_bodyfit_project(
            staging_path,
            "Save standardized F05 staging project",
        )
        mark("reload_standard_staging_project")
        staging_load_status, staging_load_dialogs = (
            load_file_with_optional_undo_warning(
                staging_path,
                "Reload standardized F05 staging project",
            )
        )
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Reloaded standard staging project has multiple avatars"
            )
        force_avatar_scene_evaluation(avatar)
        staging_state = validate_standard_bodyfit_state(
            avatar,
            portable_targets,
            source_head_scale,
        )
        staging_bounds = capture_bounds(avatar)
        if (
            not staging_state["valid"]
            or abs(bodyfit_height_cm(staging_bounds) - source_height) > 1e-4
        ):
            raise ReconstructionError(
                "Reloaded standard staging project did not round-trip"
            )

        mark("install_formal_project")
        formal_install = install_standard_bodyfit_project(
            staging_path,
            formal_project_path,
            output_dir,
        )
        formal_replaced = True
        mark("reload_formal_project")
        formal_load_status, formal_load_dialogs = (
            load_file_with_optional_undo_warning(
                formal_project_path,
                "Reload installed formal F05 project",
            )
        )
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Installed formal BodyFit has multiple avatars"
            )
        force_avatar_scene_evaluation(avatar)
        formal_state = validate_standard_bodyfit_state(
            avatar,
            portable_targets,
            source_head_scale,
        )
        formal_bounds = capture_bounds(avatar)
        formal_height = bodyfit_height_cm(formal_bounds)
        if not formal_state["valid"] or abs(formal_height - source_height) > 1e-4:
            raise ReconstructionError(
                "Installed formal BodyFit failed final validation"
            )
        formal_preview = os.path.join(output_dir, "formal_project.png")
        render_preview(formal_preview)

        report.update(
            {
                "application": application,
                "asset_cleanup": asset_cleanup,
                "base_load_attempts": base_load_attempts,
                "base_motion_cleanup": base_motion_cleanup,
                "formal_install": formal_install,
                "formal_load_dialogs": formal_load_dialogs,
                "formal_load_status": formal_load_status,
                "formal_preview": formal_preview,
                "formal_state": formal_state,
                "head_application": head_application,
                "measurements": {
                    "production": {
                        "bounds": production_bounds,
                        "head_scale": production_head_scale,
                        "height_cm": production_height,
                        "preview": production_preview,
                    },
                    "source": {
                        "bounds": source_bounds,
                        "head_scale": source_head_scale,
                        "height_cm": source_height,
                        "preview": source_standard_preview,
                    },
                },
                "motion_cleanup": motion_cleanup,
                "neutral_material_fingerprint": neutral_material,
                "neutral_material_structure": neutral_material_structure,
                "portable_targets": portable_targets,
                "post_measurement_motion_cleanup": (
                    post_measurement_motion_cleanup
                ),
                "post_measurement_state": post_measurement_state,
                "production_head_application": production_application,
                "restore_head_application": restore_head_application,
                "staging": staging,
                "staging_load_dialogs": staging_load_dialogs,
                "staging_load_status": staging_load_status,
                "staging_state": staging_state,
                "standardized_material_fingerprint": standardized_material,
                "standardized_material_structure": (
                    standardized_material_structure
                ),
                "standardized_state": standardized_state,
                "unavailable_source_morphs": unavailable,
            }
        )
    except Exception:
        if formal_replaced and formal_install and formal_install.get("previous"):
            previous_path = formal_install["previous"]["path"]
            restore_temp = formal_project_path + ".lance_restore_tmp"
            try:
                shutil.copy2(previous_path, restore_temp)
                os.replace(restore_temp, formal_project_path)
            finally:
                if os.path.isfile(restore_temp):
                    os.remove(restore_temp)
        try:
            load_file_with_optional_undo_warning(
                backup_path,
                "Restore current F05 scene after freeze failure",
            )
        except Exception:
            pass
        raise

    report["finished_at"] = now()
    report["success"] = True
    write_json(report, report_path)
    summary = {
        "diagnostic_mode": "current_scene_bodyfit_freeze",
        "failure_count": 0,
        "finished_at": report["finished_at"],
        "formal_project": formal_install["installed"],
        "freeze_report_path": report_path,
        "measurements": report["measurements"],
        "operation": operation,
        "requested_count": 1,
        "schema_version": 1,
        "started_at": started_at,
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    mark("complete")
    return summary


def probe_source_project_load(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("source_project_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError("source_project_probe must be an object")
    source_project = canonical_existing_file(
        probe.get("path"),
        "Source project probe",
    )
    source_project_sha256 = sha256_file(source_project)
    expected_sha256 = probe.get("sha256")
    if expected_sha256 is not None and expected_sha256 != source_project_sha256:
        raise ReconstructionError("Source project probe hash changed")
    progress_path = os.path.join(output_dir, "progress.json")
    result_path = os.path.join(output_dir, "source_project_load_result.json")
    catalog_path = os.path.join(output_dir, "filtered_morph_catalog.json")

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
    asset_inventory = avatar_asset_inventory(avatar)
    catalog_terms = probe.get("catalog_terms")
    catalog_report = None
    if catalog_terms is not None:
        catalog_report = capture_filtered_morph_catalog(
            avatar,
            catalog_terms,
        )
        write_json(catalog_report, catalog_path)
    source_project_after_sha256 = sha256_file(source_project)
    source_project_unchanged = (
        source_project_after_sha256 == source_project_sha256
    )
    result = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": source_project_unchanged,
        "diagnostic_mode": "source_project_load",
        "source_project": source_project,
        "source_project_sha256": source_project_sha256,
        "source_project_after_sha256": source_project_after_sha256,
        "source_project_unchanged": source_project_unchanged,
        "load_status": load_status,
        "avatar_count": len(avatars),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "asset_inventory": asset_inventory,
        "body_and_junction_fingerprint_sha256": vectors[
            "body_and_junction_fingerprint_sha256"
        ],
        "morph_catalog": (
            {
                "path": catalog_path,
                "filter_terms": catalog_report["filter_terms"],
                "matched_morph_count": catalog_report[
                    "matched_morph_count"
                ],
            }
            if catalog_report is not None
            else None
        ),
        "progress_path": progress_path,
        "summary_path": result_path,
    }
    write_json(result, result_path)
    mark_phase("complete")
    return result


def probe_outfit_component_resave(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("outfit_component_resave_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError(
            "outfit_component_resave_probe must be an object"
        )
    source_avatar_path = canonical_existing_file(
        probe.get("source_avatar"),
        "Outfit component source avatar",
    )
    target_project_path = canonical_existing_file(
        probe.get("target_project"),
        "Outfit component target project",
    )
    source_object_name = probe.get("source_object_name")
    output_basename = probe.get("output_basename")
    if not isinstance(source_object_name, str) or not source_object_name:
        raise ReconstructionError(
            "Outfit component source_object_name is invalid"
        )
    if (
        not isinstance(output_basename, str)
        or not output_basename
        or any(char in output_basename for char in '<>:"/\\|?*')
    ):
        raise ReconstructionError(
            "Outfit component output_basename is invalid"
        )

    progress_path = os.path.join(output_dir, "progress.json")
    result_path = os.path.join(
        output_dir,
        "outfit_component_resave_result.json",
    )
    def mark_phase(phase, detail=None):
        write_json(
            {
                "schema_version": 1,
                "updated_at": now(),
                "phase": phase,
                "detail": detail,
            },
            progress_path,
        )

    def status_report(status):
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
        return detail

    started_at = now()
    mark_phase("load_source_avatar", {"path": source_avatar_path})
    source_load_status = checked(
        "Load outfit component source avatar",
        RLPy.RFileIO.LoadFile(source_avatar_path),
    )
    source_avatar, source_avatars = resolve_avatar()
    if len(source_avatars) != 1:
        raise ReconstructionError(
            "Outfit component probe expected one source avatar"
        )
    matching_objects = [
        item
        for item in list(source_avatar.GetClothes() or [])
        if scene_object_name(item) == source_object_name
    ]
    if len(matching_objects) != 1:
        raise ReconstructionError(
            "Expected one source cloth named {}, found {}".format(
                source_object_name,
                len(matching_objects),
            )
        )
    source_object = matching_objects[0]
    original_clothe_type = source_object.GetClotheType()

    save_attempt_specs = (
        {
            "attempt_id": "component_gloves_component_selected",
            "save_object": source_object,
            "save_object_kind": "component",
            "selected_object": source_object,
            "selected_object_kind": "component",
            "clothe_type": original_clothe_type,
            "save_type": RLPy.ESaveFileType_Gloves,
            "extension": ".ccGloves",
        },
        {
            "attempt_id": "avatar_gloves_component_selected",
            "save_object": source_avatar,
            "save_object_kind": "avatar",
            "selected_object": source_object,
            "selected_object_kind": "component",
            "clothe_type": original_clothe_type,
            "save_type": RLPy.ESaveFileType_Gloves,
            "extension": ".ccGloves",
        },
        {
            "attempt_id": "avatar_gloves_avatar_selected",
            "save_object": source_avatar,
            "save_object_kind": "avatar",
            "selected_object": source_avatar,
            "selected_object_kind": "avatar",
            "clothe_type": original_clothe_type,
            "save_type": RLPy.ESaveFileType_Gloves,
            "extension": ".ccGloves",
        },
        {
            "attempt_id": "component_upper_component_selected",
            "save_object": source_object,
            "save_object_kind": "component",
            "selected_object": source_object,
            "selected_object_kind": "component",
            "clothe_type": RLPy.EClotheType_Upper,
            "save_type": RLPy.ESaveFileType_Upper,
            "extension": ".ccCloth",
        },
        {
            "attempt_id": "avatar_upper_component_selected",
            "save_object": source_avatar,
            "save_object_kind": "avatar",
            "selected_object": source_object,
            "selected_object_kind": "component",
            "clothe_type": RLPy.EClotheType_Upper,
            "save_type": RLPy.ESaveFileType_Upper,
            "extension": ".ccCloth",
        },
        {
            "attempt_id": "avatar_upper_avatar_selected",
            "save_object": source_avatar,
            "save_object_kind": "avatar",
            "selected_object": source_avatar,
            "selected_object_kind": "avatar",
            "clothe_type": RLPy.EClotheType_Upper,
            "save_type": RLPy.ESaveFileType_Upper,
            "extension": ".ccCloth",
        },
    )
    save_attempts = []
    try:
        for spec in save_attempt_specs:
            attempt_path = os.path.join(
                output_dir,
                "{}_{}{}".format(
                    output_basename,
                    spec["attempt_id"],
                    spec["extension"],
                ),
            )
            mark_phase(
                "save_component_attempt",
                {
                    "attempt_id": spec["attempt_id"],
                    "path": attempt_path,
                },
            )
            attempt = {
                "attempt_id": spec["attempt_id"],
                "save_object_kind": spec["save_object_kind"],
                "selected_object_kind": spec["selected_object_kind"],
                "clothe_type": int(spec["clothe_type"]),
                "save_type": int(spec["save_type"]),
                "path": attempt_path,
            }
            try:
                attempt["set_clothe_type_status"] = status_report(
                    source_object.SetClotheType(spec["clothe_type"])
                )
                attempt["clear_selection_status"] = status_report(
                    RLPy.RScene.ClearSelectObjects()
                )
                attempt["select_status"] = status_report(
                    RLPy.RScene.SelectObject(spec["selected_object"])
                )
                save_setting = RLPy.RSaveFileSetting()
                save_setting.SetSaveType(spec["save_type"])
                attempt["save_status"] = status_report(
                    RLPy.RFileIO.SaveFile(
                        spec["save_object"],
                        save_setting,
                        attempt_path,
                    )
                )
                settle_cc_ui(2.0)
            except Exception as exc:
                attempt["exception"] = "{}: {}".format(
                    type(exc).__name__,
                    exc,
                )
            if (
                os.path.isfile(attempt_path)
                and os.path.getsize(attempt_path) > 0
            ):
                attempt["file"] = {
                    "path": attempt_path,
                    "size_bytes": os.path.getsize(attempt_path),
                    "sha256": sha256_file(attempt_path),
                }
            else:
                attempt["file"] = None
            save_attempts.append(attempt)
    finally:
        restore_type_status = status_report(
            source_object.SetClotheType(original_clothe_type)
        )
        RLPy.RScene.ClearSelectObjects()
        RLPy.RScene.SelectObject(source_avatar)

    saved_attempts = [item for item in save_attempts if item["file"]]
    application_attempts = []
    for saved_attempt in saved_attempts:
        mark_phase(
            "apply_saved_component_attempt",
            {
                "attempt_id": saved_attempt["attempt_id"],
                "path": saved_attempt["path"],
            },
        )
        application = {
            "attempt_id": saved_attempt["attempt_id"],
            "path": saved_attempt["path"],
            "success": False,
        }
        try:
            application["target_load_status"] = checked(
                "Load outfit component target project",
                RLPy.RFileIO.LoadFile(target_project_path),
            )
            target_avatar, target_avatars = resolve_avatar()
            if len(target_avatars) != 1:
                raise ReconstructionError(
                    "Outfit component probe expected one target avatar"
                )
            existing_clothing_names = sorted(
                set(
                    scene_object_name(item)
                    for item in list(target_avatar.GetClothes() or [])
                )
            )
            target_avatar, cleanup = remove_base_clothing(
                target_avatar,
                existing_clothing_names,
                allow_missing=False,
            )
            before_inventory = avatar_asset_inventory(target_avatar)
            RLPy.RScene.ClearSelectObjects()
            RLPy.RScene.SelectObject(target_avatar)
            apply_status, apply_dialogs = (
                load_clothing_asset_with_known_dialogs(
                    saved_attempt["path"],
                    "Apply resaved outfit component",
                    "fit_body_shape",
                    record_step=False,
                )
            )
            settle_cc_ui(4.0)
            applied_avatar, applied_avatars = resolve_avatar()
            if len(applied_avatars) != 1:
                raise ReconstructionError(
                    "Resaved component changed avatar count"
                )
            after_inventory = avatar_asset_inventory(applied_avatar)
            inventory_changes = _outfit_gate_inventory_changes(
                before_inventory,
                after_inventory,
            )
            added_clothes = [
                item
                for item in inventory_changes["added"]
                if item["collection"] == "GetClothes"
            ]
            application.update(
                {
                    "success": len(added_clothes) == 1,
                    "target_clothing_cleanup": cleanup,
                    "apply_status": apply_status,
                    "apply_dialogs": apply_dialogs,
                    "inventory_before": before_inventory,
                    "inventory_after": after_inventory,
                    "inventory_changes": inventory_changes,
                    "added_clothes": added_clothes,
                }
            )
            if len(added_clothes) != 1:
                application["error"] = (
                    "Expected exactly one added cloth object"
                )
        except Exception as exc:
            application["error"] = "{}: {}".format(
                type(exc).__name__,
                exc,
            )
        application_attempts.append(application)

    viable_attempts = [
        item for item in application_attempts if item["success"]
    ]
    success = bool(viable_attempts)

    result = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "requested_count": len(save_attempt_specs),
        "success_count": len(viable_attempts),
        "failure_count": len(save_attempt_specs) - len(viable_attempts),
        "success": success,
        "diagnostic_mode": "outfit_component_resave",
        "source_avatar": source_avatar_path,
        "source_load_status": source_load_status,
        "source_object": {
            "name": source_object_name,
            "python_type": type(source_object).__name__,
            "original_clothe_type": int(original_clothe_type),
        },
        "save_attempts": save_attempts,
        "restore_type_status": restore_type_status,
        "target_project": target_project_path,
        "application_attempts": application_attempts,
        "viable_attempt_ids": [
            item["attempt_id"] for item in viable_attempts
        ],
        "summary_path": result_path,
    }
    write_json(result, result_path)
    mark_phase("complete", {"success": success})
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


def probe_face_prototype_storage(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    probe = library.get("face_prototype_storage_probe") or {}
    if not isinstance(probe, dict):
        raise ReconstructionError(
            "face_prototype_storage_probe must be an object"
        )
    source_project = canonical_existing_file(
        probe.get("source_project"),
        "Face prototype source project",
    )
    neutral_base = canonical_existing_file(
        probe.get("neutral_base"),
        "Face prototype neutral base",
    )
    target_profile = None
    if probe.get("target_facial_profile"):
        target_profile = canonical_existing_file(
            probe.get("target_facial_profile"),
            "Face prototype target Facial Profile",
        )
    subject_id = str(probe.get("subject_id") or "face_prototype").strip()
    if (
        not subject_id
        or any(char in subject_id for char in '<>:"/\\|?*')
    ):
        raise ReconstructionError("Face prototype subject_id is invalid")
    settle_seconds = float(probe.get("settle_seconds", 8.0))
    if settle_seconds < 0.0 or settle_seconds > 120.0:
        raise ReconstructionError(
            "Face prototype settle_seconds must be from 0 to 120"
        )
    supported_mode_ids = {
        "facial_profile_preset",
        "avatar_preset_all",
    }
    save_mode_ids = probe.get(
        "save_mode_ids", ["facial_profile_preset"]
    )
    if (
        not isinstance(save_mode_ids, list)
        or any(item not in supported_mode_ids for item in save_mode_ids)
        or len(save_mode_ids) != len(set(save_mode_ids))
    ):
        raise ReconstructionError(
            "Face prototype save_mode_ids are invalid"
        )
    existing_mode_files = probe.get("existing_mode_files") or {}
    if (
        not isinstance(existing_mode_files, dict)
        or any(item not in supported_mode_ids for item in existing_mode_files)
    ):
        raise ReconstructionError(
            "Face prototype existing_mode_files are invalid"
        )

    progress_path = os.path.join(output_dir, "progress.json")
    result_path = os.path.join(
        output_dir, "face_prototype_storage_report.json"
    )
    subject_dir = os.path.join(output_dir, subject_id)
    os.makedirs(subject_dir, exist_ok=True)
    source_vectors_path = os.path.join(subject_dir, "source_vectors.json")
    profile_path = os.path.join(subject_dir, "facial_profile.ccFacialProfile")
    source_project_record = bodyfit_freeze_file_record(source_project)

    def mark_phase(phase, details=None):
        payload = {
            "schema_version": 1,
            "diagnostic_mode": "face_prototype_storage",
            "subject_id": subject_id,
            "updated_at": now(),
            "phase": phase,
        }
        if details:
            payload["details"] = details
        write_json(payload, progress_path)

    def profile_summary(avatar):
        face_component = avatar.GetFaceComponent()
        profile_component = avatar.GetFacialProfileComponent()
        if face_component is None or profile_component is None:
            raise ReconstructionError(
                "Face prototype avatar has no facial components"
            )
        expressions = list(face_component.GetExpressionNames("") or [])
        return {
            "expression_set_uid": str(
                face_component.GetExpressionSetUid()
            ),
            "expression_count": len(expressions),
            "profile_type": str(profile_component.GetProfileType()),
        }

    def vector_deltas(reference, candidate):
        return {
            classification: group_delta(
                reference["groups"][classification]["entries"],
                candidate["groups"][classification]["entries"],
            )
            for classification in ("body", "junction", "face", "other")
        }

    started_at = now()
    report = {
        "schema_version": 1,
        "diagnostic_mode": "face_prototype_storage",
        "subject_id": subject_id,
        "started_at": started_at,
        "success": False,
        "source_project": source_project_record,
        "neutral_base": bodyfit_freeze_file_record(neutral_base),
        "target_facial_profile": (
            bodyfit_freeze_file_record(target_profile)
            if target_profile
            else None
        ),
        "application_policy": {
            "Apply Morph": True,
            "Apply Textures": False,
            "Restore neutral lash strip before application.": True,
        },
        "save_mode_ids": list(save_mode_ids),
        "existing_mode_files": dict(existing_mode_files),
        "modes": {},
    }
    write_json(report, result_path)

    mark_phase("load_source_project")
    source_load_status, source_dialogs = load_file_with_optional_undo_warning(
        source_project,
        "Load face prototype source {}".format(subject_id),
    )
    settle_cc_ui(settle_seconds)
    source_avatar, source_avatars = resolve_avatar()
    if len(source_avatars) != 1:
        raise ReconstructionError(
            "Face prototype storage expected one source avatar"
        )
    RLPy.RScene.SelectObject(source_avatar)
    force_avatar_scene_evaluation(source_avatar)
    if target_profile:
        mark_phase("load_target_facial_profile")
        source_profile_component = (
            source_avatar.GetFacialProfileComponent()
        )
        checked(
            "Load face prototype target Facial Profile",
            source_profile_component.LoadProfile(target_profile),
        )
        settle_cc_ui(settle_seconds)
        source_avatar, source_avatars = resolve_avatar()
        if len(source_avatars) != 1:
            raise ReconstructionError(
                "Face prototype Profile load expected one avatar"
            )
        RLPy.RScene.SelectObject(source_avatar)
        force_avatar_scene_evaluation(source_avatar)
    source_vectors = capture_vectors(source_avatar)
    write_json(source_vectors, source_vectors_path)
    source_profile = profile_summary(source_avatar)
    source_material = avatar_material_fingerprint(source_avatar)
    source_eye = capture_eye_integrity_state(source_avatar)
    report["source"] = {
        "load_status": source_load_status,
        "dialogs": source_dialogs,
        "profile": source_profile,
        "vector_counts": {
            classification: len(
                source_vectors["groups"][classification]["entries"]
            )
            for classification in ("body", "junction", "face", "other")
        },
        "vector_fingerprints": {
            classification: source_vectors["groups"][classification][
                "fingerprint_sha256"
            ]
            for classification in ("body", "junction", "face", "other")
        },
        "material_fingerprint": source_material,
        "eye_structure_signature": eye_integrity_structure_signature(
            source_eye
        ),
        "vectors": source_vectors_path,
    }

    mark_phase("save_facial_profile_sidecar")
    profile_component = source_avatar.GetFacialProfileComponent()
    checked(
        "Save face prototype Facial Profile",
        profile_component.SaveProfile(profile_path),
    )
    wait_for_rendered_preview(
        profile_path,
        timeout_seconds=300.0,
        stable_seconds=2.0,
    )
    report["facial_profile_sidecar"] = bodyfit_freeze_file_record(
        profile_path
    )

    mode_specs = (
        (
            "facial_profile_preset",
            RLPy.ESaveFileType_AvatarPresetFacialProfile,
            "facial_profile_preset.ccAvatarPreset",
        ),
        (
            "avatar_preset_all",
            RLPy.ESaveFileType_AvatarPresetAll,
            "identity_carrier.ccAvatarPreset",
        ),
    )
    saved_modes = []
    for mode_id, save_type, filename in mode_specs:
        if mode_id in existing_mode_files:
            preset_path = canonical_existing_file(
                existing_mode_files[mode_id],
                "Existing face prototype {}".format(mode_id),
            )
            saved_modes.append(
                {
                    "mode_id": mode_id,
                    "path": preset_path,
                    "save_status": {
                        "source": "existing_file",
                        "returned": False,
                        "is_error": False,
                    },
                    "file": bodyfit_freeze_file_record(preset_path),
                }
            )
            continue
        if mode_id not in save_mode_ids:
            continue
        mark_phase("save_{}".format(mode_id))
        preset_path = os.path.join(subject_dir, filename)
        save_setting = RLPy.RSaveFileSetting()
        save_setting.SetSaveType(save_type)
        save_status = checked(
            "Save face prototype {}".format(mode_id),
            RLPy.RFileIO.SaveFile(
                source_avatar,
                save_setting,
                preset_path,
            ),
        )
        wait_for_rendered_preview(
            preset_path,
            timeout_seconds=300.0,
            stable_seconds=2.0,
        )
        saved_modes.append(
            {
                "mode_id": mode_id,
                "path": preset_path,
                "save_status": save_status,
                "file": bodyfit_freeze_file_record(preset_path),
            }
        )

    checkbox_policy = dict(report["application_policy"])
    for saved_mode in saved_modes:
        mode_id = saved_mode["mode_id"]
        mark_phase("apply_{}_to_neutral".format(mode_id))
        neutral_avatar, base_attempts = load_base(neutral_base)
        settle_cc_ui(settle_seconds)
        RLPy.RScene.SelectObject(neutral_avatar)
        force_avatar_scene_evaluation(neutral_avatar)
        neutral_id = scene_object_id(neutral_avatar)
        baseline_vectors = capture_vectors(neutral_avatar)
        baseline_profile = profile_summary(neutral_avatar)
        baseline_material = avatar_material_fingerprint(neutral_avatar)
        baseline_eye = capture_eye_integrity_state(neutral_avatar)
        apply_status, apply_dialogs = load_file_with_known_cc_dialogs(
            saved_mode["path"],
            "Apply face prototype {}".format(mode_id),
            allow_character_preset=True,
            character_preset_checkbox_states=checkbox_policy,
        )
        settle_cc_ui(settle_seconds)
        applied_avatar, applied_avatars = resolve_avatar()
        if len(applied_avatars) != 1:
            raise ReconstructionError(
                "Face prototype application expected one avatar"
            )
        RLPy.RScene.SelectObject(applied_avatar)
        force_avatar_scene_evaluation(applied_avatar)
        applied_vectors = capture_vectors(applied_avatar)
        applied_profile = profile_summary(applied_avatar)
        applied_material = avatar_material_fingerprint(applied_avatar)
        applied_eye = capture_eye_integrity_state(applied_avatar)
        source_deltas = vector_deltas(source_vectors, applied_vectors)
        baseline_deltas = vector_deltas(
            baseline_vectors, applied_vectors
        )
        face_matches_source = not bool(source_deltas["face"])
        body_matches_source = not bool(
            source_deltas["body"] or source_deltas["junction"]
        )
        face_unchanged_from_baseline = not bool(
            baseline_deltas["face"]
        )
        body_unchanged_from_baseline = not bool(
            baseline_deltas["body"] or baseline_deltas["junction"]
        )
        profile_matches_source = bool(
            applied_profile["expression_set_uid"]
            == source_profile["expression_set_uid"]
            and applied_profile["expression_count"]
            == source_profile["expression_count"]
        )
        report["modes"][mode_id] = {
            "save_type": (
                "ESaveFileType_AvatarPresetFacialProfile"
                if mode_id == "facial_profile_preset"
                else "ESaveFileType_AvatarPresetAll"
            ),
            "file": saved_mode["file"],
            "save_status": saved_mode["save_status"],
            "base_load_attempts": base_attempts,
            "apply_status": apply_status,
            "apply_dialogs": apply_dialogs,
            "avatar_object_preserved": bool(
                scene_object_id(applied_avatar) == neutral_id
            ),
            "baseline_profile": baseline_profile,
            "applied_profile": applied_profile,
            "profile_matches_source": profile_matches_source,
            "face_matches_source": face_matches_source,
            "body_matches_source": body_matches_source,
            "face_unchanged_from_baseline": face_unchanged_from_baseline,
            "body_unchanged_from_baseline": body_unchanged_from_baseline,
            "material_unchanged_from_baseline": bool(
                applied_material["digest"]
                == baseline_material["digest"]
            ),
            "eye_structure_unchanged_from_baseline": bool(
                eye_integrity_structure_signature(applied_eye)
                == eye_integrity_structure_signature(baseline_eye)
            ),
            "source_deltas": source_deltas,
            "baseline_deltas": baseline_deltas,
        }
        write_json(report, result_path)

    profile_mode = report["modes"].get("facial_profile_preset")
    all_mode = report["modes"].get("avatar_preset_all")
    report["conclusion"] = {
        "facial_profile_preset_is_identity_carrier": bool(
            profile_mode
            and profile_mode["face_matches_source"]
            and not profile_mode["face_unchanged_from_baseline"]
        ),
        "avatar_preset_all_is_identity_carrier": bool(
            all_mode
            and all_mode["face_matches_source"]
            and not all_mode["face_unchanged_from_baseline"]
        ),
        "avatar_preset_all_preserves_target_body": bool(
            all_mode and all_mode["body_unchanged_from_baseline"]
        ),
        "facial_profile_sidecar_required": True,
    }
    source_project_after = bodyfit_freeze_file_record(source_project)
    report["source_project_after"] = source_project_after
    report["source_project_unchanged"] = bool(
        source_project_after["sha256"] == source_project_record["sha256"]
        and source_project_after["bytes"] == source_project_record["bytes"]
    )
    report["finished_at"] = now()
    report["success"] = bool(report["source_project_unchanged"])
    write_json(report, result_path)
    mark_phase("complete")
    return {
        "schema_version": 1,
        "diagnostic_mode": "face_prototype_storage",
        "started_at": started_at,
        "finished_at": report["finished_at"],
        "success": report["success"],
        "success_count": 1 if report["success"] else 0,
        "failure_count": 0 if report["success"] else 1,
        "report_path": result_path,
        "summary_path": result_path,
    }


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


def probe_current_full_body_camera_sweep(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Full-body camera sweep expected one avatar, found {}".format(
                len(avatars)
            )
        )
    camera_path = canonical_existing_file(
        library.get("camera_path"),
        "Full-body camera sweep camera",
    )
    lightroom_path = canonical_existing_file(
        library.get("preview_lightroom"),
        "Full-body camera sweep Lightroom",
    )
    candidates = library.get("framing_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ReconstructionError(
            "Full-body camera sweep framing candidates are missing"
        )
    checked(
        "Load full-body camera sweep Lightroom",
        RLPy.RFileIO.LoadFile(lightroom_path),
    )
    checked(
        "Load full-body camera sweep camera",
        RLPy.RFileIO.LoadFile(camera_path),
    )
    settle_cc_ui(1.0)
    camera = RLPy.RScene.GetCurrentCamera()
    if camera is None:
        raise ReconstructionError(
            "Full-body camera sweep has no active camera"
        )
    motion_cleanup = clear_avatar_motion(avatar)
    baseline_avatar_position = {
        "x": 0.0,
        "y": 8.0,
        "z": 6.0,
    }
    set_avatar_position(
        avatar,
        position_x=baseline_avatar_position["x"],
        position_y=baseline_avatar_position["y"],
        position_z=baseline_avatar_position["z"],
    )
    set_avatar_yaw(avatar, 90.0)
    force_avatar_scene_evaluation(avatar)
    light_objects = []
    light_query_errors = []
    seen_light_ids = set()
    for constant_name in (
        "EObjectType_Light",
        "EObjectType_SpotLight",
        "EObjectType_PointLight",
        "EObjectType_DirectionalLight",
    ):
        object_type = getattr(RLPy, constant_name, None)
        if object_type is None:
            continue
        try:
            candidates_for_type = list(
                RLPy.RScene.FindObjects(object_type) or []
            )
        except Exception as exc:
            light_query_errors.append(
                {"type": constant_name, "error": str(exc)}
            )
            continue
        for light in candidates_for_type:
            light_id = scene_object_id(light)
            if light_id in seen_light_ids:
                continue
            seen_light_ids.add(light_id)
            light_objects.append(light)
    movable_lights = []
    skipped_lights = []
    for light in light_objects:
        try:
            position = {
                "x": _transform_float(light, "Position/PositionX"),
                "y": _transform_float(light, "Position/PositionY"),
                "z": _transform_float(light, "Position/PositionZ"),
            }
        except Exception as exc:
            skipped_lights.append(
                {
                    "id": scene_object_id(light),
                    "name": scene_object_name(light),
                    "python_type": type(light).__name__,
                    "error": str(exc),
                }
            )
            continue
        movable_lights.append(
            {
                "object": light,
                "id": scene_object_id(light),
                "name": scene_object_name(light),
                "python_type": type(light).__name__,
                "position": position,
            }
        )
    if not movable_lights:
        raise ReconstructionError(
            "Full-body camera sweep found no movable Lightroom lights: {}"
            .format(light_query_errors + skipped_lights)
        )
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "full_body_camera_sweep",
        "camera_path": camera_path,
        "preview_lightroom": lightroom_path,
        "initial_camera": camera_state(camera),
        "motion_cleanup": motion_cleanup,
        "baseline_avatar_position": baseline_avatar_position,
        "movable_lights": [
            dict(
                (key, value)
                for key, value in item.items()
                if key != "object"
            )
            for item in movable_lights
        ],
        "skipped_lights": skipped_lights,
        "light_query_errors": light_query_errors,
        "candidates": [],
    }
    try:
        for item in candidates:
            candidate_id = item.get("id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ReconstructionError(
                    "Full-body camera sweep candidate has no ID"
                )
            avatar_position = {
                axis: float(item.get(axis, 0.0))
                for axis in ("x", "y", "z")
            }
            offset = {
                axis: avatar_position[axis] - baseline_avatar_position[axis]
                for axis in ("x", "y", "z")
            }
            set_avatar_position(
                avatar,
                position_x=avatar_position["x"],
                position_y=avatar_position["y"],
                position_z=avatar_position["z"],
            )
            for light_record in movable_lights:
                base = light_record["position"]
                set_avatar_position(
                    light_record["object"],
                    position_x=base["x"] + offset["x"],
                    position_y=base["y"] + offset["y"],
                    position_z=base["z"] + offset["z"],
                )
            force_avatar_scene_evaluation(avatar)
            checked(
                "Activate full-body sweep camera {}".format(candidate_id),
                RLPy.RScene.SetCurrentCamera(camera),
            )
            image_path = os.path.join(
                output_dir,
                "camera_{}.png".format(candidate_id),
            )
            render_preview(image_path)
            report["candidates"].append(
                {
                    "id": candidate_id,
                    "avatar_position": avatar_position,
                    "light_offset": offset,
                    "image": image_path,
                    "camera": camera_state(camera),
                }
            )
    finally:
        set_avatar_position(
            avatar,
            position_x=baseline_avatar_position["x"],
            position_y=baseline_avatar_position["y"],
            position_z=baseline_avatar_position["z"],
        )
        for light_record in movable_lights:
            base = light_record["position"]
            set_avatar_position(
                light_record["object"],
                position_x=base["x"],
                position_y=base["y"],
                position_z=base["z"],
            )
        force_avatar_scene_evaluation(avatar)
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
        "diagnostic_mode": "full_body_camera_sweep",
        "camera_sweep_path": report_path,
        "summary_path": report_path,
        "scene_policy": "leave_current_scene_motionless_for_next_load",
    }


def probe_current_timeline_state(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Timeline probe expected one avatar, found {}".format(
                len(avatars)
            )
        )
    fps = RLPy.RGlobal.GetFps()
    start_time = RLPy.RGlobal.GetStartTime()
    end_time = RLPy.RGlobal.GetEndTime()
    current_time = RLPy.RGlobal.GetTime()
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": now(),
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "timeline_state",
        "subject": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "timeline": {
            "start_frame": int(fps.GetFrameIndex(start_time)),
            "end_frame": int(fps.GetFrameIndex(end_time)),
            "current_frame": int(fps.GetFrameIndex(current_time)),
        },
        "motion_inventory": avatar_motion_inventory(avatar),
        "scene_policy": "read_only",
    }


def character_quality_benchmark_artifacts(subject_dir):
    return {
        "neutral_front": os.path.join(subject_dir, "neutral_front.png"),
        "neutral_three_quarter": os.path.join(
            subject_dir, "neutral_three_quarter.png"
        ),
        "neutral_profile": os.path.join(subject_dir, "neutral_profile.png"),
        "full_body_front": os.path.join(subject_dir, "full_body_front.png"),
        "facial_pose_validation": os.path.join(
            subject_dir, "facial_pose_validation.json"
        ),
        "face_blink_bilateral_preview": os.path.join(
            subject_dir, "blink_bilateral_front.png"
        ),
        "face_blink_left_preview": os.path.join(
            subject_dir, "blink_left_front.png"
        ),
        "face_blink_right_preview": os.path.join(
            subject_dir, "blink_right_front.png"
        ),
        "face_look_left_preview": os.path.join(
            subject_dir, "look_left_front.png"
        ),
        "face_look_right_preview": os.path.join(
            subject_dir, "look_right_front.png"
        ),
        "face_look_up_preview": os.path.join(
            subject_dir, "look_up_front.png"
        ),
        "face_look_down_preview": os.path.join(
            subject_dir, "look_down_front.png"
        ),
        "face_squint_preview": os.path.join(
            subject_dir, "squint_bilateral_front.png"
        ),
        "face_widen_preview": os.path.join(
            subject_dir, "widen_bilateral_front.png"
        ),
        "face_brow_raise_preview": os.path.join(
            subject_dir, "brow_raise_front.png"
        ),
        "face_brow_down_preview": os.path.join(
            subject_dir, "brow_down_front.png"
        ),
        "face_brow_raise_left_preview": os.path.join(
            subject_dir, "brow_raise_left_front.png"
        ),
        "face_smile_preview": os.path.join(subject_dir, "smile_front.png"),
        "face_jaw_open_preview": os.path.join(
            subject_dir, "jaw_open_front.png"
        ),
        "face_jaw_open_three_quarter_preview": os.path.join(
            subject_dir, "jaw_open_three_quarter.png"
        ),
        "face_post_pose_neutral_preview": os.path.join(
            subject_dir, "post_pose_neutral_front.png"
        ),
    }


def _quality_benchmark_position(value, label):
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(
            isinstance(item, bool) or not isinstance(item, (int, float))
            for item in value
        )
    ):
        raise ReconstructionError(
            "{} must contain three numeric coordinates".format(label)
        )
    return [float(item) for item in value]


def _quality_benchmark_file_record(path):
    return {
        "bytes": os.path.getsize(path),
        "path": path,
        "sha256": sha256_file(path),
    }


def quality_benchmark_movable_lights():
    light_objects = []
    query_errors = []
    seen_ids = set()
    for constant_name in (
        "EObjectType_Light",
        "EObjectType_SpotLight",
        "EObjectType_PointLight",
        "EObjectType_DirectionalLight",
    ):
        object_type = getattr(RLPy, constant_name, None)
        if object_type is None:
            continue
        try:
            objects = list(RLPy.RScene.FindObjects(object_type) or [])
        except Exception as exc:
            query_errors.append(
                {"type": constant_name, "error": str(exc)}
            )
            continue
        for light in objects:
            light_id = scene_object_id(light)
            if light_id in seen_ids:
                continue
            seen_ids.add(light_id)
            light_objects.append(light)

    movable = []
    skipped = []
    for light in light_objects:
        try:
            position = {
                "x": _transform_float(light, "Position/PositionX"),
                "y": _transform_float(light, "Position/PositionY"),
                "z": _transform_float(light, "Position/PositionZ"),
            }
        except Exception as exc:
            skipped.append(
                {
                    "id": scene_object_id(light),
                    "name": scene_object_name(light),
                    "python_type": type(light).__name__,
                    "error": str(exc),
                }
            )
            continue
        movable.append(
            {
                "object": light,
                "id": scene_object_id(light),
                "name": scene_object_name(light),
                "python_type": type(light).__name__,
                "position": position,
            }
        )
    return movable, skipped, query_errors


def set_quality_benchmark_light_offset(movable_lights, offset):
    for light_record in movable_lights:
        base = light_record["position"]
        set_avatar_position(
            light_record["object"],
            position_x=base["x"] + float(offset["x"]),
            position_y=base["y"] + float(offset["y"]),
            position_z=base["z"] + float(offset["z"]),
        )


def probe_character_quality_benchmark_v1(library, output_dir, log):
    os.makedirs(output_dir, exist_ok=True)
    benchmark = library.get("quality_benchmark") or {}
    if not isinstance(benchmark, dict):
        raise ReconstructionError("quality_benchmark must be an object")
    subject = benchmark.get("subject") or {}
    if not isinstance(subject, dict):
        raise ReconstructionError("quality_benchmark.subject must be an object")
    subject_id = subject.get("id")
    if (
        not isinstance(subject_id, str)
        or not subject_id
        or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in subject_id)
    ):
        raise ReconstructionError(
            "quality_benchmark.subject.id must be a lowercase file-safe ID"
        )
    source_project = canonical_existing_file(
        subject.get("source_project"),
        "Quality benchmark source project",
    )
    camera_path = canonical_existing_file(
        benchmark.get("face_camera"),
        "Quality benchmark face camera",
    )
    lightroom_path = canonical_existing_file(
        benchmark.get("preview_lightroom"),
        "Quality benchmark Lightroom",
    )
    face_position = _quality_benchmark_position(
        benchmark.get("face_position", [0.0, 8.0, 6.0]),
        "quality_benchmark.face_position",
    )
    full_body_position = _quality_benchmark_position(
        benchmark.get("full_body_position", [-600.0, 8.0, 75.0]),
        "quality_benchmark.full_body_position",
    )
    pose_ids = benchmark.get(
        "pose_ids",
        ["blink_bilateral_front", "smile_front", "jaw_open_front"],
    )
    if (
        not isinstance(pose_ids, list)
        or not pose_ids
        or any(not isinstance(item, str) or not item for item in pose_ids)
    ):
        raise ReconstructionError(
            "quality_benchmark.pose_ids must be a non-empty string list"
        )
    load_settle_seconds = float(subject.get("load_settle_seconds", 12.0))
    if load_settle_seconds < 0.0 or load_settle_seconds > 120.0:
        raise ReconstructionError(
            "quality_benchmark load_settle_seconds must be from 0 to 120"
        )

    subject_dir = os.path.join(output_dir, subject_id)
    os.makedirs(subject_dir, exist_ok=False)
    artifacts = character_quality_benchmark_artifacts(subject_dir)
    progress_path = os.path.join(output_dir, "progress.json")
    report_path = os.path.join(output_dir, "subject_benchmark.json")
    started_at = now()

    def mark_phase(phase, details=None):
        payload = {
            "schema_version": 1,
            "updated_at": now(),
            "diagnostic_mode": "character_quality_benchmark",
            "subject_id": subject_id,
            "phase": phase,
        }
        if details:
            payload["details"] = details
        write_json(payload, progress_path)
        log("Quality benchmark {}: {}".format(subject_id, phase))
        QtWidgets.QApplication.processEvents()

    report = {
        "schema_version": 1,
        "diagnostic_mode": "character_quality_benchmark",
        "subject_id": subject_id,
        "started_at": started_at,
        "success": False,
        "conditions": {
            "preview_capture_mode": PREVIEW_CAPTURE_MODE,
            "preview_resolution": [
                VIEWPORT_PREVIEW_WIDTH,
                VIEWPORT_PREVIEW_HEIGHT,
            ],
            "face_camera": camera_path,
            "preview_lightroom": lightroom_path,
            "face_position": face_position,
            "full_body_position": full_body_position,
            "static_views": {
                "neutral_front": 90.0,
                "neutral_three_quarter": 45.0,
                "neutral_profile": 0.0,
                "full_body_front": 90.0,
            },
            "pose_ids": list(pose_ids),
        },
        "source_project": _quality_benchmark_file_record(source_project),
        "progress_path": progress_path,
        "summary_path": report_path,
    }
    write_json(report, report_path)

    mark_phase("load_source_project", {"path": source_project})
    load_status, load_dialogs = load_file_with_optional_undo_warning(
        source_project,
        "Load quality benchmark source {}".format(subject_id),
    )
    settle_cc_ui(load_settle_seconds)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Quality benchmark expected one avatar for {}, found {}".format(
                subject_id, len(avatars)
            )
        )
    RLPy.RScene.SelectObject(avatar)
    checked(
        "Evaluate quality benchmark project start",
        RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
    )
    report["source_load"] = {
        "status": load_status,
        "dialogs": load_dialogs,
        "settle_seconds": load_settle_seconds,
    }

    mark_phase("load_standard_lightroom")
    checked(
        "Load quality benchmark Lightroom",
        RLPy.RFileIO.LoadFile(lightroom_path),
    )
    settle_cc_ui(1.0)
    mark_phase("load_standard_camera")
    checked(
        "Load quality benchmark camera",
        RLPy.RFileIO.LoadFile(camera_path),
    )
    settle_cc_ui(1.0)
    if RLPy.RScene.GetCurrentCamera() is None:
        raise ReconstructionError("Quality benchmark has no active camera")

    set_avatar_position(
        avatar,
        position_x=face_position[0],
        position_y=face_position[1],
        position_z=face_position[2],
    )
    set_avatar_yaw(avatar, 90.0)
    force_avatar_scene_evaluation(avatar)
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Quality benchmark subject has no Facial Profile: {}".format(
                subject_id
            )
        )
    mark_phase("capture_subject_inventory")
    standardized_bounds = capture_bounds(avatar)
    report["subject"] = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
            "python_type": type(avatar).__name__,
        },
        "bounds": standardized_bounds,
        "height_cm": bodyfit_height_cm(standardized_bounds),
        "asset_inventory": avatar_asset_inventory(avatar),
        "avatar_part_inventory": avatar_part_inventory(avatar),
        "motion_inventory": avatar_motion_inventory(avatar),
        "facial_profile": {
            "expression_count": len(
                list(face_component.GetExpressionNames("") or [])
            ),
            "expression_clip_count": int(face_component.GetClipCount()),
            "expression_set_uid": str(face_component.GetExpressionSetUid()),
        },
        "material_fingerprint": avatar_material_fingerprint(avatar),
        "material_structure": avatar_material_structure(avatar),
        "neutral_eye_state": capture_eye_integrity_state(avatar),
    }
    report["camera"] = camera_state(RLPy.RScene.GetCurrentCamera())
    write_json(report, report_path)

    static_specs = (
        ("neutral_front", 90.0),
        ("neutral_three_quarter", 45.0),
        ("neutral_profile", 0.0),
    )
    report["static_captures"] = {}
    for capture_id, yaw_degrees in static_specs:
        set_avatar_yaw(avatar, yaw_degrees)
        mark_phase("render_{}".format(capture_id))
        render_preview(artifacts[capture_id])
        report["static_captures"][capture_id] = (
            _quality_benchmark_file_record(artifacts[capture_id])
        )

    set_avatar_position(
        avatar,
        position_x=full_body_position[0],
        position_y=full_body_position[1],
        position_z=full_body_position[2],
    )
    set_avatar_yaw(avatar, 90.0)
    mark_phase("render_full_body_front")
    render_preview(artifacts["full_body_front"])
    report["static_captures"]["full_body_front"] = (
        _quality_benchmark_file_record(artifacts["full_body_front"])
    )
    set_avatar_position(
        avatar,
        position_x=face_position[0],
        position_y=face_position[1],
        position_z=face_position[2],
    )
    set_avatar_yaw(avatar, 90.0)
    force_avatar_scene_evaluation(avatar)
    write_json(report, report_path)

    mark_phase("render_expression_matrix")
    pose_report = render_face_identity_safety_previews(
        avatar,
        artifacts,
        mark_phase,
        pose_ids=pose_ids,
    )
    report["facial_pose_validation"] = {
        "path": artifacts["facial_pose_validation"],
        "pose_count": len(pose_report.get("poses") or []),
        "neutral_eye_integrity": pose_report.get("neutral_eye_integrity"),
        "snapshot": pose_report.get("snapshot"),
    }
    report["dynamic_captures"] = {}
    for pose in pose_report.get("poses") or []:
        pose_id = pose["pose_id"]
        report["dynamic_captures"][pose_id] = (
            _quality_benchmark_file_record(pose["image"])
        )
    report["dynamic_captures"]["post_pose_neutral_front"] = (
        _quality_benchmark_file_record(
            artifacts["face_post_pose_neutral_preview"]
        )
    )
    report["finished_at"] = now()
    report["success"] = True
    write_json(report, report_path)
    mark_phase("complete")
    capture_count = len(report["static_captures"]) + len(
        report["dynamic_captures"]
    )
    return {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "diagnostic_mode": "character_quality_benchmark",
        "subject_id": subject_id,
        "started_at": started_at,
        "finished_at": report["finished_at"],
        "requested_count": capture_count,
        "success_count": capture_count,
        "failure_count": 0,
        "success": True,
        "subject_benchmark_path": report_path,
        "summary_path": report_path,
        "scene_policy": "leave_restored_subject_loaded",
    }


def resolve_quality_benchmark_targets(expression_names):
    expression_names = list(expression_names or [])
    teeth = resolve_teeth_expression_targets(expression_names)
    blink_targets = []
    required_blink_ids = ("blink_left", "blink_right")
    for target_id in required_blink_ids:
        resolved = first_expression_alias(
            expression_names,
            EYELASH_EXPRESSION_ALIASES[target_id],
        )
        if resolved is None:
            raise ReconstructionError(
                "Unable to resolve quality benchmark expression target: {}"
                .format(target_id)
            )
        blink_targets.append(resolved)

    optional_blink_ids = (
        "blink_corrective_left",
        "blink_corrective_right",
        "lash_down_inner_left",
        "lash_down_outer_left",
        "lash_down_inner_right",
        "lash_down_outer_right",
    )
    available_optional = []
    missing_optional = []
    for target_id in optional_blink_ids:
        resolved = first_expression_alias(
            expression_names,
            EYELASH_EXPRESSION_ALIASES[target_id],
        )
        if resolved is None:
            missing_optional.append(target_id)
        else:
            available_optional.append(resolved)
            blink_targets.append(resolved)
    return {
        "blink_bilateral": blink_targets,
        "blink_correction_mode": (
            "base_plus_available_correctives"
            if available_optional
            else "base_profile_only"
        ),
        "available_optional_blink_targets": available_optional,
        "missing_optional_blink_target_ids": missing_optional,
        "jaw_open": teeth["jaw_open"],
        "oral_reveal": teeth["oral_reveal"],
        "smile": teeth["smile"],
    }


def _quality_benchmark_pose_specs(expression_names):
    targets = resolve_quality_benchmark_targets(expression_names)

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
    for target_id, expression_name in targets["oral_reveal"].items():
        jaw_weights[expression_name] = reveal_strengths[target_id]
    return {
        "blink_bilateral_front": uniform_weights(
            targets["blink_bilateral"], 1.0
        ),
        "smile_front": smile_weights,
        "jaw_open_front": jaw_weights,
    }, targets


def profile_upgrade_pose_specs(expression_names):
    targets = resolve_quality_benchmark_targets(expression_names)
    support = {}
    for target_id, aliases in NATURAL_SMILE_SUPPORT_ALIASES.items():
        resolved = first_expression_alias(expression_names, aliases)
        if resolved is not None:
            support[target_id] = resolved

    def smile_pose(smile, cheek, squint, jaw):
        weights = dict(
            (name, float(smile)) for name in targets["smile"]
        )
        for target_id in ("cheek_raise_left", "cheek_raise_right"):
            if target_id in support:
                weights[support[target_id]] = float(cheek)
        for target_id in ("squint_inner_left", "squint_inner_right"):
            if target_id in support:
                weights[support[target_id]] = float(squint)
        if jaw > 0.0:
            weights[targets["jaw_open"]] = float(jaw)
        return weights

    jaw_weights = {targets["jaw_open"]: 0.55}
    reveal_strengths = {
        "upper_lip_raise_left": 0.25,
        "upper_lip_raise_right": 0.25,
        "lower_lip_depress_left": 0.35,
        "lower_lip_depress_right": 0.35,
        "stretch_left": 0.2,
        "stretch_right": 0.2,
    }
    for target_id, expression_name in targets["oral_reveal"].items():
        jaw_weights[expression_name] = reveal_strengths[target_id]

    targets["natural_smile_support"] = support
    return {
        "blink_bilateral_front": dict(
            (name, 1.0) for name in targets["blink_bilateral"]
        ),
        "smile_subtle_front": smile_pose(0.32, 0.12, 0.04, 0.0),
        "smile_medium_front": smile_pose(0.52, 0.22, 0.08, 0.04),
        "smile_broad_front": smile_pose(0.72, 0.32, 0.12, 0.10),
        "jaw_open_front": jaw_weights,
    }, targets


def render_profile_upgrade_pose_matrix(
    avatar,
    output_dir,
    mark_phase,
    neutral_time,
    face_position,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Profile upgrade subject has no face component"
        )
    expression_names = list(face_component.GetExpressionNames("") or [])
    pose_specs, targets = profile_upgrade_pose_specs(expression_names)
    fps = RLPy.RGlobal.GetFps()
    interval = RLPy.IndexedFrameTime(0, fps)
    expression_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )
    neutral_weights = [0.0] * len(expression_names)
    checked(
        "Begin profile upgrade initial neutral editing",
        face_component.BeginKeyEditing(),
    )
    try:
        checked(
            "Write profile upgrade initial neutral key",
            face_component.AddExpressionKeys(
                neutral_time,
                expression_names,
                neutral_weights,
                interval,
            ),
        )
    finally:
        checked(
            "End profile upgrade initial neutral editing",
            face_component.EndKeyEditing(),
        )
    checked(
        "Evaluate profile upgrade initial neutral",
        RLPy.RGlobal.SetTime(neutral_time, True),
    )
    set_avatar_position(
        avatar,
        position_x=face_position[0],
        position_y=face_position[1],
        position_z=face_position[2],
    )
    set_avatar_yaw(avatar, 90.0)
    force_avatar_scene_evaluation(avatar)
    neutral_eye_state, neutral_stabilization = (
        capture_stable_neutral_eye_state(avatar)
    )
    report = {
        "schema_version": 1,
        "profile": "cc5_hd_tiered_natural_smile_v1",
        "expression_set_uid": str(face_component.GetExpressionSetUid()),
        "expression_count": len(expression_names),
        "available_expression_names": expression_names,
        "resolved_targets": targets,
        "neutral_eye_capture_stabilization_before": neutral_stabilization,
        "poses": [],
    }
    for pose_id, target_weights in pose_specs.items():
        weights = list(neutral_weights)
        for expression_name, weight in target_weights.items():
            if expression_name not in expression_index:
                raise ReconstructionError(
                    "Profile upgrade expression disappeared: {}".format(
                        expression_name
                    )
                )
            weights[expression_index[expression_name]] = float(weight)
        checked(
            "Begin profile upgrade {} editing".format(pose_id),
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Write profile upgrade {} key".format(pose_id),
                face_component.AddExpressionKeys(
                    neutral_time,
                    expression_names,
                    weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End profile upgrade {} editing".format(pose_id),
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate profile upgrade {}".format(pose_id),
            RLPy.RGlobal.SetTime(neutral_time, True),
        )
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1],
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, 90.0)
        force_avatar_scene_evaluation(avatar)
        image_path = os.path.join(output_dir, "{}.png".format(pose_id))
        mark_phase("render_{}".format(pose_id))
        render_preview(image_path, neutral_time)
        evaluated_names = sorted(target_weights)
        report["poses"].append(
            {
                "pose_id": pose_id,
                "image": image_path,
                "target_weights": dict(sorted(target_weights.items())),
                "evaluated_expression_weights": dict(
                    zip(
                        evaluated_names,
                        expression_weights_at(
                            face_component,
                            neutral_time,
                            evaluated_names,
                        ),
                    )
                ),
                "capture": _quality_benchmark_file_record(image_path),
            }
        )

    checked(
        "Begin profile upgrade neutral restore editing",
        face_component.BeginKeyEditing(),
    )
    try:
        checked(
            "Write profile upgrade neutral restore key",
            face_component.AddExpressionKeys(
                neutral_time,
                expression_names,
                neutral_weights,
                interval,
            ),
        )
    finally:
        checked(
            "End profile upgrade neutral restore editing",
            face_component.EndKeyEditing(),
        )
    checked(
        "Evaluate profile upgrade restored neutral",
        RLPy.RGlobal.SetTime(neutral_time, True),
    )
    set_avatar_position(
        avatar,
        position_x=face_position[0],
        position_y=face_position[1],
        position_z=face_position[2],
    )
    set_avatar_yaw(avatar, 90.0)
    force_avatar_scene_evaluation(avatar)
    neutral_path = os.path.join(output_dir, "post_pose_neutral_front.png")
    mark_phase("render_post_pose_neutral_front")
    render_preview(neutral_path, neutral_time)
    report["post_pose_neutral_capture"] = _quality_benchmark_file_record(
        neutral_path
    )
    neutral_eye_after, neutral_stabilization_after = (
        capture_stable_neutral_eye_state(avatar)
    )
    report["neutral_eye_capture_stabilization_after"] = (
        neutral_stabilization_after
    )
    report["neutral_eye_integrity"] = compare_neutral_eye_states(
        neutral_eye_state,
        neutral_eye_after,
        include_world=True,
        include_runtime_ids=False,
        t_pose_tolerance=0.5,
    )
    liveness = []
    for pose in report["poses"]:
        rmse = rendered_image_rmse(
            pose["image"],
            neutral_path,
        )
        liveness.append(
            {
                "pose_id": pose["pose_id"],
                "rmse": rmse,
                "matches": rmse >= FACE_EVIDENCE_MIN_RMSE,
            }
        )
    report["evidence_liveness"] = {
        "minimum_rmse": FACE_EVIDENCE_MIN_RMSE,
        "poses": liveness,
        "status": (
            "passed"
            if liveness and all(item["matches"] for item in liveness)
            else "failed"
        ),
    }
    report_path = os.path.join(output_dir, "facial_pose_validation.json")
    write_json(report, report_path)
    if not report["neutral_eye_integrity"]["matches"]:
        raise ReconstructionError(
            "Profile upgrade pose matrix changed neutral eye state"
        )
    if report["evidence_liveness"]["status"] != "passed":
        raise ReconstructionError(
            "Profile upgrade pose evidence did not differ from neutral"
        )
    return report


def render_quality_benchmark_pose_matrix(
    avatar,
    artifacts,
    mark_phase,
    neutral_time,
    expression_names,
    pose_ids,
    face_position,
):
    face_component = avatar.GetFaceComponent()
    if face_component is None:
        raise ReconstructionError(
            "Quality benchmark character has no face component"
        )
    pose_specs, targets = _quality_benchmark_pose_specs(expression_names)
    unknown_pose_ids = sorted(set(pose_ids) - set(pose_specs))
    if unknown_pose_ids:
        raise ReconstructionError(
            "Unknown quality benchmark pose IDs: {}".format(
                unknown_pose_ids
            )
        )
    fps = RLPy.RGlobal.GetFps()
    interval = RLPy.IndexedFrameTime(0, fps)
    neutral_frame = int(fps.GetFrameIndex(neutral_time))
    neutral_weights = [0.0] * len(expression_names)
    expression_index = dict(
        (name, index) for index, name in enumerate(expression_names)
    )
    neutral_eye_state, neutral_eye_stabilization = (
        capture_stable_neutral_eye_state(avatar)
    )
    report = {
        "schema_version": 1,
        "profile": "matched_condition_existing_face_clip_v1",
        "available_expression_names": list(expression_names),
        "expression_count": len(expression_names),
        "resolved_targets": targets,
        "neutral_eye_capture_stabilization_before": (
            neutral_eye_stabilization
        ),
        "neutral_frame": neutral_frame,
        "poses": [],
    }
    pose_artifact_keys = {
        "blink_bilateral_front": "face_blink_bilateral_preview",
        "smile_front": "face_smile_preview",
        "jaw_open_front": "face_jaw_open_preview",
    }
    for pose_id in pose_ids:
        pose_frame = neutral_frame
        pose_time = neutral_time
        weights = list(neutral_weights)
        target_weights = pose_specs[pose_id]
        for expression_name, weight in target_weights.items():
            if expression_name not in expression_index:
                raise ReconstructionError(
                    "Quality benchmark expression disappeared: {}".format(
                        expression_name
                    )
                )
            weights[expression_index[expression_name]] = float(weight)
        checked(
            "Begin quality benchmark {} editing".format(pose_id),
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Write quality benchmark {} key".format(pose_id),
                face_component.AddExpressionKeys(
                    pose_time,
                    expression_names,
                    weights,
                    interval,
                ),
            )
        finally:
            checked(
                "End quality benchmark {} editing".format(pose_id),
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate quality benchmark {}".format(pose_id),
            RLPy.RGlobal.SetTime(pose_time, True),
        )
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1],
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, 90.0)
        force_avatar_scene_evaluation(avatar)
        image_path = artifacts[pose_artifact_keys[pose_id]]
        mark_phase("render_quality_benchmark_{}".format(pose_id))
        render_preview(image_path, pose_time)
        evaluated_names = sorted(target_weights)
        report["poses"].append(
            {
                "pose_id": pose_id,
                "frame": pose_frame,
                "image": image_path,
                "target_weights": dict(sorted(target_weights.items())),
                "evaluated_expression_weights": dict(
                    zip(
                        evaluated_names,
                        expression_weights_at(
                            face_component,
                            pose_time,
                            evaluated_names,
                        ),
                    )
                ),
                "capture": _quality_benchmark_file_record(image_path),
            }
        )

    post_neutral_frame = neutral_frame
    post_neutral_time = neutral_time
    checked(
        "Begin quality benchmark neutral restore editing",
        face_component.BeginKeyEditing(),
    )
    try:
        checked(
            "Write quality benchmark neutral restore key",
            face_component.AddExpressionKeys(
                post_neutral_time,
                expression_names,
                neutral_weights,
                interval,
            ),
        )
    finally:
        checked(
            "End quality benchmark neutral restore editing",
            face_component.EndKeyEditing(),
        )
    checked(
        "Evaluate quality benchmark restored neutral",
        RLPy.RGlobal.SetTime(post_neutral_time, True),
    )
    set_avatar_position(
        avatar,
        position_x=face_position[0],
        position_y=face_position[1],
        position_z=face_position[2],
    )
    set_avatar_yaw(avatar, 90.0)
    force_avatar_scene_evaluation(avatar)
    mark_phase("render_quality_benchmark_post_pose_neutral")
    render_preview(
        artifacts["face_post_pose_neutral_preview"],
        post_neutral_time,
    )
    report["post_pose_neutral_frame"] = post_neutral_frame
    report["post_pose_neutral_image"] = artifacts[
        "face_post_pose_neutral_preview"
    ]
    report["post_pose_neutral_capture"] = (
        _quality_benchmark_file_record(
            artifacts["face_post_pose_neutral_preview"]
        )
    )
    neutral_eye_state_after, neutral_eye_stabilization_after = (
        capture_stable_neutral_eye_state(avatar)
    )
    report["neutral_eye_capture_stabilization_after"] = (
        neutral_eye_stabilization_after
    )
    report["neutral_eye_integrity"] = compare_neutral_eye_states(
        neutral_eye_state,
        neutral_eye_state_after,
        include_world=True,
        include_runtime_ids=False,
        t_pose_tolerance=0.5,
    )
    if not report["neutral_eye_integrity"]["matches"]:
        write_json(report, artifacts["facial_pose_validation"])
        raise ReconstructionError(
            "Quality benchmark pose matrix changed neutral eye state"
        )
    liveness_records = []
    for pose_record in report["poses"]:
        rmse = rendered_image_rmse(
            pose_record["image"],
            report["post_pose_neutral_image"],
        )
        liveness_records.append(
            {
                "pose_id": pose_record["pose_id"],
                "rmse": rmse,
                "matches": rmse >= FACE_EVIDENCE_MIN_RMSE,
            }
        )
    report["evidence_liveness"] = {
        "minimum_rmse": FACE_EVIDENCE_MIN_RMSE,
        "poses": liveness_records,
        "reference_image": report["post_pose_neutral_image"],
        "status": (
            "passed"
            if liveness_records
            and all(item["matches"] for item in liveness_records)
            else "failed"
        ),
    }
    write_json(report, artifacts["facial_pose_validation"])
    if report["evidence_liveness"]["status"] != "passed":
        raise ReconstructionError(
            "Quality benchmark expression evidence did not differ from neutral"
        )
    return report


def probe_character_quality_benchmark(library, output_dir, log):
    os.makedirs(output_dir, exist_ok=True)
    benchmark = library.get("quality_benchmark") or {}
    if not isinstance(benchmark, dict):
        raise ReconstructionError("quality_benchmark must be an object")
    subject = benchmark.get("subject") or {}
    if not isinstance(subject, dict):
        raise ReconstructionError("quality_benchmark.subject must be an object")
    subject_id = subject.get("id")
    if (
        not isinstance(subject_id, str)
        or not subject_id
        or any(
            char not in "abcdefghijklmnopqrstuvwxyz0123456789_-"
            for char in subject_id
        )
    ):
        raise ReconstructionError(
            "quality_benchmark.subject.id must be a lowercase file-safe ID"
        )
    source_project = canonical_existing_file(
        subject.get("source_project"),
        "Quality benchmark source project",
    )
    camera_path = canonical_existing_file(
        benchmark.get("face_camera"),
        "Quality benchmark face camera",
    )
    lightroom_path = canonical_existing_file(
        benchmark.get("preview_lightroom"),
        "Quality benchmark Lightroom",
    )
    face_position = _quality_benchmark_position(
        benchmark.get("face_position", [0.0, 8.0, 6.0]),
        "quality_benchmark.face_position",
    )
    full_body_position = _quality_benchmark_position(
        benchmark.get("full_body_position", [-600.0, 8.0, 75.0]),
        "quality_benchmark.full_body_position",
    )
    pose_ids = benchmark.get(
        "pose_ids",
        ["blink_bilateral_front", "smile_front", "jaw_open_front"],
    )
    if (
        not isinstance(pose_ids, list)
        or not pose_ids
        or any(not isinstance(item, str) or not item for item in pose_ids)
    ):
        raise ReconstructionError(
            "quality_benchmark.pose_ids must be a non-empty string list"
        )
    load_settle_seconds = float(subject.get("load_settle_seconds", 12.0))
    if load_settle_seconds < 0.0 or load_settle_seconds > 120.0:
        raise ReconstructionError(
            "quality_benchmark load_settle_seconds must be from 0 to 120"
        )

    subject_dir = os.path.join(output_dir, subject_id)
    os.makedirs(subject_dir, exist_ok=False)
    artifacts = character_quality_benchmark_artifacts(subject_dir)
    progress_path = os.path.join(output_dir, "progress.json")
    report_path = os.path.join(output_dir, "subject_benchmark.json")
    snapshot_path = os.path.join(
        subject_dir, "_quality_benchmark_scene_snapshot.ccProject"
    )
    started_at = now()

    def mark_phase(phase, details=None):
        payload = {
            "schema_version": 1,
            "updated_at": now(),
            "diagnostic_mode": "character_quality_benchmark",
            "subject_id": subject_id,
            "phase": phase,
        }
        if details:
            payload["details"] = details
        write_json(payload, progress_path)
        log("Quality benchmark {}: {}".format(subject_id, phase))
        QtWidgets.QApplication.processEvents()

    report = {
        "schema_version": 1,
        "diagnostic_mode": "character_quality_benchmark",
        "benchmark_strategy": "snapshot_existing_face_clip_v4",
        "subject_id": subject_id,
        "started_at": started_at,
        "success": False,
        "conditions": {
            "preview_capture_mode": PREVIEW_CAPTURE_MODE,
            "preview_resolution": [
                VIEWPORT_PREVIEW_WIDTH,
                VIEWPORT_PREVIEW_HEIGHT,
            ],
            "face_camera": camera_path,
            "preview_lightroom": lightroom_path,
            "face_position": face_position,
            "full_body_position": full_body_position,
            "static_views": {
                "neutral_front": {"yaw": 90.0, "y_offset": 8.0},
                "neutral_three_quarter": {"yaw": 45.0, "y_offset": 4.0},
                "neutral_profile": {"yaw": 0.0, "y_offset": 0.0},
                "full_body_front": {"yaw": 90.0, "y_offset": 8.0},
            },
            "pose_ids": list(pose_ids),
            "source_motion_policy": (
                "snapshot_then_clear_body_motion_and_edit_existing_face_clip"
            ),
        },
        "source_project": _quality_benchmark_file_record(source_project),
        "progress_path": progress_path,
        "summary_path": report_path,
        "restoration": {
            "attempted": False,
            "restored": False,
            "snapshot_deleted": False,
        },
    }
    write_json(report, report_path)

    mark_phase("load_source_project", {"path": source_project})
    load_status, load_dialogs = load_file_with_optional_undo_warning(
        source_project,
        "Load quality benchmark source {}".format(subject_id),
    )
    settle_cc_ui(load_settle_seconds)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Quality benchmark expected one avatar for {}, found {}".format(
                subject_id, len(avatars)
            )
        )
    RLPy.RScene.SelectObject(avatar)
    checked(
        "Evaluate quality benchmark project start",
        RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
    )
    report["source_load"] = {
        "status": load_status,
        "dialogs": load_dialogs,
        "settle_seconds": load_settle_seconds,
    }
    report["source_state"] = {
        "bounds": capture_bounds(avatar),
        "motion_inventory": avatar_motion_inventory(avatar),
        "eye_state": capture_eye_integrity_state(avatar),
    }

    mark_phase("load_standard_lightroom")
    checked(
        "Load quality benchmark Lightroom",
        RLPy.RFileIO.LoadFile(lightroom_path),
    )
    settle_cc_ui(1.0)
    mark_phase("load_standard_camera")
    checked(
        "Load quality benchmark camera",
        RLPy.RFileIO.LoadFile(camera_path),
    )
    settle_cc_ui(1.0)
    if RLPy.RScene.GetCurrentCamera() is None:
        raise ReconstructionError("Quality benchmark has no active camera")
    report["camera"] = camera_state(RLPy.RScene.GetCurrentCamera())
    movable_lights, skipped_lights, light_query_errors = (
        quality_benchmark_movable_lights()
    )
    if not movable_lights:
        raise ReconstructionError(
            "Quality benchmark found no movable Lightroom lights: {}"
            .format(light_query_errors + skipped_lights)
        )
    report["lighting"] = {
        "policy": "translate_movable_lights_with_full_body_subject",
        "movable_lights": [
            dict(
                (key, value)
                for key, value in item.items()
                if key != "object"
            )
            for item in movable_lights
        ],
        "skipped_lights": skipped_lights,
        "query_errors": light_query_errors,
    }

    snapshot_saved = False
    work_finished_at = None
    try:
        mark_phase("save_quality_benchmark_snapshot")
        checked(
            "Save quality benchmark scene snapshot",
            RLPy.RFileIO.SaveProject(snapshot_path),
        )
        snapshot_stat = wait_for_rendered_preview(
            snapshot_path,
            timeout_seconds=600.0,
            stable_seconds=2.0,
        )
        snapshot_saved = True
        report["snapshot"] = {
            "path": snapshot_path,
            "bytes": snapshot_stat,
            "saved": True,
        }

        mark_phase("clear_body_motion_preserve_existing_face_clip")
        face_component = avatar.GetFaceComponent()
        if face_component is None:
            raise ReconstructionError(
                "Quality benchmark subject has no Facial Profile"
            )
        project_start_time = RLPy.RGlobal.GetStartTime()
        baseline_face_clip_count = int(face_component.GetClipCount())
        if baseline_face_clip_count < 1:
            raise ReconstructionError(
                "Quality benchmark requires an existing face clip"
            )
        baseline_face_clip = face_component.GetClipByTime(
            project_start_time
        )
        if baseline_face_clip is None or not baseline_face_clip.IsValid():
            raise ReconstructionError(
                "Quality benchmark has no face clip at the project start"
            )
        motion_cleanup = clear_avatar_skeleton_motion(avatar)
        expression_names = list(
            face_component.GetExpressionNames("") or []
        )
        if not expression_names:
            raise ReconstructionError(
                "Quality benchmark subject has no facial expressions"
        )
        fps = RLPy.RGlobal.GetFps()
        project_start_frame = int(fps.GetFrameIndex(project_start_time))
        neutral_time = project_start_time
        checked(
            "Begin quality benchmark neutral key editing",
            face_component.BeginKeyEditing(),
        )
        try:
            checked(
                "Write quality benchmark neutral expression key",
                face_component.AddExpressionKeys(
                    neutral_time,
                    expression_names,
                    [0.0] * len(expression_names),
                    RLPy.IndexedFrameTime(0, fps),
                ),
            )
        finally:
            checked(
                "End quality benchmark neutral key editing",
                face_component.EndKeyEditing(),
            )
        checked(
            "Evaluate quality benchmark neutral frame",
            RLPy.RGlobal.SetTime(neutral_time, True),
        )
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1],
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, 90.0)
        force_avatar_scene_evaluation(avatar)

        mark_phase("capture_subject_inventory")
        standardized_bounds = capture_bounds(avatar)
        report["subject"] = {
            "avatar": {
                "id": scene_object_id(avatar),
                "name": scene_object_name(avatar),
                "python_type": type(avatar).__name__,
            },
            "bounds": standardized_bounds,
            "height_cm": bodyfit_height_cm(standardized_bounds),
            "asset_inventory": avatar_asset_inventory(avatar),
            "avatar_part_inventory": avatar_part_inventory(avatar),
            "source_motion_cleanup": motion_cleanup,
            "motion_inventory": avatar_motion_inventory(avatar),
            "facial_profile": {
                "expression_count": len(expression_names),
                "expression_clip_count": int(face_component.GetClipCount()),
                "baseline_expression_clip_count": (
                    baseline_face_clip_count
                ),
                "capture_frame": project_start_frame,
                "clip_policy": "edit_existing_clip_then_restore_snapshot",
                "expression_set_uid": str(
                    face_component.GetExpressionSetUid()
                ),
            },
            "material_fingerprint": avatar_material_fingerprint(avatar),
            "material_structure": avatar_material_structure(avatar),
            "neutral_eye_state": capture_eye_integrity_state(avatar),
        }
        write_json(report, report_path)

        report["static_captures"] = {}
        static_specs = (
            ("neutral_front", 90.0, 8.0),
            ("neutral_three_quarter", 45.0, 4.0),
            ("neutral_profile", 0.0, 0.0),
        )
        for capture_id, yaw_degrees, canonical_y in static_specs:
            view_y = face_position[1] + canonical_y - 8.0
            set_avatar_position(
                avatar,
                position_x=face_position[0],
                position_y=view_y,
                position_z=face_position[2],
            )
            set_avatar_yaw(avatar, yaw_degrees)
            force_avatar_scene_evaluation(avatar)
            mark_phase("render_{}".format(capture_id))
            render_preview(artifacts[capture_id], neutral_time)
            report["static_captures"][capture_id] = (
                _quality_benchmark_file_record(artifacts[capture_id])
            )

        full_body_light_offset = {
            "x": full_body_position[0] - face_position[0],
            "y": full_body_position[1] - face_position[1],
            "z": full_body_position[2] - face_position[2],
        }
        report["lighting"]["full_body_light_offset"] = (
            full_body_light_offset
        )
        try:
            set_avatar_position(
                avatar,
                position_x=full_body_position[0],
                position_y=full_body_position[1],
                position_z=full_body_position[2],
            )
            set_quality_benchmark_light_offset(
                movable_lights, full_body_light_offset
            )
            set_avatar_yaw(avatar, 90.0)
            force_avatar_scene_evaluation(avatar)
            mark_phase("render_full_body_front")
            render_preview(artifacts["full_body_front"], neutral_time)
            report["static_captures"]["full_body_front"] = (
                _quality_benchmark_file_record(
                    artifacts["full_body_front"]
                )
            )
        finally:
            set_quality_benchmark_light_offset(
                movable_lights, {"x": 0.0, "y": 0.0, "z": 0.0}
            )
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1],
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, 90.0)
        force_avatar_scene_evaluation(avatar)
        write_json(report, report_path)

        mark_phase("render_expression_matrix")
        pose_report = render_quality_benchmark_pose_matrix(
            avatar,
            artifacts,
            mark_phase,
            neutral_time,
            expression_names,
            pose_ids,
            face_position,
        )
        report["facial_pose_validation"] = {
            "path": artifacts["facial_pose_validation"],
            "pose_count": len(pose_report.get("poses") or []),
            "neutral_eye_integrity": pose_report.get(
                "neutral_eye_integrity"
            ),
            "evidence_liveness": pose_report.get("evidence_liveness"),
        }
        report["dynamic_captures"] = {}
        for pose in pose_report.get("poses") or []:
            report["dynamic_captures"][pose["pose_id"]] = pose[
                "capture"
            ]
        report["dynamic_captures"]["post_pose_neutral_front"] = (
            pose_report["post_pose_neutral_capture"]
        )
        work_finished_at = now()
        write_json(report, report_path)
    finally:
        if snapshot_saved:
            report["restoration"]["attempted"] = True
            mark_phase("restore_quality_benchmark_snapshot")
            unused_status, restore_dialogs = (
                load_file_with_optional_undo_warning(
                    snapshot_path,
                    "Restore quality benchmark scene snapshot",
                )
            )
            settle_cc_ui(2.0)
            restored_avatar, restored_avatars = resolve_avatar()
            if len(restored_avatars) != 1:
                raise ReconstructionError(
                    "Quality benchmark snapshot restore expected one avatar"
                )
            force_avatar_scene_evaluation(restored_avatar)
            restored_eye_state = capture_eye_integrity_state(
                restored_avatar
            )
            restoration_eye_integrity = compare_neutral_eye_states(
                report["source_state"]["eye_state"],
                restored_eye_state,
                include_world=True,
                include_runtime_ids=False,
                t_pose_tolerance=0.5,
            )
            report["restoration"].update(
                {
                    "restored": True,
                    "dialogs": restore_dialogs,
                    "eye_integrity": restoration_eye_integrity,
                }
            )
            try:
                os.remove(snapshot_path)
            except OSError as exc:
                report["restoration"]["snapshot_cleanup_error"] = str(exc)
            else:
                report["restoration"]["snapshot_deleted"] = True
            write_json(report, report_path)

    if not report["restoration"].get("restored"):
        raise ReconstructionError(
            "Quality benchmark did not restore the source snapshot"
        )
    if not report["restoration"]["eye_integrity"]["matches"]:
        raise ReconstructionError(
            "Quality benchmark snapshot changed source eye state"
        )
    report["finished_at"] = work_finished_at or now()
    report["success"] = True
    write_json(report, report_path)
    mark_phase("complete")
    capture_count = len(report["static_captures"]) + len(
        report["dynamic_captures"]
    )
    validation_summary_path = os.path.join(
        output_dir, "validation_result.json"
    )
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "diagnostic_mode": "character_quality_benchmark",
        "subject_id": subject_id,
        "started_at": started_at,
        "finished_at": report["finished_at"],
        "requested_count": capture_count,
        "success_count": capture_count,
        "failure_count": 0,
        "success": True,
        "subject_benchmark_path": report_path,
        "summary_path": validation_summary_path,
        "scene_policy": "leave_restored_subject_loaded",
    }
    write_json(summary, validation_summary_path)
    return summary


def probe_facial_profile_upgrade(library, output_dir, log):
    os.makedirs(output_dir, exist_ok=True)
    config = library.get("facial_profile_upgrade") or {}
    if not isinstance(config, dict):
        raise ReconstructionError("facial_profile_upgrade must be an object")
    subject = config.get("subject") or {}
    if not isinstance(subject, dict):
        raise ReconstructionError(
            "facial_profile_upgrade.subject must be an object"
        )
    subject_id = subject.get("id")
    if (
        not isinstance(subject_id, str)
        or not subject_id
        or any(
            char not in "abcdefghijklmnopqrstuvwxyz0123456789_-"
            for char in subject_id
        )
    ):
        raise ReconstructionError(
            "Facial Profile upgrade subject.id must be lowercase file-safe"
        )
    source_project = canonical_existing_file(
        subject.get("source_project"),
        "Facial Profile upgrade source project",
    )
    target_profile = canonical_existing_file(
        config.get("target_facial_profile"),
        "Facial Profile upgrade target",
    )
    require_file_extension(
        target_profile,
        ".ccFacialProfile",
        "Facial Profile upgrade target",
    )
    camera_path = canonical_existing_file(
        config.get("face_camera"),
        "Facial Profile upgrade camera",
    )
    lightroom_path = canonical_existing_file(
        config.get("preview_lightroom"),
        "Facial Profile upgrade Lightroom",
    )
    baseline_neutral = canonical_existing_file(
        config.get("baseline_neutral_image"),
        "Facial Profile upgrade baseline neutral image",
    )
    face_position = _quality_benchmark_position(
        config.get("face_position", [0.0, 8.0, 6.0]),
        "facial_profile_upgrade.face_position",
    )
    load_settle_seconds = float(subject.get("load_settle_seconds", 20.0))
    profile_settle_seconds = float(config.get("profile_settle_seconds", 20.0))
    expected_min_expression_count = int(
        config.get("expected_min_expression_count", 300)
    )
    expected_uid_term = str(config.get("expected_uid_term", "CC5")).lower()
    subject_dir = os.path.join(output_dir, subject_id)
    os.makedirs(subject_dir, exist_ok=False)
    progress_path = os.path.join(output_dir, "progress.json")
    report_path = os.path.join(output_dir, "profile_upgrade_report.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    source_profile_path = os.path.join(
        subject_dir, "source_cc4_extended.ccFacialProfile"
    )
    upgraded_profile_path = os.path.join(
        subject_dir, "derived_cc5_hd.ccFacialProfile"
    )
    derived_project_path = os.path.join(
        subject_dir, "{}_cc5_hd_inspection_v001.ccProject".format(subject_id)
    )
    neutral_three_quarter_path = os.path.join(
        subject_dir, "neutral_three_quarter.png"
    )
    started_at = now()

    def mark_phase(phase, details=None):
        payload = {
            "schema_version": 1,
            "diagnostic_mode": "facial_profile_upgrade",
            "subject_id": subject_id,
            "updated_at": now(),
            "phase": phase,
        }
        if details:
            payload["details"] = details
        write_json(payload, progress_path)
        log("Facial Profile upgrade {}: {}".format(subject_id, phase))
        QtWidgets.QApplication.processEvents()

    source_project_record = _quality_benchmark_file_record(source_project)
    target_profile_record = _quality_benchmark_file_record(target_profile)
    report = {
        "schema_version": 1,
        "diagnostic_mode": "facial_profile_upgrade",
        "upgrade_mode": "derived_direct_hd_profile_load_with_source_profile_sidecar_v1",
        "conversion_api_available": False,
        "subject_id": subject_id,
        "sex": subject.get("sex"),
        "started_at": started_at,
        "success": False,
        "source_project": source_project_record,
        "target_facial_profile": target_profile_record,
        "baseline_neutral_image": _quality_benchmark_file_record(
            baseline_neutral
        ),
        "artifacts": {
            "source_facial_profile": source_profile_path,
            "derived_facial_profile": upgraded_profile_path,
            "derived_project": derived_project_path,
            "pose_validation": os.path.join(
                subject_dir, "facial_pose_validation.json"
            ),
        },
        "restoration": {
            "attempted": False,
            "derived_project_reloaded": False,
        },
    }
    write_json(report, report_path)
    derived_saved = False
    finished_at = None
    try:
        mark_phase("load_source_project", {"path": source_project})
        load_status, load_dialogs = load_file_with_optional_undo_warning(
            source_project,
            "Load Facial Profile upgrade source {}".format(subject_id),
        )
        settle_cc_ui(load_settle_seconds)
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Facial Profile upgrade expected one source avatar"
            )
        RLPy.RScene.SelectObject(avatar)
        checked(
            "Evaluate Facial Profile upgrade source start",
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
        )
        force_avatar_scene_evaluation(avatar)
        face_component = avatar.GetFaceComponent()
        profile_component = avatar.GetFacialProfileComponent()
        if face_component is None or profile_component is None:
            raise ReconstructionError(
                "Facial Profile upgrade source has no facial components"
            )
        source_avatar_id = scene_object_id(avatar)
        source_expression_names = list(
            face_component.GetExpressionNames("") or []
        )
        before_vectors = capture_vectors(avatar)
        before_eye = capture_eye_integrity_state(avatar)
        before_material = avatar_material_fingerprint(avatar)
        before_bounds = capture_bounds(avatar)
        report["source_load"] = {
            "status": load_status,
            "dialogs": load_dialogs,
            "settle_seconds": load_settle_seconds,
        }
        report["before"] = {
            "avatar_id": source_avatar_id,
            "expression_set_uid": str(face_component.GetExpressionSetUid()),
            "expression_count": len(source_expression_names),
            "profile_type": str(profile_component.GetProfileType()),
            "bounds": before_bounds,
            "eye_state": before_eye,
            "material_fingerprint": before_material,
        }

        mark_phase("save_source_facial_profile_sidecar")
        checked(
            "Save source Facial Profile sidecar",
            profile_component.SaveProfile(source_profile_path),
        )
        wait_for_rendered_preview(
            source_profile_path,
            timeout_seconds=300.0,
            stable_seconds=2.0,
        )
        report["source_facial_profile_sidecar"] = (
            _quality_benchmark_file_record(source_profile_path)
        )

        mark_phase("load_target_cc5_hd_facial_profile")
        checked(
            "Load target CC5 HD Facial Profile",
            profile_component.LoadProfile(target_profile),
        )
        settle_cc_ui(profile_settle_seconds)
        upgraded_avatar, upgraded_avatars = resolve_avatar()
        if len(upgraded_avatars) != 1:
            raise ReconstructionError(
                "Facial Profile upgrade expected one upgraded avatar"
            )
        if scene_object_id(upgraded_avatar) != source_avatar_id:
            raise ReconstructionError(
                "Loading CC5 HD Facial Profile replaced the avatar object"
            )
        avatar = upgraded_avatar
        RLPy.RScene.SelectObject(avatar)
        force_avatar_scene_evaluation(avatar)
        face_component = avatar.GetFaceComponent()
        profile_component = avatar.GetFacialProfileComponent()
        upgraded_expression_names = list(
            face_component.GetExpressionNames("") or []
        )
        after_vectors = capture_vectors(avatar)
        after_eye = capture_eye_integrity_state(avatar)
        after_material = avatar_material_fingerprint(avatar)
        after_bounds = capture_bounds(avatar)
        morph_delta = {
            classification: group_delta(
                before_vectors["groups"][classification]["entries"],
                after_vectors["groups"][classification]["entries"],
            )
            for classification in ("body", "junction", "face", "other")
        }
        morphs_unchanged = not any(morph_delta.values())
        eye_structure_unchanged = (
            eye_integrity_structure_signature(before_eye)
            == eye_integrity_structure_signature(after_eye)
        )
        material_unchanged = (
            before_material["digest"] == after_material["digest"]
        )
        bounds_max_abs_delta = max(
            abs(float(before_value) - float(after_value))
            for key in ("minimum", "maximum", "center")
            for before_value, after_value in zip(
                before_bounds[key], after_bounds[key]
            )
        )
        bounds_unchanged = bounds_max_abs_delta <= 0.01
        upgraded_uid = str(face_component.GetExpressionSetUid())
        profile_gate = bool(
            expected_uid_term in upgraded_uid.lower()
            and len(upgraded_expression_names)
            >= expected_min_expression_count
        )
        report["after"] = {
            "avatar_id": scene_object_id(avatar),
            "expression_set_uid": upgraded_uid,
            "expression_count": len(upgraded_expression_names),
            "profile_type": str(profile_component.GetProfileType()),
            "bounds": after_bounds,
            "eye_state": after_eye,
            "material_fingerprint": after_material,
        }
        report["identity_preservation"] = {
            "morph_delta": morph_delta,
            "morphs_unchanged": morphs_unchanged,
            "eye_structure_unchanged": eye_structure_unchanged,
            "material_unchanged": material_unchanged,
            "bounds_unchanged": bounds_unchanged,
            "bounds_max_abs_delta": bounds_max_abs_delta,
        }
        report["profile_gate"] = {
            "expected_uid_term": expected_uid_term,
            "expected_min_expression_count": expected_min_expression_count,
            "matches": profile_gate,
        }
        write_json(report, report_path)
        if not morphs_unchanged:
            raise ReconstructionError(
                "CC5 HD Facial Profile load changed static Morph weights"
            )
        if not eye_structure_unchanged:
            raise ReconstructionError(
                "CC5 HD Facial Profile load changed eye object structure"
            )
        if not material_unchanged:
            raise ReconstructionError(
                "CC5 HD Facial Profile load changed material assignments"
            )
        if not profile_gate:
            raise ReconstructionError(
                "Loaded Facial Profile did not satisfy the CC5 HD gate"
            )

        mark_phase("save_derived_cc5_hd_facial_profile")
        checked(
            "Save derived CC5 HD Facial Profile",
            profile_component.SaveProfile(upgraded_profile_path),
        )
        wait_for_rendered_preview(
            upgraded_profile_path,
            timeout_seconds=300.0,
            stable_seconds=2.0,
        )
        report["derived_facial_profile"] = (
            _quality_benchmark_file_record(upgraded_profile_path)
        )

        mark_phase("save_derived_cc5_hd_project")
        checked(
            "Save derived CC5 HD inspection project",
            RLPy.RFileIO.SaveProject(derived_project_path),
        )
        wait_for_rendered_preview(
            derived_project_path,
            timeout_seconds=600.0,
            stable_seconds=2.0,
        )
        derived_saved = True
        report["derived_project"] = _quality_benchmark_file_record(
            derived_project_path
        )
        write_json(report, report_path)

        mark_phase("load_standard_lightroom")
        checked(
            "Load Facial Profile upgrade Lightroom",
            RLPy.RFileIO.LoadFile(lightroom_path),
        )
        settle_cc_ui(1.0)
        mark_phase("load_standard_camera")
        checked(
            "Load Facial Profile upgrade camera",
            RLPy.RFileIO.LoadFile(camera_path),
        )
        settle_cc_ui(1.0)
        neutral_time = RLPy.RGlobal.GetStartTime()
        mark_phase("render_tiered_pose_matrix")
        pose_report = render_profile_upgrade_pose_matrix(
            avatar,
            subject_dir,
            mark_phase,
            neutral_time,
            face_position,
        )
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1] - 4.0,
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, 45.0)
        force_avatar_scene_evaluation(avatar)
        mark_phase("render_neutral_three_quarter")
        render_preview(neutral_three_quarter_path, neutral_time)
        upgraded_neutral = pose_report["post_pose_neutral_capture"]["path"]
        report["visual_evidence"] = {
            "neutral_front": pose_report["post_pose_neutral_capture"],
            "neutral_three_quarter": _quality_benchmark_file_record(
                neutral_three_quarter_path
            ),
            "baseline_neutral_rmse": rendered_image_rmse(
                baseline_neutral,
                upgraded_neutral,
            ),
            "pose_validation": report["artifacts"]["pose_validation"],
            "natural_smile_visual_status": "pending_user_review",
        }
        report["pose_gate"] = {
            "neutral_eye_integrity": pose_report["neutral_eye_integrity"],
            "evidence_liveness": pose_report["evidence_liveness"],
            "pose_count": len(pose_report["poses"]),
            "matches": bool(
                pose_report["neutral_eye_integrity"]["matches"]
                and pose_report["evidence_liveness"]["status"] == "passed"
            ),
        }
        finished_at = now()
        write_json(report, report_path)
    finally:
        report["restoration"]["attempted"] = True
        restore_path = derived_project_path if derived_saved else source_project
        report["restoration"]["path"] = restore_path
        mark_phase("reload_saved_project", {"path": restore_path})
        restore_status, restore_dialogs = load_file_with_optional_undo_warning(
            restore_path,
            "Reload Facial Profile upgrade saved project",
        )
        settle_cc_ui(3.0)
        restored_avatar, restored_avatars = resolve_avatar()
        if len(restored_avatars) != 1:
            raise ReconstructionError(
                "Facial Profile upgrade restore expected one avatar"
            )
        restored_face = restored_avatar.GetFaceComponent()
        restored_names = list(restored_face.GetExpressionNames("") or [])
        restored_uid = str(restored_face.GetExpressionSetUid())
        expected_uid = (
            report.get("after", {}).get("expression_set_uid")
            if derived_saved
            else report.get("before", {}).get("expression_set_uid")
        )
        report["restoration"].update(
            {
                "status": restore_status,
                "dialogs": restore_dialogs,
                "derived_project_reloaded": derived_saved,
                "expression_set_uid": restored_uid,
                "expression_count": len(restored_names),
                "profile_persisted": restored_uid == expected_uid,
            }
        )
        report["source_project_after"] = _quality_benchmark_file_record(
            source_project
        )
        report["source_project_unchanged"] = bool(
            report["source_project_after"]["sha256"]
            == source_project_record["sha256"]
        )
        write_json(report, report_path)

    if not report["restoration"].get("profile_persisted"):
        raise ReconstructionError(
            "Derived Facial Profile did not persist after project reload"
        )
    if not report.get("source_project_unchanged"):
        raise ReconstructionError("Source Headshot project hash changed")
    if not report.get("pose_gate", {}).get("matches"):
        raise ReconstructionError("Facial Profile upgrade pose gate failed")
    report["finished_at"] = finished_at or now()
    report["success"] = True
    write_json(report, report_path)
    mark_phase("complete")
    summary = {
        "schema_version": 1,
        "diagnostic_mode": "facial_profile_upgrade",
        "subject_id": subject_id,
        "started_at": started_at,
        "finished_at": report["finished_at"],
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "report_path": report_path,
        "summary_path": summary_path,
        "scene_policy": "leave_derived_cc5_hd_project_loaded",
    }
    write_json(summary, summary_path)
    return summary


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
        "initial_avatar_bounds": capture_bounds(avatar),
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


def vectors_excluding_morph_fingerprint(vectors, excluded_morph_id):
    return vectors_excluding_morphs_fingerprint(
        vectors,
        {excluded_morph_id},
    )


def vectors_excluding_morphs_fingerprint(vectors, excluded_morph_ids):
    excluded_morph_ids = set(excluded_morph_ids)
    entries = []
    for group in (vectors.get("groups") or {}).values():
        entries.extend(
            item
            for item in (group.get("entries") or [])
            if item.get("id") not in excluded_morph_ids
        )
    return vector_fingerprint(entries)


def signed_morph_token(value):
    points = int(round(float(value) * 100.0))
    if points < 0:
        return "n{:03d}".format(abs(points))
    if points > 0:
        return "p{:03d}".format(points)
    return "z000"


def render_head_scale_review(
    avatar,
    review_config,
    output_dir,
    report_path,
    progress_callback=None,
):
    morph_id = review_config.get("morph_id")
    values = review_config.get("values")
    if not isinstance(morph_id, str) or not morph_id:
        raise ReconstructionError(
            "Head Scale review morph_id must be a non-empty string"
        )
    if not isinstance(values, list) or not values:
        raise ReconstructionError(
            "Head Scale review values must be a non-empty list"
        )
    values = [float(value) for value in values]
    if len(values) != len(set(values)):
        raise ReconstructionError("Head Scale review values contain duplicates")

    component, catalog, unused_categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "Head Scale review Morph is unavailable: {}".format(morph_id)
        )
    bounds = component.GetShapingMorphMinMax(morph_id)
    minimum = float(bounds.first)
    maximum = float(bounds.second)
    for value in values:
        if value < minimum - 1e-7 or value > maximum + 1e-7:
            raise ReconstructionError(
                "Head Scale review target {} is outside [{}, {}]".format(
                    value,
                    minimum,
                    maximum,
                )
            )

    os.makedirs(output_dir, exist_ok=True)
    initial_weight = float(component.GetShapingMorphWeight(morph_id))
    initial_time = RLPy.RGlobal.GetTime()
    initial_vectors = capture_vectors(avatar)
    protected_fingerprint = vectors_excluding_morph_fingerprint(
        initial_vectors,
        morph_id,
    )
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "camera": camera_state(RLPy.RScene.GetCurrentCamera()),
        "face_shape_role": review_config.get("face_shape_role"),
        "initial_weight": initial_weight,
        "morph": dict(
            catalog[morph_id],
            minimum=minimum,
            maximum=maximum,
        ),
        "protected_morph_fingerprint": protected_fingerprint,
        "review_groups": list(review_config.get("review_groups") or []),
        "values": values,
        "candidates": [],
    }
    try:
        for index, value in enumerate(values):
            if progress_callback is not None:
                progress_callback(
                    "render_head_scale_{}".format(signed_morph_token(value)),
                    {
                        "candidate_index": index + 1,
                        "candidate_count": len(values),
                        "value": value,
                    },
                )
            application = apply_single_morph_weight(
                avatar,
                morph_id,
                value,
                "Head Scale review",
            )
            force_avatar_scene_evaluation(avatar)
            image_path = os.path.join(
                output_dir,
                "head_scale_{}.png".format(signed_morph_token(value)),
            )
            render_preview(image_path, initial_time)
            candidate_vectors = capture_vectors(avatar)
            candidate_protected_fingerprint = (
                vectors_excluding_morph_fingerprint(
                    candidate_vectors,
                    morph_id,
                )
            )
            if candidate_protected_fingerprint != protected_fingerprint:
                raise ReconstructionError(
                    "Head Scale review changed a protected Morph at {}".format(
                        value
                    )
                )
            report["candidates"].append(
                {
                    "application": application,
                    "avatar_bounds": capture_bounds(avatar),
                    "image": image_path,
                    "protected_morph_fingerprint": (
                        candidate_protected_fingerprint
                    ),
                    "value": value,
                }
            )
    finally:
        checked(
            "Restore Head Scale after review",
            component.SetShapingMorphWeight(morph_id, initial_weight),
        )
        checked(
            "Refresh restored Head Scale after review",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        checked(
            "Restore current time after Head Scale review",
            RLPy.RGlobal.SetTime(initial_time, True),
        )
        QtWidgets.QApplication.processEvents()

    restored_weight = float(component.GetShapingMorphWeight(morph_id))
    restored_vectors = capture_vectors(avatar)
    restored_fingerprint = vectors_excluding_morph_fingerprint(
        restored_vectors,
        morph_id,
    )
    report["restored_weight"] = restored_weight
    report["restored_vector_fingerprint"] = restored_fingerprint
    report["restored_exactly"] = bool(
        abs(restored_weight - initial_weight) <= 1e-6
        and restored_fingerprint == protected_fingerprint
    )
    if not report["restored_exactly"]:
        raise ReconstructionError(
            "Head Scale review did not restore the composed character"
        )
    write_json(report, report_path)
    return report


def render_neck_morph_review(
    avatar,
    review_config,
    output_dir,
    report_path,
    progress_callback=None,
):
    head_scale_config = review_config.get("head_scale") or {}
    head_scale_morph_id = head_scale_config.get("morph_id")
    if not isinstance(head_scale_morph_id, str) or not head_scale_morph_id:
        raise ReconstructionError(
            "Neck review head_scale.morph_id must be a non-empty string"
        )
    head_scale_target = float(head_scale_config.get("target"))
    morph_configs = review_config.get("morphs")
    if not isinstance(morph_configs, list) or not morph_configs:
        raise ReconstructionError(
            "Neck review morphs must be a non-empty list"
        )

    component, catalog, unused_categories = morph_catalog(avatar)
    controlled_ids = {head_scale_morph_id}
    normalized_morphs = []
    review_ids = set()
    for item in morph_configs:
        if not isinstance(item, dict):
            raise ReconstructionError("Neck review Morph entry must be an object")
        morph_id = item.get("morph_id")
        review_id = item.get("review_id")
        values = item.get("values")
        if not isinstance(morph_id, str) or not morph_id:
            raise ReconstructionError("Neck review morph_id is missing")
        if not isinstance(review_id, str) or not review_id:
            raise ReconstructionError("Neck review review_id is missing")
        if review_id in review_ids:
            raise ReconstructionError(
                "Neck review review_id is duplicated: {}".format(review_id)
            )
        if morph_id in controlled_ids:
            raise ReconstructionError(
                "Neck review Morph ID is duplicated: {}".format(morph_id)
            )
        if not isinstance(values, list) or not values:
            raise ReconstructionError(
                "Neck review values are missing for {}".format(review_id)
            )
        values = [float(value) for value in values]
        if len(values) != len(set(values)):
            raise ReconstructionError(
                "Neck review values contain duplicates for {}".format(
                    review_id
                )
            )
        review_ids.add(review_id)
        controlled_ids.add(morph_id)
        normalized_morphs.append(
            {
                "morph_id": morph_id,
                "review_id": review_id,
                "values": values,
            }
        )

    for morph_id in controlled_ids:
        if morph_id not in catalog:
            raise ReconstructionError(
                "Neck review Morph is unavailable: {}".format(morph_id)
            )
    head_scale_bounds = component.GetShapingMorphMinMax(
        head_scale_morph_id
    )
    head_scale_minimum = float(head_scale_bounds.first)
    head_scale_maximum = float(head_scale_bounds.second)
    if (
        head_scale_target < head_scale_minimum - 1e-7
        or head_scale_target > head_scale_maximum + 1e-7
    ):
        raise ReconstructionError(
            "Neck review Head Scale target is outside bounds"
        )

    for item in normalized_morphs:
        bounds = component.GetShapingMorphMinMax(item["morph_id"])
        item["minimum"] = float(bounds.first)
        item["maximum"] = float(bounds.second)
        for value in item["values"]:
            if value < item["minimum"] - 1e-7 or value > item["maximum"] + 1e-7:
                raise ReconstructionError(
                    "Neck review target {} for {} is outside [{}, {}]".format(
                        value,
                        item["review_id"],
                        item["minimum"],
                        item["maximum"],
                    )
                )

    views = review_config.get("views") or [
        {"view_id": "yaw_000", "yaw_degrees": 0.0},
        {"view_id": "yaw_045", "yaw_degrees": 45.0},
        {"view_id": "yaw_090", "yaw_degrees": 90.0},
    ]
    normalized_views = []
    view_ids = set()
    for item in views:
        view_id = item.get("view_id")
        if not isinstance(view_id, str) or not view_id:
            raise ReconstructionError("Neck review view_id is missing")
        if view_id in view_ids:
            raise ReconstructionError(
                "Neck review view_id is duplicated: {}".format(view_id)
            )
        view_ids.add(view_id)
        normalized_views.append(
            {
                "view_id": view_id,
                "yaw_degrees": float(item.get("yaw_degrees")),
            }
        )

    save_selected = review_config.get("save_selected_candidate")
    if save_selected is not None:
        if not isinstance(save_selected, dict):
            raise ReconstructionError(
                "Neck review save_selected_candidate must be an object"
            )
        selected_review_id = save_selected.get("review_id")
        selected_project_path = save_selected.get("project_path")
        selected_value = save_selected.get("value")
        if selected_review_id not in review_ids:
            raise ReconstructionError(
                "Neck review selected review_id is unavailable: {}".format(
                    selected_review_id
                )
            )
        if (
            not isinstance(selected_project_path, str)
            or not selected_project_path.lower().endswith(".ccproject")
        ):
            raise ReconstructionError(
                "Neck review selected project_path must be a ccProject path"
            )
        if (
            isinstance(selected_value, bool)
            or not isinstance(selected_value, (int, float))
            or not math.isfinite(float(selected_value))
        ):
            raise ReconstructionError(
                "Neck review selected value must be finite"
            )
        selected_value = float(selected_value)
        selected_morph = next(
            item
            for item in normalized_morphs
            if item["review_id"] == selected_review_id
        )
        if (
            selected_value < selected_morph["minimum"] - 1e-7
            or selected_value > selected_morph["maximum"] + 1e-7
        ):
            raise ReconstructionError(
                "Neck review selected value is outside Morph bounds"
            )

    os.makedirs(output_dir, exist_ok=True)
    initial_weights = dict(
        (
            morph_id,
            float(component.GetShapingMorphWeight(morph_id)),
        )
        for morph_id in controlled_ids
    )
    initial_time = RLPy.RGlobal.GetTime()
    initial_yaw_radians = _transform_float(
        avatar,
        "Rotation/RotationZ",
    )
    initial_vectors = capture_vectors(avatar)
    initial_full_fingerprint = vectors_excluding_morphs_fingerprint(
        initial_vectors,
        set(),
    )
    protected_fingerprint = vectors_excluding_morphs_fingerprint(
        initial_vectors,
        controlled_ids,
    )
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "camera": camera_state(RLPy.RScene.GetCurrentCamera()),
        "controlled_morph_ids": sorted(controlled_ids),
        "head_scale": {
            "initial_weight": initial_weights[head_scale_morph_id],
            "maximum": head_scale_maximum,
            "minimum": head_scale_minimum,
            "morph": catalog[head_scale_morph_id],
            "target": head_scale_target,
        },
        "initial_full_fingerprint": initial_full_fingerprint,
        "initial_yaw_degrees": math.degrees(initial_yaw_radians),
        "protected_morph_fingerprint": protected_fingerprint,
        "views": normalized_views,
        "morphs": [],
        "saved_selected_candidate": None,
    }
    try:
        report["head_scale"]["application"] = apply_single_morph_weight(
            avatar,
            head_scale_morph_id,
            head_scale_target,
            "Neck review Head Scale",
        )
        for morph_index, item in enumerate(normalized_morphs):
            morph_id = item["morph_id"]
            morph_dir = os.path.join(output_dir, item["review_id"])
            os.makedirs(morph_dir, exist_ok=True)
            morph_report = {
                "review_id": item["review_id"],
                "morph": dict(
                    catalog[morph_id],
                    minimum=item["minimum"],
                    maximum=item["maximum"],
                ),
                "initial_weight": initial_weights[morph_id],
                "values": item["values"],
                "candidates": [],
            }
            report["morphs"].append(morph_report)
            for value_index, value in enumerate(item["values"]):
                if progress_callback is not None:
                    progress_callback(
                        "render_neck_{}_{}".format(
                            item["review_id"],
                            signed_morph_token(value),
                        ),
                        {
                            "morph_index": morph_index + 1,
                            "morph_count": len(normalized_morphs),
                            "candidate_index": value_index + 1,
                            "candidate_count": len(item["values"]),
                            "value": value,
                        },
                    )
                for reset_id in controlled_ids:
                    target = initial_weights[reset_id]
                    if reset_id == head_scale_morph_id:
                        target = head_scale_target
                    checked(
                        "Reset Neck review Morph {}".format(reset_id),
                        component.SetShapingMorphWeight(reset_id, target),
                    )
                checked(
                    "Refresh reset Neck review Morphs",
                    RLPy.RGlobal.ObjectModified(
                        avatar,
                        RLPy.EObjectModifiedType_MorphWeight,
                    ),
                )
                QtWidgets.QApplication.processEvents()
                application = apply_single_morph_weight(
                    avatar,
                    morph_id,
                    value,
                    "Neck review {}".format(item["review_id"]),
                )
                force_avatar_scene_evaluation(avatar)
                rendered_views = {}
                for view in normalized_views:
                    set_avatar_yaw(avatar, view["yaw_degrees"])
                    image_path = os.path.join(
                        morph_dir,
                        "{}_{}_{}.png".format(
                            item["review_id"],
                            signed_morph_token(value),
                            view["view_id"],
                        ),
                    )
                    render_preview(image_path, initial_time)
                    rendered_views[view["view_id"]] = image_path
                candidate_vectors = capture_vectors(avatar)
                candidate_protected_fingerprint = (
                    vectors_excluding_morphs_fingerprint(
                        candidate_vectors,
                        controlled_ids,
                    )
                )
                if candidate_protected_fingerprint != protected_fingerprint:
                    raise ReconstructionError(
                        "Neck review changed a protected Morph at {} {}".format(
                            item["review_id"],
                            value,
                        )
                    )
                morph_report["candidates"].append(
                    {
                        "application": application,
                        "avatar_bounds": capture_bounds(avatar),
                        "protected_morph_fingerprint": (
                            candidate_protected_fingerprint
                        ),
                        "value": value,
                        "views": rendered_views,
                    }
                )
        if save_selected is not None:
            for reset_id in controlled_ids:
                target = initial_weights[reset_id]
                if reset_id == head_scale_morph_id:
                    target = head_scale_target
                checked(
                    "Reset selected candidate Morph {}".format(reset_id),
                    component.SetShapingMorphWeight(reset_id, target),
                )
            checked(
                "Refresh selected candidate Morphs",
                RLPy.RGlobal.ObjectModified(
                    avatar,
                    RLPy.EObjectModifiedType_MorphWeight,
                ),
            )
            selected_application = apply_single_morph_weight(
                avatar,
                selected_morph["morph_id"],
                selected_value,
                "Selected Neck review candidate",
            )
            force_avatar_scene_evaluation(avatar)
            set_avatar_yaw(avatar, 0.0)
            selected_preview = os.path.join(
                output_dir,
                "selected_{}_{}.png".format(
                    selected_review_id,
                    signed_morph_token(selected_value),
                ),
            )
            render_preview(selected_preview, initial_time)
            project_directory = os.path.dirname(selected_project_path)
            if project_directory:
                os.makedirs(project_directory, exist_ok=True)
            checked(
                "Save selected Neck review candidate",
                RLPy.RFileIO.SaveProject(selected_project_path),
            )
            project_stat = wait_for_rendered_preview(
                selected_project_path,
                timeout_seconds=600.0,
                stable_seconds=2.0,
            )
            report["saved_selected_candidate"] = {
                "application": selected_application,
                "avatar_bounds": capture_bounds(avatar),
                "preview": selected_preview,
                "project_path": selected_project_path,
                "project_size": project_stat,
                "review_id": selected_review_id,
                "value": selected_value,
            }
    finally:
        for morph_id, initial_weight in initial_weights.items():
            checked(
                "Restore Neck review Morph {}".format(morph_id),
                component.SetShapingMorphWeight(morph_id, initial_weight),
            )
        checked(
            "Refresh restored Neck review Morphs",
            RLPy.RGlobal.ObjectModified(
                avatar,
                RLPy.EObjectModifiedType_MorphWeight,
            ),
        )
        set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
        checked(
            "Restore current time after Neck review",
            RLPy.RGlobal.SetTime(initial_time, True),
        )
        QtWidgets.QApplication.processEvents()

    restored_vectors = capture_vectors(avatar)
    restored_yaw_radians = _transform_float(
        avatar,
        "Rotation/RotationZ",
    )
    yaw_delta_radians = math.atan2(
        math.sin(restored_yaw_radians - initial_yaw_radians),
        math.cos(restored_yaw_radians - initial_yaw_radians),
    )
    restored_full_fingerprint = vectors_excluding_morphs_fingerprint(
        restored_vectors,
        set(),
    )
    report["restored_weights"] = dict(
        (
            morph_id,
            float(component.GetShapingMorphWeight(morph_id)),
        )
        for morph_id in controlled_ids
    )
    report["restored_full_fingerprint"] = restored_full_fingerprint
    report["restored_yaw_degrees"] = math.degrees(restored_yaw_radians)
    report["yaw_restored_exactly"] = bool(
        abs(math.degrees(yaw_delta_radians)) <= 1e-5
    )
    report["restored_exactly"] = bool(
        restored_full_fingerprint == initial_full_fingerprint
        and report["yaw_restored_exactly"]
        and all(
            abs(report["restored_weights"][morph_id] - initial_weight)
            <= 1e-6
            for morph_id, initial_weight in initial_weights.items()
        )
    )
    if not report["restored_exactly"]:
        raise ReconstructionError(
            "Neck review did not restore the composed character"
        )
    write_json(report, report_path)
    return report


def probe_current_head_scale_sweep(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Head Scale sweep expected one avatar, found {}".format(
                len(avatars)
            )
        )
    morph_id = library.get("head_scale_morph_id")
    values = library.get("head_scale_values")
    if not isinstance(morph_id, str) or not morph_id:
        raise ReconstructionError(
            "head_scale_morph_id must be a non-empty string"
        )
    if not isinstance(values, list) or not values:
        raise ReconstructionError(
            "head_scale_values must be a non-empty list"
        )
    values = [float(value) for value in values]
    if len(values) != len(set(values)):
        raise ReconstructionError("head_scale_values contains duplicates")

    component, catalog, unused_categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "Head Scale Morph is unavailable: {}".format(morph_id)
        )
    bounds = component.GetShapingMorphMinMax(morph_id)
    minimum = float(bounds.first)
    maximum = float(bounds.second)
    for value in values:
        if value < minimum - 1e-7 or value > maximum + 1e-7:
            raise ReconstructionError(
                "Head Scale target {} is outside [{}, {}]".format(
                    value,
                    minimum,
                    maximum,
                )
            )

    initial_weight = float(component.GetShapingMorphWeight(morph_id))
    initial_time = RLPy.RGlobal.GetTime()
    initial_vectors = capture_vectors(avatar)
    protected_fingerprint = vectors_excluding_morph_fingerprint(
        initial_vectors,
        morph_id,
    )
    initial_image = os.path.join(output_dir, "head_scale_initial.png")
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "camera": camera_state(RLPy.RScene.GetCurrentCamera()),
        "morph": dict(
            catalog[morph_id],
            minimum=minimum,
            maximum=maximum,
        ),
        "initial_weight": initial_weight,
        "initial_image": initial_image,
        "protected_morph_fingerprint": protected_fingerprint,
        "candidates": [],
    }
    try:
        render_preview(initial_image, initial_time)
        for value in values:
            application = apply_single_morph_weight(
                avatar,
                morph_id,
                value,
                "Head Scale sweep",
            )
            image_path = os.path.join(
                output_dir,
                "head_scale_{}.png".format(signed_morph_token(value)),
            )
            render_preview(image_path, initial_time)
            candidate_vectors = capture_vectors(avatar)
            candidate_protected_fingerprint = (
                vectors_excluding_morph_fingerprint(
                    candidate_vectors,
                    morph_id,
                )
            )
            if candidate_protected_fingerprint != protected_fingerprint:
                raise ReconstructionError(
                    "Head Scale sweep changed a protected Morph at {}".format(
                        value
                    )
                )
            report["candidates"].append(
                {
                    "application": application,
                    "image": image_path,
                    "protected_morph_fingerprint": (
                        candidate_protected_fingerprint
                    ),
                    "value": value,
                }
            )
    finally:
        checked(
            "Restore Head Scale after sweep",
            component.SetShapingMorphWeight(morph_id, initial_weight),
        )
        checked(
            "Refresh restored Head Scale",
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            ),
        )
        checked(
            "Restore current time after Head Scale sweep",
            RLPy.RGlobal.SetTime(initial_time, True),
        )
        QtWidgets.QApplication.processEvents()

    restored_weight = float(component.GetShapingMorphWeight(morph_id))
    restored_vectors = capture_vectors(avatar)
    report["restored_weight"] = restored_weight
    report["restored_vector_fingerprint"] = (
        vectors_excluding_morph_fingerprint(restored_vectors, morph_id)
    )
    report["restored_exactly"] = bool(
        abs(restored_weight - initial_weight) <= 1e-6
        and report["restored_vector_fingerprint"] == protected_fingerprint
    )
    if not report["restored_exactly"]:
        raise ReconstructionError(
            "Current character did not restore exactly after Head Scale sweep"
        )

    report_path = os.path.join(output_dir, "head_scale_sweep.json")
    write_json(report, report_path)
    summary_path = os.path.join(output_dir, "validation_result.json")
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": len(values),
        "success_count": len(report["candidates"]),
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "head_scale_sweep",
        "head_scale_sweep_path": report_path,
        "restored_exactly": report["restored_exactly"],
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def apply_current_head_scale(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Head Scale apply expected one avatar, found {}".format(
                len(avatars)
            )
        )
    morph_id = library.get("head_scale_morph_id")
    if not isinstance(morph_id, str) or not morph_id:
        raise ReconstructionError(
            "head_scale_morph_id must be a non-empty string"
        )
    target = float(library.get("head_scale_target"))
    component, catalog, unused_categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "Head Scale Morph is unavailable: {}".format(morph_id)
        )

    initial_weight = float(component.GetShapingMorphWeight(morph_id))
    initial_time = RLPy.RGlobal.GetTime()
    initial_vectors = capture_vectors(avatar)
    protected_fingerprint = vectors_excluding_morph_fingerprint(
        initial_vectors,
        morph_id,
    )
    image_path = os.path.join(
        output_dir,
        "head_scale_{}_applied.png".format(signed_morph_token(target)),
    )
    applied = False
    try:
        application = apply_single_morph_weight(
            avatar,
            morph_id,
            target,
            "selected Head Scale",
        )
        applied = True
        render_preview(image_path, initial_time)
        final_vectors = capture_vectors(avatar)
        final_protected_fingerprint = vectors_excluding_morph_fingerprint(
            final_vectors,
            morph_id,
        )
        if final_protected_fingerprint != protected_fingerprint:
            raise ReconstructionError(
                "Applying selected Head Scale changed a protected Morph"
            )
        final_weight = float(component.GetShapingMorphWeight(morph_id))
        if abs(final_weight - target) > 1e-6:
            raise ReconstructionError(
                "Selected Head Scale did not remain at target"
            )
    except Exception:
        if applied:
            component.SetShapingMorphWeight(morph_id, initial_weight)
            RLPy.RGlobal.ObjectModified(
                avatar, RLPy.EObjectModifiedType_MorphWeight
            )
            QtWidgets.QApplication.processEvents()
        raise
    finally:
        checked(
            "Restore current time after Head Scale apply",
            RLPy.RGlobal.SetTime(initial_time, True),
        )
        QtWidgets.QApplication.processEvents()

    report = {
        "schema_version": 1,
        "captured_at": now(),
        "avatar": {
            "name": scene_object_name(avatar),
            "id": scene_object_id(avatar),
        },
        "application": application,
        "camera": camera_state(RLPy.RScene.GetCurrentCamera()),
        "final_weight": final_weight,
        "image": image_path,
        "initial_weight": initial_weight,
        "morph": catalog[morph_id],
        "protected_morph_fingerprint": protected_fingerprint,
        "protected_morphs_unchanged": True,
    }
    report_path = os.path.join(output_dir, "head_scale_apply.json")
    write_json(report, report_path)
    summary_path = os.path.join(output_dir, "validation_result.json")
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": report["captured_at"],
        "finished_at": now(),
        "requested_count": 1,
        "success_count": 1,
        "failure_count": 0,
        "success": True,
        "diagnostic_mode": "head_scale_apply",
        "head_scale_apply_path": report_path,
        "protected_morphs_unchanged": True,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


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
    face_material_quality_reference = preset.get(
        "face_material_quality_profile"
    )
    if face_material_quality_reference is not None and not isinstance(
        face_material_quality_reference,
        dict,
    ):
        raise ReconstructionError(
            "face_material_quality_profile must be an object"
        )
    render_static_hair_views = render_static_hair_views_enabled(
        appearance_validation_plan
    )
    asset_load_pacing = resolve_asset_load_pacing(preset)
    head_scale_review_config = preset.get("head_scale_review")
    if head_scale_review_config is not None and not isinstance(
        head_scale_review_config,
        dict,
    ):
        raise ReconstructionError("head_scale_review must be an object")
    neck_morph_review_config = preset.get("neck_morph_review")
    if neck_morph_review_config is not None and not isinstance(
        neck_morph_review_config,
        dict,
    ):
        raise ReconstructionError("neck_morph_review must be an object")
    skip_post_diagnostic_face_validation = preset.get(
        "skip_post_diagnostic_face_validation",
        False,
    )
    if not isinstance(skip_post_diagnostic_face_validation, bool):
        raise ReconstructionError(
            "skip_post_diagnostic_face_validation must be boolean"
        )
    if skip_post_diagnostic_face_validation and not (
        head_scale_review_config is not None
        or neck_morph_review_config is not None
    ):
        raise ReconstructionError(
            "Post-diagnostic face validation can only be skipped for a review"
        )
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
    if face_material_quality_reference is not None:
        artifacts["face_material_quality_profile"] = os.path.join(
            preset_dir,
            "face_material_quality_profile.json",
        )
    save_character_project = library.get("save_character_projects", False)
    if not isinstance(save_character_project, bool):
        raise ReconstructionError("save_character_projects must be boolean")
    if save_character_project:
        artifacts["character_project"] = os.path.join(
            preset_dir,
            "{}.ccProject".format(preset["preset_id"]),
        )
    if preset.get("bodyfit_proportion_adjustment") is not None:
        artifacts["bodyfit_proportion_adjustment"] = os.path.join(
            preset_dir,
            "bodyfit_proportion_adjustment.json",
        )
    if head_scale_review_config is not None:
        artifacts["head_scale_review"] = os.path.join(
            preset_dir,
            "head_scale_review.json",
        )
        artifacts["head_scale_review_directory"] = os.path.join(
            preset_dir,
            "head_scale_review",
        )
    if neck_morph_review_config is not None:
        artifacts["neck_morph_review"] = os.path.join(
            preset_dir,
            "neck_morph_review.json",
        )
        artifacts["neck_morph_review_directory"] = os.path.join(
            preset_dir,
            "neck_morph_review",
        )
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
        "bodyfit_proportion_adjustment": None,
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
        "head_scale_review": None,
        "neck_morph_review": None,
        "post_diagnostic_face_validation_skipped": bool(
            skip_post_diagnostic_face_validation
        ),
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

        avatar, proportion_adjustment_result = (
            apply_bodyfit_proportion_adjustment(
                avatar,
                preset,
                progress_callback=mark_phase,
            )
        )
        if proportion_adjustment_result is not None:
            result["bodyfit_proportion_adjustment"] = (
                proportion_adjustment_result
            )
            write_json(
                proportion_adjustment_result,
                artifacts["bodyfit_proportion_adjustment"],
            )
            result["eye_integrity"]["phases"][
                "after_bodyfit_proportion_adjustment"
            ] = capture_eye_integrity_state(avatar)
            if expected_eyeball_move_weight is not None:
                validate_expected_eye_integrity(
                    result["eye_integrity"]["phases"][
                        "after_bodyfit_proportion_adjustment"
                    ],
                    expected_eyeball_move_weight,
                    "BodyFit proportion adjustment",
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

        if face_material_quality_reference is not None:
            mark_phase(
                "apply_face_material_quality_profile",
                {
                    "profile_id": face_material_quality_reference.get(
                        "profile_id"
                    )
                },
            )
            result["face_material_quality_profile"] = (
                apply_face_material_quality_profile(
                    avatar,
                    face_material_quality_reference,
                )
            )
            write_json(
                result["face_material_quality_profile"],
                artifacts["face_material_quality_profile"],
            )
            result["eye_integrity"]["phases"][
                "after_face_material_quality_profile"
            ] = capture_eye_integrity_state(avatar)
            if expected_eyeball_move_weight is not None:
                validate_expected_eye_integrity(
                    result["eye_integrity"]["phases"][
                        "after_face_material_quality_profile"
                    ],
                    expected_eyeball_move_weight,
                    "face material quality profile",
                )

        if head_scale_review_config is not None:
            result["head_scale_review"] = render_head_scale_review(
                avatar,
                head_scale_review_config,
                artifacts["head_scale_review_directory"],
                artifacts["head_scale_review"],
                progress_callback=mark_phase,
            )
        if neck_morph_review_config is not None:
            result["neck_morph_review"] = render_neck_morph_review(
                avatar,
                neck_morph_review_config,
                artifacts["neck_morph_review_directory"],
                artifacts["neck_morph_review"],
                progress_callback=mark_phase,
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
        ) and not skip_post_diagnostic_face_validation
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
                (
                    post_snapshot_state,
                    post_snapshot_stabilization,
                ) = capture_stable_neutral_eye_state(avatar)
                result["eye_integrity"]["phases"][
                    "post_face_validation_snapshot_restore"
                ] = post_snapshot_state
                result["eye_integrity"][
                    "post_face_validation_snapshot_stabilization"
                ] = post_snapshot_stabilization
            set_avatar_yaw(avatar, math.degrees(initial_yaw_radians))
            set_avatar_position(
                avatar,
                position_x=initial_position["x"],
                position_y=initial_position["y"],
                position_z=initial_position["z"],
            )
            if facial_pose_timeline.get("capture_strategy") == (
                "facial_profile_start_frame_snapshot_restore_v1"
            ):
                post_pose_world_tolerance = float(
                    (
                        appearance_validation_plan
                        or {}
                    ).get(
                        "post_pose_eye_world_translation_tolerance_cm",
                        2e-2,
                    )
                )
                if (
                    not math.isfinite(post_pose_world_tolerance)
                    or post_pose_world_tolerance < 2e-2
                    or post_pose_world_tolerance > 1e-1
                ):
                    raise ReconstructionError(
                        "post-pose eye world tolerance must be from 0.02 to 0.1 cm"
                    )
                (
                    post_face_validation_state,
                    post_face_validation_attempts,
                ) = capture_stable_neutral_eye_state(avatar)
                post_face_validation_comparison = (
                    compare_neutral_eye_states(
                        post_face_validation_expected,
                        post_face_validation_state,
                        include_world=True,
                        include_runtime_ids=False,
                        t_pose_tolerance=0.5,
                        world_translation_tolerance=(
                            post_pose_world_tolerance
                        ),
                    )
                )
                result["eye_integrity"]["phases"][
                    "post_face_validation"
                ] = post_face_validation_state
                result["eye_integrity"][
                    "post_face_validation_comparison"
                ] = post_face_validation_comparison
                result["eye_integrity"][
                    "post_face_validation_refresh_attempts"
                ] = post_face_validation_attempts
            else:
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
        if save_character_project:
            mark_phase("save_character_project")
            result["character_project"] = save_bodyfit_project(
                artifacts["character_project"],
                "Save assembled character project",
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


def capture_current_hair_physics(avatar, require_hair=True):
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
    if not hair_records and require_hair:
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
        "hair_required": bool(require_hair),
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


def _motion_scene_prop_inventory():
    getter = getattr(RLPy.RScene, "GetProps", None)
    if not callable(getter):
        return {"available": False, "objects": []}
    try:
        objects = list(getter() or [])
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "objects": [],
        }
    records = [
        {
            "id": scene_object_id(item),
            "name": scene_object_name(item),
            "python_type": type(item).__name__,
        }
        for item in objects
    ]
    records.sort(key=lambda item: (item["name"], item["id"]))
    return {"available": True, "objects": records}


def _motion_animated_bone_inventory(skeleton):
    face_tokens = (
        "brow",
        "cheek",
        "eye",
        "eyelid",
        "facial",
        "jaw",
        "lip",
        "mouth",
        "nose",
        "teeth",
        "tongue",
    )
    animated = []
    errors = []
    for bone in list(skeleton.GetSkinBones() or []):
        name = str(bone.GetName())
        try:
            if skeleton.IsBoneAnimated(bone):
                animated.append(name)
        except Exception as exc:
            if len(errors) < 12:
                errors.append({"bone": name, "error": str(exc)})
    animated = sorted(set(animated))
    facial = [
        name
        for name in animated
        if any(token in name.lower() for token in face_tokens)
    ]
    return {
        "animated_bone_count": len(animated),
        "animated_bones": animated,
        "facial_bone_candidate_count": len(facial),
        "facial_bone_candidates": facial,
        "read_errors": errors,
    }


def _motion_landmark_priority(name):
    lowered = str(name).lower()
    if lowered in ("root", "cc_base_root", "rl_boneroot"):
        priority = 0
    elif lowered.endswith("_boneroot") or lowered.endswith("_root"):
        priority = 1
    elif "hip" in lowered:
        priority = 2
    elif "pelvis" in lowered:
        priority = 3
    else:
        priority = 4
    return priority, lowered


def _motion_landmark_bones(skeleton):
    candidates = {}
    for bone in list(skeleton.GetSkinBones() or []):
        name = str(bone.GetName())
        lowered = name.lower()
        if any(token in lowered for token in ("root", "hip", "pelvis")):
            candidates.setdefault(
                name,
                (_motion_landmark_priority(name), name, bone),
            )
    ordered = sorted(candidates.values(), key=lambda item: item[0])
    return [item[2] for item in ordered[:6]]


def _capture_motion_landmark_bones(bones):
    records = []
    for bone in bones:
        name = str(bone.GetName())
        try:
            bone.Update()
            records.append(
                {
                    "name": name,
                    "local_transform": _transform_data(
                        bone.LocalTransform()
                    ),
                    "world_transform": _transform_data(
                        bone.WorldTransform()
                    ),
                }
            )
        except Exception as exc:
            records.append({"name": name, "error": str(exc)})
    return records


def _motion_primary_landmark_translation(records):
    candidates = [
        item
        for item in records
        if item.get("name")
        and not item.get("error")
        and isinstance(
            (item.get("world_transform") or {}).get("translation"),
            dict,
        )
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: _motion_landmark_priority(item["name"])
    )
    selected = candidates[0]
    translation = selected["world_transform"]["translation"]
    return {
        "name": selected["name"],
        "translation": dict(
            (axis, float(translation[axis]))
            for axis in ("x", "y", "z")
        ),
    }


def _motion_capture_reference(subject_position, primary_landmark):
    if isinstance(subject_position, dict) and all(
        isinstance(subject_position.get(axis), (int, float))
        for axis in ("x", "y", "z")
    ):
        return {
            "source": "framing_target",
            "translation": dict(
                (axis, float(subject_position[axis]))
                for axis in ("x", "y", "z")
            ),
        }
    return {
        "source": "first_sample_root",
        "translation": dict(primary_landmark["translation"]),
    }


def _motion_avatar_transform_values(avatar, time_value):
    control = avatar.GetControl("Transform")
    if control is None:
        raise ReconstructionError(
            "Motion capture subject has no Transform control"
        )
    data_block = control.GetDataBlock()
    if data_block is None:
        raise ReconstructionError(
            "Motion capture subject Transform has no data block"
        )
    values = {}
    for axis, parameter_id in (
        ("x", "Position/PositionX"),
        ("y", "Position/PositionY"),
        ("z", "Position/PositionZ"),
    ):
        value = data_block.GetData(parameter_id, time_value)
        if value is None:
            raise ReconstructionError(
                "Motion capture Transform parameter is unavailable: {}".format(
                    parameter_id
                )
            )
        values[axis] = float(value.ToFloat())
    return data_block, values


def _motion_set_avatar_transform_values(
    data_block,
    time_value,
    values,
    label,
):
    for axis, parameter_id in (
        ("x", "Position/PositionX"),
        ("y", "Position/PositionY"),
        ("z", "Position/PositionZ"),
    ):
        checked(
            "{} {}".format(label, parameter_id),
            data_block.SetData(
                parameter_id,
                time_value,
                RLPy.RVariant(float(values[axis])),
            ),
        )
    checked(
        "Refresh {}".format(label),
        RLPy.RGlobal.SetTime(time_value, True),
    )


def _motion_horizontal_distance(first, last):
    return math.sqrt(
        (float(last["x"]) - float(first["x"])) ** 2
        + (float(last["y"]) - float(first["y"])) ** 2
    )


def _classify_motion_root_evidence(samples):
    if len(samples) < 2:
        return {
            "classification": "insufficient_samples",
            "evidence_source": None,
        }
    first = samples[0]
    last = samples[-1]
    first_landmarks = dict(
        (item.get("name"), item)
        for item in first.get("landmark_bones") or []
        if item.get("name") and not item.get("error")
    )
    last_landmarks = dict(
        (item.get("name"), item)
        for item in last.get("landmark_bones") or []
        if item.get("name") and not item.get("error")
    )
    common = [name for name in first_landmarks if name in last_landmarks]
    common.sort(key=_motion_landmark_priority)
    displacement = None
    evidence_source = None
    landmark_name = None
    if common:
        landmark_name = common[0]
        first_translation = first_landmarks[landmark_name][
            "world_transform"
        ]["translation"]
        last_translation = last_landmarks[landmark_name][
            "world_transform"
        ]["translation"]
        displacement = _motion_horizontal_distance(
            first_translation, last_translation
        )
        evidence_source = "landmark_bone_world_translation"
    else:
        first_bounds = first.get("avatar_bounds") or {}
        last_bounds = last.get("avatar_bounds") or {}
        if len(first_bounds.get("center") or []) >= 2 and len(
            last_bounds.get("center") or []
        ) >= 2:
            displacement = math.sqrt(
                (
                    float(last_bounds["center"][0])
                    - float(first_bounds["center"][0])
                )
                ** 2
                + (
                    float(last_bounds["center"][1])
                    - float(first_bounds["center"][1])
                )
                ** 2
            )
            evidence_source = "avatar_bounds_center"
    if displacement is None:
        classification = "unavailable"
    elif displacement >= 15.0:
        classification = "moving_candidate"
    elif displacement <= 5.0:
        classification = "in_place_candidate"
    else:
        classification = "ambiguous"
    return {
        "classification": classification,
        "evidence_source": evidence_source,
        "landmark_bone": landmark_name,
        "first_to_last_horizontal_distance_cm": displacement,
        "thresholds_cm": {"in_place_max": 5.0, "moving_min": 15.0},
    }


def _motion_facial_channel_class(face_clip_delta, animated_bones):
    has_face_clip = int(face_clip_delta) > 0
    has_facial_bones = int(
        animated_bones.get("facial_bone_candidate_count", 0)
    ) > 0
    if has_face_clip and has_facial_bones:
        return "mixed_face_clip_and_facial_bones"
    if has_face_clip:
        return "face_clip_present"
    if has_facial_bones:
        return "facial_bones_present"
    return "none_detected"


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
    camera_mode = probe.get("camera_mode", "loaded_preset")
    if camera_mode not in ("loaded_preset", "lightroom_current"):
        raise ReconstructionError(
            "Unsupported hair motion camera mode: {}".format(camera_mode)
        )
    camera_path = None
    if camera_mode == "loaded_preset":
        camera_path = canonical_existing_file(
            probe.get("camera_path"),
            "Hair motion probe camera",
        )
    sample_normalized_positions = probe.get(
        "sample_normalized_positions"
    )
    sample_frames = probe.get("sample_frames")
    sample_interval_frames = probe.get("sample_interval_frames")
    if sample_normalized_positions is not None:
        if (
            not isinstance(sample_normalized_positions, list)
            or not sample_normalized_positions
            or any(
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not math.isfinite(float(item))
                or float(item) < 0.0
                or float(item) > 1.0
                for item in sample_normalized_positions
            )
        ):
            raise ReconstructionError(
                "hair_motion_probe.sample_normalized_positions must "
                "contain values from 0 to 1"
            )
        sample_normalized_positions = sorted(
            set(float(item) for item in sample_normalized_positions)
        )
        if sample_frames is not None or sample_interval_frames is not None:
            raise ReconstructionError(
                "hair_motion_probe sampling modes are mutually exclusive"
            )
    elif sample_interval_frames is not None:
        if (
            isinstance(sample_interval_frames, bool)
            or not isinstance(sample_interval_frames, int)
            or sample_interval_frames <= 0
        ):
            raise ReconstructionError(
                "hair_motion_probe.sample_interval_frames must be a "
                "positive integer"
            )
        if sample_frames is not None:
            raise ReconstructionError(
                "hair_motion_probe sampling modes are mutually exclusive"
            )
    else:
        sample_frames = sample_frames or [0, 30, 60, 90, 120]
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
    raw_yaw_degrees = probe.get("yaw_degrees", 90.0)
    yaw_degrees = (
        None if raw_yaw_degrees is None else float(raw_yaw_degrees)
    )
    segment_timeout_seconds = float(
        probe.get("segment_timeout_seconds", 20.0)
    )
    if segment_timeout_seconds <= 0.0:
        raise ReconstructionError(
            "hair_motion_probe.segment_timeout_seconds must be positive"
        )
    auto_frame_full_body = probe.get("auto_frame_full_body", False)
    if not isinstance(auto_frame_full_body, bool):
        raise ReconstructionError(
            "hair_motion_probe.auto_frame_full_body must be a boolean"
        )
    require_hair_physics = probe.get("require_hair_physics", True)
    if not isinstance(require_hair_physics, bool):
        raise ReconstructionError(
            "hair_motion_probe.require_hair_physics must be a boolean"
        )
    follow_root_for_capture = probe.get("follow_root_for_capture", False)
    if not isinstance(follow_root_for_capture, bool):
        raise ReconstructionError(
            "hair_motion_probe.follow_root_for_capture must be a boolean"
        )
    align_motion_start_to_source = probe.get(
        "align_motion_start_to_source", False
    )
    if not isinstance(align_motion_start_to_source, bool):
        raise ReconstructionError(
            "hair_motion_probe.align_motion_start_to_source must be a boolean"
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
    initial_scene_props = _motion_scene_prop_inventory()
    report = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "captured_at": now(),
        "camera_mode": camera_mode,
        "camera_path": camera_path,
        "fps": float(fps.ToFloat()),
        "initial_hair_physics": capture_current_hair_physics(
            avatar,
            require_hair=require_hair_physics,
        ),
        "initial_scene_props": initial_scene_props,
        "motion_path": motion_path,
        "samples": [],
        "schema_version": 1,
    }
    baseline_clip_count = initial_clip_count
    baseline_face_clip_count = initial_face_clip_count
    landmark_bones = _motion_landmark_bones(skeleton)
    source_anchor_landmarks = []
    source_anchor = None
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
            "Set source anchor frame",
            RLPy.RGlobal.SetTime(clip_start, True),
        )
        source_anchor_landmarks = _capture_motion_landmark_bones(
            landmark_bones
        )
        source_anchor = _motion_primary_landmark_translation(
            source_anchor_landmarks
        )
        if align_motion_start_to_source and source_anchor is None:
            raise ReconstructionError(
                "Motion start alignment has no source root landmark"
            )
        report["source_anchor_landmarks"] = source_anchor_landmarks

        if camera_mode == "loaded_preset":
            camera_status, camera_dialogs = (
                load_file_with_optional_undo_warning(
                    camera_path,
                    "Load hair motion probe camera",
                )
            )
        else:
            camera_status = {
                "is_error": False,
                "returned": True,
                "status_code": "current_after_lightroom",
            }
            camera_dialogs = {
                "observed_dialogs": [],
                "policy": "no_camera_file_load",
            }
        motion_camera = RLPy.RScene.GetCurrentCamera()
        if motion_camera is None:
            raise ReconstructionError(
                "Hair motion probe has no active camera"
            )
        report["camera"] = camera_state(motion_camera)
        report["camera_follow_policy"] = {
            "enabled": follow_root_for_capture,
            "evidence_captured_before_camera_follow": True,
            "landmark_priority": "RL_BoneRoot_then_root_then_hip",
            "method": "temporary_avatar_transform_offset",
            "subject_transform_restored_after_each_capture": True,
        }
        report["camera_load_status"] = camera_status
        report["camera_load_dialogs"] = camera_dialogs
        RLPy.RScene.SelectObject(avatar)
        props_before_motion = _motion_scene_prop_inventory()
        motion_status, motion_dialogs = (
            load_file_with_optional_undo_warning(
                motion_path,
                "Load hair motion probe",
            )
        )
        QtWidgets.QApplication.processEvents()
        props_after_motion = _motion_scene_prop_inventory()
        report["motion_load_status"] = motion_status
        report["motion_load_dialogs"] = motion_dialogs
        report["scene_props_before_motion"] = props_before_motion
        report["scene_props_after_motion"] = props_after_motion
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
        if sample_normalized_positions is not None:
            bounded_frames = sorted(
                set(
                    min(
                        int(round(position * clip_length_frame)),
                        clip_length_frame,
                    )
                    for position in sample_normalized_positions
                )
            )
        elif sample_interval_frames is not None:
            bounded_frames = list(
                range(0, clip_length_frame + 1, sample_interval_frames)
            )
            if bounded_frames[-1] != clip_length_frame:
                bounded_frames.append(clip_length_frame)
        else:
            bounded_frames = sorted(
                set(
                    min(frame, clip_length_frame)
                    for frame in sample_frames
                )
            )
        animated_bones = _motion_animated_bone_inventory(skeleton)
        face_clip_count_after_load = (
            int(face_component.GetClipCount())
            if face_component is not None
            else 0
        )
        face_clip_delta = (
            face_clip_count_after_load - baseline_face_clip_count
        )
        report["clip"] = {
            "clip_count_after_load": clip_count,
            "face_clip_count_after_load": face_clip_count_after_load,
            "face_clip_delta": face_clip_delta,
            "animated_bones": animated_bones,
            "facial_channel_class": _motion_facial_channel_class(
                face_clip_delta, animated_bones
            ),
            "length_frame": clip_length_frame,
            "load_method": "RFileIO.LoadFile",
            "python_type": type(clip).__name__,
            "sample_normalized_positions": sample_normalized_positions,
            "sample_frames": bounded_frames,
            "sample_interval_frames": sample_interval_frames,
        }
        checked(
            "Set hair motion start frame for framing",
            RLPy.RGlobal.SetTime(clip_start, True),
        )
        motion_start_alignment = None
        capture_position = dict(subject_position)
        if auto_frame_full_body:
            framing = _outfit_gate_frame_full_body(
                avatar,
                motion_camera,
                yaw_degrees=(
                    yaw_degrees
                    if yaw_degrees is not None
                    else math.degrees(initial_yaw_radians)
                ),
            )
            subject_position = dict(framing["target_position"])
            capture_position = dict(subject_position)
            report["framing"] = framing
        else:
            report["framing"] = None
            if align_motion_start_to_source:
                motion_start_landmarks = _capture_motion_landmark_bones(
                    landmark_bones
                )
                motion_start_anchor = _motion_primary_landmark_translation(
                    motion_start_landmarks
                )
                if motion_start_anchor is None:
                    raise ReconstructionError(
                        "Motion start alignment has no motion root landmark"
                    )
                offset = dict(
                    (
                        axis,
                        source_anchor["translation"][axis]
                        - motion_start_anchor["translation"][axis],
                    )
                    for axis in ("x", "y", "z")
                )
                capture_position = dict(
                    (
                        axis,
                        initial_position[axis] + offset[axis],
                    )
                    for axis in ("x", "y", "z")
                )
                motion_start_alignment = {
                    "enabled": True,
                    "landmark": source_anchor["name"],
                    "source_translation": dict(
                        source_anchor["translation"]
                    ),
                    "motion_translation_before_alignment": dict(
                        motion_start_anchor["translation"]
                    ),
                    "avatar_transform_offset": offset,
                    "target_avatar_position": dict(capture_position),
                }
        report["motion_start_alignment"] = motion_start_alignment
        set_avatar_position(
            avatar,
            position_x=float(
                capture_position.get(
                    "x", initial_position["x"]
                )
            ),
            position_y=float(
                capture_position.get(
                    "y", initial_position["y"]
                )
            ),
            position_z=float(
                capture_position.get(
                    "z", initial_position["z"]
                )
            ),
        )
        if yaw_degrees is not None:
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
        camera_follow_reference = None
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
            sample_bounds = capture_bounds(avatar)
            sample_world_transform = _transform_data(
                avatar.WorldTransform()
            )
            sample_landmarks = _capture_motion_landmark_bones(
                landmark_bones
            )
            sample_hair_physics = capture_current_hair_physics(
                avatar,
                require_hair=require_hair_physics,
            )
            camera_follow = None
            transform_data_block = None
            original_transform_values = None
            if follow_root_for_capture:
                primary_landmark = (
                    _motion_primary_landmark_translation(
                        sample_landmarks
                    )
                )
                if primary_landmark is None:
                    raise ReconstructionError(
                        "Hair motion camera follow has no root landmark"
                    )
                if camera_follow_reference is None:
                    camera_follow_reference = _motion_capture_reference(
                        subject_position if auto_frame_full_body else {},
                        primary_landmark,
                    )
                reference_translation = camera_follow_reference[
                    "translation"
                ]
                current_translation = primary_landmark["translation"]
                root_delta = dict(
                    (
                        axis,
                        current_translation[axis]
                        - reference_translation[axis],
                    )
                    for axis in ("x", "y", "z")
                )
                transform_data_block, original_transform_values = (
                    _motion_avatar_transform_values(
                        avatar,
                        target_time,
                    )
                )
                capture_offset = dict(
                    (axis, -root_delta[axis])
                    for axis in ("x", "y", "z")
                )
                capture_transform_values = dict(
                    (
                        axis,
                        original_transform_values[axis]
                        + capture_offset[axis],
                    )
                    for axis in ("x", "y", "z")
                )
                _motion_set_avatar_transform_values(
                    transform_data_block,
                    target_time,
                    capture_transform_values,
                    "Offset hair motion capture frame {}".format(frame),
                )
                checked(
                    "Restore hair motion camera at followed frame {}".format(
                        frame
                    ),
                    RLPy.RScene.SetCurrentCamera(motion_camera),
                )
                QtWidgets.QApplication.processEvents()
                camera_follow = {
                    "capture_offset": capture_offset,
                    "landmark": primary_landmark["name"],
                    "reference_source": camera_follow_reference["source"],
                    "reference_translation": dict(reference_translation),
                    "root_delta": root_delta,
                }
            image_path = os.path.join(
                output_dir,
                "hair_motion_frame_{:04d}.png".format(frame),
            )
            try:
                render_preview(image_path, target_time)
            finally:
                if (
                    transform_data_block is not None
                    and original_transform_values is not None
                ):
                    _motion_set_avatar_transform_values(
                        transform_data_block,
                        target_time,
                        original_transform_values,
                        "Restore hair motion subject frame {}".format(frame),
                    )
                    QtWidgets.QApplication.processEvents()
            report["samples"].append(
                {
                    "avatar_bounds": sample_bounds,
                    "avatar_world_transform": sample_world_transform,
                    "camera_follow": camera_follow,
                    "frame": frame,
                    "hair_physics": sample_hair_physics,
                    "image": image_path,
                    "image_record": _outfit_gate_image_record(
                        image_path
                    ),
                    "landmark_bones": sample_landmarks,
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

    report["root_motion_evidence"] = (
        _classify_motion_root_evidence(report["samples"])
    )
    before_prop_ids = set(
        item["id"]
        for item in report.get("scene_props_before_motion", {}).get(
            "objects", []
        )
    )
    added_props = [
        item
        for item in report.get("scene_props_after_motion", {}).get(
            "objects", []
        )
        if item["id"] not in before_prop_ids
    ]
    report["hidden_dependency_evidence"] = {
        "added_scene_props": added_props,
        "automatic_classification": (
            "scene_prop_added" if added_props else "none_detected"
        ),
        "manual_visual_review_required": True,
    }
    report["loop_evidence"] = {
        "automatic_classification": "pending_visual_review",
        "first_frame": (
            report["samples"][0]["frame"] if report["samples"] else None
        ),
        "last_frame": (
            report["samples"][-1]["frame"] if report["samples"] else None
        ),
    }
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


def _animation_p0_verified_file(record, label):
    if not isinstance(record, dict):
        raise ReconstructionError("{} record must be an object".format(label))
    path = canonical_existing_file(record.get("path"), label)
    expected_size = record.get("size_bytes", record.get("bytes"))
    if expected_size is not None and os.path.getsize(path) != int(
        expected_size
    ):
        raise ReconstructionError("{} size changed".format(label))
    digest = sha256_file(path)
    expected_digest = record.get("sha256")
    if expected_digest is not None and digest != expected_digest:
        raise ReconstructionError("{} SHA-256 changed".format(label))
    return {
        "bytes": os.path.getsize(path),
        "path": path,
        "sha256": digest,
    }


def run_animation_p0_dynamic_gate(
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "P0 animation actor IDs must be non-empty and unique"
        )
    unknown = sorted(set(selected_ids) - set(by_id))
    if unknown:
        raise ReconstructionError(
            "Unknown P0 animation actors: {}".format(unknown)
        )

    capture_policy = library.get("capture_policy") or {}
    camera_mode = capture_policy.get("camera_mode", "lightroom_current")
    if camera_mode not in ("loaded_preset", "lightroom_current"):
        raise ReconstructionError(
            "Unsupported P0 animation camera mode: {}".format(camera_mode)
        )
    camera_record = None
    if camera_mode == "loaded_preset":
        camera_record = _animation_p0_verified_file(
            library.get("full_body_camera"),
            "P0 animation full-body camera",
        )
    lightroom_record = _animation_p0_verified_file(
        library.get("lightroom"),
        "P0 animation Lightroom",
    )
    manifest_record = _animation_p0_verified_file(
        library.get("source_pilot_manifest"),
        "P0 Pilot manifest",
    )
    review_template_record = _animation_p0_verified_file(
        library.get("source_dynamic_review_template"),
        "P0 dynamic review template",
    )
    pilot_manifest = read_json(manifest_record["path"])
    review_document = read_json(review_template_record["path"])
    expected_pilot_id = (
        library.get("source_pilot_manifest") or {}
    ).get("pilot_id")
    if pilot_manifest.get("pilot_id") != expected_pilot_id:
        raise ReconstructionError("P0 Pilot manifest ID changed")
    if review_document.get("pilot_id") != expected_pilot_id:
        raise ReconstructionError("P0 dynamic review ID changed")
    if review_document.get("status") != "not_started":
        raise ReconstructionError("P0 dynamic review template is not pristine")

    review_cases = review_document.get("cases") or []
    review_by_id = dict((item.get("case_id"), item) for item in review_cases)
    if len(review_by_id) != len(review_cases):
        raise ReconstructionError(
            "P0 dynamic review case IDs are invalid or duplicated"
        )
    execution_policy = library.get("execution_policy") or {}
    sample_positions = capture_policy.get("sample_normalized_positions")
    sample_interval_frames = capture_policy.get("sample_interval_frames")
    if sample_positions is None and sample_interval_frames is None:
        sample_positions = [0.0, 0.25, 0.5, 0.75, 1.0]
    raw_yaw_degrees = capture_policy.get("yaw_degrees")
    yaw_degrees = (
        None if raw_yaw_degrees is None else float(raw_yaw_degrees)
    )
    auto_frame_full_body = capture_policy.get(
        "auto_frame_full_body", False
    )
    if not isinstance(auto_frame_full_body, bool):
        raise ReconstructionError(
            "P0 auto_frame_full_body must be a boolean"
        )
    align_motion_start_to_source = capture_policy.get(
        "align_motion_start_to_source", True
    )
    if not isinstance(align_motion_start_to_source, bool):
        raise ReconstructionError(
            "P0 align_motion_start_to_source must be a boolean"
        )
    segment_timeout_seconds = float(
        capture_policy.get("segment_timeout_seconds", 45.0)
    )
    continue_after_failure = bool(
        execution_policy.get("continue_after_motion_failure", True)
    )

    selected_case_count = sum(
        len(by_id[preset_id].get("motion_cases") or [])
        for preset_id in selected_ids
    )
    if selected_case_count <= 0:
        raise ReconstructionError("P0 animation gate has no selected cases")
    selected_case_ids = []
    for preset_id in selected_ids:
        for case in by_id[preset_id].get("motion_cases") or []:
            case_id = case.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                raise ReconstructionError("P0 animation case ID is invalid")
            selected_case_ids.append(case_id)
            if case_id not in review_by_id:
                raise ReconstructionError(
                    "P0 animation review is missing {}".format(case_id)
                )
            if case.get("production_status") != "not_approved":
                raise ReconstructionError(
                    "P0 animation case inherited production approval"
                )
    if len(selected_case_ids) != len(set(selected_case_ids)):
        raise ReconstructionError("P0 animation case IDs are duplicated")

    started_at = now()
    progress_path = os.path.join(output_dir, "progress.json")
    review_output_path = os.path.join(
        output_dir, "dynamic_review_automation.json"
    )
    summary_path = os.path.join(output_dir, "validation_result.json")
    cases_root = os.path.join(output_dir, "cases")
    os.makedirs(cases_root, exist_ok=True)
    results = []
    actor_results = []
    completed_case_ids = set()

    def write_checkpoint(phase, active_actor=None, active_case=None):
        failed = [item for item in results if not item.get("success")]
        review_status = (
            "automation_complete_pending_visual_review"
            if phase == "complete" and not failed
            else (
                "automation_complete_with_failures_pending_review"
                if phase == "complete"
                else "automation_in_progress"
            )
        )
        review_document["status"] = review_status
        review_document["automation"] = {
            "completed_case_count": len(completed_case_ids),
            "expected_case_count": selected_case_count,
            "failure_count": len(failed),
            "finished_at": now() if phase == "complete" else None,
            "phase": phase,
            "production_approved_count": 0,
            "started_at": started_at,
        }
        write_json(review_document, review_output_path)
        summary = {
            "schema_version": 1,
            "diagnostic_mode": "animation_p0_dynamic_gate",
            "library_id": library.get("library_id"),
            "pilot_id": expected_pilot_id,
            "started_at": started_at,
            "finished_at": now() if phase == "complete" else None,
            "phase": phase,
            "requested_count": selected_case_count,
            "success_count": len(results) - len(failed),
            "failure_count": len(failed),
            "success": bool(
                phase == "complete"
                and not failed
                and len(results) == selected_case_count
            ),
            "production_approved_count": 0,
            "actor_results": actor_results,
            "results": results,
            "review_path": review_output_path,
            "progress_path": progress_path,
            "summary_path": summary_path,
        }
        write_json(summary, summary_path)
        write_json(
            {
                "schema_version": 1,
                "updated_at": now(),
                "phase": phase,
                "active_actor": active_actor,
                "active_case": active_case,
                "completed_case_count": len(completed_case_ids),
                "expected_case_count": selected_case_count,
                "failure_count": len(failed),
            },
            progress_path,
        )
        return summary

    write_checkpoint("initializing")
    for actor_index, preset_id in enumerate(selected_ids, 1):
        preset = by_id[preset_id]
        log(
            "P0 animation actor {}/{}: {}".format(
                actor_index, len(selected_ids), preset_id
            )
        )
        source_project = _animation_p0_verified_file(
            preset.get("source_project"),
            "P0 actor project {}".format(preset_id),
        )
        actor_started_at = now()
        write_checkpoint("loading_actor", preset_id)
        source_status, source_dialogs = (
            load_file_with_optional_undo_warning(
                source_project["path"],
                "Load P0 animation actor {}".format(preset_id),
            )
        )
        settle_cc_ui(5.0)
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "P0 actor {} loaded {} avatars".format(
                    preset_id, len(avatars)
                )
            )
        motion_cleanup = clear_avatar_motion(avatar)
        lightroom_status, lightroom_dialogs = (
            load_file_with_optional_undo_warning(
                lightroom_record["path"],
                "Load P0 animation Lightroom",
            )
        )
        settle_cc_ui(1.0)
        actor_result = {
            "preset_id": preset_id,
            "sex": preset.get("sex"),
            "started_at": actor_started_at,
            "source_project": source_project,
            "source_load_status": source_status,
            "source_load_dialogs": source_dialogs,
            "initial_motion_cleanup": motion_cleanup,
            "lightroom": lightroom_record,
            "lightroom_load_status": lightroom_status,
            "lightroom_load_dialogs": lightroom_dialogs,
            "case_ids": [],
        }
        actor_results.append(actor_result)

        for case_index, case in enumerate(preset.get("motion_cases") or [], 1):
            case_id = case["case_id"]
            log(
                "P0 animation {} {}/{}: {}".format(
                    preset_id,
                    case_index,
                    len(preset.get("motion_cases") or []),
                    case_id,
                )
            )
            write_checkpoint("running_motion", preset_id, case_id)
            motion_record = _animation_p0_verified_file(
                case.get("motion"),
                "P0 motion {}".format(case_id),
            )
            case_dir = os.path.join(cases_root, preset_id, case_id)
            result = {
                "case_id": case_id,
                "motion_id": case.get("motion_id"),
                "pilot_actor_preset_id": preset_id,
                "review_family": case.get("review_family"),
                "source_format": case.get("source_format"),
                "motion": motion_record,
                "started_at": now(),
                "success": False,
            }
            review_case = review_by_id[case_id]
            try:
                motion_summary = probe_current_hair_motion(
                    {
                        "hair_motion_probe": {
                            "motion_path": motion_record["path"],
                            "camera_mode": camera_mode,
                            "camera_path": (
                                camera_record["path"]
                                if camera_record is not None
                                else None
                            ),
                            "sample_normalized_positions": sample_positions,
                            "sample_interval_frames": sample_interval_frames,
                            "yaw_degrees": yaw_degrees,
                            "replace_existing_motion_clips": True,
                            "segment_timeout_seconds": (
                                segment_timeout_seconds
                            ),
                            "auto_frame_full_body": auto_frame_full_body,
                            "align_motion_start_to_source": (
                                align_motion_start_to_source
                            ),
                            "follow_root_for_capture": True,
                            "require_hair_physics": False,
                        }
                    },
                    case_dir,
                )
                motion_report = read_json(
                    motion_summary["hair_motion_probe_path"]
                )
                if sha256_file(motion_record["path"]) != motion_record["sha256"]:
                    raise ReconstructionError(
                        "P0 motion changed while loaded: {}".format(case_id)
                    )
                hidden_props = (
                    motion_report.get("hidden_dependency_evidence", {})
                    .get("added_scene_props", [])
                )
                review_case.update(
                    {
                        "load_status": "succeeded",
                        "motion_length_frames": motion_report["clip"][
                            "length_frame"
                        ],
                        "fps": motion_report.get("fps"),
                        "loop_class": "pending_visual_review",
                        "root_motion_class": motion_report.get(
                            "root_motion_evidence", {}
                        ).get("classification", "unavailable"),
                        "facial_channel_class": motion_report["clip"].get(
                            "facial_channel_class", "unavailable"
                        ),
                        "hidden_dependencies": [
                            {
                                "type": "scene_prop_added",
                                "name": item.get("name"),
                                "object_id": item.get("id"),
                            }
                            for item in hidden_props
                        ],
                        "visual_decision": "pending",
                        "notes": [
                            "Automation evidence only; visual approval is pending."
                        ],
                        "automation_evidence": {
                            "report_path": motion_summary[
                                "hair_motion_probe_path"
                            ],
                            "sample_images": [
                                item.get("image_record", {}).get(
                                    "path", item.get("image")
                                )
                                for item in motion_report.get("samples") or []
                            ],
                            "root_motion_evidence": motion_report.get(
                                "root_motion_evidence"
                            ),
                            "face_clip_delta": motion_report["clip"].get(
                                "face_clip_delta"
                            ),
                            "facial_bone_candidate_count": motion_report[
                                "clip"
                            ].get("animated_bones", {}).get(
                                "facial_bone_candidate_count"
                            ),
                        },
                    }
                )
                result.update(
                    {
                        "success": True,
                        "finished_at": now(),
                        "motion_summary": motion_summary,
                        "motion_report_path": motion_summary[
                            "hair_motion_probe_path"
                        ],
                    }
                )
            except BlockingDialogError:
                review_case["load_status"] = "blocked_by_dialog"
                review_case["notes"] = [traceback.format_exc()]
                result["error"] = {
                    "type": "BlockingDialogError",
                    "message": "Known-safe automation could not resolve a dialog",
                    "traceback": traceback.format_exc(),
                }
                result["finished_at"] = now()
                results.append(result)
                actor_result["case_ids"].append(case_id)
                completed_case_ids.add(case_id)
                write_checkpoint("blocked", preset_id, case_id)
                raise
            except Exception as exc:
                review_case["load_status"] = "failed"
                review_case["notes"] = [
                    "{}: {}".format(type(exc).__name__, exc)
                ]
                result["error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
                result["finished_at"] = now()
            results.append(result)
            actor_result["case_ids"].append(case_id)
            completed_case_ids.add(case_id)
            write_checkpoint("motion_complete", preset_id, case_id)
            QtWidgets.QApplication.processEvents()
            if not result["success"] and not continue_after_failure:
                return write_checkpoint(
                    "stopped_after_failure", preset_id, case_id
                )

        actor_result["finished_at"] = now()
        actor_result["source_project_unchanged"] = bool(
            sha256_file(source_project["path"]) == source_project["sha256"]
        )
        if not actor_result["source_project_unchanged"]:
            raise ReconstructionError(
                "P0 actor source project changed: {}".format(preset_id)
            )
        write_checkpoint("actor_complete", preset_id)

    return write_checkpoint("complete")


def export_current_rlmotion_fbx(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    payload = library.get("rlmotion_fbx_export") or {}
    source_project = payload.get("source_project") or {}
    source_project_path = None
    source_project_sha256 = None
    source_project_load = None
    if source_project:
        if not isinstance(source_project, dict):
            raise ReconstructionError(
                "rlmotion_fbx_export.source_project must be an object"
            )
        source_project_path = canonical_existing_file(
            source_project.get("path"),
            "rlMotion FBX carrier project",
        )
        expected_bytes = source_project.get("bytes")
        if expected_bytes is not None and os.path.getsize(source_project_path) != int(
            expected_bytes
        ):
            raise ReconstructionError("rlMotion FBX carrier project size changed")
        source_project_sha256 = sha256_file(source_project_path)
        expected_sha256 = source_project.get("sha256")
        if expected_sha256 and source_project_sha256 != expected_sha256:
            raise ReconstructionError("rlMotion FBX carrier project hash changed")
        load_status, load_dialogs = load_file_with_optional_undo_warning(
            source_project_path,
            "Load rlMotion FBX carrier project",
        )
        source_project_load = {
            "dialogs": load_dialogs,
            "status": load_status,
        }
        QtWidgets.QApplication.processEvents()

    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "rlMotion FBX export expected one avatar, found {}".format(
                len(avatars)
            )
        )
    motion_path = canonical_existing_file(
        payload.get("motion_path"),
        "rlMotion FBX export",
    )
    require_file_extension(
        motion_path,
        ".rlmotion",
        "rlMotion FBX export",
    )
    output_filename = payload.get("output_filename")
    if (
        not isinstance(output_filename, str)
        or not output_filename
        or os.path.basename(output_filename) != output_filename
        or not output_filename.lower().endswith(".fbx")
    ):
        raise ReconstructionError(
            "rlmotion_fbx_export.output_filename must be a simple .fbx filename"
        )
    fbx_path = os.path.join(output_dir, output_filename)
    if os.path.isfile(fbx_path):
        os.remove(fbx_path)

    skeleton = avatar.GetSkeletonComponent()
    if skeleton is None:
        raise ReconstructionError(
            "rlMotion FBX export avatar has no skeleton component"
        )
    face_component = avatar.GetFaceComponent()
    initial_clip_count = int(skeleton.GetClipCount())
    initial_face_clip_count = (
        int(face_component.GetClipCount())
        if face_component is not None
        else 0
    )
    cleared_timeline = {
        "body_clip_count": 0,
        "face_clip_count": 0,
    }
    if bool(payload.get("clear_existing_timeline", False)):
        for clip_index in range(initial_clip_count - 1, -1, -1):
            skeleton.DeleteClip(skeleton.GetClip(clip_index))
            cleared_timeline["body_clip_count"] += 1
            QtWidgets.QApplication.processEvents()
        if face_component is not None:
            for clip_index in range(initial_face_clip_count - 1, -1, -1):
                face_component.DeleteClip(face_component.GetClip(clip_index))
                cleared_timeline["face_clip_count"] += 1
                QtWidgets.QApplication.processEvents()
        initial_clip_count = int(skeleton.GetClipCount())
        initial_face_clip_count = (
            int(face_component.GetClipCount())
            if face_component is not None
            else 0
        )
    if bool(payload.get("require_empty_timeline", True)) and (
        initial_clip_count != 0 or initial_face_clip_count != 0
    ):
        raise ReconstructionError(
            "rlMotion FBX export requires an empty timeline; found {} body and "
            "{} face clips".format(
                initial_clip_count,
                initial_face_clip_count,
            )
        )

    started_at = now()
    initial_time = RLPy.RGlobal.GetTime()
    initial_start_time = RLPy.RGlobal.GetStartTime()
    initial_end_time = RLPy.RGlobal.GetEndTime()
    fps = RLPy.RGlobal.GetFps()
    clip_start = RLPy.IndexedFrameTime(0, fps)
    report = {
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "diagnostic_mode": "rlmotion_fbx_export",
        "export_path": fbx_path,
        "motion_path": motion_path,
        "timeline_cleanup": cleared_timeline,
        "schema_version": 1,
        "source_project": (
            {
                "bytes": os.path.getsize(source_project_path),
                "load": source_project_load,
                "path": source_project_path,
                "sha256": source_project_sha256,
            }
            if source_project_path
            else None
        ),
        "started_at": started_at,
    }
    try:
        RLPy.RScene.SelectObject(avatar)
        checked(
            "Load rlMotion for FBX export",
            RLPy.RFileIO.LoadFile(motion_path, False),
        )
        QtWidgets.QApplication.processEvents()
        clip_count = int(skeleton.GetClipCount())
        if clip_count <= initial_clip_count:
            raise ReconstructionError(
                "rlMotion FBX export did not add a skeleton clip"
            )
        clip = skeleton.GetClip(clip_count - 1)
        clip_length = clip.GetLength()
        clip_length_frame = int(fps.GetFrameIndex(clip_length))
        if clip_length_frame <= 0:
            clip_length = clip.GetClipLength()
            clip_length_frame = int(fps.GetFrameIndex(clip_length))
        if clip_length_frame <= 0:
            raise ReconstructionError(
                "rlMotion FBX export clip has no positive length"
            )

        checked(
            "Set rlMotion FBX export start time",
            RLPy.RGlobal.SetStartTime(clip_start),
        )
        checked(
            "Set rlMotion FBX export end time",
            RLPy.RGlobal.SetEndTime(clip_length),
        )
        checked(
            "Initialize rlMotion FBX export time",
            RLPy.RGlobal.SetTime(clip_start, True),
        )
        license_status = checked(
            "Check rlMotion FBX export license",
            RLPy.RFileIO.CheckExportFbxHasLicense(avatar),
        )
        raise_if_fatal_cc_dialog(output_dir)

        motion_only = bool(payload.get("motion_only", True))
        export_option = RLPy.EExportFbxOptions__None
        export_option |= RLPy.EExportFbxOptions_ExportRootMotion
        if motion_only:
            export_option |= RLPy.EExportFbxOptions_RemoveAllMesh
        else:
            export_option |= RLPy.EExportFbxOptions_AutoSkinRigidMesh
        export_option2 = RLPy.EExportFbxOptions2__None
        export_option2 |= RLPy.EExportFbxOptions2_UnrealEngine4BoneAxis
        export_option2 |= RLPy.EExportFbxOptions2_UnrealPreset
        export_option2 |= RLPy.EExportFbxOptions2_UnrealIkBone
        export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateBoneName
        export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMaterialName
        export_option2 |= RLPy.EExportFbxOptions2_RenameTransparencyWithPostFix
        export_option2 |= RLPy.EExportFbxOptions2_RenameBoneRootToGameType
        export_option2 |= RLPy.EExportFbxOptions2_RenameBoneToLowerCase
        export_option2 |= RLPy.EExportFbxOptions2_RenameBoneOnStd
        export_option2 |= RLPy.EExportFbxOptions2_ResetBoneScale
        export_option2 |= RLPy.EExportFbxOptions2_ResetSelfillumination
        export_option2 |= RLPy.EExportFbxOptions2_ExtraWordForUnityAndUnreal
        ascii_format = bool(payload.get("ascii_format", False))
        if ascii_format:
            export_option2 |= RLPy.EExportFbxOptions2_AsciiFormat

        setting = RLPy.RExportFbxSetting()
        checked(
            "Enable rlMotion FBX motion export",
            setting.EnableExportMotion(True),
        )
        checked(
            "Set rlMotion FBX export FPS",
            setting.SetExportMotionFps(fps),
        )
        checked(
            "Set rlMotion FBX export range",
            setting.SetExportMotionRange(
                RLPy.RRangePair(0, clip_length_frame)
            ),
        )
        checked(
            "Set rlMotion FBX primary options",
            setting.SetOption(export_option),
        )
        checked(
            "Set rlMotion FBX Unreal options",
            setting.SetOption2(export_option2),
        )
        checked(
            "Disable rlMotion FBX JSON export",
            setting.SetOption3(RLPy.EExportFbxOptions3__None),
        )
        checked(
            "Set rlMotion FBX texture size",
            setting.SetTextureSize(RLPy.EExportTextureSize_Original),
        )
        checked(
            "Set rlMotion FBX texture format",
            setting.SetTextureFormat(RLPy.EExportTextureFormat_Default),
        )
        checked(
            "Set rlMotion FBX UE5 bone structure",
            setting.SetUnrealBoneStructure(
                RLPy.EUnrealBoneStructure_UE5_BoneStructure
            ),
        )
        checked(
            "Disable basic bind pose in rlMotion FBX export",
            setting.EnableBasicBindPose(False),
        )
        export_status = checked(
            "Export rlMotion FBX",
            RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, setting),
        )
        raise_if_fatal_cc_dialog(output_dir)
        file_state = wait_for_rendered_preview(
            fbx_path,
            timeout_seconds=float(payload.get("export_timeout_seconds", 180.0)),
            stable_seconds=1.0,
        )
        report.update(
            {
                "clip": {
                    "body_clip_count_after_load": clip_count,
                    "face_clip_count_after_load": (
                        int(face_component.GetClipCount())
                        if face_component is not None
                        else 0
                    ),
                    "length_frame": clip_length_frame,
                },
                "export": {
                    "api": "RFileIO.ExportFbxFile(object, path, setting)",
                    "ascii_format": ascii_format,
                    "bytes": file_state["bytes"],
                    "export_root_motion": True,
                    "license_status": license_status,
                    "motion_only": motion_only,
                    "option": int(export_option),
                    "option2": int(export_option2),
                    "option3": int(RLPy.EExportFbxOptions3__None),
                    "sha256": sha256_file(fbx_path),
                    "status": export_status,
                    "unreal_bone_structure": "UE5",
                },
                "finished_at": now(),
                "success": True,
            }
        )
    finally:
        if RLPy.RGlobal.IsPlaying():
            RLPy.RGlobal.Stop()
        for clip_index in range(
            int(skeleton.GetClipCount()) - 1,
            initial_clip_count - 1,
            -1,
        ):
            skeleton.DeleteClip(skeleton.GetClip(clip_index))
            QtWidgets.QApplication.processEvents()
        if face_component is not None:
            for clip_index in range(
                int(face_component.GetClipCount()) - 1,
                initial_face_clip_count - 1,
                -1,
            ):
                face_component.DeleteClip(face_component.GetClip(clip_index))
                QtWidgets.QApplication.processEvents()
        RLPy.RGlobal.SetStartTime(initial_start_time)
        RLPy.RGlobal.SetEndTime(initial_end_time)
        RLPy.RGlobal.SetTime(initial_time, True)
        QtWidgets.QApplication.processEvents()

    if source_project_path and sha256_file(source_project_path) != source_project_sha256:
        raise ReconstructionError("rlMotion FBX carrier project changed during export")

    report_path = os.path.join(output_dir, "rlmotion_fbx_export.json")
    write_json(report, report_path)
    summary_path = os.path.join(
        output_dir, "rlmotion_fbx_export_summary.json"
    )
    summary = {
        "diagnostic_mode": "rlmotion_fbx_export",
        "export_path": fbx_path,
        "failure_count": 0,
        "finished_at": report["finished_at"],
        "motion_length_frame": report["clip"]["length_frame"],
        "requested_count": 1,
        "rlmotion_fbx_export_path": report_path,
        "schema_version": 1,
        "started_at": started_at,
        "success": True,
        "success_count": 1,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def export_animation_p0_ue_runtime_pilot(library, output_dir, log):
    """Export two clothed references and their P0 motion-only FBXs."""
    payload = library.get("animation_p0_ue_export") or {}
    if not isinstance(payload, dict):
        raise ReconstructionError(
            "animation_p0_ue_export must be an object"
        )
    work_order_path = canonical_existing_file(
        payload.get("work_order_path"),
        "P0 UE runtime export work order",
    )
    expected_work_order_sha256 = payload.get("work_order_sha256")
    if (
        not isinstance(expected_work_order_sha256, str)
        or len(expected_work_order_sha256) != 64
    ):
        raise ReconstructionError(
            "animation_p0_ue_export.work_order_sha256 is required"
        )
    actual_work_order_sha256 = sha256_file(work_order_path)
    if actual_work_order_sha256 != expected_work_order_sha256:
        raise ReconstructionError(
            "P0 UE runtime export work order hash changed"
        )
    work_order = read_json(work_order_path)
    if work_order.get("status") != "ready_for_cc_export":
        raise ReconstructionError(
            "P0 UE runtime work order is not ready for CC export"
        )
    target_export_root = os.path.realpath(
        os.path.abspath((work_order.get("export") or {}).get("root", ""))
    )
    staging_output_root = os.path.realpath(
        os.path.abspath(payload.get("staging_output_root", ""))
    )
    if staging_output_root != output_dir:
        raise ReconstructionError(
            "P0 UE runtime output must match the configured staging root"
        )

    actors = work_order.get("actors") or []
    motions = work_order.get("motions") or []
    actor_project_overrides = payload.get("actor_project_overrides") or {}
    if not isinstance(actor_project_overrides, dict):
        raise ReconstructionError(
            "animation_p0_ue_export.actor_project_overrides must be an object"
        )
    expected_source_timeline = payload.get("expected_source_timeline") or {}
    if not isinstance(expected_source_timeline, dict):
        raise ReconstructionError(
            "animation_p0_ue_export.expected_source_timeline must be an object"
        )
    export_names = payload.get("export_names") or {}
    actor_export_names = export_names.get("actors") or {}
    motion_export_names = export_names.get("motions") or {}
    if not isinstance(actor_export_names, dict) or not isinstance(
        motion_export_names, dict
    ):
        raise ReconstructionError(
            "animation_p0_ue_export.export_names is invalid"
        )
    expected_motion_count = int(
        (work_order.get("scope") or {}).get("motion_count", -1)
    )
    if expected_motion_count < 1 or expected_motion_count > 64:
        raise ReconstructionError(
            "P0 UE runtime work order has an invalid motion count"
        )
    if len(actors) != 2 or len(motions) != expected_motion_count:
        raise ReconstructionError(
            "P0 UE runtime export requires two actors and the declared "
            "motion count"
        )
    actor_ids = {
        actor.get("actor_binding_id")
        for actor in actors
        if isinstance(actor, dict)
    }
    if len(actor_ids) != 2 or None in actor_ids:
        raise ReconstructionError("P0 UE runtime actor bindings are invalid")
    if any(
        motion.get("actor_binding_id") not in actor_ids
        for motion in motions
        if isinstance(motion, dict)
    ):
        raise ReconstructionError(
            "P0 UE runtime motion references an unknown actor"
        )

    timeout_seconds = float(payload.get("export_timeout_seconds", 900.0))
    if timeout_seconds < 30.0 or timeout_seconds > 3600.0:
        raise ReconstructionError(
            "P0 UE runtime export timeout must be from 30 to 3600 seconds"
        )
    started_at = now()
    progress_path = os.path.join(output_dir, "progress.json")
    report_path = os.path.join(
        output_dir, "p0_ue_runtime_cc_export.json"
    )
    summary_path = os.path.join(
        output_dir, "p0_ue_runtime_cc_export_summary.json"
    )

    def mark_phase(phase, detail=None):
        write_json(
            {
                "detail": detail,
                "diagnostic_mode": "animation_p0_ue_runtime_export",
                "phase": phase,
                "updated_at": now(),
                "work_order_id": work_order.get("work_order_id"),
            },
            progress_path,
        )

    def directory_state(path):
        if not os.path.isdir(path):
            raise ReconstructionError(
                "Expected export directory is missing: {}".format(path)
            )
        files = []
        total_bytes = 0
        for root, _directories, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                size = os.path.getsize(file_path)
                files.append(os.path.relpath(file_path, path))
                total_bytes += size
        if not files:
            raise ReconstructionError(
                "Expected export directory is empty: {}".format(path)
            )
        return {
            "file_count": len(files),
            "path": path,
            "sample_files": sorted(files)[:20],
            "total_bytes": total_bytes,
        }

    def unreal_option2(ascii_format=False):
        option2 = RLPy.EExportFbxOptions2__None
        option2 |= RLPy.EExportFbxOptions2_UnrealEngine4BoneAxis
        option2 |= RLPy.EExportFbxOptions2_UnrealPreset
        option2 |= RLPy.EExportFbxOptions2_UnrealIkBone
        option2 |= RLPy.EExportFbxOptions2_RenameDuplicateBoneName
        option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMaterialName
        option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMorphName
        option2 |= RLPy.EExportFbxOptions2_RenameTransparencyWithPostFix
        option2 |= RLPy.EExportFbxOptions2_RenameBoneRootToGameType
        option2 |= RLPy.EExportFbxOptions2_RenameBoneToLowerCase
        option2 |= RLPy.EExportFbxOptions2_RenameBoneOnStd
        option2 |= RLPy.EExportFbxOptions2_RenameMorphInvalidCharacter
        option2 |= RLPy.EExportFbxOptions2_ResetBoneScale
        option2 |= RLPy.EExportFbxOptions2_ResetSelfillumination
        option2 |= RLPy.EExportFbxOptions2_ExtraWordForUnityAndUnreal
        if ascii_format:
            option2 |= RLPy.EExportFbxOptions2_AsciiFormat
        return option2

    def export_reference_character(
        avatar,
        actor,
        actor_root,
        reference_basename,
    ):
        reference_root = os.path.join(actor_root, "reference")
        os.makedirs(reference_root, exist_ok=False)
        basename = reference_basename
        fbx_path = os.path.join(reference_root, basename + ".fbx")
        json_path = os.path.join(reference_root, basename + ".json")

        export_option = RLPy.EExportFbxOptions__None
        export_option |= RLPy.EExportFbxOptions_AutoSkinRigidMesh
        export_option |= RLPy.EExportFbxOptions_TPoseForCreateMorphTargetMesh
        export_option2 = unreal_option2(False)
        export_option3 = RLPy.EExportFbxOptions3__None
        export_option3 |= RLPy.EExportFbxOptions3_ExportJson
        setting = RLPy.RExportFbxSetting()
        checked(
            "Disable P0 reference motion export",
            setting.EnableExportMotion(False),
        )
        checked(
            "Set P0 reference primary options",
            setting.SetOption(export_option),
        )
        checked(
            "Set P0 reference Unreal options",
            setting.SetOption2(export_option2),
        )
        checked(
            "Enable P0 reference Auto Setup JSON",
            setting.SetOption3(export_option3),
        )
        checked(
            "Set P0 reference texture size",
            setting.SetTextureSize(RLPy.EExportTextureSize_Original),
        )
        checked(
            "Set P0 reference texture format",
            setting.SetTextureFormat(RLPy.EExportTextureFormat_Default),
        )
        checked(
            "Set P0 reference UE5 bone structure",
            setting.SetUnrealBoneStructure(
                RLPy.EUnrealBoneStructure_UE5_BoneStructure
            ),
        )
        checked(
            "Disable P0 reference basic bind pose",
            setting.EnableBasicBindPose(False),
        )
        RLPy.RScene.SelectObject(avatar)
        license_status = checked(
            "Check P0 reference export license",
            RLPy.RFileIO.CheckExportFbxHasLicense(avatar),
        )
        raise_if_fatal_cc_dialog(output_dir)
        status = checked(
            "Export P0 clothed reference character",
            RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, setting),
        )
        raise_if_fatal_cc_dialog(output_dir)
        fbx_state = wait_for_rendered_preview(
            fbx_path,
            timeout_seconds=timeout_seconds,
            stable_seconds=1.0,
        )
        json_state = wait_for_rendered_preview(
            json_path,
            timeout_seconds=timeout_seconds,
            stable_seconds=0.5,
        )
        return {
            "fbx": {
                "bytes": fbx_state["bytes"],
                "path": fbx_path,
                "sha256": sha256_file(fbx_path),
            },
            "json": {
                "bytes": json_state["bytes"],
                "path": json_path,
                "sha256": sha256_file(json_path),
            },
            "fbm": directory_state(
                os.path.join(reference_root, basename + ".fbm")
            ),
            "textures": directory_state(
                os.path.join(reference_root, "textures")
            ),
            "license_status": license_status,
            "options": {
                "auto_skin_rigid_mesh": True,
                "export_json": True,
                "motion": False,
                "option": int(export_option),
                "option2": int(export_option2),
                "option3": int(export_option3),
                "unreal_bone_structure": "UE5",
            },
            "status": status,
        }

    def delete_added_clips(
        skeleton,
        face_component,
        initial_body_count,
        initial_face_count,
    ):
        for clip_index in range(
            int(skeleton.GetClipCount()) - 1,
            initial_body_count - 1,
            -1,
        ):
            skeleton.DeleteClip(skeleton.GetClip(clip_index))
            QtWidgets.QApplication.processEvents()
        if face_component is not None:
            for clip_index in range(
                int(face_component.GetClipCount()) - 1,
                initial_face_count - 1,
                -1,
            ):
                face_component.DeleteClip(
                    face_component.GetClip(clip_index)
                )
                QtWidgets.QApplication.processEvents()

    def export_motion(avatar, motion, actor_root, motion_basename):
        source = motion.get("source_motion") or {}
        motion_path = canonical_existing_file(
            source.get("path"),
            "P0 motion {}".format(motion.get("case_id")),
        )
        extension = os.path.splitext(motion_path)[1].lower()
        if extension not in (".rlmotion", ".imotion"):
            raise ReconstructionError(
                "P0 motion must use .rlmotion or .imotion: {}".format(
                    motion_path
                )
            )
        if os.path.getsize(motion_path) != int(source.get("bytes", -1)):
            raise ReconstructionError(
                "P0 motion size changed: {}".format(motion.get("case_id"))
            )
        if sha256_file(motion_path) != source.get("sha256"):
            raise ReconstructionError(
                "P0 motion hash changed: {}".format(motion.get("case_id"))
            )

        motions_root = os.path.join(actor_root, "motions")
        os.makedirs(motions_root, exist_ok=True)
        fbx_path = os.path.join(
            motions_root,
            "{}_UE5_ASCII.fbx".format(motion_basename),
        )
        skeleton = avatar.GetSkeletonComponent()
        face_component = avatar.GetFaceComponent()
        if skeleton is None:
            raise ReconstructionError("P0 export avatar has no skeleton")
        initial_body_count = int(skeleton.GetClipCount())
        initial_face_count = (
            int(face_component.GetClipCount())
            if face_component is not None
            else 0
        )
        initial_time = RLPy.RGlobal.GetTime()
        initial_start_time = RLPy.RGlobal.GetStartTime()
        initial_end_time = RLPy.RGlobal.GetEndTime()
        fps = RLPy.RGlobal.GetFps()
        clip_start = RLPy.IndexedFrameTime(0, fps)
        try:
            RLPy.RScene.SelectObject(avatar)
            checked(
                "Load P0 motion {}".format(motion.get("case_id")),
                RLPy.RFileIO.LoadFile(motion_path, False),
            )
            QtWidgets.QApplication.processEvents()
            body_count = int(skeleton.GetClipCount())
            if body_count <= initial_body_count:
                raise ReconstructionError(
                    "P0 motion did not add a skeleton clip: {}".format(
                        motion.get("case_id")
                    )
                )
            clip = skeleton.GetClip(body_count - 1)
            clip_length = clip.GetLength()
            clip_length_frame = int(fps.GetFrameIndex(clip_length))
            if clip_length_frame <= 0:
                clip_length = clip.GetClipLength()
                clip_length_frame = int(fps.GetFrameIndex(clip_length))
            if clip_length_frame <= 0:
                raise ReconstructionError(
                    "P0 motion has no positive length: {}".format(
                        motion.get("case_id")
                    )
                )
            checked(
                "Set P0 motion start time",
                RLPy.RGlobal.SetStartTime(clip_start),
            )
            checked(
                "Set P0 motion end time",
                RLPy.RGlobal.SetEndTime(clip_length),
            )
            checked(
                "Initialize P0 motion time",
                RLPy.RGlobal.SetTime(clip_start, True),
            )

            root_policy = (motion.get("root_motion") or {}).get("policy")
            if root_policy not in (
                "preserve_source_root_motion",
                "in_place",
            ):
                raise ReconstructionError(
                    "Unsupported P0 root-motion policy: {}".format(
                        root_policy
                    )
                )
            export_option = RLPy.EExportFbxOptions__None
            export_option |= RLPy.EExportFbxOptions_RemoveAllMesh
            export_option |= RLPy.EExportFbxOptions_ExportRootMotion
            if root_policy == "in_place":
                export_option |= RLPy.EExportFbxOptions_ZeroMotionRoot
            export_option2 = unreal_option2(True)
            setting = RLPy.RExportFbxSetting()
            checked(
                "Enable P0 motion export",
                setting.EnableExportMotion(True),
            )
            checked(
                "Set P0 motion FPS",
                setting.SetExportMotionFps(fps),
            )
            checked(
                "Set P0 motion range",
                setting.SetExportMotionRange(
                    RLPy.RRangePair(0, clip_length_frame)
                ),
            )
            checked(
                "Set P0 motion primary options",
                setting.SetOption(export_option),
            )
            checked(
                "Set P0 motion Unreal options",
                setting.SetOption2(export_option2),
            )
            checked(
                "Disable P0 motion JSON export",
                setting.SetOption3(RLPy.EExportFbxOptions3__None),
            )
            checked(
                "Set P0 motion UE5 bone structure",
                setting.SetUnrealBoneStructure(
                    RLPy.EUnrealBoneStructure_UE5_BoneStructure
                ),
            )
            checked(
                "Disable P0 motion basic bind pose",
                setting.EnableBasicBindPose(False),
            )
            license_status = checked(
                "Check P0 motion export license",
                RLPy.RFileIO.CheckExportFbxHasLicense(avatar),
            )
            raise_if_fatal_cc_dialog(output_dir)
            status = checked(
                "Export P0 motion {}".format(motion.get("case_id")),
                RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, setting),
            )
            raise_if_fatal_cc_dialog(output_dir)
            file_state = wait_for_rendered_preview(
                fbx_path,
                timeout_seconds=timeout_seconds,
                stable_seconds=1.0,
            )
            return {
                "actor_binding_id": motion.get("actor_binding_id"),
                "case_id": motion.get("case_id"),
                "clip": {
                    "body_clip_count_after_load": body_count,
                    "face_clip_count_after_load": (
                        int(face_component.GetClipCount())
                        if face_component is not None
                        else 0
                    ),
                    "length_frame": clip_length_frame,
                },
                "fbx": {
                    "bytes": file_state["bytes"],
                    "path": fbx_path,
                    "sha256": sha256_file(fbx_path),
                },
                "license_status": license_status,
                "options": {
                    "ascii_format": True,
                    "motion_only": True,
                    "option": int(export_option),
                    "option2": int(export_option2),
                    "root_motion_policy": root_policy,
                    "unreal_bone_structure": "UE5",
                },
                "source_motion": source,
                "status": status,
            }
        finally:
            if RLPy.RGlobal.IsPlaying():
                RLPy.RGlobal.Stop()
            delete_added_clips(
                skeleton,
                face_component,
                initial_body_count,
                initial_face_count,
            )
            RLPy.RGlobal.SetStartTime(initial_start_time)
            RLPy.RGlobal.SetEndTime(initial_end_time)
            RLPy.RGlobal.SetTime(initial_time, True)
            QtWidgets.QApplication.processEvents()

    mark_phase("initializing")
    report = {
        "actors": [],
        "diagnostic_mode": "animation_p0_ue_runtime_export",
        "motions": [],
        "schema_version": 1,
        "started_at": started_at,
        "staging_output_root": output_dir,
        "target_export_root": target_export_root,
        "work_order": {
            "id": work_order.get("work_order_id"),
            "path": work_order_path,
            "sha256": actual_work_order_sha256,
        },
    }
    for actor_index, actor in enumerate(actors, 1):
        actor_id = actor.get("actor_binding_id")
        source_project = actor.get("source_project") or {}
        project_path = canonical_existing_file(
            source_project.get("path"),
            "P0 actor source project {}".format(actor_id),
        )
        if os.path.getsize(project_path) != int(
            source_project.get("bytes", -1)
        ):
            raise ReconstructionError(
                "P0 actor source project size changed: {}".format(actor_id)
            )
        if sha256_file(project_path) != source_project.get("sha256"):
            raise ReconstructionError(
                "P0 actor source project hash changed: {}".format(actor_id)
            )
        bridge_project = actor_project_overrides.get(actor_id) or {}
        actor_export_name = actor_export_names.get(actor_id) or {}
        actor_directory = actor_export_name.get("directory")
        reference_basename = actor_export_name.get("reference_basename")
        for value, label in (
            (actor_directory, "actor directory"),
            (reference_basename, "reference basename"),
        ):
            if (
                not isinstance(value, str)
                or not value
                or os.path.basename(value) != value
            ):
                raise ReconstructionError(
                    "Invalid P0 export {} for {}".format(label, actor_id)
                )
        bridge_project_path = canonical_existing_file(
            bridge_project.get("path"),
            "P0 actor bridge project {}".format(actor_id),
        )
        if os.path.getsize(bridge_project_path) != int(
            bridge_project.get("bytes", -1)
        ):
            raise ReconstructionError(
                "P0 actor bridge project size changed: {}".format(actor_id)
            )
        bridge_project_sha256 = sha256_file(bridge_project_path)
        if bridge_project_sha256 != bridge_project.get("sha256"):
            raise ReconstructionError(
                "P0 actor bridge project hash changed: {}".format(actor_id)
            )
        if bridge_project_sha256 != source_project.get("sha256"):
            raise ReconstructionError(
                "P0 actor bridge project does not match source: {}".format(
                    actor_id
                )
            )
        mark_phase(
            "load_actor",
            {"actor_binding_id": actor_id, "index": actor_index},
        )
        load_status, load_dialogs = load_file_with_optional_undo_warning(
            bridge_project_path,
            "Load P0 actor source project {}".format(actor_id),
        )
        QtWidgets.QApplication.processEvents()
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "P0 export expected one avatar for {}, found {}".format(
                    actor_id, len(avatars)
                )
            )
        skeleton = avatar.GetSkeletonComponent()
        face_component = avatar.GetFaceComponent()
        if skeleton is None:
            raise ReconstructionError(
                "P0 actor has no skeleton: {}".format(actor_id)
            )
        body_clip_count = int(skeleton.GetClipCount())
        face_clip_count = (
            int(face_component.GetClipCount())
            if face_component is not None
            else 0
        )
        expected_timeline = expected_source_timeline.get(actor_id) or {}
        expected_body_count = int(expected_timeline.get("body_clip_count", -1))
        expected_face_count = int(expected_timeline.get("face_clip_count", -1))
        if (
            body_clip_count != expected_body_count
            or face_clip_count != expected_face_count
        ):
            raise ReconstructionError(
                "P0 actor source timeline differs from the frozen expectation: "
                "{} body, {} face".format(
                    body_clip_count,
                    face_clip_count,
                )
            )
        timeline_cleanup = clear_avatar_motion(avatar)
        actor_root = os.path.join(output_dir, actor_directory)
        os.makedirs(actor_root, exist_ok=False)
        mark_phase("export_reference", {"actor_binding_id": actor_id})
        reference = export_reference_character(
            avatar,
            actor,
            actor_root,
            reference_basename,
        )
        actor_report = {
            "actor_binding_id": actor_id,
            "appearance_recipe_id": actor.get("appearance_recipe_id"),
            "bodyfit_id": actor.get("bodyfit_id"),
            "character_id": actor.get("character_id"),
            "bridge_project": {
                "bytes": os.path.getsize(bridge_project_path),
                "path": bridge_project_path,
                "sha256": bridge_project_sha256,
            },
            "load": {"dialogs": load_dialogs, "status": load_status},
            "reference": reference,
            "sex": actor.get("sex"),
            "source_project": source_project,
            "timeline_cleanup": timeline_cleanup,
        }
        report["actors"].append(actor_report)
        for motion in motions:
            if motion.get("actor_binding_id") != actor_id:
                continue
            mark_phase(
                "export_motion",
                {
                    "actor_binding_id": actor_id,
                    "case_id": motion.get("case_id"),
                },
            )
            motion_basename = motion_export_names.get(
                motion.get("case_id")
            )
            if (
                not isinstance(motion_basename, str)
                or not motion_basename
                or os.path.basename(motion_basename) != motion_basename
            ):
                raise ReconstructionError(
                    "Invalid P0 motion export basename: {}".format(
                        motion.get("case_id")
                    )
                )
            report["motions"].append(
                export_motion(
                    avatar,
                    motion,
                    actor_root,
                    motion_basename,
                )
            )
        if sha256_file(project_path) != source_project.get("sha256"):
            raise ReconstructionError(
                "P0 actor source project changed during export: {}".format(
                    actor_id
                )
            )
        if sha256_file(bridge_project_path) != bridge_project_sha256:
            raise ReconstructionError(
                "P0 actor bridge project changed during export: {}".format(
                    actor_id
                )
            )
        write_json(report, report_path)
        log("Completed P0 CC export actor {}".format(actor_id))

    report["finished_at"] = now()
    report["success"] = True
    report["status"] = "cc_export_complete_patch_pending"
    write_json(report, report_path)
    summary = {
        "actor_count": len(report["actors"]),
        "diagnostic_mode": "animation_p0_ue_runtime_export",
        "failure_count": 0,
        "finished_at": report["finished_at"],
        "motion_count": len(report["motions"]),
        "p0_ue_runtime_cc_export_path": report_path,
        "requested_count": len(actors) + len(motions),
        "schema_version": 1,
        "started_at": started_at,
        "status": report["status"],
        "success": True,
        "success_count": len(report["actors"]) + len(report["motions"]),
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    mark_phase("complete")
    return summary


def export_elder_morph_pilot(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    payload = library.get("elder_morph_export") or {}
    if not isinstance(payload, dict):
        raise ReconstructionError("elder_morph_export must be an object")
    source_project = canonical_existing_file(
        payload.get("source_project"),
        "Elder Morph export source project",
    )
    age_morph = payload.get("age_morph") or {}
    morph_id = age_morph.get("id")
    morph_display = age_morph.get("display")
    if not isinstance(morph_id, str) or not morph_id:
        raise ReconstructionError("elder_morph_export.age_morph.id is required")
    if not isinstance(morph_display, str) or not morph_display:
        raise ReconstructionError(
            "elder_morph_export.age_morph.display is required"
        )

    export_json = bool(payload.get("export_json", True))
    ascii_format = bool(payload.get("ascii_format", False))
    create_morph_target_mesh = bool(
        payload.get("create_morph_target_mesh", True)
    )
    timeout_seconds = float(payload.get("export_timeout_seconds", 600.0))
    filenames = payload.get("filenames") or {
        "young": "M02_Young_Base_UE5.fbx",
        "elder": "M02_Elder_Target_UE5.fbx",
    }
    for label in ("young", "elder"):
        filename = filenames.get(label)
        if (
            not isinstance(filename, str)
            or not filename
            or os.path.basename(filename) != filename
            or not filename.lower().endswith(".fbx")
        ):
            raise ReconstructionError(
                "elder_morph_export.filenames.{} must be a simple .fbx filename".format(
                    label
                )
            )

    started_at = now()
    progress_path = os.path.join(output_dir, "progress.json")
    report_path = os.path.join(output_dir, "elder_morph_export_pilot.json")
    summary_path = os.path.join(
        output_dir, "elder_morph_export_pilot_summary.json"
    )

    def mark_phase(phase, detail=None):
        write_json(
            {
                "detail": detail,
                "diagnostic_mode": "elder_morph_export_pilot",
                "phase": phase,
                "source_project": source_project,
                "updated_at": now(),
            },
            progress_path,
        )

    mark_phase("load_source_project")
    load_status, load_dialogs = load_file_with_optional_undo_warning(
        source_project,
        "Load Elder Morph export source project",
    )
    QtWidgets.QApplication.processEvents()
    avatar, avatars = resolve_avatar()
    if len(avatars) != 1:
        raise ReconstructionError(
            "Elder Morph export expected one avatar, found {}".format(
                len(avatars)
            )
        )
    component, catalog, _categories = morph_catalog(avatar)
    if morph_id not in catalog:
        raise ReconstructionError(
            "Elder Morph is unavailable: {}".format(morph_id)
        )
    if catalog[morph_id]["display"] != morph_display:
        raise ReconstructionError(
            "Elder Morph display mismatch: expected {}, found {}".format(
                morph_display,
                catalog[morph_id]["display"],
            )
        )

    initial_weight = float(component.GetShapingMorphWeight(morph_id))
    report = {
        "age_morph": {
            "display": morph_display,
            "id": morph_id,
            "initial_weight": initial_weight,
        },
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
        },
        "diagnostic_mode": "elder_morph_export_pilot",
        "exports": [],
        "load": {
            "dialogs": load_dialogs,
            "status": load_status,
        },
        "schema_version": 1,
        "source_project": source_project,
        "started_at": started_at,
    }

    try:
        for label, target_weight in (("young", 0.0), ("elder", 1.0)):
            mark_phase("apply_{}".format(label))
            application = set_direct_morph_weight(
                avatar,
                morph_id,
                target_weight,
                "Full Face Elder {} export".format(label),
            )
            fbx_path = os.path.join(output_dir, filenames[label])
            if os.path.isfile(fbx_path):
                os.remove(fbx_path)
            json_path = os.path.splitext(fbx_path)[0] + ".json"
            if os.path.isfile(json_path):
                os.remove(json_path)

            export_option = RLPy.EExportFbxOptions__None
            export_option |= RLPy.EExportFbxOptions_AutoSkinRigidMesh
            if create_morph_target_mesh:
                export_option |= (
                    RLPy.EExportFbxOptions_TPoseForCreateMorphTargetMesh
                )

            export_option2 = RLPy.EExportFbxOptions2__None
            export_option2 |= RLPy.EExportFbxOptions2_UnrealEngine4BoneAxis
            export_option2 |= RLPy.EExportFbxOptions2_UnrealPreset
            export_option2 |= RLPy.EExportFbxOptions2_UnrealIkBone
            export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateBoneName
            export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMaterialName
            export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMorphName
            export_option2 |= RLPy.EExportFbxOptions2_RenameTransparencyWithPostFix
            export_option2 |= RLPy.EExportFbxOptions2_RenameBoneRootToGameType
            export_option2 |= RLPy.EExportFbxOptions2_RenameBoneToLowerCase
            export_option2 |= RLPy.EExportFbxOptions2_RenameBoneOnStd
            export_option2 |= RLPy.EExportFbxOptions2_RenameMorphInvalidCharacter
            export_option2 |= RLPy.EExportFbxOptions2_ResetBoneScale
            export_option2 |= RLPy.EExportFbxOptions2_ResetSelfillumination
            export_option2 |= RLPy.EExportFbxOptions2_ExtraWordForUnityAndUnreal
            if ascii_format:
                export_option2 |= RLPy.EExportFbxOptions2_AsciiFormat

            export_option3 = RLPy.EExportFbxOptions3__None
            if export_json:
                export_option3 |= RLPy.EExportFbxOptions3_ExportJson

            setting = RLPy.RExportFbxSetting()
            checked(
                "Disable {} Elder Morph motion export".format(label),
                setting.EnableExportMotion(False),
            )
            checked(
                "Set {} Elder Morph primary options".format(label),
                setting.SetOption(export_option),
            )
            checked(
                "Set {} Elder Morph Unreal options".format(label),
                setting.SetOption2(export_option2),
            )
            checked(
                "Set {} Elder Morph JSON options".format(label),
                setting.SetOption3(export_option3),
            )
            checked(
                "Set {} Elder Morph texture size".format(label),
                setting.SetTextureSize(RLPy.EExportTextureSize_Original),
            )
            checked(
                "Set {} Elder Morph texture format".format(label),
                setting.SetTextureFormat(RLPy.EExportTextureFormat_Default),
            )
            checked(
                "Set {} Elder Morph UE5 bone structure".format(label),
                setting.SetUnrealBoneStructure(
                    RLPy.EUnrealBoneStructure_UE5_BoneStructure
                ),
            )
            checked(
                "Disable {} Elder Morph basic bind pose".format(label),
                setting.EnableBasicBindPose(False),
            )

            RLPy.RScene.SelectObject(avatar)
            license_status = checked(
                "Check {} Elder Morph export license".format(label),
                RLPy.RFileIO.CheckExportFbxHasLicense(avatar),
            )
            mark_phase("export_{}".format(label), {"path": fbx_path})
            export_status = checked(
                "Export {} Elder Morph FBX".format(label),
                RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, setting),
            )
            file_state = wait_for_rendered_preview(
                fbx_path,
                timeout_seconds=timeout_seconds,
                stable_seconds=1.0,
            )
            json_state = None
            if export_json:
                json_state = wait_for_rendered_preview(
                    json_path,
                    timeout_seconds=timeout_seconds,
                    stable_seconds=0.5,
                )
            report["exports"].append(
                {
                    "application": application,
                    "fbx": {
                        "bytes": file_state["bytes"],
                        "path": fbx_path,
                        "sha256": sha256_file(fbx_path),
                    },
                    "json": (
                        {
                            "bytes": json_state["bytes"],
                            "path": json_path,
                            "sha256": sha256_file(json_path),
                        }
                        if json_state is not None
                        else None
                    ),
                    "label": label,
                    "options": {
                        "ascii_format": ascii_format,
                        "create_morph_target_mesh": create_morph_target_mesh,
                        "export_json": export_json,
                        "option": int(export_option),
                        "option2": int(export_option2),
                        "option3": int(export_option3),
                        "unreal_bone_structure": "UE5",
                    },
                    "status": export_status,
                    "target_weight": target_weight,
                    "license_status": license_status,
                }
            )
    finally:
        mark_phase("restore_age_morph")
        set_direct_morph_weight(
            avatar,
            morph_id,
            initial_weight,
            "Restore Full Face Elder after export pilot",
        )

    report["finished_at"] = now()
    report["success"] = True
    write_json(report, report_path)
    summary = {
        "diagnostic_mode": "elder_morph_export_pilot",
        "elder_morph_export_pilot_path": report_path,
        "export_count": len(report["exports"]),
        "failure_count": 0,
        "finished_at": report["finished_at"],
        "requested_count": 2,
        "schema_version": 1,
        "started_at": started_at,
        "success": True,
        "success_count": len(report["exports"]),
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    mark_phase("complete")
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


def run_first_batch_identity_reference_capture(
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    """Render deterministic neutral identity portraits from frozen projects."""
    capture = library.get("identity_reference_capture") or {}
    if not isinstance(capture, dict):
        raise ReconstructionError(
            "identity_reference_capture must be an object"
        )

    camera_path = canonical_existing_file(
        capture.get("camera_path"),
        "Identity reference camera",
    )
    lightroom_path = canonical_existing_file(
        capture.get("lightroom_path"),
        "Identity reference Lightroom",
    )
    base_position = capture.get("avatar_position") or {}
    if not isinstance(base_position, dict):
        raise ReconstructionError(
            "identity_reference_capture.avatar_position must be an object"
        )
    base_position = dict(
        (axis, float(base_position.get(axis, 0.0)))
        for axis in ("x", "y", "z")
    )
    position_by_sex = capture.get("avatar_position_by_sex") or {}
    if not isinstance(position_by_sex, dict):
        raise ReconstructionError(
            "identity_reference_capture.avatar_position_by_sex must be an object"
        )

    views = capture.get("views")
    if not isinstance(views, list) or not views:
        raise ReconstructionError(
            "identity_reference_capture.views must be a non-empty list"
        )
    normalized_views = []
    seen_view_ids = set()
    for item in views:
        if not isinstance(item, dict):
            raise ReconstructionError(
                "Every identity reference view must be an object"
            )
        view_id = item.get("view_id")
        if not isinstance(view_id, str) or not view_id:
            raise ReconstructionError(
                "Every identity reference view requires view_id"
            )
        if view_id in seen_view_ids:
            raise ReconstructionError(
                "Duplicate identity reference view_id: {}".format(view_id)
            )
        seen_view_ids.add(view_id)
        position_offset = item.get("avatar_position_offset") or {}
        if not isinstance(position_offset, dict):
            raise ReconstructionError(
                "Identity reference view {} avatar_position_offset must be an object".format(
                    view_id
                )
            )
        normalized_views.append(
            {
                "view_id": view_id,
                "yaw_degrees": float(item.get("yaw_degrees")),
                "avatar_position_offset": dict(
                    (
                        axis,
                        float(position_offset.get(axis, 0.0)),
                    )
                    for axis in ("x", "y", "z")
                ),
            }
        )

    by_id = dict((item.get("preset_id"), item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item.get("preset_id") for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "Identity reference preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown identity reference preset IDs: {}".format(missing)
        )

    started_at = now()
    results = []
    for preset_id in selected_ids:
        preset = by_id[preset_id]
        sex = preset.get("sex")
        sex_position = position_by_sex.get(sex) or {}
        if not isinstance(sex_position, dict):
            raise ReconstructionError(
                "Identity position override for {} must be an object".format(
                    sex
                )
            )
        position = dict(
            (
                axis,
                float(sex_position.get(axis, base_position[axis])),
            )
            for axis in ("x", "y", "z")
        )
        source_record = preset.get("source_project") or {}
        source_project = canonical_existing_file(
            source_record.get("path"),
            "Identity reference source project {}".format(preset_id),
        )
        expected_sha256 = source_record.get("sha256")
        actual_sha256 = sha256_file(source_project)
        if expected_sha256 and actual_sha256 != expected_sha256:
            raise ReconstructionError(
                "Identity source project hash changed for {}".format(
                    preset_id
                )
            )

        log("Loading frozen identity project {}".format(preset_id))
        load_status, load_dialogs = load_file_with_optional_undo_warning(
            source_project,
            "Load frozen identity project {}".format(preset_id),
        )
        settle_cc_ui(float(capture.get("project_settle_seconds", 3.0)))
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Identity {} loaded {} avatars; expected one".format(
                    preset_id, len(avatars)
                )
            )
        motion_cleanup = clear_avatar_motion(avatar)
        clothing_names = sorted(
            set(
                scene_object_name(item)
                for item in list(avatar.GetClothes() or [])
            )
        )
        avatar, clothing_cleanup = remove_base_clothing(
            avatar,
            clothing_names,
        )
        avatar, accessory_cleanup = (
            remove_source_accessories_for_outfit_gate(avatar)
        )
        set_avatar_position(
            avatar,
            position_x=position["x"],
            position_y=position["y"],
            position_z=position["z"],
        )
        force_avatar_scene_evaluation(avatar)

        checked(
            "Load identity reference Lightroom",
            RLPy.RFileIO.LoadFile(lightroom_path),
        )
        checked(
            "Load identity reference camera",
            RLPy.RFileIO.LoadFile(camera_path),
        )
        settle_cc_ui(float(capture.get("stage_settle_seconds", 1.5)))
        camera = RLPy.RScene.GetCurrentCamera()
        if camera is None:
            raise ReconstructionError(
                "Identity reference camera did not become active"
            )

        identity_dir = os.path.join(output_dir, preset_id)
        os.makedirs(identity_dir, exist_ok=True)
        view_results = []
        for view in normalized_views:
            view_position = dict(
                (
                    axis,
                    position[axis]
                    + view["avatar_position_offset"][axis],
                )
                for axis in ("x", "y", "z")
            )
            set_avatar_position(
                avatar,
                position_x=view_position["x"],
                position_y=view_position["y"],
                position_z=view_position["z"],
            )
            set_avatar_yaw(avatar, view["yaw_degrees"])
            force_avatar_scene_evaluation(
                avatar,
                settle_seconds=float(
                    capture.get("view_settle_seconds", 1.0)
                ),
            )
            image_path = os.path.join(
                identity_dir,
                "{}__{}.png".format(preset_id, view["view_id"]),
            )
            log(
                "Rendering {} {} at yaw {}".format(
                    preset_id,
                    view["view_id"],
                    view["yaw_degrees"],
                )
            )
            render_preview(image_path, RLPy.RGlobal.GetStartTime())
            view_results.append(
                {
                    "view_id": view["view_id"],
                    "yaw_degrees": view["yaw_degrees"],
                    "avatar_position": view_position,
                    "avatar_position_offset": view[
                        "avatar_position_offset"
                    ],
                    "image": {
                        "path": image_path,
                        "bytes": os.path.getsize(image_path),
                        "sha256": sha256_file(image_path),
                    },
                    "avatar_bounds": capture_bounds(avatar),
                    "camera": camera_state(camera),
                }
            )

        results.append(
            {
                "preset_id": preset_id,
                "sex": sex,
                "source_project": {
                    "path": source_project,
                    "sha256": actual_sha256,
                },
                "load_status": load_status,
                "load_dialogs": load_dialogs,
                "avatar_position": position,
                "motion_cleanup": motion_cleanup,
                "clothing_cleanup": clothing_cleanup,
                "accessory_cleanup": accessory_cleanup,
                "camera_path": camera_path,
                "lightroom_path": lightroom_path,
                "views": view_results,
            }
        )

    summary_path = os.path.join(
        output_dir,
        "identity_reference_capture_summary.json",
    )
    summary = {
        "schema_version": 1,
        "diagnostic_mode": "first_batch_identity_reference_capture",
        "started_at": started_at,
        "finished_at": now(),
        "success": True,
        "requested_count": len(selected_ids),
        "success_count": len(results),
        "failure_count": 0,
        "preview_resolution": [
            VIEWPORT_PREVIEW_WIDTH,
            VIEWPORT_PREVIEW_HEIGHT,
        ],
        "render_contract": capture.get("render_contract") or {},
        "results": results,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def probe_current_facial_profile_api(library, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    avatars = list(RLPy.RScene.GetAvatars() or [])
    if len(avatars) != 1:
        raise ReconstructionError(
            "Facial Profile API probe expected exactly one avatar, found {}"
            .format(len(avatars))
        )
    avatar = avatars[0]
    RLPy.RScene.SelectObject(avatar)
    face_component = avatar.GetFaceComponent()
    profile_component = avatar.GetFacialProfileComponent()
    if face_component is None or profile_component is None:
        raise ReconstructionError(
            "Current avatar does not expose both face and Facial Profile components"
        )

    def public_members(value):
        return sorted(
            name for name in dir(value) if not name.startswith("_")
        )

    def member_docs(value, names):
        docs = {}
        for name in names:
            member = getattr(value, name, None)
            if member is None:
                continue
            docs[name] = {
                "doc": str(getattr(member, "__doc__", None)),
                "repr": repr(member),
            }
        return docs

    expression_names = list(face_component.GetExpressionNames("") or [])
    report = {
        "schema_version": 1,
        "captured_at": now(),
        "diagnostic_mode": "facial_profile_api_probe",
        "avatar": {
            "id": scene_object_id(avatar),
            "name": scene_object_name(avatar),
            "python_type": type(avatar).__name__,
        },
        "facial_profile": {
            "expression_count": len(expression_names),
            "expression_set_uid": str(face_component.GetExpressionSetUid()),
        },
        "components": {
            "face": {
                "python_type": type(face_component).__name__,
                "public_members": public_members(face_component),
            },
            "facial_profile": {
                "python_type": type(profile_component).__name__,
                "public_members": public_members(profile_component),
                "member_docs": member_docs(
                    profile_component,
                    (
                        "GetProfileType",
                        "ImportMorphs",
                        "LoadProfile",
                        "SaveProfile",
                    ),
                ),
            },
        },
        "save_file_type_constants": sorted(
            name for name in dir(RLPy) if name.startswith("ESaveFileType_")
        ),
    }
    if bool(library.get("save_profile_probe", False)):
        profile_path = os.path.join(
            output_dir,
            "current_source_profile.ccFacialProfile",
        )
        try:
            save_status = checked(
                "Save current Facial Profile probe",
                profile_component.SaveProfile(profile_path),
            )
            settle_cc_ui(1.0)
            if not os.path.isfile(profile_path):
                raise ReconstructionError(
                    "Facial Profile SaveProfile returned without creating a file"
                )
            report["profile_save_probe"] = {
                "success": True,
                "status": save_status,
                "file": bodyfit_freeze_file_record(profile_path),
            }
        except Exception as exc:
            report["profile_save_probe"] = {
                "success": False,
                "error": "{}: {}".format(type(exc).__name__, exc),
                "path": profile_path,
            }
    report_path = os.path.join(output_dir, "facial_profile_api_probe.json")
    summary_path = os.path.join(output_dir, "validation_result.json")
    write_json(report, report_path)
    summary = {
        "schema_version": 1,
        "diagnostic_mode": "facial_profile_api_probe",
        "started_at": report["captured_at"],
        "finished_at": now(),
        "success": True,
        "success_count": 1,
        "failure_count": 0,
        "report_path": report_path,
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def run_head_bodyfit_scale_review_matrix(
    library_path,
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    diagnostic_mode = library.get("diagnostic_mode")
    if diagnostic_mode == "neck_morph_review_matrix":
        review_label = "Neck Morph"
        review_token = "neck_morph"
    elif diagnostic_mode == "bodyfit_proportion_smoke_matrix":
        review_label = "BodyFit Proportion Smoke"
        review_token = "bodyfit_proportion_smoke"
    else:
        review_label = "Head Scale"
        review_token = "head_scale"
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "Selected review preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown Head Scale review preset IDs: {}".format(missing)
        )

    started_at = now()
    snapshot_path = os.path.join(
        output_dir,
        "_current_scene_before_{}_matrix.ccProject".format(review_token),
    )
    before_image = os.path.join(
        output_dir,
        "_current_scene_before_{}_matrix.png".format(review_token),
    )
    restored_image = os.path.join(
        output_dir,
        "_current_scene_restored_after_{}_matrix.png".format(review_token),
    )
    restoration_path = os.path.join(
        output_dir,
        "scene_snapshot_restoration.json",
    )
    if os.path.isfile(snapshot_path):
        os.remove(snapshot_path)

    initial_avatars = list(RLPy.RScene.GetAvatars() or [])
    if len(initial_avatars) > 1:
        raise ReconstructionError(
            "{} review matrix expected at most one initial avatar".format(
                review_label
            )
        )
    initial_avatar = initial_avatars[0] if initial_avatars else None
    initial_scene_was_empty = initial_avatar is None
    initial_vector_fingerprint = None
    if initial_avatar is not None:
        RLPy.RScene.SelectObject(initial_avatar)
        initial_vectors = capture_vectors(initial_avatar)
        initial_vector_fingerprint = vectors_excluding_morph_fingerprint(
            initial_vectors,
            "__no_excluded_morph__",
        )
    initial_time = RLPy.RGlobal.GetTime()
    render_preview(before_image, initial_time)
    log("Saving current CC scene before {} review matrix".format(review_label))
    checked(
        "Save current scene before {} review matrix".format(review_label),
        RLPy.RFileIO.SaveProject(snapshot_path),
    )
    snapshot_stat = wait_for_rendered_preview(
        snapshot_path,
        timeout_seconds=600.0,
        stable_seconds=2.0,
    )
    restoration = {
        "schema_version": 1,
        "snapshot_path": snapshot_path,
        "snapshot_size": snapshot_stat,
        "snapshot_retained": True,
        "before_image": before_image,
        "initial_avatar": (
            {
                "id": scene_object_id(initial_avatar),
                "name": scene_object_name(initial_avatar),
            }
            if initial_avatar is not None
            else None
        ),
        "initial_scene_was_empty": initial_scene_was_empty,
        "initial_vector_fingerprint": initial_vector_fingerprint,
        "restore_attempted": False,
        "restored": False,
        "restored_exactly": False,
    }

    appearance_catalog = load_appearance_catalog(library)
    body_catalog_paths = {
        "male": os.path.join(output_dir, "catalogs", "male_body_catalog.json"),
        "female": os.path.join(
            output_dir,
            "catalogs",
            "female_body_catalog.json",
        ),
    }
    face_catalog_paths = {
        "male": os.path.join(output_dir, "catalogs", "male_face_catalog.json"),
        "female": os.path.join(
            output_dir,
            "catalogs",
            "female_face_catalog.json",
        ),
    }
    delay_seconds = max(
        0.0,
        float(library.get("inter_case_delay_seconds", 5.0)),
    )
    results = []
    try:
        for index, preset_id in enumerate(selected_ids):
            log(
                "{} REVIEW {}/{} {}".format(
                    review_label.upper(),
                    index + 1,
                    len(selected_ids),
                    preset_id,
                )
            )
            preset = by_id[preset_id]
            results.append(
                validate_preset(
                    library,
                    preset,
                    os.path.join(output_dir, preset_id),
                    log,
                    body_catalog_paths.get(preset.get("sex")),
                    face_catalog_paths.get(preset.get("sex")),
                    appearance_catalog,
                )
            )
            QtWidgets.QApplication.processEvents()
            if delay_seconds and index + 1 < len(selected_ids):
                settle_cc_ui(delay_seconds)
    finally:
        restoration["restore_attempted"] = True
        log(
            "Restoring current CC scene after {} review matrix".format(
                review_label
            )
        )
        restore_status, restore_dialogs = load_file_with_optional_undo_warning(
            snapshot_path,
            "Restore current scene after {} review matrix".format(
                review_label
            ),
        )
        settle_cc_ui(3.0)
        restored_avatars = list(RLPy.RScene.GetAvatars() or [])
        expected_avatar_count = 0 if initial_scene_was_empty else 1
        if len(restored_avatars) != expected_avatar_count:
            restoration["restore_error"] = (
                "Expected {} avatar(s) after scene snapshot restore".format(
                    expected_avatar_count
                )
            )
            write_json(restoration, restoration_path)
            raise ReconstructionError(restoration["restore_error"])
        restored_avatar = restored_avatars[0] if restored_avatars else None
        restored_vector_fingerprint = None
        if restored_avatar is not None:
            RLPy.RScene.SelectObject(restored_avatar)
            force_avatar_scene_evaluation(restored_avatar)
            restored_vectors = capture_vectors(restored_avatar)
            restored_vector_fingerprint = vectors_excluding_morph_fingerprint(
                restored_vectors,
                "__no_excluded_morph__",
            )
        render_preview(restored_image, RLPy.RGlobal.GetTime())
        restoration.update(
            {
                "restore_dialogs": restore_dialogs,
                "restore_status": restore_status,
                "restored": True,
                "restored_avatar": (
                    {
                        "id": scene_object_id(restored_avatar),
                        "name": scene_object_name(restored_avatar),
                    }
                    if restored_avatar is not None
                    else None
                ),
                "restored_image": restored_image,
                "restored_vector_fingerprint": (
                    restored_vector_fingerprint
                ),
                "restored_exactly": (
                    restored_vector_fingerprint
                    == initial_vector_fingerprint
                ),
            }
        )
        write_json(restoration, restoration_path)
        if not restoration["restored_exactly"]:
            raise ReconstructionError(
                "Scene snapshot restored with a different Morph fingerprint"
            )

    failures = [item for item in results if not item.get("success")]
    summary_path = os.path.join(output_dir, "validation_result.json")
    summary = {
        "schema_version": 1,
        "run_id": os.path.basename(output_dir),
        "started_at": started_at,
        "finished_at": now(),
        "started_from_library": library_path,
        "library_id": library.get("library_id"),
        "diagnostic_mode": diagnostic_mode,
        "requested_count": len(selected_ids),
        "success_count": len(results) - len(failures),
        "failure_count": len(failures),
        "success": (
            not failures
            and len(results) == len(selected_ids)
            and restoration["restored_exactly"]
        ),
        "scene_restoration": restoration,
        "scene_restoration_path": restoration_path,
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
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def run_bodyfit_height_matrix(
    library_path,
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    """Measure comparable crown-to-sole bounds without rendering images."""
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "BodyFit height preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown BodyFit height preset IDs: {}".format(missing)
        )

    initial_avatars = list(RLPy.RScene.GetAvatars() or [])
    if len(initial_avatars) > 1:
        raise ReconstructionError(
            "BodyFit height matrix expected at most one initial avatar"
        )
    initial_avatar = initial_avatars[0] if initial_avatars else None
    initial_scene_was_empty = initial_avatar is None
    initial_vector_fingerprint = None
    if initial_avatar is not None:
        RLPy.RScene.SelectObject(initial_avatar)
        initial_vector_fingerprint = vectors_excluding_morph_fingerprint(
            capture_vectors(initial_avatar),
            "__no_excluded_morph__",
        )

    snapshot_path = os.path.join(
        output_dir,
        "_current_scene_before_bodyfit_height_matrix.ccProject",
    )
    restoration_path = os.path.join(
        output_dir,
        "scene_snapshot_restoration.json",
    )
    if os.path.isfile(snapshot_path):
        os.remove(snapshot_path)
    checked(
        "Save current scene before BodyFit height matrix",
        RLPy.RFileIO.SaveProject(snapshot_path),
    )
    snapshot_stat = wait_for_rendered_preview(
        snapshot_path,
        timeout_seconds=600.0,
        stable_seconds=2.0,
    )
    restoration = {
        "schema_version": 1,
        "snapshot_path": snapshot_path,
        "snapshot_size": snapshot_stat,
        "snapshot_retained": True,
        "initial_scene_was_empty": initial_scene_was_empty,
        "initial_vector_fingerprint": initial_vector_fingerprint,
        "restore_attempted": False,
        "restored": False,
        "restored_exactly": False,
    }

    started_at = now()
    results = []
    try:
        for index, preset_id in enumerate(selected_ids):
            preset = by_id[preset_id]
            record = {
                "preset_id": preset_id,
                "sex": preset.get("sex"),
                "body_class": preset.get("body_class"),
                "success": False,
                "error": None,
            }
            try:
                source = preset.get("source_project")
                source_path = (
                    source.get("path")
                    if isinstance(source, dict)
                    else source
                )
                if not isinstance(source_path, str) or not os.path.isfile(
                    source_path
                ):
                    raise ReconstructionError(
                        "BodyFit height source project is missing: {}".format(
                            source_path
                        )
                    )
                expected_sha256 = (
                    source.get("sha256")
                    if isinstance(source, dict)
                    else None
                )
                actual_sha256 = sha256_file(source_path)
                if (
                    expected_sha256 is not None
                    and actual_sha256 != expected_sha256
                ):
                    raise ReconstructionError(
                        "BodyFit height source project hash changed"
                    )
                log(
                    "BODYFIT HEIGHT {}/{} {}".format(
                        index + 1,
                        len(selected_ids),
                        preset_id,
                    )
                )
                load_status, load_dialogs = (
                    load_file_with_optional_undo_warning(
                        source_path,
                        "Load BodyFit height source project",
                    )
                )
                settle_cc_ui(1.0)
                avatar, avatars = resolve_avatar()
                if len(avatars) != 1:
                    raise ReconstructionError(
                        "BodyFit height matrix expected one loaded avatar"
                    )
                force_avatar_scene_evaluation(avatar)
                source_vectors = capture_vectors(avatar)
                source_vectors_path = os.path.join(
                    output_dir,
                    "{}_source_vectors.json".format(preset_id),
                )
                write_json(source_vectors, source_vectors_path)
                source_bounds = capture_bounds(avatar)
                measurement_morphs = list(
                    preset.get("measurement_morphs") or []
                )
                controlled_ids = []
                for item in measurement_morphs:
                    morph_id = item.get("id")
                    target = item.get("target")
                    if not isinstance(morph_id, str) or not morph_id:
                        raise ReconstructionError(
                            "BodyFit height Morph ID is missing"
                        )
                    if morph_id in controlled_ids:
                        raise ReconstructionError(
                            "BodyFit height Morph IDs are duplicated"
                        )
                    if (
                        isinstance(target, bool)
                        or not isinstance(target, (int, float))
                        or not math.isfinite(float(target))
                    ):
                        raise ReconstructionError(
                            "BodyFit height Morph target must be finite"
                        )
                    controlled_ids.append(morph_id)
                protected_before = vectors_excluding_morphs_fingerprint(
                    capture_vectors(avatar),
                    controlled_ids,
                )
                applications = []
                for item in measurement_morphs:
                    applications.append(
                        apply_single_morph_weight(
                            avatar,
                            item["id"],
                            item["target"],
                            "BodyFit height",
                        )
                    )
                force_avatar_scene_evaluation(avatar)
                measured_bounds = capture_bounds(avatar)
                protected_after = vectors_excluding_morphs_fingerprint(
                    capture_vectors(avatar),
                    controlled_ids,
                )
                if protected_after != protected_before:
                    raise ReconstructionError(
                        "BodyFit height adjustment changed protected Morphs"
                    )
                record.update(
                    {
                        "source_project": {
                            "path": source_path,
                            "sha256": actual_sha256,
                            "bytes": os.path.getsize(source_path),
                        },
                        "load_status": load_status,
                        "load_dialogs": load_dialogs,
                        "source_bounds": source_bounds,
                        "source_vectors_path": source_vectors_path,
                        "measurement_morphs": applications,
                        "measured_bounds": measured_bounds,
                        "height_cm": float(
                            measured_bounds["maximum"][2]
                            - measured_bounds["minimum"][2]
                        ),
                        "minimum_z_cm": float(
                            measured_bounds["minimum"][2]
                        ),
                        "maximum_z_cm": float(
                            measured_bounds["maximum"][2]
                        ),
                        "success": True,
                    }
                )
            except Exception as exc:
                record["error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            results.append(record)
            QtWidgets.QApplication.processEvents()
    finally:
        restoration["restore_attempted"] = True
        restore_status, restore_dialogs = load_file_with_optional_undo_warning(
            snapshot_path,
            "Restore current scene after BodyFit height matrix",
        )
        settle_cc_ui(3.0)
        restored_avatars = list(RLPy.RScene.GetAvatars() or [])
        expected_avatar_count = 0 if initial_scene_was_empty else 1
        restored_vector_fingerprint = None
        if len(restored_avatars) == expected_avatar_count and restored_avatars:
            restored_avatar = restored_avatars[0]
            RLPy.RScene.SelectObject(restored_avatar)
            force_avatar_scene_evaluation(restored_avatar)
            restored_vector_fingerprint = vectors_excluding_morph_fingerprint(
                capture_vectors(restored_avatar),
                "__no_excluded_morph__",
            )
        restoration.update(
            {
                "restore_status": restore_status,
                "restore_dialogs": restore_dialogs,
                "restored": len(restored_avatars) == expected_avatar_count,
                "restored_avatar_count": len(restored_avatars),
                "restored_vector_fingerprint": restored_vector_fingerprint,
                "restored_exactly": bool(
                    len(restored_avatars) == expected_avatar_count
                    and restored_vector_fingerprint
                    == initial_vector_fingerprint
                ),
            }
        )
        write_json(restoration, restoration_path)
        if not restoration["restored_exactly"]:
            raise ReconstructionError(
                "BodyFit height matrix did not restore the initial scene"
            )

    failures = [item for item in results if not item["success"]]
    summary_path = os.path.join(output_dir, "bodyfit_height_matrix.json")
    summary = {
        "schema_version": 1,
        "library_id": library.get("library_id"),
        "diagnostic_mode": "bodyfit_height_matrix",
        "started_at": started_at,
        "finished_at": now(),
        "requested_count": len(selected_ids),
        "success_count": len(results) - len(failures),
        "failure_count": len(failures),
        "success": not failures and len(results) == len(selected_ids),
        "measurement": (
            "world-space avatar bounds maximum Z minus minimum Z, in CC cm"
        ),
        "results": results,
        "scene_restoration": restoration,
        "summary_path": summary_path,
        "started_from_library": library_path,
    }
    write_json(summary, summary_path)
    return summary


def _targeted_morph_state(component, morph_id):
    try:
        bounds = component.GetShapingMorphMinMax(morph_id)
        weight = float(component.GetShapingMorphWeight(morph_id))
    except Exception as exc:
        raise ReconstructionError(
            "Targeted Morph is unavailable: {} ({})".format(
                morph_id,
                exc,
            )
        )
    return {
        "id": morph_id,
        "maximum": float(bounds.second),
        "minimum": float(bounds.first),
        "weight": weight,
    }


def _prepare_targeted_morph_states(avatar, morph_ids):
    # CC can report unsigned default bounds until its shaping catalog has been
    # enumerated after a project load. Prime IDs/names before reading Min/Max.
    component, catalog, unused_categories = morph_catalog(avatar)
    missing = sorted(set(morph_ids) - set(catalog))
    if missing:
        raise ReconstructionError(
            "Targeted Morphs are unavailable: {}".format(missing)
        )
    return component, dict(
        (
            morph_id,
            _targeted_morph_state(component, morph_id),
        )
        for morph_id in sorted(set(morph_ids))
    )


def _apply_targeted_morph_weights(component, avatar, targets, label):
    states = {}
    changed = False
    for morph_id, raw_target in targets.items():
        target = float(raw_target)
        state = _targeted_morph_state(component, morph_id)
        reported_out_of_bounds = (
            target < state["minimum"] - 1e-7
            or target > state["maximum"] + 1e-7
        )
        signed_embed = morph_id.lower().startswith("cc embed morphs/")
        bounds_probe_allowed = allows_reported_bounds_probe(morph_id)
        if reported_out_of_bounds and not bounds_probe_allowed:
            raise ReconstructionError(
                "{} target {} for {} is outside [{}, {}]".format(
                    label,
                    target,
                    morph_id,
                    state["minimum"],
                    state["maximum"],
                )
            )
        state["reported_out_of_bounds"] = reported_out_of_bounds
        state["signed_embed_bounds_override"] = (
            reported_out_of_bounds and signed_embed
        )
        state["reported_bounds_override"] = (
            reported_out_of_bounds and bounds_probe_allowed
        )
        if abs(state["weight"] - target) > 1e-7:
            checked(
                "Set {} Morph {}".format(label, morph_id),
                component.SetShapingMorphWeight(morph_id, target),
            )
            changed = True
        states[morph_id] = dict(state, target=target)
    if changed:
        checked(
            "Refresh {} Morphs".format(label),
            RLPy.RGlobal.ObjectModified(
                avatar,
                RLPy.EObjectModifiedType_MorphWeight,
            ),
        )
        checked(
            "Evaluate {} Morphs".format(label),
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
        )
        settle_cc_ui(0.35)
    for morph_id, state in states.items():
        actual = float(component.GetShapingMorphWeight(morph_id))
        state["actual"] = actual
        if abs(actual - state["target"]) > 1e-6:
            raise ReconstructionError(
                "{} Morph did not reach target: {}".format(
                    label,
                    morph_id,
                )
            )
    return states


def run_targeted_bodyfit_height_matrix(
    library_path,
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    """Measure known BodyFit projects without catalog-wide Morph reads."""
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "Targeted height preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown targeted height preset IDs: {}".format(missing)
        )

    started_at = now()
    results = []
    progress_path = os.path.join(output_dir, "progress.json")
    for index, preset_id in enumerate(selected_ids):
        preset = by_id[preset_id]
        record = {
            "body_class": preset.get("body_class"),
            "error": None,
            "preset_id": preset_id,
            "sex": preset.get("sex"),
            "success": False,
        }
        try:
            write_json(
                {
                    "index": index + 1,
                    "phase": "load_bodyfit",
                    "preset_count": len(selected_ids),
                    "preset_id": preset_id,
                    "schema_version": 1,
                    "updated_at": now(),
                },
                progress_path,
            )
            source = preset.get("source_project")
            source_path = (
                source.get("path")
                if isinstance(source, dict)
                else source
            )
            if not isinstance(source_path, str) or not os.path.isfile(
                source_path
            ):
                raise ReconstructionError(
                    "Targeted height source project is missing: {}".format(
                        source_path
                    )
                )
            actual_sha256 = sha256_file(source_path)
            expected_sha256 = (
                source.get("sha256") if isinstance(source, dict) else None
            )
            if (
                expected_sha256 is not None
                and actual_sha256 != expected_sha256
            ):
                raise ReconstructionError(
                    "Targeted height source project hash changed"
                )
            log(
                "TARGETED HEIGHT {}/{} {}".format(
                    index + 1,
                    len(selected_ids),
                    preset_id,
                )
            )
            load_status, load_dialogs = (
                load_file_with_optional_undo_warning(
                    source_path,
                    "Load targeted height source project",
                )
            )
            avatar, avatars = resolve_avatar()
            if len(avatars) != 1:
                raise ReconstructionError(
                    "Targeted height expected one loaded avatar"
                )
            RLPy.RScene.SelectObject(avatar)
            component = avatar.GetAvatarShapingComponent()
            if component is None:
                raise ReconstructionError(
                    "Targeted height avatar has no shaping component"
                )
            source_bounds = capture_bounds(avatar)
            measurement_morphs = list(
                preset.get("measurement_morphs") or []
            )
            morph_ids = [item.get("id") for item in measurement_morphs]
            if (
                any(not isinstance(item, str) or not item for item in morph_ids)
                or len(morph_ids) != len(set(morph_ids))
            ):
                raise ReconstructionError(
                    "Targeted height Morph IDs are invalid or duplicated"
                )
            applications = {}
            measured_bounds = source_bounds
            restored_exactly = True
            if measurement_morphs:
                component, initial_states = _prepare_targeted_morph_states(
                    avatar,
                    morph_ids,
                )
                targets = dict(
                    (item["id"], float(item["target"]))
                    for item in measurement_morphs
                )
                applications = _apply_targeted_morph_weights(
                    component,
                    avatar,
                    targets,
                    "BodyFit height",
                )
                measured_bounds = capture_bounds(avatar)
                restored_targets = dict(
                    (morph_id, state["weight"])
                    for morph_id, state in initial_states.items()
                )
                _apply_targeted_morph_weights(
                    component,
                    avatar,
                    restored_targets,
                    "restore BodyFit height",
                )
                restored_exactly = all(
                    abs(
                        float(component.GetShapingMorphWeight(morph_id))
                        - target
                    )
                    <= 1e-6
                    for morph_id, target in restored_targets.items()
                )
            if not restored_exactly:
                raise ReconstructionError(
                    "Targeted height did not restore controlled Morphs"
                )
            record.update(
                {
                    "height_cm": float(
                        measured_bounds["maximum"][2]
                        - measured_bounds["minimum"][2]
                    ),
                    "load_dialogs": load_dialogs,
                    "load_status": load_status,
                    "measured_bounds": measured_bounds,
                    "measurement_morphs": [
                        applications[item["id"]]
                        for item in measurement_morphs
                    ],
                    "restored_exactly": restored_exactly,
                    "source_bounds": source_bounds,
                    "source_project": {
                        "bytes": os.path.getsize(source_path),
                        "path": source_path,
                        "sha256": actual_sha256,
                    },
                    "success": True,
                }
            )
        except Exception as exc:
            record["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "type": type(exc).__name__,
            }
        results.append(record)
        QtWidgets.QApplication.processEvents()

    failures = [item for item in results if not item["success"]]
    summary_path = os.path.join(output_dir, "bodyfit_height_matrix.json")
    summary = {
        "diagnostic_mode": "targeted_bodyfit_height_matrix",
        "failure_count": len(failures),
        "finished_at": now(),
        "library_id": library.get("library_id"),
        "measurement_policy": library.get("measurement_policy"),
        "requested_count": len(selected_ids),
        "results": results,
        "scene_policy": "leave_last_source_project_with_morphs_restored",
        "schema_version": 1,
        "started_at": started_at,
        "started_from_library": library_path,
        "success": not failures and len(results) == len(selected_ids),
        "success_count": len(results) - len(failures),
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    return summary


def run_targeted_morph_visual_matrix(
    library_path,
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    """Render known Morph candidates without reading all Morph weights."""
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "Targeted Morph preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown targeted Morph preset IDs: {}".format(missing)
        )

    started_at = now()
    results = []
    progress_path = os.path.join(output_dir, "progress.json")
    inter_case_delay_seconds = max(
        0.0,
        float(library.get("inter_case_delay_seconds", 0.0)),
    )
    review_scene = library.get("targeted_morph_review_scene") or {}
    if not isinstance(review_scene, dict):
        raise ReconstructionError(
            "targeted_morph_review_scene must be an object"
        )
    review_lightroom = None
    review_cameras = {}
    review_positions = {}
    review_views = review_scene.get("views")
    dynamic_pose_review = library.get(
        "targeted_morph_dynamic_pose_review"
    )
    if dynamic_pose_review is None:
        dynamic_pose_review = {}
    if not isinstance(dynamic_pose_review, dict):
        raise ReconstructionError(
            "targeted_morph_dynamic_pose_review must be an object"
        )
    dynamic_pose_enabled = dynamic_pose_review.get("enabled", False)
    if not isinstance(dynamic_pose_enabled, bool):
        raise ReconstructionError(
            "targeted_morph_dynamic_pose_review.enabled must be boolean"
        )
    required_dynamic_pose_ids = dynamic_pose_review.get(
        "required_pose_ids",
        [],
    )
    if dynamic_pose_enabled:
        if not review_scene:
            raise ReconstructionError(
                "Dynamic targeted Morph review requires a review scene"
            )
        if (
            not isinstance(required_dynamic_pose_ids, list)
            or not required_dynamic_pose_ids
            or any(
                not isinstance(item, str) or not item
                for item in required_dynamic_pose_ids
            )
            or len(required_dynamic_pose_ids)
            != len(set(required_dynamic_pose_ids))
        ):
            raise ReconstructionError(
                "Dynamic targeted Morph required_pose_ids must be unique strings"
            )
    if review_scene:
        review_lightroom = canonical_existing_file(
            review_scene.get("preview_lightroom"),
            "Targeted Morph review Lightroom",
        )
        raw_cameras = review_scene.get("face_camera_by_sex") or {}
        raw_positions = review_scene.get("face_position_by_sex") or {}
        if not isinstance(raw_cameras, dict) or not isinstance(
            raw_positions, dict
        ):
            raise ReconstructionError(
                "Targeted Morph review cameras and positions must be objects"
            )
        for sex in ("female", "male"):
            review_cameras[sex] = canonical_existing_file(
                raw_cameras.get(sex),
                "Targeted Morph {} face camera".format(sex),
            )
            review_positions[sex] = _quality_benchmark_position(
                raw_positions.get(sex),
                "targeted_morph_review_scene.{}_position".format(sex),
            )
        if not isinstance(review_views, list) or not review_views:
            raise ReconstructionError(
                "Targeted Morph review views must be a non-empty list"
            )

    def mark(phase, detail=None):
        write_json(
            {
                "detail": detail,
                "phase": phase,
                "schema_version": 1,
                "updated_at": now(),
            },
            progress_path,
        )

    for preset_index, preset_id in enumerate(selected_ids):
        preset = by_id[preset_id]
        case_dir = os.path.join(output_dir, preset_id)
        os.makedirs(case_dir, exist_ok=False)
        record = {
            "application": None,
            "dynamic_pose_reviews": [],
            "error": None,
            "head_scale_review": None,
            "neck_morph_review": None,
            "preset_id": preset_id,
            "sex": preset.get("sex"),
            "success": False,
        }
        try:
            source = preset.get("source_project")
            source_path = (
                source.get("path")
                if isinstance(source, dict)
                else source
            )
            if not isinstance(source_path, str) or not os.path.isfile(
                source_path
            ):
                raise ReconstructionError(
                    "Targeted Morph source project is missing: {}".format(
                        source_path
                    )
                )
            actual_sha256 = sha256_file(source_path)
            expected_sha256 = (
                source.get("sha256") if isinstance(source, dict) else None
            )
            if (
                expected_sha256 is not None
                and actual_sha256 != expected_sha256
            ):
                raise ReconstructionError(
                    "Targeted Morph source project hash changed"
                )
            mark(
                "load_source_project",
                {
                    "index": preset_index + 1,
                    "preset_count": len(selected_ids),
                    "preset_id": preset_id,
                },
            )
            log(
                "TARGETED MORPH {}/{} {}".format(
                    preset_index + 1,
                    len(selected_ids),
                    preset_id,
                )
            )
            load_status, load_dialogs = (
                load_file_with_optional_undo_warning(
                    source_path,
                    "Load targeted Morph source project",
                )
            )
            avatar, avatars = resolve_avatar()
            if len(avatars) != 1:
                raise ReconstructionError(
                    "Targeted Morph scan expected one loaded avatar"
                )
            RLPy.RScene.SelectObject(avatar)
            if review_scene:
                sex = preset.get("sex")
                checked(
                    "Load targeted Morph review Lightroom",
                    RLPy.RFileIO.LoadFile(review_lightroom),
                )
                settle_cc_ui(1.0)
                checked(
                    "Load targeted Morph review camera",
                    RLPy.RFileIO.LoadFile(review_cameras[sex]),
                )
                settle_cc_ui(1.0)
                review_position = review_positions[sex]
                set_avatar_position(
                    avatar,
                    position_x=review_position[0],
                    position_y=review_position[1],
                    position_z=review_position[2],
                )
                force_avatar_scene_evaluation(avatar)
            component = avatar.GetAvatarShapingComponent()
            if component is None:
                raise ReconstructionError(
                    "Targeted Morph avatar has no shaping component"
                )

            head_review = preset.get("head_scale_review")
            neck_review = preset.get("neck_morph_review")
            if bool(head_review) == bool(neck_review):
                raise ReconstructionError(
                    "Targeted Morph scan requires exactly one review block"
                )
            baseline_targets = {}
            fixed_targets = []
            review_specs = []
            if head_review:
                review_specs.append(
                    {
                        "morph_id": head_review.get("morph_id"),
                        "review_id": "head_scale",
                        "values": head_review.get("values"),
                    }
                )
            else:
                head_scale = neck_review.get("head_scale") or {}
                head_scale_id = head_scale.get("morph_id")
                if not isinstance(head_scale_id, str) or not head_scale_id:
                    raise ReconstructionError(
                        "Targeted Morph head_scale.morph_id is missing"
                    )
                baseline_targets[head_scale_id] = float(
                    head_scale.get("target")
                )
                fixed_morphs = neck_review.get("fixed_morphs") or []
                if not isinstance(fixed_morphs, list):
                    raise ReconstructionError(
                        "Targeted Morph fixed_morphs must be a list"
                    )
                for fixed in fixed_morphs:
                    if not isinstance(fixed, dict):
                        raise ReconstructionError(
                            "Targeted Morph fixed Morph must be an object"
                        )
                    fixed_id = fixed.get("morph_id")
                    fixed_target = fixed.get("target")
                    if not isinstance(fixed_id, str) or not fixed_id:
                        raise ReconstructionError(
                            "Targeted Morph fixed morph_id is missing"
                        )
                    if fixed_id in baseline_targets:
                        raise ReconstructionError(
                            "Targeted Morph fixed ID is duplicated: {}".format(
                                fixed_id
                            )
                        )
                    if (
                        isinstance(fixed_target, bool)
                        or not isinstance(fixed_target, (int, float))
                        or not math.isfinite(float(fixed_target))
                    ):
                        raise ReconstructionError(
                            "Targeted Morph fixed target must be finite"
                        )
                    fixed_target = float(fixed_target)
                    baseline_targets[fixed_id] = fixed_target
                    fixed_targets.append(
                        {
                            "morph_id": fixed_id,
                            "target": fixed_target,
                        }
                    )
                review_specs.extend(neck_review.get("morphs") or [])
            if not review_specs:
                raise ReconstructionError(
                    "Targeted Morph review contains no Morph candidates"
                )

            normalized_specs = []
            controlled_ids = set(baseline_targets)
            for item in review_specs:
                morph_id = item.get("morph_id")
                review_id = item.get("review_id")
                values = item.get("values")
                if not isinstance(morph_id, str) or not morph_id:
                    raise ReconstructionError(
                        "Targeted Morph candidate ID is missing"
                    )
                if not isinstance(review_id, str) or not review_id:
                    raise ReconstructionError(
                        "Targeted Morph review ID is missing"
                    )
                if morph_id in controlled_ids:
                    raise ReconstructionError(
                        "Targeted Morph ID is duplicated: {}".format(
                            morph_id
                        )
                    )
                if not isinstance(values, list) or not values:
                    raise ReconstructionError(
                        "Targeted Morph values are missing for {}".format(
                            review_id
                        )
                    )
                values = [float(value) for value in values]
                if len(values) != len(set(values)):
                    raise ReconstructionError(
                        "Targeted Morph values contain duplicates"
                    )
                controlled_ids.add(morph_id)
                normalized_specs.append(
                    {
                        "morph_id": morph_id,
                        "review_id": review_id,
                        "values": values,
                    }
                )
            if dynamic_pose_enabled and (
                len(normalized_specs) != 1
                or len(normalized_specs[0]["values"]) != 1
            ):
                raise ReconstructionError(
                    "Dynamic targeted Morph review requires one candidate per preset"
                )

            component, initial_states = _prepare_targeted_morph_states(
                avatar,
                controlled_ids,
            )
            initial_targets = dict(
                (morph_id, state["weight"])
                for morph_id, state in initial_states.items()
            )
            initial_yaw = _transform_float(
                avatar,
                "Rotation/RotationZ",
            )
            views = review_views or (
                neck_review.get("views")
                if neck_review
                else None
            ) or [{"view_id": "yaw_000", "yaw_degrees": 0.0}]
            review_reports = []
            flat_candidates = []
            for morph_index, item in enumerate(normalized_specs):
                morph_dir = os.path.join(case_dir, item["review_id"])
                os.makedirs(morph_dir, exist_ok=False)
                morph_report = {
                    "candidates": [],
                    "initial_weight": initial_states[
                        item["morph_id"]
                    ]["weight"],
                    "morph": dict(initial_states[item["morph_id"]]),
                    "review_id": item["review_id"],
                    "values": item["values"],
                }
                review_reports.append(morph_report)
                for value_index, value in enumerate(item["values"]):
                    targets = dict(initial_targets)
                    targets.update(baseline_targets)
                    targets[item["morph_id"]] = value
                    mark(
                        "render_candidate",
                        {
                            "candidate_count": len(item["values"]),
                            "candidate_index": value_index + 1,
                            "morph_count": len(normalized_specs),
                            "morph_index": morph_index + 1,
                            "preset_id": preset_id,
                            "review_id": item["review_id"],
                            "value": value,
                        },
                    )
                    applications = _apply_targeted_morph_weights(
                        component,
                        avatar,
                        targets,
                        "targeted candidate",
                    )
                    if morph_index == 0 and value_index == 0:
                        # RenderImage can return the pre-load camera frame on
                        # its first capture. Discard one frame while the first
                        # candidate is already applied.
                        warmup_view = views[0]
                        set_avatar_yaw(
                            avatar,
                            float(warmup_view.get("yaw_degrees")),
                        )
                        warmup_path = os.path.join(
                            case_dir,
                            "_capture_warmup.png",
                        )
                        mark(
                            "warm_preview_capture",
                            {
                                "preset_id": preset_id,
                                "review_id": item["review_id"],
                                "value": value,
                            },
                        )
                        render_preview(warmup_path)
                        if os.path.isfile(warmup_path):
                            os.remove(warmup_path)
                    rendered_views = {}
                    for view in views:
                        view_id = str(view.get("view_id"))
                        yaw_degrees = float(view.get("yaw_degrees"))
                        set_avatar_yaw(avatar, yaw_degrees)
                        image_path = os.path.join(
                            morph_dir,
                            "{}_{}_{}.png".format(
                                item["review_id"],
                                signed_morph_token(value),
                                view_id,
                            ),
                        )
                        render_preview(image_path)
                        rendered_views[view_id] = image_path
                    dynamic_pose_result = None
                    if dynamic_pose_enabled:
                        dynamic_dir = os.path.join(
                            morph_dir,
                            "dynamic_pose_review",
                        )
                        os.makedirs(dynamic_dir, exist_ok=False)

                        def mark_dynamic_phase(phase, details=None):
                            detail = {
                                "preset_id": preset_id,
                                "review_id": item["review_id"],
                                "value": value,
                            }
                            if details:
                                detail["pose_details"] = details
                            mark("dynamic_{}".format(phase), detail)

                        pose_report = render_profile_upgrade_pose_matrix(
                            avatar,
                            dynamic_dir,
                            mark_dynamic_phase,
                            RLPy.RGlobal.GetStartTime(),
                            review_positions[preset.get("sex")],
                        )
                        observed_pose_ids = [
                            pose["pose_id"]
                            for pose in pose_report["poses"]
                        ]
                        missing_pose_ids = sorted(
                            set(required_dynamic_pose_ids)
                            - set(observed_pose_ids)
                        )
                        if missing_pose_ids:
                            raise ReconstructionError(
                                "Dynamic targeted Morph poses are missing: {}"
                                .format(missing_pose_ids)
                            )
                        post_dynamic_weights = dict(
                            (
                                morph_id,
                                float(
                                    component.GetShapingMorphWeight(morph_id)
                                ),
                            )
                            for morph_id in controlled_ids
                        )
                        morphs_unchanged = all(
                            abs(post_dynamic_weights[morph_id] - target)
                            <= 1e-6
                            for morph_id, target in targets.items()
                        )
                        if not morphs_unchanged:
                            raise ReconstructionError(
                                "Dynamic pose review changed controlled Morphs"
                            )
                        dynamic_pose_result = {
                            "evidence_liveness": pose_report[
                                "evidence_liveness"
                            ],
                            "expression_count": pose_report[
                                "expression_count"
                            ],
                            "expression_set_uid": pose_report[
                                "expression_set_uid"
                            ],
                            "morphs_unchanged": morphs_unchanged,
                            "neutral_eye_integrity": pose_report[
                                "neutral_eye_integrity"
                            ],
                            "observed_pose_ids": observed_pose_ids,
                            "post_dynamic_weights": post_dynamic_weights,
                            "report_path": os.path.join(
                                dynamic_dir,
                                "facial_pose_validation.json",
                            ),
                            "required_pose_ids": list(
                                required_dynamic_pose_ids
                            ),
                        }
                        record["dynamic_pose_reviews"].append(
                            dynamic_pose_result
                        )
                    bounds = capture_bounds(avatar)
                    candidate = {
                        "application": applications[item["morph_id"]],
                        "avatar_bounds": bounds,
                        "height_cm": float(
                            bounds["maximum"][2]
                            - bounds["minimum"][2]
                        ),
                        "value": value,
                        "views": rendered_views,
                    }
                    if dynamic_pose_result is not None:
                        candidate["dynamic_pose_review"] = (
                            dynamic_pose_result
                        )
                    morph_report["candidates"].append(candidate)
                    if head_review:
                        flat_candidates.append(
                            dict(
                                candidate,
                                image=rendered_views[
                                    next(iter(rendered_views))
                                ],
                            )
                        )

            saved_selected = None
            save_config = (
                neck_review.get("save_selected_candidate")
                if neck_review
                else None
            )
            if save_config:
                selected_review_id = save_config.get("review_id")
                selected_spec = next(
                    (
                        item
                        for item in normalized_specs
                        if item["review_id"] == selected_review_id
                    ),
                    None,
                )
                if selected_spec is None:
                    raise ReconstructionError(
                        "Selected targeted Morph review ID is unavailable"
                    )
                selected_value = float(save_config.get("value"))
                selected_targets = dict(initial_targets)
                selected_targets.update(baseline_targets)
                selected_targets[selected_spec["morph_id"]] = (
                    selected_value
                )
                applications = _apply_targeted_morph_weights(
                    component,
                    avatar,
                    selected_targets,
                    "selected targeted candidate",
                )
                selected_project = os.path.realpath(
                    os.path.abspath(save_config.get("project_path"))
                )
                os.makedirs(os.path.dirname(selected_project), exist_ok=True)
                checked(
                    "Save selected targeted Morph candidate",
                    RLPy.RFileIO.SaveProject(selected_project),
                )
                project_size = wait_for_rendered_preview(
                    selected_project,
                    timeout_seconds=600.0,
                    stable_seconds=2.0,
                )
                selected_bounds = capture_bounds(avatar)
                saved_selected = {
                    "application": applications[
                        selected_spec["morph_id"]
                    ],
                    "avatar_bounds": selected_bounds,
                    "height_cm": float(
                        selected_bounds["maximum"][2]
                        - selected_bounds["minimum"][2]
                    ),
                    "project_path": selected_project,
                    "project_sha256": sha256_file(selected_project),
                    "project_size": project_size,
                    "review_id": selected_review_id,
                    "value": selected_value,
                }

            _apply_targeted_morph_weights(
                component,
                avatar,
                initial_targets,
                "restore targeted scan",
            )
            set_avatar_yaw(avatar, math.degrees(initial_yaw))
            restored_weights = dict(
                (
                    morph_id,
                    float(component.GetShapingMorphWeight(morph_id)),
                )
                for morph_id in controlled_ids
            )
            restored_exactly = all(
                abs(restored_weights[morph_id] - target) <= 1e-6
                for morph_id, target in initial_targets.items()
            )
            if not restored_exactly:
                raise ReconstructionError(
                    "Targeted Morph scan did not restore controlled weights"
                )
            record["application"] = {
                "load_dialogs": load_dialogs,
                "load_status": load_status,
                "review_scene": (
                    {
                        "camera": review_cameras[preset.get("sex")],
                        "lightroom": review_lightroom,
                        "position": review_positions[preset.get("sex")],
                        "views": views,
                    }
                    if review_scene
                    else None
                ),
                "source_project": source_path,
                "source_project_sha256": actual_sha256,
            }
            if head_review:
                record["head_scale_review"] = {
                    "candidates": flat_candidates,
                    "initial_weight": initial_states[
                        normalized_specs[0]["morph_id"]
                    ]["weight"],
                    "morph": initial_states[
                        normalized_specs[0]["morph_id"]
                    ],
                    "restored_exactly": restored_exactly,
                    "restored_weights": restored_weights,
                }
            else:
                record["neck_morph_review"] = {
                    "controlled_morph_ids": sorted(controlled_ids),
                    "fixed_morphs": fixed_targets,
                    "morphs": review_reports,
                    "restored_exactly": restored_exactly,
                    "restored_weights": restored_weights,
                    "saved_selected_candidate": saved_selected,
                }
            record["success"] = True
        except Exception as exc:
            record["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "type": type(exc).__name__,
            }
        results.append(record)
        write_json(record, os.path.join(case_dir, "result.json"))
        QtWidgets.QApplication.processEvents()
        if (
            inter_case_delay_seconds
            and preset_index + 1 < len(selected_ids)
        ):
            settle_cc_ui(inter_case_delay_seconds)

    failures = [item for item in results if not item["success"]]
    summary_path = os.path.join(output_dir, "validation_result.json")
    summary = {
        "diagnostic_mode": "targeted_morph_visual_matrix",
        "failure_count": len(failures),
        "finished_at": now(),
        "library_id": library.get("library_id"),
        "requested_count": len(selected_ids),
        "results": results,
        "scene_policy": "leave_last_source_project_loaded",
        "schema_version": 1,
        "started_at": started_at,
        "started_from_library": library_path,
        "success": not failures and len(results) == len(selected_ids),
        "success_count": len(results) - len(failures),
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    mark("completed", {"success": summary["success"]})
    return summary


def run_headshot_project_seed_bodyfit_pilot(
    library_path,
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    """Validate baked Headshot identity projects on canonical BodyFits."""
    by_id = dict((item["preset_id"], item) for item in all_presets)
    selection_mode = (
        "explicit_subset" if preset_ids is not None else "complete_library"
    )
    selected_ids = list(
        preset_ids
        if preset_ids is not None
        else [item["preset_id"] for item in all_presets]
    )
    if not selected_ids or len(selected_ids) != len(set(selected_ids)):
        raise ReconstructionError(
            "Headshot project-seed Pilot IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown Headshot project-seed Pilot IDs: {}".format(missing)
        )
    policy = library.get("pilot_policy") or {}
    if policy.get("pipeline") != "headshot_project_seed_then_bodyfit_v1":
        raise ReconstructionError("Unexpected Headshot project-seed pipeline")
    if int(policy.get("case_count", 0)) != len(all_presets):
        raise ReconstructionError("Headshot project-seed Pilot case count changed")
    if library.get("save_character_projects") is not True:
        raise ReconstructionError("Headshot project-seed Pilot must save projects")
    lightroom_path = canonical_existing_file(
        library.get("preview_lightroom"),
        "Headshot project-seed Pilot Lightroom",
    )
    inter_case_delay = float(library.get("inter_case_delay_seconds", 0.0))
    if not math.isfinite(inter_case_delay) or inter_case_delay < 0.0:
        raise ReconstructionError("Invalid project-seed inter-case delay")

    def file_record(record, label):
        if not isinstance(record, dict):
            raise ReconstructionError("{} must be a file record".format(label))
        path = canonical_existing_file(record.get("path"), label)
        actual_sha256 = sha256_file(path)
        expected_sha256 = record.get("sha256")
        if expected_sha256 is not None and expected_sha256 != actual_sha256:
            raise ReconstructionError("{} SHA-256 changed".format(label))
        return {
            "bytes": os.path.getsize(path),
            "path": path,
            "sha256": actual_sha256,
        }

    def load_project(record, label):
        status, dialogs = load_file_with_optional_undo_warning(
            record["path"], label
        )
        settle_cc_ui(2.0)
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "{} expected one avatar, found {}".format(label, len(avatars))
            )
        RLPy.RScene.SelectObject(avatar)
        checked(
            "Evaluate {} start frame".format(label),
            RLPy.RGlobal.SetTime(RLPy.RGlobal.GetStartTime(), True),
        )
        force_avatar_scene_evaluation(avatar)
        return avatar, {"dialogs": dialogs, "status": status}

    def capture_avatar_transform(avatar):
        return {
            "position": {
                "x": _transform_float(avatar, "Position/PositionX"),
                "y": _transform_float(avatar, "Position/PositionY"),
                "z": _transform_float(avatar, "Position/PositionZ"),
            },
            "yaw_radians": _transform_float(avatar, "Rotation/RotationZ"),
        }

    def restore_avatar_transform(avatar, state):
        set_avatar_position(
            avatar,
            position_x=state["position"]["x"],
            position_y=state["position"]["y"],
            position_z=state["position"]["z"],
        )
        set_avatar_yaw(avatar, math.degrees(state["yaw_radians"]))
        force_avatar_scene_evaluation(avatar)

    def render_face_view(avatar, camera_path, face_position, yaw, image_path):
        checked("Load Headshot Pilot face camera", RLPy.RFileIO.LoadFile(camera_path))
        settle_cc_ui(0.5)
        set_avatar_position(
            avatar,
            position_x=face_position[0],
            position_y=face_position[1],
            position_z=face_position[2],
        )
        set_avatar_yaw(avatar, yaw)
        force_avatar_scene_evaluation(avatar)
        render_preview(image_path)

    def render_full_body_view(
        avatar,
        camera_path,
        face_position,
        full_body_position,
        image_path,
    ):
        checked("Load Headshot Pilot full-body camera", RLPy.RFileIO.LoadFile(camera_path))
        settle_cc_ui(0.5)
        camera = RLPy.RScene.GetCurrentCamera()
        if camera is None:
            raise ReconstructionError("Headshot Pilot full-body camera is unavailable")
        movable_lights, skipped_lights, light_query_errors = (
            quality_benchmark_movable_lights()
        )
        if not movable_lights:
            raise ReconstructionError(
                "Headshot Pilot found no movable Lightroom lights: {}".format(
                    light_query_errors + skipped_lights
                )
            )
        light_offset = {
            "x": full_body_position[0] - face_position[0],
            "y": full_body_position[1] - face_position[1],
            "z": full_body_position[2] - face_position[2],
        }
        try:
            set_avatar_position(
                avatar,
                position_x=full_body_position[0],
                position_y=full_body_position[1],
                position_z=full_body_position[2],
            )
            set_quality_benchmark_light_offset(movable_lights, light_offset)
            set_avatar_yaw(avatar, 90.0)
            force_avatar_scene_evaluation(avatar)
            checked(
                "Activate Headshot Pilot full-body camera",
                RLPy.RScene.SetCurrentCamera(camera),
            )
            render_preview(image_path)
        finally:
            set_quality_benchmark_light_offset(
                movable_lights,
                {"x": 0.0, "y": 0.0, "z": 0.0},
            )
        return {
            "camera": camera_state(camera),
            "lighting": {
                "light_offset": light_offset,
                "movable_light_count": len(movable_lights),
                "policy": "translate_movable_lights_with_full_body_subject",
                "query_errors": light_query_errors,
                "skipped_lights": skipped_lights,
            },
        }

    started_at = now()
    progress_path = os.path.join(output_dir, "progress.json")
    results = []

    def mark(index, preset_id, phase, detail=None):
        write_json(
            {
                "detail": detail,
                "index": index,
                "phase": phase,
                "preset_count": len(selected_ids),
                "preset_id": preset_id,
                "schema_version": 1,
                "updated_at": now(),
            },
            progress_path,
        )

    for index, preset_id in enumerate(selected_ids, 1):
        preset = by_id[preset_id]
        case_dir = os.path.join(output_dir, preset_id)
        os.makedirs(case_dir, exist_ok=False)
        dynamic_dir = os.path.join(case_dir, "dynamic")
        os.makedirs(dynamic_dir, exist_ok=False)
        artifacts = {
            "assembled_face_front": os.path.join(case_dir, "assembled_face_front.png"),
            "assembled_face_profile": os.path.join(case_dir, "assembled_face_profile.png"),
            "assembled_face_three_quarter": os.path.join(
                case_dir, "assembled_face_three_quarter.png"
            ),
            "assembled_full_body": os.path.join(case_dir, "assembled_full_body.png"),
            "bodyfit_reference_full_body": os.path.join(
                case_dir, "bodyfit_reference_full_body.png"
            ),
            "character_project": os.path.join(case_dir, preset_id + ".ccProject"),
            "dynamic_directory": dynamic_dir,
            "identity_source_front": os.path.join(case_dir, "identity_source_front.png"),
            "identity_vectors": os.path.join(case_dir, "identity_vectors.json"),
            "final_vectors": os.path.join(case_dir, "final_vectors.json"),
            "reloaded_neutral_front": os.path.join(
                case_dir, "reloaded_neutral_front.png"
            ),
            "reloaded_vectors": os.path.join(case_dir, "reloaded_vectors.json"),
            "result": os.path.join(case_dir, "result.json"),
        }
        record = {
            "artifacts": artifacts,
            "bodyfit_id": preset.get("bodyfit_id"),
            "error": None,
            "head_profile_id": preset.get("head_profile_id"),
            "preset_id": preset_id,
            "prototype_id": preset.get("prototype_id"),
            "sex": preset.get("sex"),
            "success": False,
        }
        try:
            mark(index, preset_id, "validate_inputs")
            identity_record = file_record(
                preset.get("source_project"), "Headshot identity project"
            )
            bodyfit_record = file_record(
                preset.get("bodyfit_reference_project"),
                "BodyFit reference project",
            )
            profile_record = file_record(
                preset.get("source_facial_profile"),
                "Canonical Headshot Facial Profile",
            )
            prototype_record = file_record(
                preset.get("prototype_manifest"), "Headshot prototype manifest"
            )
            camera_path = canonical_existing_file(
                preset.get("face_camera"), "Headshot Pilot face camera"
            )
            face_position = preset.get("face_position")
            if (
                not isinstance(face_position, list)
                or len(face_position) != 3
                or any(not isinstance(value, (int, float)) for value in face_position)
            ):
                raise ReconstructionError("Headshot Pilot face position is invalid")
            face_position = [float(value) for value in face_position]
            full_body_position = preset.get("full_body_position")
            if (
                not isinstance(full_body_position, list)
                or len(full_body_position) != 3
                or any(
                    not isinstance(value, (int, float))
                    for value in full_body_position
                )
            ):
                raise ReconstructionError(
                    "Headshot Pilot full-body position is invalid"
                )
            full_body_position = [float(value) for value in full_body_position]
            assembly = preset.get("project_seed_assembly") or {}
            if assembly.get("pipeline") != "headshot_project_seed_then_bodyfit_v1":
                raise ReconstructionError("Headshot assembly contract changed")
            head_target_items = assembly.get("head_shape_targets") or []
            head_targets = {}
            for item in head_target_items:
                morph_id = item.get("id")
                if not isinstance(morph_id, str) or not morph_id:
                    raise ReconstructionError("Headshot profile Morph ID is invalid")
                if morph_id in head_targets:
                    raise ReconstructionError("Duplicate Headshot profile Morph")
                head_targets[morph_id] = float(item["target"])
            if len(head_targets) != 7:
                raise ReconstructionError("Canonical Headshot profile must own seven Morphs")

            target_body_ids = {
                item["id"] for item in preset.get("target_body_morphs") or []
            }
            target_junction_ids = {
                item["id"] for item in preset.get("target_junction_morphs") or []
            }
            proportion_targets = {
                item["id"]: float(item["target"])
                for item in (
                    preset.get("bodyfit_proportion_adjustment") or {}
                ).get("targets", [])
            }
            controlled_ids = set(head_targets) | set(proportion_targets)

            mark(index, preset_id, "load_bodyfit_reference")
            bodyfit_avatar, bodyfit_load = load_project(
                bodyfit_record, "Load BodyFit reference project"
            )
            bodyfit_vectors = capture_vectors(bodyfit_avatar)
            bodyfit_delta = {
                "body": group_delta(
                    preset["target_body_morphs"],
                    bodyfit_vectors["groups"]["body"]["entries"],
                ),
                "junction": group_delta(
                    preset["target_junction_morphs"],
                    bodyfit_vectors["groups"]["junction"]["entries"],
                ),
            }
            if any(bodyfit_delta.values()):
                raise ReconstructionError("BodyFit reference no longer matches its vector")
            if (
                bodyfit_vectors["body_and_junction_fingerprint_sha256"]
                != preset["body_and_junction_fingerprint"]
            ):
                raise ReconstructionError("BodyFit reference fingerprint changed")
            bodyfit_motion_cleanup = clear_avatar_motion(bodyfit_avatar)
            checked("Load project-seed Pilot Lightroom", RLPy.RFileIO.LoadFile(lightroom_path))
            settle_cc_ui(0.75)
            bodyfit_full_body_capture = render_full_body_view(
                bodyfit_avatar,
                camera_path,
                face_position,
                full_body_position,
                artifacts["bodyfit_reference_full_body"],
            )

            mark(index, preset_id, "load_identity_project")
            avatar, identity_load = load_project(
                identity_record, "Load Headshot identity project"
            )
            identity_motion_cleanup = clear_avatar_motion(avatar)
            checked("Load identity Pilot Lightroom", RLPy.RFileIO.LoadFile(lightroom_path))
            settle_cc_ui(0.75)
            identity_transform = capture_avatar_transform(avatar)
            identity_vectors = capture_vectors(avatar)
            identity_bounds = capture_bounds(avatar)
            identity_eye = capture_eye_integrity_state(avatar)
            identity_material = avatar_material_fingerprint(avatar)
            write_json(identity_vectors, artifacts["identity_vectors"])
            unowned_identity_body = unowned_entries(
                identity_vectors,
                target_body_ids | target_junction_ids,
                ("body", "junction"),
            )
            if unowned_identity_body:
                raise ReconstructionError(
                    "Headshot identity contains unregistered Body/Junction Morphs"
                )
            render_face_view(
                avatar,
                camera_path,
                face_position,
                90.0,
                artifacts["identity_source_front"],
            )
            restore_avatar_transform(avatar, identity_transform)

            mark(index, preset_id, "apply_bodyfit")
            body_application = apply_bodyfit(
                avatar,
                preset["target_body_morphs"],
                preset["target_junction_morphs"],
            )
            after_body = capture_vectors(avatar)
            after_body_eye = capture_eye_integrity_state(avatar)
            if group_delta(
                preset["target_body_morphs"],
                after_body["groups"]["body"]["entries"],
            ) or group_delta(
                preset["target_junction_morphs"],
                after_body["groups"]["junction"]["entries"],
            ):
                raise ReconstructionError("Project-seed BodyFit targets did not round-trip")
            if (
                after_body["body_and_junction_fingerprint_sha256"]
                != preset["body_and_junction_fingerprint"]
            ):
                raise ReconstructionError("Project-seed BodyFit fingerprint mismatch")
            body_face_delta = {
                classification: group_delta(
                    identity_vectors["groups"][classification]["entries"],
                    after_body["groups"][classification]["entries"],
                )
                for classification in ("face", "other")
            }
            if any(body_face_delta.values()):
                raise ReconstructionError("Applying BodyFit changed Headshot identity Morphs")
            if eye_integrity_structure_signature(identity_eye) != (
                eye_integrity_structure_signature(after_body_eye)
            ):
                raise ReconstructionError("Applying BodyFit changed eye structure")

            mark(index, preset_id, "load_canonical_facial_profile")
            before_profile = capture_vectors(avatar)
            before_profile_eye = capture_eye_integrity_state(avatar)
            profile_component = avatar.GetFacialProfileComponent()
            if profile_component is None:
                raise ReconstructionError("Headshot identity has no Facial Profile component")
            checked(
                "Load canonical Headshot Facial Profile",
                profile_component.LoadProfile(profile_record["path"]),
            )
            settle_cc_ui(2.0)
            avatar_after_profile, profile_avatars = resolve_avatar()
            if len(profile_avatars) != 1 or scene_object_id(avatar_after_profile) != scene_object_id(avatar):
                raise ReconstructionError("Facial Profile load replaced the Headshot avatar")
            avatar = avatar_after_profile
            force_avatar_scene_evaluation(avatar)
            after_profile = capture_vectors(avatar)
            after_profile_eye = capture_eye_integrity_state(avatar)
            profile_delta = {
                classification: group_delta(
                    before_profile["groups"][classification]["entries"],
                    after_profile["groups"][classification]["entries"],
                )
                for classification in ("body", "junction", "face", "other")
            }
            if any(profile_delta.values()):
                raise ReconstructionError("Facial Profile changed static Morphs")
            if eye_integrity_structure_signature(before_profile_eye) != (
                eye_integrity_structure_signature(after_profile_eye)
            ):
                raise ReconstructionError("Facial Profile changed eye structure")
            face_component = avatar.GetFaceComponent()
            expression_uid = str(face_component.GetExpressionSetUid())
            expression_count = len(list(face_component.GetExpressionNames("") or []))
            if expression_uid != assembly["expected_expression_set_uid"]:
                raise ReconstructionError("Unexpected Facial Profile expression set")
            if expression_count != int(assembly["expected_expression_count"]):
                raise ReconstructionError("Unexpected Facial Profile expression count")

            mark(index, preset_id, "apply_head_profile")
            component, unused_initial_head_states = _prepare_targeted_morph_states(
                avatar, list(head_targets)
            )
            before_head_unowned = unowned_entries(
                after_profile,
                controlled_ids,
                ("body", "junction", "face", "other"),
            )
            head_application = _apply_targeted_morph_weights(
                component, avatar, head_targets, "canonical Headshot profile"
            )
            after_head = capture_vectors(avatar)
            after_head_unowned = unowned_entries(
                after_head,
                controlled_ids,
                ("body", "junction", "face", "other"),
            )
            if group_delta(before_head_unowned, after_head_unowned):
                raise ReconstructionError("Head profile changed unowned Morphs")

            mark(index, preset_id, "apply_bodyfit_proportions")
            avatar, proportion_application = apply_bodyfit_proportion_adjustment(
                avatar,
                preset,
                progress_callback=lambda phase, detail=None: mark(
                    index, preset_id, phase, detail
                ),
            )
            if proportion_application is None:
                raise ReconstructionError("BodyFit proportion decision was not applied")
            final_vectors = capture_vectors(avatar)
            final_eye, final_eye_stabilization = capture_stable_neutral_eye_state(
                avatar
            )
            final_material = avatar_material_fingerprint(avatar)
            final_bounds = capture_bounds(avatar)
            write_json(final_vectors, artifacts["final_vectors"])
            if final_vectors["body_and_junction_fingerprint_sha256"] != (
                preset["body_and_junction_fingerprint"]
            ):
                raise ReconstructionError("Final BodyFit fingerprint changed")
            final_component, unused_states = _prepare_targeted_morph_states(
                avatar, list(controlled_ids)
            )
            controlled_targets = dict(head_targets)
            controlled_targets.update(proportion_targets)
            final_controlled = {}
            for morph_id, target in controlled_targets.items():
                actual = float(final_component.GetShapingMorphWeight(morph_id))
                final_controlled[morph_id] = {"actual": actual, "target": target}
                if abs(actual - target) > 1e-6:
                    raise ReconstructionError(
                        "Final controlled Morph differs: {}".format(morph_id)
                    )
            final_unowned = unowned_entries(
                final_vectors,
                controlled_ids,
                ("face", "other"),
            )
            after_body_unowned = unowned_entries(
                after_body,
                controlled_ids,
                ("face", "other"),
            )
            if group_delta(after_body_unowned, final_unowned):
                raise ReconstructionError("Final assembly changed unowned identity Morphs")
            if eye_integrity_structure_signature(identity_eye) != (
                eye_integrity_structure_signature(final_eye)
            ):
                raise ReconstructionError("Final assembly changed eye structure")
            if identity_material["digest"] != final_material["digest"]:
                raise ReconstructionError("Final assembly changed identity materials")

            mark(index, preset_id, "render_assembled_full_body")
            assembled_transform = capture_avatar_transform(avatar)
            assembled_full_body_capture = render_full_body_view(
                avatar,
                camera_path,
                face_position,
                full_body_position,
                artifacts["assembled_full_body"],
            )
            restore_avatar_transform(avatar, assembled_transform)

            mark(index, preset_id, "render_assembled_face_views")
            render_face_view(
                avatar, camera_path, face_position, 90.0, artifacts["assembled_face_front"]
            )
            render_face_view(
                avatar,
                camera_path,
                face_position,
                45.0,
                artifacts["assembled_face_three_quarter"],
            )
            render_face_view(
                avatar, camera_path, face_position, 0.0, artifacts["assembled_face_profile"]
            )
            restore_avatar_transform(avatar, assembled_transform)

            mark(index, preset_id, "save_clean_assembled_project")
            project_record = save_bodyfit_project(
                artifacts["character_project"],
                "Save Headshot project-seed BodyFit Pilot",
            )

            mark(index, preset_id, "run_dynamic_pose_gate")
            checked("Load dynamic Pilot face camera", RLPy.RFileIO.LoadFile(camera_path))
            dynamic_report = render_profile_upgrade_pose_matrix(
                avatar,
                dynamic_dir,
                lambda phase, detail=None: mark(index, preset_id, phase, detail),
                RLPy.RGlobal.GetStartTime(),
                face_position,
            )
            restore_avatar_transform(avatar, assembled_transform)

            mark(index, preset_id, "reload_saved_project")
            reloaded_avatar, reload_status = load_project(
                project_record, "Reload Headshot project-seed Pilot project"
            )
            reloaded_vectors = capture_vectors(reloaded_avatar)
            (
                reloaded_eye,
                reloaded_eye_stabilization,
            ) = capture_stable_neutral_eye_state(reloaded_avatar)
            reloaded_material = avatar_material_fingerprint(reloaded_avatar)
            write_json(reloaded_vectors, artifacts["reloaded_vectors"])
            reloaded_face_component = reloaded_avatar.GetFaceComponent()
            reloaded_uid = str(reloaded_face_component.GetExpressionSetUid())
            reloaded_expression_count = len(
                list(reloaded_face_component.GetExpressionNames("") or [])
            )
            reload_delta = {
                classification: group_delta(
                    final_vectors["groups"][classification]["entries"],
                    reloaded_vectors["groups"][classification]["entries"],
                )
                for classification in ("body", "junction", "face", "other")
            }
            if any(reload_delta.values()):
                raise ReconstructionError("Saved Pilot project did not preserve Morphs")
            if reloaded_uid != expression_uid or reloaded_expression_count != expression_count:
                raise ReconstructionError("Saved Pilot project did not preserve Facial Profile")
            reload_eye_comparison = compare_neutral_eye_states(
                final_eye,
                reloaded_eye,
                include_runtime_ids=False,
                t_pose_tolerance=0.5,
            )
            if not reload_eye_comparison["matches"]:
                raise ReconstructionError(
                    "Saved Pilot project did not preserve eye state: {}".format(
                        reload_eye_comparison["differences"]
                    )
                )
            if final_material["digest"] != reloaded_material["digest"]:
                raise ReconstructionError("Saved Pilot project did not preserve materials")
            reloaded_transform = capture_avatar_transform(reloaded_avatar)
            checked("Reload Pilot Lightroom", RLPy.RFileIO.LoadFile(lightroom_path))
            render_face_view(
                reloaded_avatar,
                camera_path,
                face_position,
                90.0,
                artifacts["reloaded_neutral_front"],
            )
            restore_avatar_transform(reloaded_avatar, reloaded_transform)

            record.update(
                {
                    "assembly": {
                        "body_application": body_application,
                        "body_face_delta": body_face_delta,
                        "controlled_morphs": final_controlled,
                        "head_application": head_application,
                        "profile_delta": profile_delta,
                        "proportion_application": proportion_application,
                    },
                    "bodyfit_reference": {
                        "camera": bodyfit_full_body_capture["camera"],
                        "lighting": bodyfit_full_body_capture["lighting"],
                        "load": bodyfit_load,
                        "motion_cleanup": bodyfit_motion_cleanup,
                        "project": bodyfit_record,
                    },
                    "dynamic_pose_gate": {
                        "evidence_liveness": dynamic_report["evidence_liveness"],
                        "expression_count": dynamic_report["expression_count"],
                        "expression_set_uid": dynamic_report["expression_set_uid"],
                        "neutral_eye_integrity": dynamic_report["neutral_eye_integrity"],
                        "pose_count": len(dynamic_report["poses"]),
                        "report_path": os.path.join(
                            dynamic_dir, "facial_pose_validation.json"
                        ),
                    },
                    "final": {
                        "bounds": final_bounds,
                        "eye_structure_preserved": True,
                        "eye_stabilization": final_eye_stabilization,
                        "material_preserved": True,
                    },
                    "identity_source": {
                        "bounds": identity_bounds,
                        "load": identity_load,
                        "motion_cleanup": identity_motion_cleanup,
                        "project": identity_record,
                        "prototype_manifest": prototype_record,
                    },
                    "reload": {
                        "expression_count": reloaded_expression_count,
                        "expression_set_uid": reloaded_uid,
                        "load": reload_status,
                        "morph_delta": reload_delta,
                        "eye_comparison": reload_eye_comparison,
                        "eye_stabilization": reloaded_eye_stabilization,
                        "passed": True,
                    },
                    "rendering": {
                        "assembled_full_body_camera": (
                            assembled_full_body_capture["camera"]
                        ),
                        "assembled_full_body_lighting": (
                            assembled_full_body_capture["lighting"]
                        ),
                        "face_camera": camera_path,
                        "face_position": face_position,
                        "full_body_position": full_body_position,
                        "lightroom": lightroom_path,
                    },
                    "saved_project": project_record,
                    "source_facial_profile": profile_record,
                    "success": True,
                }
            )
        except Exception as exc:
            record["error"] = {
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "type": type(exc).__name__,
            }
            log("FAILED {}: {}".format(preset_id, exc))
        write_json(record, artifacts["result"])
        results.append(record)
        mark(index, preset_id, "case_complete", {"success": record["success"]})
        QtWidgets.QApplication.processEvents()
        if inter_case_delay and index < len(selected_ids):
            settle_cc_ui(inter_case_delay)

    failures = [item for item in results if not item["success"]]
    summary_path = os.path.join(output_dir, "validation_result.json")
    summary = {
        "diagnostic_mode": "headshot_project_seed_bodyfit_pilot",
        "failure_count": len(failures),
        "finished_at": now(),
        "library_id": library.get("library_id"),
        "library_case_count": len(all_presets),
        "pilot_policy": policy,
        "requested_count": len(selected_ids),
        "results": results,
        "scene_policy": "leave_last_saved_pilot_project_reloaded",
        "schema_version": 1,
        "selection_mode": selection_mode,
        "started_at": started_at,
        "started_from_library": library_path,
        "success": not failures and len(results) == len(selected_ids),
        "success_count": len(results) - len(failures),
        "summary_path": summary_path,
    }
    write_json(summary, summary_path)
    mark(len(selected_ids), None, "completed", {"success": summary["success"]})
    return summary


def _outfit_gate_verified_file(record, label, cache):
    if not isinstance(record, dict):
        raise ReconstructionError("{} must be a file record".format(label))
    path = canonical_existing_file(record.get("path"), label)
    expected_size = record.get("size_bytes")
    expected_sha256 = record.get("sha256")
    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or expected_size <= 0
    ):
        raise ReconstructionError("{} has no valid size_bytes".format(label))
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
    ):
        raise ReconstructionError("{} has no valid SHA-256".format(label))
    actual_size = os.path.getsize(path)
    if actual_size != expected_size:
        raise ReconstructionError(
            "{} size changed: expected {}, found {}".format(
                label,
                expected_size,
                actual_size,
            )
        )
    cache_key = (path, actual_size, expected_sha256)
    actual_sha256 = cache.get(cache_key)
    if actual_sha256 is None:
        actual_sha256 = sha256_file(path)
        cache[cache_key] = actual_sha256
    if actual_sha256 != expected_sha256:
        raise ReconstructionError("{} SHA-256 changed".format(label))
    return {
        "bytes": actual_size,
        "path": path,
        "sha256": actual_sha256,
    }


def _outfit_gate_inventory_changes(before, after):
    before_by_id = dict(
        (item["id"], item) for item in before.get("objects", [])
    )
    after_by_id = dict(
        (item["id"], item) for item in after.get("objects", [])
    )
    before_ids = set(before_by_id)
    after_ids = set(after_by_id)
    changed_ids = sorted(
        item_id
        for item_id in before_ids & after_ids
        if before_by_id[item_id] != after_by_id[item_id]
    )
    return {
        "added": [after_by_id[item_id] for item_id in sorted(after_ids - before_ids)],
        "removed": [before_by_id[item_id] for item_id in sorted(before_ids - after_ids)],
        "changed": [
            {
                "before": before_by_id[item_id],
                "after": after_by_id[item_id],
            }
            for item_id in changed_ids
        ],
    }


def _outfit_gate_inventory_signature(inventory):
    return sorted(
        [
            {
                "collection": item.get("collection"),
                "name": item.get("name"),
                "python_type": item.get("python_type"),
            }
            for item in inventory.get("objects", [])
        ],
        key=lambda item: (
            str(item.get("collection")),
            str(item.get("name")),
            str(item.get("python_type")),
        ),
    )


def _outfit_gate_image_record(path):
    from PySide2 import QtGui

    image = QtGui.QImage(path)
    if image.isNull():
        raise ReconstructionError(
            "Outfit gate rendered an unreadable image: {}".format(path)
        )
    if (
        image.width() != VIEWPORT_PREVIEW_WIDTH
        or image.height() != VIEWPORT_PREVIEW_HEIGHT
    ):
        raise ReconstructionError(
            "Outfit gate image dimensions changed: {}x{}".format(
                image.width(),
                image.height(),
            )
        )
    if os.path.getsize(path) < 4096:
        raise ReconstructionError(
            "Outfit gate rendered an implausibly small image: {}".format(path)
        )
    return {
        "bytes": os.path.getsize(path),
        "height": image.height(),
        "path": path,
        "sha256": sha256_file(path),
        "width": image.width(),
    }


def _outfit_gate_bounds_center_error(
    before_center,
    after_center,
    source_position,
    target_position,
    target_center,
    bounds_space=None,
):
    intended_shift = float(target_position) - float(source_position)
    observed_shift = float(after_center) - float(before_center)
    if bounds_space is None:
        tolerance = max(1.0, abs(intended_shift) * 0.05)
        bounds_space = (
            "world_space"
            if abs(observed_shift - intended_shift) <= tolerance
            else "object_space"
        )
    if bounds_space == "world_space":
        error = float(after_center) - float(target_center)
    elif bounds_space == "object_space":
        error = (
            float(after_center)
            + float(target_position)
            - float(target_center)
        )
    else:
        raise ValueError("Unsupported bounds space: {}".format(bounds_space))
    return {
        "bounds_space": bounds_space,
        "center_error": error,
        "intended_shift": intended_shift,
        "observed_shift": observed_shift,
    }


def _outfit_gate_frame_full_body(avatar, camera, yaw_degrees=90.0):
    if camera is None:
        raise ReconstructionError("Outfit gate has no active camera")
    set_avatar_yaw(avatar, yaw_degrees)
    force_avatar_scene_evaluation(avatar)
    before_bounds = capture_bounds(avatar)
    current_position = {
        "x": _transform_float(avatar, "Position/PositionX"),
        "y": _transform_float(avatar, "Position/PositionY"),
        "z": _transform_float(avatar, "Position/PositionZ"),
    }
    camera_record = camera_state(camera)
    camera_position = (
        (camera_record or {})
        .get("world_transform", {})
        .get("translation")
    )
    if not isinstance(camera_position, dict) or any(
        axis not in camera_position for axis in ("x", "y", "z")
    ):
        raise ReconstructionError(
            "Outfit gate camera has no readable world translation"
        )
    camera_position = dict(
        (axis, float(camera_position[axis]))
        for axis in ("x", "y", "z")
    )
    height = (
        before_bounds["maximum"][2]
        - before_bounds["minimum"][2]
    )
    width = (
        before_bounds["maximum"][1]
        - before_bounds["minimum"][1]
    )
    if height <= 0.0 or width <= 0.0:
        raise ReconstructionError(
            "Outfit gate received invalid avatar bounds"
        )
    framing_scale = max(height / 185.0, width / 190.0, 0.80)
    framing_scale = min(framing_scale, 1.50)
    camera_distance = 715.0 * framing_scale
    target_center = {
        "z": camera_position["z"] - 16.5,
    }
    target_position = {
        "x": camera_position["x"] - camera_distance,
        "y": 8.0,
        "z": target_center["z"] - before_bounds["center"][2],
    }
    center_corrections = []
    bounds_space = None
    for attempt in range(1, 4):
        set_avatar_position(
            avatar,
            position_x=target_position["x"],
            position_y=target_position["y"],
            position_z=target_position["z"],
        )
        force_avatar_scene_evaluation(avatar)
        after_bounds = capture_bounds(avatar)
        center_measurement = _outfit_gate_bounds_center_error(
            before_bounds["center"][2],
            after_bounds["center"][2],
            current_position["z"],
            target_position["z"],
            target_center["z"],
            bounds_space=bounds_space,
        )
        bounds_space = center_measurement["bounds_space"]
        center_error = {
            "z": center_measurement["center_error"],
        }
        center_corrections.append(
            {
                "attempt": attempt,
                "bounds_space": bounds_space,
                "center_error": dict(center_error),
                "intended_shift": center_measurement["intended_shift"],
                "observed_shift": center_measurement["observed_shift"],
                "target_position": dict(target_position),
            }
        )
        if abs(center_error["z"]) <= 1.0:
            break
        target_position["z"] -= center_error["z"]
    else:
        raise ReconstructionError(
            "Outfit gate could not center the avatar after three "
            "corrections: {}".format(center_error)
        )
    return {
        "after_bounds": after_bounds,
        "before_bounds": before_bounds,
        "camera_distance": camera_distance,
        "camera_position": camera_position,
        "bounds_space": bounds_space,
        "center_error": center_error,
        "center_corrections": center_corrections,
        "framing_scale": framing_scale,
        "height": height,
        "yaw_degrees": float(yaw_degrees),
        "source_position": current_position,
        "target_center": target_center,
        "target_position": target_position,
        "width": width,
    }


def _outfit_gate_directory_state(path):
    if not os.path.isdir(path):
        raise ReconstructionError(
            "Expected outfit export directory is missing: {}".format(path)
        )
    files = []
    total_bytes = 0
    for root, _directories, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            size = os.path.getsize(file_path)
            files.append(os.path.relpath(file_path, path))
            total_bytes += size
    if not files:
        raise ReconstructionError(
            "Expected outfit export directory is empty: {}".format(path)
        )
    return {
        "file_count": len(files),
        "path": path,
        "sample_files": sorted(files)[:20],
        "total_bytes": total_bytes,
    }


def _outfit_gate_optional_directory_state(path):
    if not os.path.isdir(path):
        return {
            "file_count": 0,
            "path": path,
            "present": False,
            "sample_files": [],
            "total_bytes": 0,
        }
    state = _outfit_gate_directory_state(path)
    state["present"] = True
    return state


def _outfit_gate_export_reference_character(
    avatar,
    export_root,
    export_basename,
    diagnostic_output_dir,
    timeout_seconds,
):
    if os.path.exists(export_root):
        raise ReconstructionError(
            "First-batch export root already exists: {}".format(export_root)
        )
    attempt_root = "{}.partial_{}_{}".format(
        export_root,
        os.getpid(),
        int(time.time() * 1000),
    )
    os.makedirs(attempt_root, exist_ok=False)
    fbx_path = os.path.join(attempt_root, export_basename + ".fbx")
    json_path = os.path.join(attempt_root, export_basename + ".json")

    export_option = RLPy.EExportFbxOptions__None
    export_option |= RLPy.EExportFbxOptions_AutoSkinRigidMesh
    export_option |= RLPy.EExportFbxOptions_TPoseForCreateMorphTargetMesh
    export_option2 = RLPy.EExportFbxOptions2__None
    export_option2 |= RLPy.EExportFbxOptions2_UnrealEngine4BoneAxis
    export_option2 |= RLPy.EExportFbxOptions2_UnrealPreset
    export_option2 |= RLPy.EExportFbxOptions2_UnrealIkBone
    export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateBoneName
    export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMaterialName
    export_option2 |= RLPy.EExportFbxOptions2_RenameDuplicateMorphName
    export_option2 |= RLPy.EExportFbxOptions2_RenameTransparencyWithPostFix
    export_option2 |= RLPy.EExportFbxOptions2_RenameBoneRootToGameType
    export_option2 |= RLPy.EExportFbxOptions2_RenameBoneToLowerCase
    export_option2 |= RLPy.EExportFbxOptions2_RenameBoneOnStd
    export_option2 |= RLPy.EExportFbxOptions2_RenameMorphInvalidCharacter
    export_option2 |= RLPy.EExportFbxOptions2_ResetBoneScale
    export_option2 |= RLPy.EExportFbxOptions2_ResetSelfillumination
    export_option2 |= RLPy.EExportFbxOptions2_ExtraWordForUnityAndUnreal
    export_option3 = RLPy.EExportFbxOptions3__None
    export_option3 |= RLPy.EExportFbxOptions3_ExportJson

    setting = RLPy.RExportFbxSetting()
    checked(
        "Disable first-batch reference motion export",
        setting.EnableExportMotion(False),
    )
    checked(
        "Set first-batch reference primary options",
        setting.SetOption(export_option),
    )
    checked(
        "Set first-batch reference Unreal options",
        setting.SetOption2(export_option2),
    )
    checked(
        "Enable first-batch Auto Setup JSON",
        setting.SetOption3(export_option3),
    )
    checked(
        "Set first-batch reference texture size",
        setting.SetTextureSize(RLPy.EExportTextureSize_Original),
    )
    checked(
        "Set first-batch reference texture format",
        setting.SetTextureFormat(RLPy.EExportTextureFormat_Default),
    )
    checked(
        "Set first-batch reference UE5 bone structure",
        setting.SetUnrealBoneStructure(
            RLPy.EUnrealBoneStructure_UE5_BoneStructure
        ),
    )
    checked(
        "Disable first-batch reference basic bind pose",
        setting.EnableBasicBindPose(False),
    )
    RLPy.RScene.SelectObject(avatar)
    license_status = checked(
        "Check first-batch reference export license",
        RLPy.RFileIO.CheckExportFbxHasLicense(avatar),
    )
    raise_if_fatal_cc_dialog(diagnostic_output_dir)
    status = checked(
        "Export first-batch FullReference character",
        RLPy.RFileIO.ExportFbxFile(avatar, fbx_path, setting),
    )
    raise_if_fatal_cc_dialog(diagnostic_output_dir)
    fbx_state = wait_for_rendered_preview(
        fbx_path,
        timeout_seconds=timeout_seconds,
        stable_seconds=1.0,
    )
    json_state = wait_for_rendered_preview(
        json_path,
        timeout_seconds=timeout_seconds,
        stable_seconds=0.5,
    )
    os.replace(attempt_root, export_root)
    fbx_path = os.path.join(export_root, export_basename + ".fbx")
    json_path = os.path.join(export_root, export_basename + ".json")
    return {
        "fbx": {
            "bytes": fbx_state["bytes"],
            "path": fbx_path,
            "sha256": sha256_file(fbx_path),
        },
        "fbm": _outfit_gate_directory_state(
            os.path.join(export_root, export_basename + ".fbm")
        ),
        "json": {
            "bytes": json_state["bytes"],
            "path": json_path,
            "sha256": sha256_file(json_path),
        },
        "license_status": license_status,
        "options": {
            "auto_skin_rigid_mesh": True,
            "export_json": True,
            "motion": False,
            "option": int(export_option),
            "option2": int(export_option2),
            "option3": int(export_option3),
            "unreal_bone_structure": "UE5",
        },
        "status": status,
        # CC creates this directory only when exported assets reference
        # auxiliary files such as cloth-physics weight maps.
        "textures": _outfit_gate_optional_directory_state(
            os.path.join(export_root, "textures")
        ),
    }


def _outfit_gate_case(
    preset,
    case_dir,
    camera_path,
    lightroom_path,
    execution_policy,
    verified_file_cache,
    log,
    diagnostic_mode="outfit_compatibility_gate",
):
    os.makedirs(case_dir, exist_ok=False)
    images_dir = os.path.join(case_dir, "images")
    os.makedirs(images_dir, exist_ok=False)
    result_path = os.path.join(case_dir, "result.json")
    progress_path = os.path.join(case_dir, "progress.json")
    result = {
        "bodyfit_id": preset.get("bodyfit_id"),
        "case_id": preset.get("case_id"),
        "diagnostic_mode": diagnostic_mode,
        "error": None,
        "finished_at": None,
        "look_id": preset.get("look_id"),
        "preset_id": preset.get("preset_id"),
        "result_path": result_path,
        "schema_version": 1,
        "sex": preset.get("sex"),
        "started_at": now(),
        "subject_id": preset.get("subject_id"),
        "success": False,
    }
    write_json(result, result_path)

    def mark(phase, detail=None):
        write_json(
            {
                "detail": detail,
                "phase": phase,
                "preset_id": preset.get("preset_id"),
                "schema_version": 1,
                "updated_at": now(),
            },
            progress_path,
        )
        log("Outfit gate {}: {}".format(preset.get("preset_id"), phase))
        QtWidgets.QApplication.processEvents()

    try:
        preset_id = preset.get("preset_id")
        if not isinstance(preset_id, str) or not preset_id:
            raise ReconstructionError("Outfit gate case has no preset_id")
        source_record = _outfit_gate_verified_file(
            preset.get("source_project"),
            "Outfit gate source project {}".format(preset_id),
            verified_file_cache,
        )
        selected_assets = preset.get("selected_assets")
        if not isinstance(selected_assets, list) or not selected_assets:
            raise ReconstructionError(
                "Outfit gate case has no selected assets: {}".format(
                    preset_id
                )
            )
        capture_views = preset.get("capture_views")
        if not isinstance(capture_views, list) or not capture_views:
            raise ReconstructionError(
                "Outfit gate case has no capture views: {}".format(
                    preset_id
                )
            )
        view_ids = [item.get("view_id") for item in capture_views]
        if (
            len(view_ids) != len(set(view_ids))
            or any(not isinstance(item, str) or not item for item in view_ids)
        ):
            raise ReconstructionError(
                "Outfit gate capture view IDs are invalid"
            )

        mark("load_source_project", {"path": source_record["path"]})
        source_status, source_dialogs = load_file_with_optional_undo_warning(
            source_record["path"],
            "Load outfit gate source project {}".format(preset_id),
        )
        settle_cc_ui(
            float(
                execution_policy.get(
                    "project_load_settle_seconds",
                    20.0,
                )
            )
        )
        avatar, avatars = resolve_avatar()
        if len(avatars) != 1:
            raise ReconstructionError(
                "Outfit gate expected one avatar, found {}".format(
                    len(avatars)
                )
            )
        avatar_id = scene_object_id(avatar)
        RLPy.RScene.SelectObject(avatar)
        result["source_project"] = source_record
        result["source_load"] = {
            "dialogs": source_dialogs,
            "status": source_status,
        }

        mark("clear_motion")
        result["motion_cleanup"] = clear_avatar_motion(avatar)
        force_avatar_scene_evaluation(avatar)
        source_inventory = avatar_asset_inventory(avatar)
        source_hairs = [
            item
            for item in source_inventory["objects"]
            if item["collection"] == "GetHairs"
        ]

        mark("remove_existing_clothing")
        clothing_names = sorted(
            set(
                scene_object_name(item)
                for item in list(avatar.GetClothes() or [])
            )
        )
        avatar, cleanup = remove_base_clothing(
            avatar,
            clothing_names,
            allow_missing=False,
        )
        result["clothing_cleanup"] = cleanup
        if scene_object_id(avatar) != avatar_id:
            raise ReconstructionError(
                "Avatar identity changed during outfit cleanup"
            )

        remove_source_accessories = bool(
            execution_policy.get("remove_source_accessories", True)
        )
        mark(
            "remove_source_accessories",
            {"enabled": remove_source_accessories},
        )
        if remove_source_accessories:
            avatar, accessory_cleanup = (
                remove_source_accessories_for_outfit_gate(avatar)
            )
        else:
            accessory_inventory = avatar_asset_inventory(avatar)
            accessory_cleanup = {
                "before_inventory": accessory_inventory,
                "after_inventory": accessory_inventory,
                "removed_objects": [],
            }
        accessory_cleanup["enabled"] = remove_source_accessories
        result["source_accessory_cleanup"] = accessory_cleanup
        if scene_object_id(avatar) != avatar_id:
            raise ReconstructionError(
                "Avatar identity changed during source accessory cleanup"
            )

        result["asset_applications"] = []
        applied_asset_object_owners = {}
        static_application_evidence = preset.get(
            "source_static_application_order"
        ) or {}
        allowed_required_asset_replacements = (
            static_application_evidence.get(
                "allowed_required_asset_replacements"
            )
            or []
        )
        record_asset_load_undo = execution_policy.get(
            "record_asset_load_undo",
            True,
        )
        if not isinstance(record_asset_load_undo, bool):
            raise ReconstructionError(
                "Outfit gate record_asset_load_undo must be a boolean"
            )
        for asset_index, asset in enumerate(selected_assets, 1):
            if not isinstance(asset, dict):
                raise ReconstructionError(
                    "Outfit gate selected asset must be an object"
                )
            asset_id = asset.get("asset_id")
            slot = asset.get("slot")
            policy = asset.get("cloth_options_policy")
            if not isinstance(asset_id, str) or not asset_id:
                raise ReconstructionError(
                    "Outfit gate selected asset has no asset_id"
                )
            if policy not in APPLY_CLOTH_OPTIONS_POLICIES:
                raise ReconstructionError(
                    "Outfit gate asset has invalid cloth policy: {}".format(
                        asset_id
                    )
                )
            file_record = _outfit_gate_verified_file(
                asset,
                "Outfit gate asset {}".format(asset_id),
                verified_file_cache,
            )
            load_mode = asset.get(
                "load_mode",
                execution_policy.get("asset_load_mode", "file"),
            )
            if load_mode not in ("file", "object"):
                raise ReconstructionError(
                    "Outfit gate asset has invalid load mode: {}".format(
                        asset_id
                    )
                )
            before = avatar_asset_inventory(avatar)
            before_seconds = float(
                execution_policy.get("asset_load_before_seconds", 1.5)
            )
            after_seconds = float(
                execution_policy.get("asset_load_after_seconds", 4.0)
            )
            if slot == "coats":
                after_seconds = float(
                    execution_policy.get(
                        "coats_load_after_seconds",
                        after_seconds,
                    )
                )
            mark(
                "apply_asset",
                {
                    "asset_count": len(selected_assets),
                    "asset_id": asset_id,
                    "asset_index": asset_index,
                    "slot": slot,
                },
            )
            settle_cc_ui(before_seconds)
            selected_before_reset = [
                {
                    "id": scene_object_id(item),
                    "name": scene_object_name(item),
                    "python_type": type(item).__name__,
                }
                for item in list(RLPy.RScene.GetSelectedObjects() or [])
            ]
            clear_selection_status = checked(
                "Clear selection before outfit asset load",
                RLPy.RScene.ClearSelectObjects(),
            )
            select_avatar_status = checked(
                "Select avatar before outfit asset load",
                RLPy.RScene.SelectObject(avatar),
            )
            selected_after_reset = [
                {
                    "id": scene_object_id(item),
                    "name": scene_object_name(item),
                    "python_type": type(item).__name__,
                }
                for item in list(RLPy.RScene.GetSelectedObjects() or [])
            ]
            status, dialogs = load_clothing_asset_with_known_dialogs(
                file_record["path"],
                "Apply outfit gate asset {}".format(asset_id),
                policy,
                record_step=record_asset_load_undo,
                load_mode=load_mode,
            )
            settle_cc_ui(after_seconds)
            current_avatar, current_avatars = resolve_avatar()
            if len(current_avatars) != 1:
                raise ReconstructionError(
                    "Outfit asset load changed avatar count"
                )
            if scene_object_id(current_avatar) != avatar_id:
                raise ReconstructionError(
                    "Outfit asset load changed avatar identity"
                )
            avatar = current_avatar
            after = avatar_asset_inventory(avatar)
            changes = _outfit_gate_inventory_changes(before, after)
            if not any(changes.values()):
                raise ReconstructionError(
                    "Outfit asset produced no scene inventory change: {}"
                    .format(asset_id)
                )
            removed_previously_applied_assets = []
            for removed in changes["removed"]:
                owner = applied_asset_object_owners.get(removed["id"])
                if owner is not None:
                    removed_previously_applied_assets.append(
                        {
                            "object": removed,
                            "owner_asset_id": owner["asset_id"],
                            "owner_slot": owner["slot"],
                        }
                    )
            application_record = {
                "asset": file_record,
                "asset_id": asset_id,
                "cloth_options_policy": policy,
                "dialogs": dialogs,
                "inventory_after": after,
                "inventory_before": before,
                "inventory_changes": changes,
                "removed_previously_applied_assets": (
                    removed_previously_applied_assets
                ),
                "allowed_required_asset_replacements": [],
                "selection_reset": {
                    "clear_status": clear_selection_status,
                    "select_avatar_status": select_avatar_status,
                    "selected_after": selected_after_reset,
                    "selected_before": selected_before_reset,
                },
                "slot": slot,
                "status": status,
            }
            result["asset_applications"].append(application_record)
            if removed_previously_applied_assets:
                unexpected_replacements = []
                for replacement in removed_previously_applied_assets:
                    observed = {
                        "removing_asset_id": asset_id,
                        "removed_owner_asset_id": replacement[
                            "owner_asset_id"
                        ],
                        "removed_owner_slot": replacement["owner_slot"],
                        "object_collection": replacement["object"].get(
                            "collection"
                        ),
                        "object_name": replacement["object"].get("name"),
                    }
                    if observed in allowed_required_asset_replacements:
                        application_record[
                            "allowed_required_asset_replacements"
                        ].append(observed)
                    else:
                        unexpected_replacements.append(replacement)
                if unexpected_replacements:
                    raise ReconstructionError(
                        "Outfit asset {} in slot {} removed a previously "
                        "applied required asset outside frozen static "
                        "evidence: {}".format(
                            asset_id,
                            slot,
                            unexpected_replacements,
                        )
                    )
            for added in changes["added"]:
                applied_asset_object_owners[added["id"]] = {
                    "asset_id": asset_id,
                    "slot": slot,
                }

        assembled_inventory = avatar_asset_inventory(avatar)
        assembled_hairs = [
            item
            for item in assembled_inventory["objects"]
            if item["collection"] == "GetHairs"
        ]
        result["preserved_source_hair"] = assembled_hairs == source_hairs
        if not result["preserved_source_hair"]:
            raise ReconstructionError(
                "Outfit assembly changed the source scalp-hair inventory"
            )
        result["assembled_inventory"] = assembled_inventory
        expected_assembled_inventory = static_application_evidence.get(
            "expected_assembled_inventory"
        )
        if expected_assembled_inventory is not None:
            actual_inventory_signature = _outfit_gate_inventory_signature(
                assembled_inventory
            )
            result["static_inventory_comparison"] = {
                "actual": actual_inventory_signature,
                "expected": expected_assembled_inventory,
                "matches": (
                    actual_inventory_signature
                    == expected_assembled_inventory
                ),
            }
            if actual_inventory_signature != expected_assembled_inventory:
                raise ReconstructionError(
                    "Final outfit inventory differs from frozen static "
                    "evidence"
                )

        production_output = preset.get("production_output")
        if production_output is not None:
            if not isinstance(production_output, dict):
                raise ReconstructionError(
                    "Outfit gate production_output must be an object"
                )
            project_path = os.path.realpath(
                os.path.abspath(production_output.get("project_path", ""))
            )
            export_root = os.path.realpath(
                os.path.abspath(production_output.get("export_root", ""))
            )
            export_basename = production_output.get("export_basename")
            if not project_path.lower().endswith(".ccproject"):
                raise ReconstructionError(
                    "First-batch project_path must end in .ccProject"
                )
            if (
                not isinstance(export_basename, str)
                or not export_basename
                or os.path.basename(export_basename) != export_basename
            ):
                raise ReconstructionError(
                    "First-batch export_basename is invalid"
                )
            if os.path.exists(project_path):
                raise ReconstructionError(
                    "First-batch project already exists: {}".format(
                        project_path
                    )
                )
            timeout_seconds = float(
                production_output.get("export_timeout_seconds", 900.0)
            )
            if timeout_seconds < 30.0 or timeout_seconds > 3600.0:
                raise ReconstructionError(
                    "First-batch export timeout must be from 30 to 3600 seconds"
                )
            os.makedirs(os.path.dirname(project_path), exist_ok=True)
            mark("save_production_project", {"path": project_path})
            result["production_project"] = save_bodyfit_project(
                project_path,
                "Save first-batch assembled Look",
            )
            set_avatar_yaw(avatar, 90.0)
            force_avatar_scene_evaluation(avatar, settle_seconds=0.5)
            mark(
                "export_production_reference",
                {
                    "export_basename": export_basename,
                    "export_root": export_root,
                },
            )
            result["production_export"] = (
                _outfit_gate_export_reference_character(
                    avatar,
                    export_root,
                    export_basename,
                    case_dir,
                    timeout_seconds,
                )
            )
            skip_preview_capture = production_output.get(
                "skip_preview_capture",
                False,
            )
            if not isinstance(skip_preview_capture, bool):
                raise ReconstructionError(
                    "First-batch skip_preview_capture must be boolean"
                )
            if skip_preview_capture:
                result["captures"] = []
                result["motion_capture_count"] = 0
                result["motion_stress_validations"] = []
                result["finished_at"] = now()
                result["success"] = True
                mark(
                    "complete",
                    {
                        "preview_capture_skipped": True,
                        "success": True,
                    },
                )
                write_json(result, result_path)
                return result

        mark("load_standard_lightroom")
        lightroom_status, lightroom_dialogs = (
            load_file_with_optional_undo_warning(
                lightroom_path,
                "Load outfit gate Lightroom",
            )
        )
        settle_cc_ui(1.0)
        movable_lights, skipped_lights, light_query_errors = (
            quality_benchmark_movable_lights()
        )
        if not movable_lights:
            raise ReconstructionError(
                "Outfit gate found no movable Lightroom lights: {}".format(
                    light_query_errors + skipped_lights
                )
            )

        mark("load_standard_camera")
        camera_status, camera_dialogs = load_file_with_optional_undo_warning(
            camera_path,
            "Load outfit gate full-body camera",
        )
        settle_cc_ui(1.0)
        camera = RLPy.RScene.GetCurrentCamera()
        if camera is None:
            raise ReconstructionError(
                "Outfit gate full-body camera is unavailable"
            )
        framing = _outfit_gate_frame_full_body(avatar, camera)
        reference_position = {"x": 0.0, "y": 8.0, "z": 6.0}
        light_offset = {
            axis: framing["target_position"][axis]
            - reference_position[axis]
            for axis in ("x", "y", "z")
        }
        set_quality_benchmark_light_offset(movable_lights, light_offset)
        result["capture_setup"] = {
            "camera": camera_state(camera),
            "camera_dialogs": camera_dialogs,
            "camera_status": camera_status,
            "framing": framing,
            "lighting": {
                "light_offset": light_offset,
                "movable_light_count": len(movable_lights),
                "query_errors": light_query_errors,
                "skipped_lights": skipped_lights,
            },
            "lightroom_dialogs": lightroom_dialogs,
            "lightroom_status": lightroom_status,
        }

        result["captures"] = []
        for view in capture_views:
            yaw_offset = view.get("yaw_degrees")
            if (
                isinstance(yaw_offset, bool)
                or not isinstance(yaw_offset, (int, float))
                or not math.isfinite(float(yaw_offset))
            ):
                raise ReconstructionError(
                    "Outfit gate view has invalid yaw"
                )
            view_id = view["view_id"]
            actual_yaw = 90.0 + float(yaw_offset)
            mark(
                "render_view",
                {"actual_yaw": actual_yaw, "view_id": view_id},
            )
            set_avatar_yaw(avatar, actual_yaw)
            force_avatar_scene_evaluation(avatar, settle_seconds=0.5)
            checked(
                "Activate outfit gate camera",
                RLPy.RScene.SetCurrentCamera(camera),
            )
            image_path = os.path.join(images_dir, view_id + ".png")
            render_preview(image_path)
            result["captures"].append(
                {
                    "actual_yaw_degrees": actual_yaw,
                    "avatar_bounds": capture_bounds(avatar),
                    "image": _outfit_gate_image_record(image_path),
                    "requested_yaw_degrees": float(yaw_offset),
                    "view_id": view_id,
                }
            )

        motion_stress_profiles = preset.get("motion_stress_profiles") or []
        if diagnostic_mode == "outfit_motion_stress_gate":
            if not isinstance(motion_stress_profiles, list) or not motion_stress_profiles:
                raise ReconstructionError(
                    "Outfit motion-stress case has no motion profiles"
                )
        elif motion_stress_profiles:
            raise ReconstructionError(
                "Static outfit gate cannot contain motion-stress profiles"
            )
        result["motion_stress_validations"] = []
        seen_motion_profile_ids = set()
        for motion_index, motion_profile in enumerate(
            motion_stress_profiles,
            1,
        ):
            if not isinstance(motion_profile, dict):
                raise ReconstructionError(
                    "Outfit motion-stress profile must be an object"
                )
            profile_id = motion_profile.get("profile_id")
            if (
                not isinstance(profile_id, str)
                or not profile_id
                or profile_id in seen_motion_profile_ids
                or os.path.basename(profile_id) != profile_id
            ):
                raise ReconstructionError(
                    "Outfit motion-stress profile ID is invalid"
                )
            seen_motion_profile_ids.add(profile_id)
            motion_record = _outfit_gate_verified_file(
                motion_profile.get("motion"),
                "Outfit motion-stress profile {}".format(profile_id),
                verified_file_cache,
            )
            probe = dict(motion_profile)
            probe.pop("motion", None)
            probe.pop("profile_id", None)
            probe["motion_path"] = motion_record["path"]
            probe["camera_path"] = camera_path
            probe["subject_position"] = dict(framing["target_position"])
            motion_dir = os.path.join(
                case_dir,
                "motion_stress",
                profile_id,
            )
            mark(
                "motion_stress_profile",
                {
                    "profile_count": len(motion_stress_profiles),
                    "profile_id": profile_id,
                    "profile_index": motion_index,
                },
            )
            motion_summary = probe_current_hair_motion(
                {"hair_motion_probe": probe},
                motion_dir,
            )
            motion_report = read_json(
                motion_summary["hair_motion_probe_path"]
            )
            samples = motion_report.get("samples") or []
            requested_samples = motion_profile.get(
                "sample_normalized_positions"
            )
            if requested_samples is None:
                requested_samples = motion_profile.get("sample_frames") or []
            expected_samples = len(sorted(set(requested_samples)))
            if expected_samples and len(samples) != expected_samples:
                raise ReconstructionError(
                    "Outfit motion-stress sample count changed for {}: "
                    "{} != {}".format(
                        profile_id,
                        len(samples),
                        expected_samples,
                    )
                )
            result["motion_stress_validations"].append(
                {
                    "motion": motion_record,
                    "profile_id": profile_id,
                    "purpose": motion_profile.get("purpose"),
                    "sample_count": len(samples),
                    "samples": samples,
                    "summary": motion_summary,
                }
            )
        result["motion_capture_count"] = sum(
            item["sample_count"]
            for item in result["motion_stress_validations"]
        )

        expected_image_count = int(
            preset.get("expected_image_count", len(capture_views))
        )
        if len(result["captures"]) != expected_image_count:
            raise ReconstructionError(
                "Outfit gate capture count changed"
            )
        result["finished_at"] = now()
        result["success"] = True
        mark("complete", {"success": True})
    except BlockingDialogError as exc:
        result["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "type": type(exc).__name__,
        }
        result["finished_at"] = now()
        write_json(result, result_path)
        mark("blocked_by_unknown_dialog", result["error"])
        raise
    except Exception as exc:
        result["error"] = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "type": type(exc).__name__,
        }
        result["finished_at"] = now()
        mark("failed", result["error"])
    write_json(result, result_path)
    return result


def run_outfit_compatibility_gate(
    library_path,
    library,
    all_presets,
    output_dir,
    log,
    preset_ids=None,
):
    diagnostic_mode = library.get(
        "diagnostic_mode",
        "outfit_compatibility_gate",
    )
    by_id = dict((item.get("preset_id"), item) for item in all_presets)
    selected_ids = list(
        preset_ids or [item.get("preset_id") for item in all_presets]
    )
    if (
        not selected_ids
        or len(selected_ids) != len(set(selected_ids))
        or any(not isinstance(item, str) or not item for item in selected_ids)
    ):
        raise ReconstructionError(
            "Outfit gate preset IDs must be non-empty and unique"
        )
    missing = sorted(set(selected_ids) - set(by_id))
    if missing:
        raise ReconstructionError(
            "Unknown outfit gate preset IDs: {}".format(missing)
        )
    camera_path = canonical_existing_file(
        library.get("full_body_camera"),
        "Outfit gate full-body camera",
    )
    lightroom_path = canonical_existing_file(
        library.get("preview_lightroom"),
        "Outfit gate Lightroom",
    )
    execution_policy = library.get("execution_policy") or {}
    if not isinstance(execution_policy, dict):
        raise ReconstructionError(
            "Outfit gate execution_policy must be an object"
        )
    if execution_policy.get("stop_on_blocking_dialog") is not True:
        raise ReconstructionError(
            "Outfit gate must stop on an unknown blocking dialog"
        )
    if execution_policy.get("checkpoint_after_each_case") is not True:
        raise ReconstructionError(
            "Outfit gate must checkpoint after every case"
        )

    started_at = now()
    cases_root = os.path.join(output_dir, "cases")
    os.makedirs(cases_root, exist_ok=False)
    summary_path = os.path.join(output_dir, "validation_result.json")
    progress_path = os.path.join(output_dir, "progress.json")
    results = []
    verified_file_cache = {}

    def checkpoint(index, preset_id, phase, blocked=False):
        failures = [item for item in results if not item.get("success")]
        result_index = [
            {
                "bodyfit_id": item.get("bodyfit_id"),
                "capture_count": len(item.get("captures") or []),
                "case_id": item.get("case_id"),
                "error": item.get("error"),
                "finished_at": item.get("finished_at"),
                "look_id": item.get("look_id"),
                "motion_capture_count": int(
                    item.get("motion_capture_count", 0)
                ),
                "preset_id": item.get("preset_id"),
                "result_path": item.get("result_path"),
                "sex": item.get("sex"),
                "success": bool(item.get("success")),
            }
            for item in results
        ]
        summary = {
            "blocked": bool(blocked),
            "completed_count": len(results),
            "diagnostic_mode": diagnostic_mode,
            "expected_image_count": sum(
                len(item.get("captures") or []) for item in results
            ),
            "motion_image_count": sum(
                int(item.get("motion_capture_count", 0))
                for item in results
            ),
            "failure_count": len(failures),
            "finished_at": now() if phase in ("complete", "blocked") else None,
            "library_case_count": len(all_presets),
            "library_id": library.get("library_id"),
            "phase": phase,
            "requested_count": len(selected_ids),
            "results": result_index,
            "run_id": os.path.basename(output_dir),
            "schema_version": 1,
            "started_at": started_at,
            "started_from_library": library_path,
            "success": (
                phase == "complete"
                and not failures
                and len(results) == len(selected_ids)
            ),
            "success_count": len(results) - len(failures),
            "summary_path": summary_path,
        }
        write_json(summary, summary_path)
        write_json(
            {
                "blocked": bool(blocked),
                "completed_count": len(results),
                "index": index,
                "phase": phase,
                "preset_count": len(selected_ids),
                "preset_id": preset_id,
                "schema_version": 1,
                "updated_at": now(),
            },
            progress_path,
        )
        return summary

    checkpoint(0, None, "initializing")
    for index, preset_id in enumerate(selected_ids, 1):
        checkpoint(index, preset_id, "case_start")
        preset = by_id[preset_id]
        case_directory_name = preset.get(
            "output_directory_name",
            preset_id,
        )
        if (
            not isinstance(case_directory_name, str)
            or not case_directory_name
            or os.path.basename(case_directory_name)
            != case_directory_name
        ):
            raise ReconstructionError(
                "Outfit gate output directory name is invalid"
            )
        try:
            result = _outfit_gate_case(
                preset,
                os.path.join(cases_root, case_directory_name),
                camera_path,
                lightroom_path,
                execution_policy,
                verified_file_cache,
                log,
                diagnostic_mode,
            )
        except BlockingDialogError:
            checkpoint(index, preset_id, "blocked", blocked=True)
            raise
        results.append(result)
        checkpoint(index, preset_id, "case_complete")
        QtWidgets.QApplication.processEvents()

    return checkpoint(len(selected_ids), None, "complete")


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
    global PREVIEW_CAPTURE_MODE
    global VIEWPORT_PREVIEW_WIDTH
    global VIEWPORT_PREVIEW_HEIGHT
    PREVIEW_CAPTURE_MODE = library.get(
        "preview_capture_mode",
        "render_image",
    )
    if PREVIEW_CAPTURE_MODE not in ("render_image", "pixel_stream"):
        raise ReconstructionError(
            "Unsupported preview_capture_mode: {}".format(
                PREVIEW_CAPTURE_MODE
            )
        )
    preview_resolution = library.get(
        "preview_resolution",
        [
            DEFAULT_VIEWPORT_PREVIEW_WIDTH,
            DEFAULT_VIEWPORT_PREVIEW_HEIGHT,
        ],
    )
    if (
        not isinstance(preview_resolution, list)
        or len(preview_resolution) != 2
        or any(
            isinstance(item, bool) or not isinstance(item, int)
            for item in preview_resolution
        )
        or any(item < 320 or item > 4096 for item in preview_resolution)
    ):
        raise ReconstructionError(
            "preview_resolution must contain two integers from 320 to 4096"
        )
    VIEWPORT_PREVIEW_WIDTH = int(preview_resolution[0])
    VIEWPORT_PREVIEW_HEIGHT = int(preview_resolution[1])
    all_presets = validate_library_document(library)
    if library.get("diagnostic_mode") == "resource_release_probe":
        log("Releasing disposable CC scene and Python/Qt cache resources")
        return probe_resource_release(library, output_dir, log)
    if library.get("diagnostic_mode") == (
        "first_batch_identity_reference_capture"
    ):
        log("Rendering frozen first-batch identity reference portraits")
        return run_first_batch_identity_reference_capture(
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") in (
        "outfit_compatibility_gate",
        "outfit_motion_stress_gate",
    ):
        if library.get("diagnostic_mode") == "outfit_motion_stress_gate":
            log("Running the outfit motion-stress gate")
        else:
            log("Running the full outfit compatibility gate")
        return run_outfit_compatibility_gate(
            library_path,
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == "animation_p0_dynamic_gate":
        log("Running the RM-09 P0 animation dynamic Pilot gate")
        return run_animation_p0_dynamic_gate(
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == "current_scene_bodyfit_freeze":
        log("Capturing or standardizing the current F05 BodyFit scene")
        return probe_current_scene_bodyfit_freeze(
            library,
            output_dir,
            log,
        )
    if library.get("diagnostic_mode") == (
        "targeted_bodyfit_height_matrix"
    ):
        log("Measuring BodyFit heights with targeted Morph reads")
        return run_targeted_bodyfit_height_matrix(
            library_path,
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == "targeted_morph_visual_matrix":
        log("Running the lightweight targeted Morph visual matrix")
        return run_targeted_morph_visual_matrix(
            library_path,
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == (
        "headshot_project_seed_bodyfit_pilot"
    ):
        log("Running the Headshot project-seed plus average BodyFit Pilot")
        return run_headshot_project_seed_bodyfit_pilot(
            library_path,
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == "bodyfit_height_matrix":
        log("Measuring BodyFit world-space heights without rendering")
        return run_bodyfit_height_matrix(
            library_path,
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") in (
        "head_bodyfit_scale_review_matrix",
        "neck_morph_review_matrix",
        "bodyfit_proportion_smoke_matrix",
    ):
        if library.get("diagnostic_mode") == (
            "bodyfit_proportion_smoke_matrix"
        ):
            log("Running the preserved-scene BodyFit proportion smoke matrix")
        elif library.get("diagnostic_mode") == "neck_morph_review_matrix":
            log("Running the preserved-scene Neck Morph review matrix")
        else:
            log("Running the preserved-scene Head Scale review matrix")
        return run_head_bodyfit_scale_review_matrix(
            library_path,
            library,
            all_presets,
            output_dir,
            log,
            preset_ids,
        )
    if library.get("diagnostic_mode") == "source_project_load":
        log("Loading one source project without face or appearance operations")
        return probe_source_project_load(library, output_dir)
    if library.get("diagnostic_mode") == "outfit_component_resave":
        log("Resaving one source outfit component as generic ccCloth")
        return probe_outfit_component_resave(library, output_dir)
    if library.get("diagnostic_mode") == "character_quality_benchmark":
        log("Rendering one matched-condition character quality benchmark")
        return probe_character_quality_benchmark(library, output_dir, log)
    if library.get("diagnostic_mode") == "facial_profile_upgrade":
        log("Creating and validating one derived CC5 HD Facial Profile project")
        return probe_facial_profile_upgrade(library, output_dir, log)
    if library.get("diagnostic_mode") == "facial_profile_api_probe":
        log("Inspecting the current Facial Profile API without changing the scene")
        return probe_current_facial_profile_api(library, output_dir)
    if library.get("diagnostic_mode") == "avatar_preset_save":
        log("Saving and reapplying one AvatarPresetAll pilot")
        return probe_avatar_preset_save(library, output_dir)
    if library.get("diagnostic_mode") == "face_prototype_storage":
        log("Comparing face prototype storage modes on a neutral avatar")
        return probe_face_prototype_storage(library, output_dir)
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
    if library.get("diagnostic_mode") == "head_scale_sweep":
        log("Rendering a reversible Head Scale sweep on the current scene")
        return probe_current_head_scale_sweep(library, output_dir)
    if library.get("diagnostic_mode") == "head_scale_apply":
        log("Applying one selected Head Scale to the current scene")
        return apply_current_head_scale(library, output_dir)
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
    if library.get("diagnostic_mode") == "face_material_parameter_probe":
        log("Reading current eye, tearline, and skin material parameters")
        return probe_current_face_material_parameters(output_dir)
    if library.get("diagnostic_mode") == "face_material_visual_matrix":
        log("Rendering a reversible eye and skin material matrix")
        return probe_current_face_material_visual_matrix(library, output_dir)
    if library.get("diagnostic_mode") == "face_material_cross_skin_matrix":
        log("Rendering the four-subject eye and skin material gate")
        return probe_face_material_cross_skin_matrix(library, output_dir, log)
    if library.get("diagnostic_mode") == "hair_physics_probe":
        log("Capturing current scalp-hair physics state")
        return probe_current_hair_physics(output_dir)
    if library.get("diagnostic_mode") == "hair_motion_probe":
        log("Playing one official motion with scalp-hair physics")
        return probe_current_hair_motion(library, output_dir)
    if library.get("diagnostic_mode") == "rlmotion_fbx_export":
        log("Exporting one rlMotion as a motion-only UE5 FBX")
        return export_current_rlmotion_fbx(library, output_dir)
    if library.get("diagnostic_mode") == "animation_p0_ue_runtime_export":
        log("Exporting clothed P0 references and UE5 animation FBXs")
        return export_animation_p0_ue_runtime_pilot(
            library, output_dir, log
        )
    if library.get("diagnostic_mode") == "elder_morph_export_pilot":
        log("Exporting young and Elder UE5 FBX snapshots from one M02 project")
        return export_elder_morph_pilot(library, output_dir)
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
    undo_guard = ExactUndoWarningGuard(output_dir)
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
