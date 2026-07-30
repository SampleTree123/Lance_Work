import importlib.util
import json
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_summarize_character_integration_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_summarize_character_integration_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class IntegrationSummaryTests(unittest.TestCase):
    def test_eye_integrity_requires_all_production_phases(self):
        expected = 0.0
        phase = {
            "avatar_part_count": 1,
            "eye_bones": [{}, {}],
            "eyeball_move": {
                "available": True,
                "weight": expected,
            },
            "look_at": {"valid": True},
        }
        report = {
            "eye_integrity": {
                "expected_weight": expected,
                "identity_write_attempted": False,
                "post_face_validation_comparison": {
                    "matches": True,
                },
                "post_face_validation_refresh_attempts": [
                    {"attempt": 1, "matches": True}
                ],
                "phases": {
                    phase_id: dict(phase)
                    for phase_id in (
                        "source_project",
                        "after_body",
                        "after_head_preset",
                        "after_primary_support",
                        "after_facial_profile",
                        "after_face_identity",
                        "after_facial_assembly",
                        "final",
                    )
                },
            }
        }
        self.assertTrue(MODULE.eye_integrity_pass(report))
        report["eye_integrity"]["phases"]["final"]["look_at"] = {
            "valid": False
        }
        self.assertFalse(MODULE.eye_integrity_pass(report))

    def test_eye_integrity_accepts_legacy_result_without_refresh_log(self):
        expected = 0.0
        phase = {
            "avatar_part_count": 1,
            "eye_bones": [{}, {}],
            "eyeball_move": {
                "available": True,
                "weight": expected,
            },
            "look_at": {"valid": True},
        }
        result = {
            "eye_integrity": {
                "expected_weight": expected,
                "identity_write_attempted": False,
                "post_face_validation_comparison": {
                    "matches": True,
                },
                "phases": {
                    phase_id: dict(phase)
                    for phase_id in (
                        "source_project",
                        "after_body",
                        "after_head_preset",
                        "after_primary_support",
                        "after_facial_profile",
                        "after_face_identity",
                        "after_facial_assembly",
                        "final",
                    )
                },
            }
        }
        self.assertTrue(MODULE.eye_integrity_pass(result))

    def test_facial_profile_requires_content_load_and_unchanged_static_state(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            vectors_path = os.path.join(
                directory,
                "facial_profile_vectors.json",
            )
            with open(vectors_path, "wb") as handle:
                handle.write(b"{}")
            result = {
                "artifacts": {
                    "facial_profile_vectors": vectors_path,
                },
                "face_facial_profile_application": {
                    "application_mode": (
                        "selected_avatar_content_load"
                    ),
                    "load_status": {"is_error": False},
                    "sha256": "a" * 64,
                },
                "face_facial_profile_eye_structure_unchanged": True,
                "face_facial_profile_morphs_unchanged": True,
            }
            self.assertTrue(MODULE.facial_profile_pass(result))
            result[
                "face_facial_profile_eye_structure_unchanged"
            ] = False
            self.assertFalse(MODULE.facial_profile_pass(result))

    def test_pigmentation_checks_every_present_hair_domain(self):
        targets = {
            "RootColor": [0.1, 0.2, 0.3],
            "TipColor": [0.4, 0.5, 0.6],
        }
        result = {
            "facial_assembly": {
                "pigmentation": {
                    "domain_material_counts": {
                        "eyebrows": 1,
                        "facial_hair": 1,
                        "scalp_hair": 1,
                    },
                    "materials": [
                        {
                            "after": {
                                key: list(value)
                                for key, value in targets.items()
                            },
                            "domain": domain,
                        }
                        for domain in (
                            "eyebrows",
                            "facial_hair",
                            "scalp_hair",
                        )
                    ],
                    "target_colors": targets,
                    "visible_gray_fraction": 0.25,
                }
            }
        }
        preset = {
            "facial_hair_asset_id": "beard",
            "visible_gray_fraction": 0.25,
        }
        self.assertTrue(MODULE.pigmentation_pass(result, preset))
        result["facial_assembly"]["pigmentation"]["materials"][1][
            "after"
        ]["RootColor"] = [0.9, 0.2, 0.3]
        self.assertFalse(MODULE.pigmentation_pass(result, preset))

    def test_pose_validation_requires_images_and_core_pose_set(self):
        with tempfile.TemporaryDirectory() as directory:
            poses = []
            for pose_id in MODULE.REQUIRED_POSE_IDS:
                path = os.path.join(directory, pose_id + ".png")
                with open(path, "wb") as handle:
                    handle.write(b"image")
                poses.append(
                    {
                        "capture": {
                            "capture_mode": (
                                MODULE.FACE_POSE_CAPTURE_MODE
                            )
                        },
                        "image": path,
                        "pose_id": pose_id,
                    }
                )
            post_pose_neutral_image = os.path.join(
                directory,
                "post_pose_neutral.png",
            )
            with open(post_pose_neutral_image, "wb") as handle:
                handle.write(b"image")
            result = {
                "facial_pose_validation": {
                    "evidence_liveness": {
                        "minimum_rmse": (
                            MODULE.FACE_EVIDENCE_MIN_RMSE
                        ),
                        "poses": [
                            {
                                "matches": True,
                                "pose_id": pose_id,
                                "rmse": 1.0,
                            }
                            for pose_id in MODULE.REQUIRED_POSE_IDS
                            if pose_id != "jaw_open_three_quarter"
                        ],
                        "reference_image": post_pose_neutral_image,
                        "status": "passed",
                    },
                    "final_expression_clip_count": 1,
                    "neutral_eye_integrity": {"matches": True},
                    "poses": poses,
                    "post_pose_neutral_capture": {
                        "capture_mode": (
                            MODULE.FACE_NEUTRAL_CAPTURE_MODE
                        )
                    },
                    "post_pose_neutral_image": (
                        post_pose_neutral_image
                    ),
                    "profile": "face_identity_safety_v1",
                    "render_warmup": {"deleted": True},
                    "snapshot": {
                        "deleted": True,
                        "restored": True,
                        "saved": True,
                    },
                    "timeline": {
                        "baseline_expression_clip_count": 1,
                        "capture_frame": 0,
                        "capture_strategy": (
                            MODULE.FACE_EVIDENCE_CAPTURE_STRATEGY
                        ),
                        "preserved_existing_expression_clips": True,
                        "removed_expression_clips": [],
                    },
                }
            }
            self.assertTrue(MODULE.pose_validation_pass(result))
            os.remove(poses[-1]["image"])
            self.assertFalse(MODULE.pose_validation_pass(result))

    def test_pose_validation_rejects_legacy_capture_strategy(self):
        result = {
            "facial_pose_validation": {
                "final_expression_clip_count": 1,
                "neutral_eye_integrity": {"matches": True},
                "poses": [],
                "profile": "face_identity_safety_v1",
            }
        }
        self.assertFalse(MODULE.pose_validation_pass(result))

    def test_pose_validation_rejects_failed_liveness(self):
        with tempfile.TemporaryDirectory() as directory:
            image = os.path.join(directory, "evidence.png")
            with open(image, "wb") as handle:
                handle.write(b"image")
            poses = [
                {
                    "capture": {
                        "capture_mode": MODULE.FACE_POSE_CAPTURE_MODE
                    },
                    "image": image,
                    "pose_id": pose_id,
                }
                for pose_id in MODULE.REQUIRED_POSE_IDS
            ]
            liveness_poses = [
                {
                    "matches": True,
                    "pose_id": pose_id,
                    "rmse": 1.0,
                }
                for pose_id in MODULE.REQUIRED_POSE_IDS
                if pose_id != "jaw_open_three_quarter"
            ]
            liveness_poses[0]["matches"] = False
            result = {
                "facial_pose_validation": {
                    "evidence_liveness": {
                        "minimum_rmse": (
                            MODULE.FACE_EVIDENCE_MIN_RMSE
                        ),
                        "poses": liveness_poses,
                        "reference_image": image,
                        "status": "passed",
                    },
                    "final_expression_clip_count": 1,
                    "neutral_eye_integrity": {"matches": True},
                    "poses": poses,
                    "post_pose_neutral_capture": {
                        "capture_mode": (
                            MODULE.FACE_NEUTRAL_CAPTURE_MODE
                        )
                    },
                    "post_pose_neutral_image": image,
                    "profile": "face_identity_safety_v1",
                    "render_warmup": {"deleted": True},
                    "snapshot": {
                        "deleted": True,
                        "restored": True,
                        "saved": True,
                    },
                    "timeline": {
                        "baseline_expression_clip_count": 1,
                        "capture_frame": 0,
                        "capture_strategy": (
                            MODULE.FACE_EVIDENCE_CAPTURE_STRATEGY
                        ),
                        "preserved_existing_expression_clips": True,
                        "removed_expression_clips": [],
                    },
                }
            }
            self.assertFalse(MODULE.pose_validation_pass(result))

    def test_explicit_result_paths_ignore_recursive_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            discovered = os.path.join(
                directory,
                "validation_result.json",
            )
            selected = os.path.join(directory, "result.json")
            for path, preset_id in (
                (discovered, "DISCOVERED"),
                (selected, "SELECTED"),
            ):
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump({"preset_id": preset_id}, handle)

            resolved = MODULE.resolve_result_paths(
                directory,
                [selected],
            )
            self.assertEqual(
                resolved,
                [os.path.realpath(selected)],
            )
            self.assertEqual(
                MODULE.load_case_results(resolved[0])[0]["preset_id"],
                "SELECTED",
            )

    def test_result_loader_accepts_validation_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "validation_result.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"results": [{"preset_id": "WRAPPED"}]},
                    handle,
                )
            self.assertEqual(
                MODULE.load_case_results(path),
                [{"preset_id": "WRAPPED"}],
            )


if __name__ == "__main__":
    unittest.main()
