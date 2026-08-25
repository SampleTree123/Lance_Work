"""Build an explicit, reference-checked cleanup plan for First Batch UE assets."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work")
OUTPUT = (
    ROOT
    / "00_engine"
    / "outputs"
    / "unreal_character_import"
    / "first_batch_cleanup_20260824_v1"
    / "cleanup_audit.json"
)

# These are completed diagnostics/reviews, not production inputs.
CANDIDATE_ROOTS = {
    "/Game/DataMake/Animations/CC5/FirstBatchExpressions": "superseded_expression_review",
    "/Game/DataMake/Animations/CC5/P0RuntimePilot": "superseded_p0_runtime_pilot",
    "/Game/DataMake/Animations/CC5/Pilot": "superseded_animation_pilot",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Comparisons": "completed_modular_comparison",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/IdlePaddingCandidates": "temporary_resize_probe",
    "/Game/DataMake/Characters": "completed_character_review_wrappers",
    "/Game/DataMake/Pilots": "completed_elder_morph_pilot",
    "/Game/DataMake/RenderTests": "empty_render_test_placeholder",
    "/Game/DataMake/Sequences/FirstBatch/ActionMatrix": "superseded_action_review_sequences",
    "/Game/DataMake/Sequences/FirstBatch/Validation": "completed_sequence_validation",
}

CANDIDATE_ASSETS = {
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/BodyOnly/A_DM_F04_AUDIENCE_09_BodyOnly_v001": "removed_action_f04",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/IdlePadded/A_DM_F04_AUDIENCE_09_IdlePadded5s_v001": "removed_action_f04",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/BodyOnly/A_DM_M03_AUDIENCE_12_BodyOnly_v001": "removed_action_m03",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/IdlePadded/A_DM_M03_AUDIENCE_12_IdlePadded5s_v001": "removed_action_m03",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/InPlaceCandidates/A_DM_F01_SEXY_DANCE_InPlaceCandidate_v001": "unapproved_inplace_candidate",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/InPlaceCandidates/A_DM_M01_BATTLE_DANCE_InPlaceCandidate_v001": "unapproved_inplace_candidate",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/InPlaceCandidates/A_DM_M04_LIVING_ROOM_SWING_InPlaceCandidate_v001": "unapproved_inplace_candidate",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/Composites/F04/A_DM_F04_AUDIENCE_09_Happy_Composite_v001": "removed_action_f04",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/Composites/F04/A_DM_F04_AUDIENCE_09_Angry_Composite_v001": "removed_action_f04",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Female/Composites/F04/A_DM_F04_AUDIENCE_09_Sad_Composite_v001": "removed_action_f04",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/Composites/M03/A_DM_M03_AUDIENCE_12_Happy_Composite_v001": "removed_action_m03",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/Composites/M03/A_DM_M03_AUDIENCE_12_Angry_Composite_v001": "removed_action_m03",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Male/Composites/M03/A_DM_M03_AUDIENCE_12_Sad_Composite_v001": "removed_action_m03",
    "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Motions/Female/Raw/A_F04_AUDIENCE_09": "removed_action_f04_raw",
    "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Motions/Male/Raw/A_M03_AUDIENCE_12": "removed_action_m03_raw",
    "/Game/DataMake/Sequences/1": "obsolete_sequence",
    "/Game/DataMake/Sequences/FirstBatch/LS_DM_FirstBatch_F02_20s_Pilot_v001": "superseded_pilot_sequence",
    "/Game/DataMake/Sequences/FirstBatch/_TMP_F02_BodyExpression4x_20260823_v001": "temporary_sequence",
    "/Game/DataMake/Sequences/FirstBatch/_TMP_F05_BodyOnly": "temporary_sequence",
    "/Game/DataMake/Sequences/FirstBatch/_TMP_NativeBinding": "temporary_sequence",
    "/Game/DataMake/Sequences/FirstBatch/_TMP_NativeBodyFace4x_20260823_v001": "temporary_sequence",
    "/Game/DataMake/Sequences/FirstBatch/_TMP_NativeSection4x_20260823": "temporary_sequence",
    "/Game/DataMake/Sequences/FirstBatch/_TMP_NativeSection4x_20260823_v002": "temporary_sequence",
    "/Game/DataMake/Render/Presets/MRQ_DM_FirstBatch_720p30_PNG_v001": "superseded_render_preset",
    "/Game/DataMake/Config/Import/DM_CC5_Animation_Pipeline_v001": "superseded_import_pipeline",
    "/Game/DataMake/Config/Import/DM_CC5_P0_F02_Animation_Pipeline_v001": "superseded_import_pipeline",
    "/Game/DataMake/Config/Import/DM_CC5_P0_M02_Animation_Pipeline_v001": "superseded_import_pipeline",
    "/Game/DataMake/Config/Import/FirstDataBatch/DM_CC5_M02_Modular_MotionCompare_Pipeline_v001": "completed_modular_comparison",
}

PROTECTED_PREFIXES = (
    "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks",
    "/Game/DataMake/Animations/CC5/FirstDataBatch/Expressions",
    "/Game/DataMake/Render/Presets/MRQ_DM_FirstBatch_1440p30_PNG_v001",
    "/Game/DataMake/Sequences/firstweek",
    "/Game/DataMake/Sequences/FirstBatch/Templates",
    "/Game/DataMake/Scenes/DreamscapeVillage",
    "/Game/DataMake/Scenes/GothicCastle",
    "/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized",
)


def package_path(path: str) -> str:
    return path.split(".", 1)[0]


def list_root(root: str) -> list[str]:
    return sorted(
        {
            package_path(path)
            for path in unreal.EditorAssetLibrary.list_assets(
                root, recursive=True, include_folder=False
            )
        }
    )


candidates: dict[str, str] = {}
for root, reason in CANDIDATE_ROOTS.items():
    for asset in list_root(root):
        candidates[asset] = reason
for asset, reason in CANDIDATE_ASSETS.items():
    if unreal.EditorAssetLibrary.does_asset_exist(asset):
        candidates[asset] = reason

# Project-created placeholders have no runtime meaning and are safe candidates,
# but only inside DataMake/Vendor FirstDataBatch roots controlled by this workflow.
for root in ("/Game/DataMake", "/Game/Vendor/Reallusion/CC5/FirstDataBatch/Motions"):
    for asset in list_root(root):
        protected = any(
            asset == prefix or asset.startswith(prefix + "/")
            for prefix in PROTECTED_PREFIXES
        )
        if asset.rsplit("/", 1)[-1] == "UE_Placeholder" and not protected:
            candidates.setdefault(asset, "placeholder_asset")

protected_collisions = sorted(
    asset
    for asset in candidates
    if any(asset == prefix or asset.startswith(prefix + "/") for prefix in PROTECTED_PREFIXES)
)
if protected_collisions:
    raise RuntimeError(f"Cleanup candidate collided with protected assets: {protected_collisions}")

candidate_set = set(candidates)
rows = []
for asset in sorted(candidate_set):
    loaded = unreal.load_asset(asset)
    referencers = sorted(
        {
            package_path(path)
            for path in unreal.EditorAssetLibrary.find_package_referencers_for_asset(
                asset, load_assets_to_confirm=True
            )
        }
    )
    external = [path for path in referencers if path not in candidate_set]
    rows.append(
        {
            "asset": asset,
            "class": loaded.get_class().get_name() if loaded is not None else None,
            "reason": candidates[asset],
            "referencers": referencers,
            "external_referencers": external,
            "safe_to_delete": loaded is not None and not external,
        }
    )

report = {
    "schema_version": 1,
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "audit_only",
    "scope": "explicit_project_owned_first_batch_diagnostics_and_retired_assets",
    "counts": {
        "candidates": len(rows),
        "safe_to_delete": sum(row["safe_to_delete"] for row in rows),
        "blocked_by_external_references": sum(
            bool(row["external_referencers"]) for row in rows
        ),
    },
    "candidate_roots": CANDIDATE_ROOTS,
    "protected_prefixes": list(PROTECTED_PREFIXES),
    "assets": rows,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    "DM_FIRST_BATCH_CLEANUP_AUDIT="
    + json.dumps(
        {
            "report": str(OUTPUT),
            "counts": report["counts"],
            "protected_collision_count": len(protected_collisions),
        },
        ensure_ascii=False,
    )
)
