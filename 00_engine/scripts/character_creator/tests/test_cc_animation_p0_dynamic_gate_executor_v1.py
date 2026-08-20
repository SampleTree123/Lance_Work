import ast
import math
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "cc_validate_body_reconstruction.py"


def load_pure_functions(*names):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = set(names)
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace = {"math": math}
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return [namespace[name] for name in names]


class P0AnimationDynamicExecutorTests(unittest.TestCase):
    def test_dispatch_and_batch_entry_exist(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("def run_animation_p0_dynamic_gate(", text)
        self.assertIn('== "animation_p0_dynamic_gate"', text)
        self.assertIn(
            'capture_policy.get("camera_mode", "lightroom_current")',
            text,
        )
        self.assertIn('"auto_frame_full_body", False', text)
        self.assertIn('"align_motion_start_to_source", True', text)
        self.assertIn('"require_hair_physics": False', text)
        self.assertIn('"follow_root_for_capture": True', text)
        self.assertIn("for attempt in range(1, 4):", text)

    def test_root_evidence_distinguishes_in_place_and_moving(self):
        distance, _, classify = load_pure_functions(
            "_motion_horizontal_distance",
            "_motion_landmark_priority",
            "_classify_motion_root_evidence",
        )
        self.assertAlmostEqual(5.0, distance({"x": 0, "y": 0}, {"x": 3, "y": 4}))

        def sample(x):
            return {
                "landmark_bones": [
                    {
                        "name": "CC_Base_Root",
                        "world_transform": {
                            "translation": {"x": x, "y": 0.0, "z": 0.0}
                        },
                    }
                ]
            }

        self.assertEqual(
            "in_place_candidate",
            classify([sample(0.0), sample(4.0)])["classification"],
        )
        self.assertEqual(
            "moving_candidate",
            classify([sample(0.0), sample(20.0)])["classification"],
        )
        self.assertEqual(
            "ambiguous",
            classify([sample(0.0), sample(10.0)])["classification"],
        )

    def test_root_evidence_prefers_skeleton_root_over_jaw_root(self):
        _, _, classify = load_pure_functions(
            "_motion_horizontal_distance",
            "_motion_landmark_priority",
            "_classify_motion_root_evidence",
        )

        def sample(root_x, jaw_x):
            def bone(name, x):
                return {
                    "name": name,
                    "world_transform": {
                        "translation": {"x": x, "y": 0.0, "z": 0.0}
                    },
                }

            return {
                "landmark_bones": [
                    bone("CC_Base_JawRoot", jaw_x),
                    bone("RL_BoneRoot", root_x),
                ]
            }

        evidence = classify([sample(0.0, 0.0), sample(0.0, 30.0)])
        self.assertEqual("RL_BoneRoot", evidence["landmark_bone"])
        self.assertEqual("in_place_candidate", evidence["classification"])

    def test_facial_channel_class_is_evidence_based(self):
        (classify,) = load_pure_functions("_motion_facial_channel_class")
        self.assertEqual(
            "none_detected",
            classify(0, {"facial_bone_candidate_count": 0}),
        )
        self.assertEqual(
            "face_clip_present",
            classify(1, {"facial_bone_candidate_count": 0}),
        )
        self.assertEqual(
            "facial_bones_present",
            classify(0, {"facial_bone_candidate_count": 2}),
        )
        self.assertEqual(
            "mixed_face_clip_and_facial_bones",
            classify(1, {"facial_bone_candidate_count": 2}),
        )

    def test_camera_follow_prefers_true_root_landmark(self):
        _, primary = load_pure_functions(
            "_motion_landmark_priority",
            "_motion_primary_landmark_translation",
        )
        records = [
            {
                "name": "CC_Base_JawRoot",
                "world_transform": {
                    "translation": {"x": 50.0, "y": 0.0, "z": 150.0}
                },
            },
            {
                "name": "RL_BoneRoot",
                "world_transform": {
                    "translation": {"x": 10.0, "y": 20.0, "z": 0.0}
                },
            },
        ]
        selected = primary(records)
        self.assertEqual("RL_BoneRoot", selected["name"])
        self.assertEqual(
            {"x": 10.0, "y": 20.0, "z": 0.0},
            selected["translation"],
        )

    def test_camera_follow_uses_framing_target_as_capture_reference(self):
        (reference,) = load_pure_functions("_motion_capture_reference")
        selected = reference(
            {"x": -590.0, "y": 8.0, "z": 68.0},
            {
                "name": "RL_BoneRoot",
                "translation": {"x": -699.0, "y": -98.0, "z": 68.0},
            },
        )
        self.assertEqual("framing_target", selected["source"])
        self.assertEqual(
            {"x": -590.0, "y": 8.0, "z": 68.0},
            selected["translation"],
        )

    def test_full_body_center_error_handles_local_and_world_bounds(self):
        (center_error,) = load_pure_functions(
            "_outfit_gate_bounds_center_error"
        )
        local = center_error(85.0, 85.0, 0.0, 68.0, 153.0)
        self.assertEqual("object_space", local["bounds_space"])
        self.assertAlmostEqual(0.0, local["center_error"])

        world = center_error(85.0, 153.0, 0.0, 68.0, 153.0)
        self.assertEqual("world_space", world["bounds_space"])
        self.assertAlmostEqual(0.0, world["center_error"])


if __name__ == "__main__":
    unittest.main()
