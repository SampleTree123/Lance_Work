"""Build the machine-readable lifecycle catalog for repository scripts.

The catalog complements Technical documentation. It does not replace the
human runbooks: every script receives an owning Technical document and a
lifecycle classification so unowned implementation drift can be audited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
    "00_engine/scripts/unreal/run_first_batch_action_expression_composites.py",
    "00_engine/scripts/unreal/run_first_batch_all_action_expression_composites.py",
    "00_engine/scripts/unreal/run_first_batch_day2_final_gate.py",
    "00_engine/scripts/unreal/run_first_batch_full_reference_import.py",
    "00_engine/scripts/unreal/run_first_batch_idle_padding.py",
    "00_engine/scripts/unreal/run_first_batch_local_sample_render.py",
    "00_engine/scripts/unreal/run_first_batch_motion_import.py",
    "00_engine/scripts/unreal/run_first_batch_render_jobs.py",
    "00_engine/scripts/unreal/run_first_batch_render_matrix.py",
    "00_engine/scripts/unreal/run_first_batch_render_profile.py",
    "00_engine/scripts/unreal/ue_audit_first_batch_day3_layout_motion.py",
    "00_engine/scripts/unreal/ue_audit_first_batch_render_assets.py",
    "00_engine/scripts/unreal/ue_build_first_batch_20s_sequence.py",
    "00_engine/scripts/unreal/ue_build_first_batch_action_expression_composites.py",
    "00_engine/scripts/unreal/ue_build_first_batch_expression_composition.py",
    "00_engine/scripts/unreal/ue_build_first_batch_expression_library.py",
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
    "00_engine/scripts/unreal/ue_validate_first_batch_day2_runtime.py",
    "00_engine/scripts/unreal/validate_first_batch_chain_visual_smoke_v1.py",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_doc_root(root: Path) -> Path:
    return root / "20_planning/data_design/character_creator/full_process"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def owner_for(relative: str) -> str:
    name = Path(relative).name.lower()
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
    if "/tests/" in lowered or name.startswith("test_"):
        return "utility", False, "automated test"
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
        for path in sorted(scripts_root.rglob("*")):
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
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    counts = Counter(str(item["lifecycle"]) for item in entries)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "00_engine/scripts/documentation/build_script_lifecycle_catalog.py",
        "documentation_root": doc_root.relative_to(root).as_posix()
        if doc_root.is_relative_to(root)
        else str(doc_root),
        "script_roots": list(SCRIPT_SCAN_ROOTS),
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
