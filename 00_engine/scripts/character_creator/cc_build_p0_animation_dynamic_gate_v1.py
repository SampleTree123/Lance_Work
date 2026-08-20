"""Build the hash-locked CC dynamic gate for the RM-09 P0 animation Pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parent
ENGINE_ROOT = SCRIPT_ROOT.parents[1]
DEFAULT_PILOT_ROOT = (
    ENGINE_ROOT
    / "outputs"
    / "character_creator_bridge"
    / "artifacts"
    / "animation_p0_pilot"
    / "pilot_20260817_v1"
)
DEFAULT_MANIFEST = DEFAULT_PILOT_ROOT / "pilot_manifest.json"
DEFAULT_REVIEW = DEFAULT_PILOT_ROOT / "dynamic_review.json"
DEFAULT_BODY_LIBRARY = SCRIPT_ROOT / "cc_body_preset_library_v2.json"
DEFAULT_OUTPUT = SCRIPT_ROOT / "cc_p0_animation_dynamic_gate_20260817_v1.json"
DEFAULT_LIGHTROOM = Path(
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Light Room"
    r"\Default\Default_CC5.ccLightroom"
)
DEFAULT_CAMERA = Path(
    r"D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera"
    r"\Headshot Ref\Ref Cam Male L.ccCam"
)
ALLOWED_ACTORS = ("F02_Average", "M02_Average")


class DynamicGateBuildError(RuntimeError):
    pass


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DynamicGateBuildError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_file(
    path: Path,
    label: str,
    expected_sha256: str | None = None,
    expected_size: int | None = None,
) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise DynamicGateBuildError(f"{label} is missing: {path}")
    size = path.stat().st_size
    if expected_size is not None and size != int(expected_size):
        raise DynamicGateBuildError(f"{label} size changed: {path}")
    digest = sha256_file(path)
    if expected_sha256 is not None and digest != expected_sha256:
        raise DynamicGateBuildError(f"{label} SHA-256 changed: {path}")
    return {"path": str(path), "size_bytes": size, "sha256": digest}


def _indexed_unique(items: list[dict[str, Any]], key: str, label: str):
    values = [item.get(key) for item in items]
    if any(not isinstance(value, str) or not value for value in values):
        raise DynamicGateBuildError(f"{label} contains an invalid {key}")
    if len(values) != len(set(values)):
        raise DynamicGateBuildError(f"{label} contains duplicate {key} values")
    return dict(zip(values, items))


def build_gate(
    manifest_path: Path,
    review_path: Path,
    body_library_path: Path,
    camera_path: Path,
    lightroom_path: Path,
    selected_case_ids: list[str] | None = None,
    library_id: str = "cc_p0_animation_dynamic_gate_20260817_v1",
    yaw_degrees: float | None = None,
    camera_mode: str = "lightroom_current",
    auto_frame_full_body: bool = False,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    review_path = review_path.resolve()
    body_library_path = body_library_path.resolve()
    manifest = read_json(manifest_path)
    review = read_json(review_path)
    body_library = read_json(body_library_path)

    if yaw_degrees is not None and not math.isfinite(yaw_degrees):
        raise DynamicGateBuildError("Capture yaw must be finite")
    if camera_mode not in {"loaded_preset", "lightroom_current"}:
        raise DynamicGateBuildError(f"Unsupported camera mode: {camera_mode}")
    if not isinstance(auto_frame_full_body, bool):
        raise DynamicGateBuildError("Auto-frame policy must be a boolean")

    if manifest.get("status") != "extracted_pending_cc_dynamic_review":
        raise DynamicGateBuildError("P0 Pilot is not ready for CC dynamic review")
    validation = manifest.get("validation") or {}
    if not validation.get("success") or not validation.get(
        "all_extracted_files_unique"
    ):
        raise DynamicGateBuildError("P0 Pilot extraction validation failed")
    if review.get("pilot_id") != manifest.get("pilot_id"):
        raise DynamicGateBuildError("Pilot manifest and review IDs differ")
    if review.get("status") != "not_started":
        raise DynamicGateBuildError("Dynamic review template is not pristine")

    cases = manifest.get("cases") or []
    if not 10 <= len(cases) <= 20:
        raise DynamicGateBuildError("P0 dynamic Pilot must contain 10..20 cases")
    cases_by_id = _indexed_unique(cases, "case_id", "Pilot manifest")
    review_cases = review.get("cases") or []
    review_by_id = _indexed_unique(review_cases, "case_id", "Review template")
    if set(cases_by_id) != set(review_by_id):
        raise DynamicGateBuildError("Pilot manifest and review cases differ")
    if any(
        item.get("production_status") != "not_approved" for item in cases
    ):
        raise DynamicGateBuildError("P0 Pilot must not contain approved motions")
    if any(
        item.get("visual_decision") != "pending" for item in review_cases
    ):
        raise DynamicGateBuildError("Review template already contains decisions")
    if selected_case_ids is not None:
        if not selected_case_ids or len(selected_case_ids) != len(
            set(selected_case_ids)
        ):
            raise DynamicGateBuildError(
                "Selected case IDs must be non-empty and unique"
            )
        unknown_cases = sorted(set(selected_case_ids) - set(cases_by_id))
        if unknown_cases:
            raise DynamicGateBuildError(
                f"Unknown selected case IDs: {unknown_cases}"
            )
        selected_case_id_set = set(selected_case_ids)
        cases = [
            case for case in cases if case["case_id"] in selected_case_id_set
        ]

    body_presets = body_library.get("presets") or []
    body_by_id = _indexed_unique(body_presets, "preset_id", "BodyFit library")
    missing_actors = sorted(set(ALLOWED_ACTORS) - set(body_by_id))
    if missing_actors:
        raise DynamicGateBuildError(f"BodyFit actors are missing: {missing_actors}")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    verified_motion_hashes: set[str] = set()
    for case in cases:
        actor_id = case.get("pilot_actor_preset_id")
        if actor_id not in ALLOWED_ACTORS:
            raise DynamicGateBuildError(f"Unsupported Pilot actor: {actor_id}")
        extracted = case.get("extracted_file") or {}
        motion = verified_file(
            Path(extracted.get("path", "")),
            f"Pilot motion {case['case_id']}",
            extracted.get("sha256"),
            extracted.get("size_bytes"),
        )
        if motion["sha256"] in verified_motion_hashes:
            raise DynamicGateBuildError("P0 Pilot contains duplicate motion bytes")
        verified_motion_hashes.add(motion["sha256"])
        grouped[actor_id].append(
            {
                "case_id": case["case_id"],
                "motion_id": case["motion_id"],
                "filename": case["filename"],
                "source_format": case["source_format"],
                "format_generation": case["format_generation"],
                "review_family": case["review_family"],
                "loop_hint": case.get("loop_hint", "unknown"),
                "semantic_tags": list(case.get("semantic_tags") or []),
                "motion": motion,
                "review_status": "pending_cc_dynamic_review",
                "production_status": "not_approved",
            }
        )

    active_actors = [
        actor_id for actor_id in ALLOWED_ACTORS if grouped[actor_id]
    ]
    if selected_case_ids is None and len(active_actors) != len(ALLOWED_ACTORS):
        raise DynamicGateBuildError("Both F02 and M02 must have Pilot cases")
    if not active_actors:
        raise DynamicGateBuildError("Selected recovery Gate has no Pilot cases")

    presets = []
    for actor_id in active_actors:
        source = body_by_id[actor_id]
        source_project = source.get("source_project") or {}
        project_record = verified_file(
            Path(source_project.get("path", "")),
            f"BodyFit source project {actor_id}",
            source_project.get("sha256"),
            source_project.get("size_bytes", source_project.get("bytes")),
        )
        base_avatar = source.get("base_avatar") or {}
        base_record = verified_file(
            Path(base_avatar.get("path", "")),
            f"BodyFit base avatar {actor_id}",
            base_avatar.get("sha256"),
            base_avatar.get("size_bytes", base_avatar.get("bytes")),
        )
        presets.append(
            {
                "preset_id": actor_id,
                "sex": source.get("sex"),
                "base_avatar": base_record,
                "source_project": project_record,
                "motion_cases": grouped[actor_id],
            }
        )

    actor_counts = Counter(case["pilot_actor_preset_id"] for case in cases)
    format_counts = Counter(case["source_format"].lower() for case in cases)
    return {
        "schema_version": 1,
        "library_id": library_id,
        "generated_at": now(),
        "status": "pending_cc_dynamic_review",
        "diagnostic_mode": "animation_p0_dynamic_gate",
        "preview_capture_mode": "render_image",
        "preview_resolution": [1024, 1024],
        "preview_lightroom": str(lightroom_path.resolve()),
        "full_body_camera": verified_file(
            camera_path, "P0 full-body camera"
        ),
        "lightroom": verified_file(lightroom_path, "P0 Lightroom"),
        "source_pilot_manifest": {
            "pilot_id": manifest["pilot_id"],
            **verified_file(manifest_path, "P0 Pilot manifest"),
        },
        "source_dynamic_review_template": verified_file(
            review_path, "P0 dynamic review template"
        ),
        "source_bodyfit_library": {
            "library_id": body_library.get("library_id"),
            **verified_file(body_library_path, "BodyFit library"),
        },
        "capture_policy": {
            "sample_normalized_positions": [0.0, 0.25, 0.5, 0.75, 1.0],
            "camera_mode": camera_mode,
            "yaw_degrees": (
                float(yaw_degrees) if yaw_degrees is not None else None
            ),
            "auto_frame_full_body": auto_frame_full_body,
            "align_motion_start_to_source": True,
            "framing": (
                "auto_full_body_centered_per_motion"
                if auto_frame_full_body
                else "preserve_lightroom_camera_and_source_transform"
            ),
            "physics_simulation": True,
            "segment_timeout_seconds": 45.0,
        },
        "execution_policy": {
            "load_each_actor_project_once": True,
            "replace_existing_motion_clips": True,
            "continue_after_motion_failure": True,
            "checkpoint_after_each_motion": True,
            "stop_on_blocking_dialog": True,
            "production_approval_from_automation": False,
        },
        "scope_policy": {
            "pilot_membership_is_not_production_approval": True,
            "actor_sex_is_not_a_permanent_motion_restriction": True,
            "loop_requires_visual_review": True,
            "hidden_prop_dependency_requires_visual_review": True,
        },
        "counts": {
            "actor_count": len(presets),
            "motion_case_count": len(cases),
            "sample_count_per_motion": 5,
            "expected_image_count": len(cases) * 5,
            "by_actor": dict(sorted(actor_counts.items())),
            "by_source_format": dict(sorted(format_counts.items())),
            "production_approved_count": 0,
        },
        "presets": presets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--body-library", type=Path, default=DEFAULT_BODY_LIBRARY)
    parser.add_argument("--camera", type=Path, default=DEFAULT_CAMERA)
    parser.add_argument("--lightroom", type=Path, default=DEFAULT_LIGHTROOM)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--yaw-degrees", type=float, default=None)
    parser.add_argument(
        "--camera-mode",
        choices=("loaded_preset", "lightroom_current"),
        default="lightroom_current",
    )
    parser.add_argument(
        "--preserve-source-yaw",
        action="store_true",
        help="Keep the source project's avatar yaw instead of overriding it.",
    )
    parser.add_argument(
        "--no-auto-frame",
        action="store_true",
        help="Keep the Lightroom camera framing instead of auto-framing.",
    )
    parser.add_argument(
        "--library-id",
        default="cc_p0_animation_dynamic_gate_20260817_v1",
    )
    args = parser.parse_args()
    document = build_gate(
        args.manifest,
        args.review,
        args.body_library,
        args.camera,
        args.lightroom,
        selected_case_ids=args.case_ids,
        library_id=args.library_id,
        yaw_degrees=(None if args.preserve_source_yaw else args.yaw_degrees),
        camera_mode=args.camera_mode,
        auto_frame_full_body=(
            args.camera_mode == "loaded_preset" and not args.no_auto_frame
        ),
    )
    write_json(args.output.resolve(), document)
    print(
        json.dumps(
            {
                "library_id": document["library_id"],
                "status": document["status"],
                "counts": document["counts"],
                "output": str(args.output.resolve()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
