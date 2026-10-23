"""Build the machine-readable lifecycle catalog for repository scripts.

The catalog complements Technical documentation. It does not replace the
human runbooks: every script receives an owning Technical document and a
lifecycle classification so unowned implementation drift can be audited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_SUFFIXES = {".py", ".ps1", ".sh", ".cmd"}
SCRIPT_SCAN_ROOTS = ("00_engine", "20_planning/implementation")
EXCLUDED_SCRIPT_PARTS = {
    ".venv",
    "__pycache__",
    "binaries",
    "intermediate",
    "node_modules",
    "outputs",
    "saved",
}

# These scripts form the accepted implementation surface for the active first
# batch. Supporting and historical first-batch scripts remain catalogued but
# are not silently promoted to production.
ACTIVE_FIRST_BATCH_SCRIPTS = {
    "20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh",
    "00_engine/scripts/character_creator/cc_audit_first_batch_full_reference_matrix_v1.py",
    "00_engine/scripts/character_creator/cc_build_first_batch_action_ue_export_v1.py",
    "00_engine/scripts/character_creator/cc_build_first_batch_full_reference_looks_v3.py",
    "00_engine/scripts/character_creator/cc_build_first_batch_identity_library_v1.py",
    "00_engine/scripts/character_creator/cc_ingest_first_batch_action_window_selection_v1.py",
    "00_engine/scripts/character_creator/cc_prepare_first_batch_action_replacements_v4.py",
    "00_engine/scripts/character_creator/cc_validate_body_reconstruction.py",
    "00_engine/scripts/character_creator/run_first_batch_missing_looks_export.ps1",
    "00_engine/scripts/dataset/build_first_batch_chain_review_v1.py",
    "00_engine/scripts/dataset/build_first_batch_config_graph_v1.py",
    "00_engine/scripts/dataset/build_first_batch_graph_source_v1.py",
    "00_engine/scripts/dataset/build_first_batch_local_render_matrix_v1.py",
    "00_engine/scripts/dataset/build_first_batch_prompt_layer_v1.py",
    "00_engine/scripts/dataset/build_first_batch_required_exports_v1.py",
    "00_engine/scripts/unreal/build_first_batch_chain_render_matrix_v1.py",
    "00_engine/scripts/unreal/prepare_first_batch_motion_fbxs.py",
    "00_engine/scripts/unreal/run_first_batch_20s_sequence.py",
    "00_engine/scripts/unreal/run_first_batch_32_video_matrix.ps1",
    "00_engine/scripts/unreal/run_first_batch_full_reference_import.py",
    "00_engine/scripts/unreal/run_first_batch_idle_padding.py",
    "00_engine/scripts/unreal/run_first_batch_local_sample_render.py",
    "00_engine/scripts/unreal/run_first_batch_motion_import.py",
    "00_engine/scripts/unreal/run_first_batch_render_jobs.py",
    "00_engine/scripts/unreal/run_first_batch_render_matrix.py",
    "00_engine/scripts/unreal/run_first_batch_render_profile.py",
    "00_engine/scripts/unreal/ue_audit_first_batch_render_assets.py",
    "00_engine/scripts/unreal/ue_build_first_batch_20s_sequence.py",
    "00_engine/scripts/unreal/ue_build_first_batch_idle_padding.py",
    "00_engine/scripts/unreal/ue_build_first_batch_inplace_candidates.py",
    "00_engine/scripts/unreal/ue_build_first_batch_render_profile.py",
    "00_engine/scripts/unreal/ue_import_first_batch_full_reference_looks.py",
    "00_engine/scripts/unreal/ue_import_first_batch_motions.py",
    "00_engine/scripts/unreal/ue_patch_first_batch_head_wrinkle_textures.py",
    "00_engine/scripts/unreal/ue_reallusion_dialog_watcher.py",
    "00_engine/scripts/unreal/ue_remote_exec.py",
    "00_engine/scripts/unreal/ue_stage_first_batch_render_look.py",
    "00_engine/scripts/unreal/ue_start_first_batch_local_sample_render.py",
    "00_engine/scripts/unreal/validate_first_batch_chain_visual_smoke_v1.py",
}


# Reviewed retirement after the 2026-10-01 cleanup; source retained for history.
RETIRED_EXECUTION_SCRIPTS = {
    '00_engine/scripts/character_creator/run_modular_outfit_pilot_export.ps1',
    '00_engine/scripts/unreal/run_modular_outfit_runtime_v1.py',
    '00_engine/scripts/unreal/ue_build_asset_restructure_compare_level_v1.py',
    '00_engine/scripts/unreal/ue_build_modular_outfit_review_level_v1.py',
    '00_engine/scripts/unreal/ue_build_modular_outfit_runtime_v1.py',
    '00_engine/scripts/unreal/ue_build_p0_runtime_composition.py',
    '00_engine/scripts/unreal/ue_build_scalp_hair_material_instances_v1.py',
    '00_engine/scripts/unreal/ue_build_scalp_hair_review_level_v1.py',
    '00_engine/scripts/unreal/ue_cleanup_p0_runtime_validation.py',
    '00_engine/scripts/unreal/ue_compare_wardrobe_corners_v1.py',
    '00_engine/scripts/unreal/ue_compare_wardrobe_probe_geometry_v1.py',
    '00_engine/scripts/unreal/ue_disable_scalp_hair_shadows_v2.py',
    '00_engine/scripts/unreal/ue_hair_pilot_import_v1.py',
    '00_engine/scripts/unreal/ue_hide_scalp_hair_probe_v1.py',
    '00_engine/scripts/unreal/ue_import_p0_runtime_motions.py',
    '00_engine/scripts/unreal/ue_import_p0_runtime_pilot.py',
    '00_engine/scripts/unreal/ue_interchange_split_pilot.py',
    '00_engine/scripts/unreal/ue_repair_scalp_hair_materials_v1.py',
    '00_engine/scripts/unreal/ue_repair_scalp_hair_review_alignment_v1.py',
    '00_engine/scripts/unreal/ue_restore_scalp_hair_visibility_v1.py',
    '00_engine/scripts/unreal/ue_toggle_scalp_hair_shadows_v1.py',
    '00_engine/scripts/unreal/ue_wardrobe_geometry_probe_v1.py',
    '00_engine/scripts/unreal/ue_write_scalp_hair_shadow_probe_report_v1.py',
    '00_engine/scripts/unreal/ue_write_scalp_hair_visibility_probe_report_v1.py',
}
SHARED_MODULES_WITH_RETIRED_MAIN = {'00_engine/scripts/unreal/ue_build_modular_outfit_review_level_v2.py', '00_engine/scripts/unreal/ue_build_modular_outfit_runtime_v2.py'}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_doc_root(root: Path) -> Path:
    return root / "20_planning/data_design/character_creator/full_process"


def sha256(path: Path) -> str:
    return hashlib.sha256(normalized_script_bytes(path)).hexdigest()


def normalized_script_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def scripts_in_scan_root(root: Path, scan_root_relative: str) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others",
             "--exclude-standard", "-z", "--", scan_root_relative],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0:
        return [
            root / relative.decode("utf-8", errors="surrogateescape")
            for relative in result.stdout.split(b"\0")
            if relative
        ]
    scripts_root = root / scan_root_relative
    return sorted(scripts_root.rglob("*")) if scripts_root.is_dir() else []


MOTION_PORTRAIT_SCENE_PILOT_SCRIPTS = {
    "build_motion_portrait_scene_gallery_v1.py", "open_motion_portrait_scene_gallery_v1.py",
    "motion_location_pilot_analysis_v1.py", "motion_portrait_camera_planner_v1.py",
    "ue_motion_scene_sequence_v1.py", "ue_motion_scene_render_v1.py",
    "ue_motion_portrait_scene_pilot_v1.py",
    "ue_motion_body_window_v1.py", "test_motion_body_window_v1.py",
    "encode_motion_scene_pilot_v1.py", "test_encode_motion_scene_pilot_v1.py",
    "assemble_motion_scene_review_v1.py", "ue_scene_location_pilot_v1.py",
    "ue_motion_body_window_numeric_validation_v1.py",
    "ue_legacy_shared_motion_reuse_v1.py", "ue_scene_character_pilot_v1.py",
    "motion_scene_space_screening_v1.py", "ue_scene_camera_preroll_v1.py",
    "test_motion_portrait_scene_gallery_v1.py", "test_motion_portrait_camera_planner_v1.py",
    "test_motion_scene_sequence_v1.py", "test_motion_scene_render_v1.py",
}


def owner_for(relative: str) -> str:
    name = Path(relative).name.lower()
    # Current shooting-panel selection and exposure maintenance is owned by
    # SceneCamera22.12-22.19, rather than the older character-runtime fallback.
    if relative.lower() in {
        "00_engine/scripts/unreal/night_character_review_v1.py",
        "00_engine/scripts/unreal/appearance_selection_policy_v1.py",
        "00_engine/scripts/unreal/panel_hair_availability_v1.py",
        "00_engine/scripts/unreal/level_exposure_policy_v1.py",
        "00_engine/scripts/unreal/mrq_streaming_warmup_v1.py",
        "00_engine/scripts/unreal/tests/test_mrq_streaming_warmup_v1.py",
        "00_engine/scripts/unreal/tests/test_night_character_saved_appearance_v1.py",
        "00_engine/scripts/unreal/tests/test_primary_scene_samples_v1.py",
    }:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in {"pair_review_site_intent_v1.py", "pair_review_site_drafts_v1.py",
                "test_pair_review_site_intent_v1.py", "test_pair_review_site_drafts_v1.py",
                "ue_camera_collision_proxy_review_v1.py",
                "test_ue_camera_collision_proxy_review_v1.py",
                "test_pair_camera_check_integration_v1.py",
                "scene_site_catalog_v1.py", "test_scene_site_catalog_v1.py",
                "build_production_camera_library_v1.py", "test_production_camera_library_v1.py",
                "test_ue_ground_height_follow_v1.py", "test_ue_production_site_runtime_v1.py",
                "test_scene_review_catalog_iteration_20261020_v1.py"}:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in {"ue_ground_height_follow_v1.py", "ue_production_site_runtime_v1.py",
                "ue_production_trial_render_v1.py", "ue_motion_scene_sequence_v1.py",
                "test_ue_production_trial_render_v1.py", "test_motion_scene_sequence_v1.py"}:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in {"pair_scene_review_20261019_v1.py", "open_pair_scene_review_20261019_v1.ps1",
                "ue_pair_revision_runtime_20261019_v1.py", "test_pair_revision_runtime_20261019_v1.py",
                "test_pair_scene_review_20261019_v1.py", "pair_review_fast_runtime_v1.py",
                "pair_review_transport_fast_v1.py", "pair_review_material_fast_v1.py", "pair_review_face_fast_v1.py",
                "test_pair_review_transport_fast_v1.py", "test_pair_review_material_fast_v1.py",
                "test_pair_review_face_fast_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    # Exact scene-relocation contracts and tests. Ownership for a proposed
    # filename does not create a catalog entry or change its lifecycle.
    if relative.lower() in {
        "00_engine/scripts/unreal/ue_medieval_water_contract_v1.py",
        "00_engine/scripts/unreal/tests/test_medieval_water_contract_v1.py",
        "00_engine/scripts/unreal/tests/test_scene_official_class_alias_v1.py",
        "00_engine/scripts/unreal/tests/test_scene_user_defined_struct_alias_v1.py",
        "00_engine/scripts/unreal/tests/test_kowloon_redirector_retirement_v1.py",
        "00_engine/scripts/unreal/tests/test_japanese_redirector_retirement_v1.py",
        "00_engine/scripts/unreal/tests/test_urban_material_relocation_v1.py",
        "00_engine/scripts/unreal/ue_kyoto_showcase_tie_contract_v1.py",
        "00_engine/scripts/unreal/ue_futuristic_public_owner_contract_v1.py",
        "00_engine/scripts/unreal/ue_post_city_compatibility_contract_v1.py",
        "00_engine/scripts/unreal/tests/test_kyoto_showcase_tie_contract_v1.py",
        "00_engine/scripts/unreal/tests/test_futuristic_public_owner_contract_v1.py",
    }:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in {"cc_skin_detail_experiment_v1.py", "test_cc_skin_detail_experiment_v1.py"}:
        return "technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md"
    if "skin_detail" in name or "/skin_detail_review/" in relative:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"ue_scene_folder_organization_v1.py", "scene_folder_organization_v1.py", "test_scene_folder_organization_v1.py", "scene_folder_batch_driver_v1.py", "test_scene_folder_batch_driver_v1.py", "scene_path_relocation_v1.py", "test_scene_path_relocation_v1.py", "restore_scene_editor_views_v1.py", "test_restore_scene_editor_views_v1.py"} or "/scene_folder_organization_20261012_v1/" in relative:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in MOTION_PORTRAIT_SCENE_PILOT_SCRIPTS or name.removeprefix("test_") in MOTION_PORTRAIT_SCENE_PILOT_SCRIPTS:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in {"ue_camera_motion_samples_v1.py", "camera_motion_planner_v1.py", "ue_camera_pilot_stage_v1.py", "ue_camera_pilot_prepare_v1.py", "ue_camera_sequence_builder_v1.py", "ue_camera_body_retime_v1.py", "ue_camera_pilot_render_v1.py", "build_camera_pilot_gallery_v1.py", "encode_camera_pilot_v1.py", "audit_camera_pilot_sources_v1.py", "audit_camera_pair_repeatability_v1.py", "ue_camera_scene_audit_v1.py", "ue_camera_studio_lighting_v2.py", "ue_camera_prepare_studio_v2.py", "test_camera_follow_heading_v2.py", "test_camera_studio_lighting_v2.py", "test_camera_scene_audit_v1.py", "test_camera_motion_planner_v1.py", "test_camera_body_retime_v1.py", "test_camera_sequence_builder_v1.py", "test_camera_pilot_render_v1.py", "test_encode_camera_pilot_v1.py"}:
        return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
    if name in {"run_cfd40_full_motion_loop_review_v1.py", "ue_cfd40_full_motion_loop_review_endpoint_v1.py", "ue_cfd40_full_motion_loop_v1.py", "test_cfd40_full_motion_loop_v1.py", "test_full_motion_loop_controller_v1.py"}:
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name in {"prepare_motion_extension_inputs_v1.py", "motion_library_panorama_v1.py", "run_motion_extension_final_smoke_v1.py", "test_prepare_motion_extension_inputs_v1.py", "test_motion_library_panorama_v1.py"}:
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name == "run_motion_extension_pilot_smoke_v1.py":
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name in {"ue_motion_library_expansion_v1.py", "ue_motion_library_face_pilot_v1.py", "motion_library_extension_contract_v1.py", "motion_library_review_adapter_v1.py", "run_cfd40_motion_extension_review_v1.py", "ue_cfd40_motion_extension_review_v1.py", "build_motion_extension_review_v1.py", "test_motion_library_expansion_v1.py", "test_motion_library_face_pilot_v1.py", "test_motion_library_extension_v1.py", "test_cc_motion_duration_probe_v1.py", "test_cc_single_imotion_export_v1.py"}:
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name in {"ue_native_face_panel_five_second_v1.py", "test_native_face_panel_five_second_v1.py", "test_native_face_library_v2.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"ue_native_face_five_second_v1.py", "ue_capture_native_face_five_second_v1.py", "ue_import_five_second_source_v1.py", "ue_native_face_five_second_body_probe_v1.py", "test_native_face_five_second_v1.py", "test_native_face_five_second_body_probe_v1.py", "test_native_face_curve_case_v1.py", "test_native_face_capture_timing_v1.py", "test_cc_native_face_experiment_output_v1.py"}:
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name in {"native_face_library_contract_v1.py", "test_native_face_library_contract_v1.py", "ue_capture_native_face_review_v1.py", "test_compose_native_face_body_v1.py"}:
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name == "test_cfd40_native_face_integration_v1.py":
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"native_face_curve_mapping_v1.py", "test_native_face_curve_mapping_v1.py", "cc_native_face_library_v1.py", "ue_compose_native_face_body_v1.py", "test_ue_compose_native_face_body_v1.py"}:
        return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
    if name == "ue_import_native_face_clip_v1.py":
        return "technical/transfer/MOTION_TRANSFER.md"
    if name in {"cfd_native_batch40_configuration_v1.py", "test_cfd_native_batch40_configuration_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"build_reviewed_wardrobe_pool_registry_v5.py", "test_reviewed_wardrobe_pool_registry_v5.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"build_reviewed_wardrobe_pool_registry_v3.py", "build_reviewed_wardrobe_pool_registry_v4.py", "test_reviewed_wardrobe_pool_registry_v3.py", "test_reviewed_wardrobe_pool_registry_v4.py", "hair_group_color_review_contract_v1.py", "run_hair_group_color_review_v1.py", "ue_hair_group_color_review_v1.py", "hair_eye_color_runtime_v1.py", "test_hair_group_color_review_v1.py", "test_hair_eye_color_runtime_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"cfd_native_batch40_modular_contract_v1.py", "run_cfd_native_batch40_modular_review_v1.py", "ue_cfd_native_batch40_modular_review_v1.py", "test_cfd_native_batch40_modular_review_v1.py", "test_cfd_native_batch40_modular_worker_v1.py", "validate_modular_runtime_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"analyze_cfd_face_diversity_v1.py", "test_cfd_face_diversity_v1.py"}:
        return "technical/character_creator/BODYFIT_IDENTITY_AGE.md"
    if name in {"run_cfd_native_shared_skeleton_probe_v1.py", "cfd_native_batch40_contract_v1.py", "run_cfd_native_batch40_transfer_v1.py", "test_cfd_native_batch40_v1.py"}:
        return "technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md"
    if name in {"run_cfd_native_batch40_review_v1.py", "ue_cfd_native_batch40_review_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"run_cfd_native_pair_transfer_v1.py", "cfd_native_pair_ue_target_v1.py", "test_cfd_native_pair_transfer_v1.py"}:
        return "technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md"
    if name in {"ue_cfd_native_pair_review_v1.py", "run_cfd_native_pair_review_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if name in {"run_cc_headshot_geometry_only_v1.py", "cc_repair_headshot_support_materials_v1.py", "test_cc_repair_headshot_support_materials_v1.py"}:
        return "technical/character_creator/BODYFIT_IDENTITY_AGE.md"
    if name in {
        "cc_extract_complete_fbx_source_v1.py", "test_cc_extract_complete_fbx_source_v1.py",
        "ue_import_complete_character_skeleton_pilot_v1.py", "test_ue_import_complete_character_skeleton_pilot_v1.py",
        "compare_complete_character_bone_standard_v1.py", "test_compare_complete_character_bone_standard_v1.py",
        "run_complete_character_skeleton_pilot_v1.py",
    }:
        return "technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md"
    if name == "ue_stage_complete_character_skeleton_pilot_v1.py":
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if any(token in name for token in ('cc_character_creation_', 'run_cc_character_creation_', 'cc_run_character_creation_', 'cc_headshot_geometry_solver_')):
        return "technical/character_creator/BODYFIT_IDENTITY_AGE.md"
    if name in {"cc_compile_headshot_base_assembly_v1.py", "cc_run_headshot_base_assembly_v1.py", "run_headshot_base_assembly_v1.py", "cc_assembly_geometry_invariants_v1.py", "cc_capture_assembly_geometry_v1.py"}:
        return "technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md"
    if name in {"hair_source_shader_v1.py", "ue_repair_fixed_head_braid_materials_v1.py", "ue_repair_fixed_head_skin_materials_v1.py", "ue_fixed_head_skin_texture_utils_v1.py", "build_fixed_head_material_registry_v1.py", "build_fixed_head_skin_seam_control_v1.py"}:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if "fixed_head_hair_manual_review" in name:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if "fixed_head_hair" in name:
        if name in {"ue_review_fixed_head_hair_pilot_v1.py", "ue_audit_fixed_head_hair_v1.py"}:
            return "technical/unreal/CHARACTER_RUNTIME.md"
        return "technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md"
    if relative.startswith("00_engine/scripts/unreal/ue_headshot_"):
        return "technical/character_creator/BODYFIT_IDENTITY_AGE.md"
    if "formal_wardrobe" in name:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if "asset_restructure" in name:
        return "technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md"
    if "wardrobe_coverage_review" in name:
        return "technical/unreal/CHARACTER_RUNTIME.md"
    if "wardrobe" in name or name in {
        "run_modular_outfit_pilot_import_v1.py",
        "ue_modular_outfit_pilot_import_v1.py",
    }:
        return "technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md"
    if relative.startswith("20_planning/implementation/"):
        return "technical/rendering_release/SERVER_EXECUTION.md"
    if relative.startswith("00_engine/character_creator_bridge/"):
        return "technical/bridge/CC_BRIDGE_OPERATIONS.md"
    if relative.startswith("00_engine/visualization_portal/"):
        return "technical/validation/VISUAL_REVIEW.md"
    if relative.startswith("00_engine/remote_desktop/"):
        return "technical/rendering_release/SERVER_EXECUTION.md"
    if relative.startswith("00_engine/projects/"):
        return "technical/environment/ENVIRONMENT_AND_SESSION.md"
    if "/documentation/" in relative:
        if name == "build_output_inventory.py":
            return "technical/output/INVENTORY_AND_RETENTION.md"
        if name == "build_script_lifecycle_catalog.py":
            return "technical/implementation/SCRIPT_LIFECYCLE.md"
        return "technical/validation/DOCUMENTATION_VALIDATION.md"
    if "/dataset/" in relative:
        if "prompt" in name:
            return "technical/dataset/PROMPT_LAYER.md"
        return "technical/dataset/CONFIG_GRAPH_AND_CHAINS.md"
    if "/character_creator/" in relative:
        if any(token in name for token in ("action", "motion")):
            return "technical/transfer/MOTION_TRANSFER.md"
        if any(token in name for token in ("outfit", "shoe", "cloth")):
            return "technical/character_creator/OUTFIT_SYSTEM.md"
        if any(token in name for token in ("face", "identity", "headshot", "appearance")):
            return "technical/character_creator/BODYFIT_IDENTITY_AGE.md"
        return "technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md"
    if "/unreal/" in relative:
        if name == "ue_remote_exec.py":
            return "technical/environment/ENVIRONMENT_AND_SESSION.md"
        if name == "ue_reallusion_dialog_watcher.py":
            return "technical/transfer/CC_TO_UE_FULLREFERENCE.md"
        if "full_reference" in name or "fullreference" in name:
            return "technical/transfer/CC_TO_UE_FULLREFERENCE.md"
        if "layout" in name or "camera" in name or "sequence" in name:
            return "technical/unreal/SCENE_CAMERA_SEQUENCE.md"
        if any(token in name for token in ("motion", "rlmotion", "fbx")):
            return "technical/transfer/MOTION_TRANSFER.md"
        if "import" in name:
            return "technical/transfer/ASSET_TRACEABILITY.md"
        if name == "run_first_batch_32_video_matrix.ps1":
            return "technical/rendering_release/RENDER_EXECUTION.md"
        if any(token in name for token in ("render", "server", "chain_visual_smoke")):
            return "technical/rendering_release/RENDER_EXECUTION.md"
        if any(token in name for token in ("expression", "motion", "animation", "inplace", "idle")):
            return "technical/unreal/ANIMATION_EXPRESSION_MORPH.md"
        return "technical/unreal/CHARACTER_RUNTIME.md"
    return "technical/environment/ENVIRONMENT_AND_SESSION.md"


def lifecycle_for(relative: str) -> tuple[str, bool, str]:
    lowered = relative.lower()
    name = Path(relative).name.lower()
    if lowered == "00_engine/scripts/unreal/level_exposure_policy_v1.py":
        return "validated_pilot", False, "SceneCamera22.19 saved-level camera exposure inheritance; live preview/formal helper UE5.8 field readback and isolated static HongKongStreet smoke verified; all-scene exposure and fresh formal character/motion acceptance remain separate, no production Gate promotion"
    if lowered == "00_engine/scripts/unreal/mrq_streaming_warmup_v1.py":
        return "validated_pilot", False, "SceneCamera22.19 isolated static HongKongStreet3-frame1024x576 smoke with bounded120/32 warmup and MRQ10240/session7000 machine budget; first-frame detail and restoration verified, not fresh40-person assembly/motion, all-view residency or production acceptance"
    if name == "ue_ground_height_follow_v1.py":
        return "experimental", False, "SceneCamera22.7/22.8 scoped absolute Actor Z follow and exact three saved-site analytic ground planes; preview/ground-check integration requires bounded runtime evidence, actual render and all-terrain visual acceptance remain separate; no IK or stairs"
    if name in {"pair_scene_review_20261019_v1.py", "open_pair_scene_review_20261019_v1.ps1",
                "ue_pair_revision_runtime_20261019_v1.py", "pair_review_fast_runtime_v1.py",
                "pair_review_transport_fast_v1.py", "pair_review_material_fast_v1.py", "pair_review_face_fast_v1.py"}:
        return "experimental", False, "Runtime3.22 exact user-edited20261019 pair private full scene-site fast review; ordinary preview skips repeated asset/compatibility audits, explicit spatial checks preserved; formal rendering unchanged andall-combination visual acceptance pending"
    if lowered == "00_engine/scripts/unreal/ue_post_city_compatibility_contract_v1.py":
        return "production", False, "current exact PostCity package/construction compatibility contract invoked by scene relocation helper; accepted1200/2 data scope, independent normal-RHI pixels and dataset production gates remain separate"
    if name == "analyze_cfd_face_diversity_v1.py":
        return "experimental", False, "offline official 2D within-group morphometric selection aid; not perceptual or Headshot diversity validation"
    if relative in RETIRED_EXECUTION_SCRIPTS:
        return "deprecated", False, "2026-10-01 reviewed asset retirement; direct execution disabled"
    if relative in SHARED_MODULES_WITH_RETIRED_MAIN:
        return "utility", False, "shared helpers used by v003/current review; standalone legacy pilot entry retired"
    if "/tests/" in lowered or name.startswith("test_"):
        return "utility", False, "automated test"
    if "skin_detail" in name or "/skin_detail_review/" in lowered:
        return "experimental", False, "SkinDetail two-identity A/B/C experiment; geometry and media evidence are scoped, final human acceptance pending"
    if name in MOTION_PORTRAIT_SCENE_PILOT_SCRIPTS:
        return "experimental", False, "SceneCamera11 motion windows, portrait framing and three scene-anchor pilot; human review pending"
    if name in {"ue_camera_motion_samples_v1.py", "camera_motion_planner_v1.py", "ue_camera_pilot_stage_v1.py", "ue_camera_pilot_prepare_v1.py", "ue_camera_sequence_builder_v1.py", "ue_camera_body_retime_v1.py", "ue_camera_pilot_render_v1.py", "build_camera_pilot_gallery_v1.py", "encode_camera_pilot_v1.py", "audit_camera_pilot_sources_v1.py", "audit_camera_pair_repeatability_v1.py", "ue_camera_scene_audit_v1.py", "ue_camera_studio_lighting_v2.py", "ue_camera_prepare_studio_v2.py"}:
        return "experimental", False, "SceneCamera7 scoped uniform ten-second camera-motion pilot; source windows or user-authorized 7-10 second body slowdown, original-speed face repeat; runtime and naturalness acceptance require evidence"
    if name in {"run_cfd40_full_motion_loop_review_v1.py", "ue_cfd40_full_motion_loop_review_endpoint_v1.py", "ue_cfd40_full_motion_loop_v1.py"}:
        return "experimental", False, "Animation10 on-demand full-body loop review with five-second face repetition and versioned configuration; bounded review evidence, not seamless production-loop acceptance"
    if name in {"prepare_motion_extension_inputs_v1.py", "motion_library_panorama_v1.py", "run_motion_extension_final_smoke_v1.py"}:
        return "experimental", False, "Animation9 explicit reviewed-input preparation, transient fixed panorama helpers and final runtime smoke; final UI validation and publication pending"
    if name == "run_motion_extension_pilot_smoke_v1.py":
        return "experimental", False, "Animation9 explicit one-pair extension runtime smoke with old-baseline restoration; no panel publication or all-library acceptance"
    if name in {"ue_motion_library_expansion_v1.py", "ue_motion_library_face_pilot_v1.py", "motion_library_extension_contract_v1.py", "motion_library_review_adapter_v1.py", "run_cfd40_motion_extension_review_v1.py", "ue_cfd40_motion_extension_review_v1.py", "build_motion_extension_review_v1.py"}:
        return "experimental", False, "Animation9 evidence-bound motion import, five-second face pilot and isolated explicit review extension; ongoing pilot, not published or all-library visual acceptance"
    if name == "ue_native_face_panel_five_second_v1.py":
        return "experimental", False, "Runtime3.19 isolated original-rate five-second body windows and accepted four-face review combinations; bounded evidence, not all-identity or arbitrary-action acceptance"
    if name == "ue_native_face_five_second_body_probe_v1.py":
        return "experimental", False, "Animation8 isolated original-rate first-five-second body crop and native face compatibility probe; requires all-frame bone/curve and endpoint comparison, offline tests do not establish UE acceptance"
    if name in {"ue_native_face_five_second_v1.py", "ue_capture_native_face_five_second_v1.py", "ue_import_five_second_source_v1.py"}:
        return "experimental", False, "Animation8 isolated native-rate five-second static samples, source imports and 151 ordered captures; existing review library preserved, naturalness acceptance pending"
    if name in {"native_face_curve_mapping_v1.py", "cc_native_face_library_v1.py", "ue_import_native_face_clip_v1.py", "ue_compose_native_face_body_v1.py"}:
        return "experimental", False, "existing native face source inspection, evidence-bound channel mapping or isolated animation import; selected library and body compatibility not yet accepted"
    if name in {"native_face_library_contract_v1.py", "ue_capture_native_face_review_v1.py"}:
        return "experimental", False, "Animation7 evidence-gated native face review registry and bounded root-only captures; runtime/visual acceptance pending"
    if name == "cfd_native_batch40_configuration_v1.py":
        return "experimental", False, "Runtime3.18 complete selection preset with exact source/palette integrity; bounded runtime restore passed, precise playback phase not captured and face integration pending"
    if name == "build_reviewed_wardrobe_pool_registry_v5.py":
        return "experimental", False, "Runtime3.17 explicit sex-scoped user hair exclusions with preserved v4 clothing/shoe and source publication chain"
    if name in {"build_reviewed_wardrobe_pool_registry_v3.py", "build_reviewed_wardrobe_pool_registry_v4.py", "hair_group_color_review_contract_v1.py", "run_hair_group_color_review_v1.py", "ue_hair_group_color_review_v1.py", "hair_eye_color_runtime_v1.py"}:
        return "experimental", False, "Runtime3.17 scoped female shared-shoe publication, sex-specific hairstyle review and independent color experiments; user grouping and color acceptance remain pending"
    if name in {"cfd_native_batch40_modular_contract_v1.py", "run_cfd_native_batch40_modular_review_v1.py", "ue_cfd_native_batch40_modular_review_v1.py", "validate_modular_runtime_v1.py"}:
        return "experimental", False, "Runtime3.16 authorized forty-identity two-character fixed38-slot review; bounded backend and new-interface human acceptance remain separate, not a general production entry"
    if name in {"run_cfd_native_pair_transfer_v1.py", "cfd_native_pair_ue_target_v1.py", "ue_cfd_native_pair_review_v1.py", "run_cfd_native_pair_review_v1.py"}:
        return "validated_pilot", False, "two CFD-native complete exports/imports and isolated saved/reloaded fixed-slot review delivered; AutoSetup/FBX interactive confirmation required, bounded pair user validation accepted; production batch start not authorized and unattended batch execution unproven"
    if name == "run_cfd_native_shared_skeleton_probe_v1.py":
        return "validated_pilot", False, "same-sex independent shared Skeleton representative integrity and bounded root neutral/body/blink/smile/jaw visual smoke passed; not exhaustive expressions or whole-batch human acceptance"
    if name in {"cfd_native_batch40_contract_v1.py", "run_cfd_native_batch40_transfer_v1.py", "run_cfd_native_batch40_review_v1.py", "ue_cfd_native_batch40_review_v1.py"}:
        return "experimental", False, "authorized forty-person scoped implementation; shared Skeleton setup passed, complete character batch import/review not yet executed"
    if name == "run_cc_headshot_geometry_only_v1.py":
        return "validated_pilot", False, "bounded native geometry: male saved-photo raw recovery and female independent corrected tail passed; repaired starter selection/probe scoped, no fresh uninterrupted current-ref batch or final human visual acceptance"
    if name == "cc_repair_headshot_support_materials_v1.py":
        return "validated_pilot", False, "four independent native starter/generated support-material copies passed recursive12mesh/owner-transform invariance and save/reload; no skin/brow/random assembly or pool-wide visual acceptance"
    if any(token in name for token in ('cc_character_creation_', 'run_cc_character_creation_', 'cc_run_character_creation_', 'cc_headshot_geometry_solver_')):
        return "validated_pilot", False, "female photo and male raw-project CC creation passed correction and eight assembly gates; current completed-state skip verified; no new human visual, full-pool or real batch acceptance"
    if name in {"hair_source_shader_v1.py", "ue_repair_fixed_head_braid_materials_v1.py", "ue_repair_fixed_head_skin_materials_v1.py", "ue_fixed_head_skin_texture_utils_v1.py", "build_fixed_head_material_registry_v1.py", "build_fixed_head_skin_seam_control_v1.py"}:
        return "utility", False, "source-driven fixed-head material maintenance and publication; bounded representative visual evidence"
    if "fixed_head_hair_manual_review" in name:
        return "utility", False, "interactive two-reference hairstyle review; visual acceptance remains human-owned"
    if "fixed_head_hair" in name:
        return "validated_pilot", False, "accepted fixed-reference 40-style dual-fit conversion and index load; other heads and full-motion fit outside scope"
    if name in {"cc_assembly_geometry_invariants_v1.py", "cc_capture_assembly_geometry_v1.py"}:
        return "validated_pilot", False, "live CC female reference self-check and eight assembly gates passed; native lash allowance is asset-specific; no arbitrary identity or pool-wide acceptance"
    if name in {"cc_compile_headshot_base_assembly_v1.py", "cc_run_headshot_base_assembly_v1.py"}:
        return "validated_pilot", False, "slim assembly has prior female human inspection and male machine gates with exact native-lash v2 registration; other identities, pool-wide appearance and new male human visual acceptance remain outside scope"
    if name == "run_headshot_base_assembly_v1.py":
        return "experimental", False, "serial preparation and recovery controller tested offline and with prepare-only; actual CC batch submission not yet exercised"
    if relative == "00_engine/scripts/character_creator/cc_build_headshot_body_restore_target_v1.py":
        return "experimental", False, "Headshot body restoration trials have not passed subdivision and face preservation gates"
    if "asset_restructure" in name:
        return "experimental", False, "fixed-scope additive migration and visual-review pilot"
    if "wardrobe" in name:
        return "experimental", False, "average-bodyfit wardrobe expansion awaiting library acceptance"
    if "/documentation/" in lowered:
        return "utility", False, "documentation maintenance"
    if "/visualization_portal/" in lowered or "/remote_desktop/" in lowered:
        return "utility", False, "operator or review utility"
    if "/projects/" in lowered:
        return "experimental", False, "sandbox project utility"
    if relative in ACTIVE_FIRST_BATCH_SCRIPTS:
        return "production", True, "accepted active first-batch implementation"
    if "first_batch" in lowered:
        if any(token in name for token in ("cleanup", "probe", "review", "stage", "sample")):
            return "experimental", False, "diagnostic or review implementation"
        return "validated_pilot", False, "first-batch support or earlier accepted pilot"
    if any(token in lowered for token in ("pilot", "probe", "diagnostic", "experimental")):
        return "experimental", False, "explicit pilot or diagnostic"
    if name.startswith(("build_", "generate_", "check_", "validate_", "audit_", "run_")):
        return "utility", False, "general build, validation, or execution utility"
    return "validated_pilot", False, "retained implementation with limited documented scope"


def load_doc_texts(doc_root: Path) -> dict[str, str]:
    if not doc_root.is_dir():
        return {}
    result: dict[str, str] = {}
    for path in sorted(doc_root.rglob("*.md")):
        result[path.relative_to(doc_root).as_posix()] = path.read_text(
            encoding="utf-8", errors="replace"
        )
    return result


def build_catalog(root: Path, doc_root: Path) -> dict[str, object]:
    doc_texts = load_doc_texts(doc_root)
    entries: list[dict[str, object]] = []
    for scan_root_relative in SCRIPT_SCAN_ROOTS:
        scripts_root = root / scan_root_relative
        if not scripts_root.is_dir():
            continue
        for path in scripts_in_scan_root(root, scan_root_relative):
            if not path.is_file() or path.suffix.lower() not in SCRIPT_SUFFIXES:
                continue
            relative_parts = path.relative_to(scripts_root).parts
            if any(part.lower() in EXCLUDED_SCRIPT_PARTS for part in relative_parts):
                continue
            relative = path.relative_to(root).as_posix()
            lifecycle, active_batch, reason = lifecycle_for(relative)
            owner = owner_for(relative)
            basename = path.name
            mentioned = sorted(
                doc_path
                for doc_path, text in doc_texts.items()
                if relative in text or basename in text
            )
            repo_parts = path.relative_to(root).parts
            entries.append(
                {
                    "path": relative,
                    "scan_root": scan_root_relative,
                    "domain": repo_parts[1] if len(repo_parts) > 1 else "root",
                    "lifecycle": lifecycle,
                    "active_batch": active_batch,
                    "classification_reason": reason,
                    "owner_document": owner,
                    "owner_exists": (doc_root / owner).is_file(),
                    "document_mentions": mentioned,
                    "bytes": len(normalized_script_bytes(path)),
                    "sha256": sha256(path),
                }
            )
    entries.sort(key=lambda item: str(item["path"]))
    counts = Counter(str(item["lifecycle"]) for item in entries)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "00_engine/scripts/documentation/build_script_lifecycle_catalog.py",
        "documentation_root": doc_root.relative_to(root).as_posix()
        if doc_root.is_relative_to(root)
        else str(doc_root),
        "script_roots": list(SCRIPT_SCAN_ROOTS),
        "content_normalization": "text_lf_v1",
        "excluded_path_parts": sorted(EXCLUDED_SCRIPT_PARTS),
        "lifecycle_vocabulary": [
            "production",
            "validated_pilot",
            "utility",
            "experimental",
            "deprecated",
            "archived",
        ],
        "counts": dict(sorted(counts.items())),
        "scripts": entries,
    }


def parse_args() -> argparse.Namespace:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=root)
    parser.add_argument("--doc-root", type=Path, default=default_doc_root(root))
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "00_engine/scripts/SCRIPT_CATALOG.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    doc_root = args.doc_root.resolve()
    payload = build_catalog(root, doc_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(payload['scripts'])} script records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
