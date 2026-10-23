import importlib.util
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_validate_body_reconstruction.py"
)


class FakeStatus:
    def IsError(self):
        return False

    def GetStatusCode(self):
        return 0


class FakeApplication:
    calls = 0

    @classmethod
    def processEvents(cls):
        cls.calls += 1


def load_subject():
    os.environ["CC_BODY_RECONSTRUCTOR_IMPORT_ONLY"] = "1"
    rlpy = types.ModuleType("RLPy")
    for index, name in enumerate(
        (
            "Diffuse",
            "Normal",
            "Roughness",
            "Specular",
            "Metallic",
            "AmbientOcclusion",
            "Opacity",
            "Bump",
            "Displacement",
            "Glow",
        )
    ):
        setattr(rlpy, "EMaterialTextureChannel_" + name, index)
    rlpy.EObjectModifiedType_MorphWeight = 1
    rlpy.RGlobal = types.SimpleNamespace(
        ObjectModified=lambda avatar, modification: FakeStatus()
    )
    sys.modules["RLPy"] = rlpy

    pyside = types.ModuleType("PySide2")
    pyside.QtCore = types.SimpleNamespace()
    pyside.QtGui = types.SimpleNamespace()
    pyside.QtWidgets = types.SimpleNamespace(QApplication=FakeApplication)
    sys.modules["PySide2"] = pyside

    spec = importlib.util.spec_from_file_location(
        "cc_validate_body_reconstruction_face_test_subject", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class Bounds:
    first = -1.0
    second = 1.0


def neutral_eye_state(local_scale=0.875, world_z=165.0):
    vector = {"x": 1.0, "y": 2.0, "z": 3.0}
    scale = {"x": local_scale, "y": local_scale, "z": local_scale}
    rotation = {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}
    return {
        "avatar_parts": [
            {
                "avatar_part_type": "1",
                "id": "eye_part",
                "mesh_names": ["CC_Base_Eye"],
                "name": "CC_Base_Eye",
                "python_type": "RIAvatarPart",
            }
        ],
        "eye_bones": [
            {
                "basis_transform": {
                    "rotation": dict(rotation),
                    "s": dict(scale),
                    "translation": dict(vector),
                },
                "id": "left_eye",
                "local_transform": {
                    "rotation": dict(rotation),
                    "s": dict(scale),
                    "translation": dict(vector),
                },
                "name": "CC_Base_L_Eye",
                "t_pose_position": dict(vector),
                "world_transform": {
                    "rotation": dict(rotation),
                    "s": dict(scale),
                    "translation": {
                        "x": 10.0,
                        "y": 20.0,
                        "z": world_z,
                    },
                },
            }
        ],
        "eyeball_move": {"weight": 0.0},
        "look_at": {"available": True, "valid": True},
    }


class NeutralEyeStateTests(unittest.TestCase):
    def test_eye_bone_capture_refreshes_all_bones_before_sampling(self):
        class DelayedEyeBone:
            def __init__(self):
                self.update_count = 0

            def GetName(self):
                return "CC_Base_L_Eye"

            def GetID(self):
                return "left_eye"

            def Update(self):
                self.update_count += 1

            def LocalTransform(self):
                return {"kind": "local"}

            def BasisTransform(self):
                return {"kind": "basis"}

            def WorldTransform(self):
                return {
                    "kind": "world",
                    "translation": {
                        "x": (
                            6.43
                            if self.update_count >= 2
                            else -6.43
                        )
                    },
                }

        class DelayedEyeSkeleton:
            def __init__(self, bone):
                self.bone = bone

            def GetSkinBones(self):
                return [self.bone]

            def GetBoneTPosePosition(self, bone):
                return {"x": 1.0, "y": 2.0, "z": 3.0}

            def IsBoneAnimated(self, bone):
                return False

        bone = DelayedEyeBone()
        original_transform = SUBJECT._transform_data
        original_vector = SUBJECT._vector3_data
        SUBJECT._transform_data = lambda value: value
        SUBJECT._vector3_data = lambda value: value
        try:
            records = SUBJECT._capture_eye_bones(
                DelayedEyeSkeleton(bone)
            )
        finally:
            SUBJECT._transform_data = original_transform
            SUBJECT._vector3_data = original_vector

        self.assertEqual(2, bone.update_count)
        self.assertEqual(
            6.43,
            records[0]["world_transform"]["translation"]["x"],
        )

    def test_identical_states_match(self):
        state = neutral_eye_state()
        result = SUBJECT.compare_neutral_eye_states(state, state)
        self.assertTrue(result["matches"])
        self.assertEqual(result["differences"], [])

    def test_local_eye_scale_reset_is_rejected(self):
        before = neutral_eye_state(local_scale=0.875)
        after = neutral_eye_state(local_scale=1.0)
        result = SUBJECT.compare_neutral_eye_states(
            before,
            after,
            include_world=False,
        )
        self.assertFalse(result["matches"])
        self.assertTrue(
            any(
                item["field"].endswith("local_transform.s.x")
                for item in result["differences"]
            )
        )

    def test_world_translation_uses_two_tenths_millimeter_tolerance(self):
        before = neutral_eye_state(world_z=165.0)
        accepted = neutral_eye_state(world_z=165.019)
        rejected = neutral_eye_state(world_z=165.021)
        accepted_result = SUBJECT.compare_neutral_eye_states(
            before,
            accepted,
        )
        self.assertTrue(accepted_result["matches"])
        self.assertEqual(
            accepted_result["world_translation_tolerance"],
            0.02,
        )
        self.assertFalse(
            SUBJECT.compare_neutral_eye_states(before, rejected)["matches"]
        )

    def test_world_rotation_still_rejects_stale_face_view(self):
        before = neutral_eye_state(world_z=165.0)
        after = json.loads(json.dumps(before))
        after["eye_bones"][0]["world_transform"]["translation"]["z"] += 0.015
        after["eye_bones"][0]["world_transform"]["rotation"]["z"] = 0.69

        result = SUBJECT.compare_neutral_eye_states(before, after)

        self.assertFalse(result["matches"])
        self.assertTrue(
            any(
                item["field"].endswith("world_transform.rotation.z")
                for item in result["differences"]
            )
        )

    def test_explicit_transform_snapshot_keeps_geometry_checks(self):
        before = neutral_eye_state()
        before["capture_mode"] = "transforms_only"
        del before["eye_bones"][0]["t_pose_position"]
        after = json.loads(json.dumps(before))
        result = SUBJECT.compare_neutral_eye_states(before, after)
        self.assertTrue(result["matches"])
        self.assertEqual(result["t_pose_comparison"], "not_sampled_sdk_modal_side_effect")
        after["eye_bones"][0]["world_transform"]["translation"]["z"] += 1.0
        self.assertFalse(SUBJECT.compare_neutral_eye_states(before, after)["matches"])

    def test_missing_t_pose_is_not_implicitly_accepted(self):
        before = neutral_eye_state()
        del before["eye_bones"][0]["t_pose_position"]
        self.assertFalse(SUBJECT.compare_neutral_eye_states(before, before)["matches"])
        after = json.loads(json.dumps(before))
        after["capture_mode"] = "transforms_only"
        self.assertFalse(SUBJECT.compare_neutral_eye_states(before, after)["matches"])

    def test_world_state_can_be_deferred_until_outer_cleanup(self):
        before = neutral_eye_state(world_z=165.0)
        after = neutral_eye_state(world_z=170.0)
        self.assertTrue(
            SUBJECT.compare_neutral_eye_states(
                before,
                after,
                include_world=False,
            )["matches"]
        )

    def test_project_reload_comparison_ignores_runtime_ids(self):
        before = neutral_eye_state()
        after = json.loads(json.dumps(before))
        after["avatar_parts"][0]["id"] = "reloaded_eye_part"
        after["eye_bones"][0]["id"] = "reloaded_left_eye"

        strict = SUBJECT.compare_neutral_eye_states(before, after)
        reloaded = SUBJECT.compare_neutral_eye_states(
            before,
            after,
            include_runtime_ids=False,
            t_pose_tolerance=0.5,
        )

        self.assertFalse(strict["matches"])
        self.assertTrue(reloaded["matches"])

    def test_project_reload_allows_reference_t_pose_recalculation_only(self):
        before = neutral_eye_state()
        after = json.loads(json.dumps(before))
        after["eye_bones"][0]["t_pose_position"]["z"] += 0.4

        accepted = SUBJECT.compare_neutral_eye_states(
            before,
            after,
            include_runtime_ids=False,
            t_pose_tolerance=0.5,
        )
        after["eye_bones"][0]["world_transform"]["translation"]["z"] += 0.03
        rejected = SUBJECT.compare_neutral_eye_states(
            before,
            after,
            include_runtime_ids=False,
            t_pose_tolerance=0.5,
        )

        self.assertTrue(accepted["matches"])
        self.assertFalse(rejected["matches"])
        self.assertFalse(
            SUBJECT.compare_neutral_eye_states(
                before,
                after,
                include_world=True,
            )["matches"]
        )


class FaceSubjectAlignmentTests(unittest.TestCase):
    def test_camera_reference_aligns_non_average_body_to_face_camera(self):
        alignment = SUBJECT.resolve_face_subject_alignment(
            baseline_top_z=170.25,
            composed_top_z=171.0,
            camera_reference_top_z=175.75,
        )

        self.assertEqual("face_camera", alignment["reference_source"])
        self.assertEqual(4.75, alignment["subject_z_offset"])
        self.assertEqual(170.25, alignment["source_project_top_z"])

    def test_missing_camera_reference_preserves_legacy_alignment(self):
        alignment = SUBJECT.resolve_face_subject_alignment(
            baseline_top_z=170.25,
            composed_top_z=171.0,
        )

        self.assertEqual("source_project", alignment["reference_source"])
        self.assertEqual(-0.75, alignment["subject_z_offset"])


class FakeTransformDataBlock:
    def __init__(self):
        self.calls = []

    def SetData(self, parameter_id, time, value):
        self.calls.append((parameter_id, time, value))
        return FakeStatus()


class FakeTransformControl:
    def __init__(self, data_block):
        self.data_block = data_block

    def GetDataBlock(self):
        return self.data_block


class FakeTransformAvatar:
    def __init__(self):
        self.data_block = FakeTransformDataBlock()

    def GetControl(self, control_name):
        if control_name != "Transform":
            return None
        return FakeTransformControl(self.data_block)


class TransformEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.original_global = SUBJECT.RLPy.RGlobal
        self.original_variant = getattr(SUBJECT.RLPy, "RVariant", None)
        self.time_calls = []
        time_calls = self.time_calls

        class FakeGlobal:
            @staticmethod
            def GetStartTime():
                return "start"

            @staticmethod
            def ObjectModified(avatar, modification):
                return FakeStatus()

            @staticmethod
            def SetTime(*args):
                time_calls.append(args)
                return FakeStatus()

        SUBJECT.RLPy.RGlobal = FakeGlobal
        SUBJECT.RLPy.RVariant = lambda value: value

    def tearDown(self):
        SUBJECT.RLPy.RGlobal = self.original_global
        if self.original_variant is None:
            delattr(SUBJECT.RLPy, "RVariant")
        else:
            SUBJECT.RLPy.RVariant = self.original_variant

    def test_yaw_forces_scene_evaluation(self):
        avatar = FakeTransformAvatar()

        SUBJECT.set_avatar_yaw(avatar, 90.0)

        self.assertEqual([("start", True)], self.time_calls)
        self.assertEqual(
            "Rotation/RotationZ",
            avatar.data_block.calls[0][0],
        )

    def test_position_forces_scene_evaluation(self):
        avatar = FakeTransformAvatar()

        SUBJECT.set_avatar_position(avatar, position_y=8.0)

        self.assertEqual([("start", True)], self.time_calls)
        self.assertEqual(
            "Position/PositionY",
            avatar.data_block.calls[0][0],
        )

    def test_eye_state_stabilization_retries_stale_world_transform(self):
        expected = neutral_eye_state(world_z=165.0)
        states = iter(
            (
                neutral_eye_state(world_z=170.0),
                neutral_eye_state(world_z=165.0),
            )
        )
        original_force = SUBJECT.force_avatar_scene_evaluation
        original_capture = SUBJECT.capture_eye_integrity_state
        SUBJECT.force_avatar_scene_evaluation = (
            lambda avatar, settle_seconds=1.0: None
        )
        SUBJECT.capture_eye_integrity_state = lambda avatar: next(states)
        try:
            actual, comparison, records = (
                SUBJECT.stabilize_neutral_eye_state(
                    object(),
                    expected,
                    attempts=4,
                )
            )
        finally:
            SUBJECT.force_avatar_scene_evaluation = original_force
            SUBJECT.capture_eye_integrity_state = original_capture

        self.assertEqual(expected, actual)
        self.assertTrue(comparison["matches"])
        self.assertEqual([False, True], [
            item["matches"] for item in records
        ])

    def test_stable_eye_capture_requires_two_matching_samples(self):
        stale = neutral_eye_state(world_z=170.0)
        stable = neutral_eye_state(world_z=165.0)
        states = iter((stale, stable, stable))
        original_force = SUBJECT.force_avatar_scene_evaluation
        original_capture = SUBJECT.capture_eye_integrity_state
        SUBJECT.force_avatar_scene_evaluation = (
            lambda avatar, settle_seconds=1.0: None
        )
        SUBJECT.capture_eye_integrity_state = lambda avatar: next(states)
        try:
            actual, records = SUBJECT.capture_stable_neutral_eye_state(
                object(),
                attempts=4,
            )
        finally:
            SUBJECT.force_avatar_scene_evaluation = original_force
            SUBJECT.capture_eye_integrity_state = original_capture

        self.assertEqual(stable, actual)
        self.assertEqual(
            [None, False, True],
            [item["matches"] for item in records],
        )

    def test_face_pose_validation_uses_project_start_frame(self):
        timeline = SUBJECT.face_identity_validation_timeline(0, 0)

        self.assertEqual(
            {
                "clip_start_frame": 1,
                "pose_frame": 10,
                "validation_end_frame": 41,
            },
            timeline,
        )

    def test_face_pose_validation_rejects_timeline_over_pose_frame(self):
        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "requires a free pose frame",
        ):
            SUBJECT.face_identity_validation_timeline(0, 10)

    def test_face_pose_validation_accepts_short_existing_timeline(self):
        timeline = SUBJECT.face_identity_validation_timeline(0, 5)

        self.assertEqual(6, timeline["clip_start_frame"])
        self.assertEqual(10, timeline["pose_frame"])
        self.assertEqual(46, timeline["validation_end_frame"])

    def test_native_viewport_selection_prefers_inner_center_window(self):
        main = {
            "global_x": 0,
            "global_y": 0,
            "height": 1500,
            "width": 2560,
        }
        records = [
            {
                "area": 1200000,
                "class_name": "Qt5152QWindowOwnDCIcon",
                "global_x": 0,
                "global_y": 280,
                "height": 1200,
                "hwnd": 1,
                "visible": True,
                "width": 1000,
            },
            {
                "area": 778240,
                "class_name": "Qt5152QWindowIcon",
                "global_x": 1060,
                "global_y": 240,
                "height": 1024,
                "hwnd": 2,
                "visible": True,
                "width": 760,
            },
            {
                "area": 715680,
                "class_name": "Qt5152QWindowIcon",
                "global_x": 1080,
                "global_y": 240,
                "height": 994,
                "hwnd": 3,
                "visible": True,
                "width": 720,
            },
        ]

        selected = SUBJECT.select_native_viewport_record(main, records)

        self.assertEqual(3, selected["hwnd"])

    def test_expression_weight_reader_accepts_nested_status_result(self):
        component = types.SimpleNamespace(
            GetExpressionWeights=lambda time, names: (
                FakeStatus(),
                [0.25, 0.75],
            )
        )

        weights = SUBJECT.expression_weights_at(
            component,
            object(),
            ["left", "right"],
        )

        self.assertEqual([0.25, 0.75], weights)


class FakeShapingComponent:
    def __init__(self):
        self.categories = {
            "Actor/Head/Eye/General": [
                ("identity_eye", "Eye Width"),
            ],
            "Actor/Head/Nose/General": [
                ("identity_nose", "Nose Width"),
            ],
            "Actor Parts/CC_Base_EyeOcclusion": [
                ("eye_occlusion", "Inner Height"),
            ],
            "Actor Parts/CC_Base_Eye/Eye/BodyFit": [
                ("bodyfit_eyeball", "BodyFit Eyeball"),
            ],
            "Actor Parts/CC_Base_Eye/Eye/Primary": [
                ("primary_eyeball", "Primary Eyeball"),
            ],
            "Actor Parts/CC_Base_TearLine": [
                ("tearline", "Tearline Inner Height"),
            ],
            "Actor/Expression/Blink": [
                ("blink", "Eye Blink"),
            ],
        }
        self.weights = {
            "identity_eye": 0.2,
            "identity_nose": 0.7,
            "eye_occlusion": 0.42,
            "bodyfit_eyeball": 0.7,
            "primary_eyeball": 0.0,
            "tearline": 0.31,
            "blink": 0.0,
        }
        self.set_calls = []

    def GetShapingMorphCatergoryNames(self):
        return list(self.categories)

    def GetShapingMorphIDs(self, category):
        return [item[0] for item in self.categories[category]]

    def GetShapingMorphDisplayNames(self, category):
        return [item[1] for item in self.categories[category]]

    def GetShapingMorphWeight(self, morph_id):
        return self.weights[morph_id]

    def GetShapingMorphMinMax(self, morph_id):
        return Bounds()

    def SetShapingMorphWeight(self, morph_id, weight):
        self.weights[morph_id] = float(weight)
        self.set_calls.append((morph_id, float(weight)))
        return FakeStatus()


class FakeAvatar:
    def __init__(self, component):
        self.component = component

    def GetAvatarShapingComponent(self):
        return self.component


class FakeWrinkleMaterialComponent:
    def __init__(self):
        self.calls = []

    def SetWrinkleDetailStrength(self, face_part, strength):
        self.calls.append((face_part, float(strength)))
        return FakeStatus()


class FakeWrinkleAvatar:
    def __init__(self, component):
        self.component = component

    def GetMaterialComponent(self):
        return self.component


class FaceIdentityApplicationTests(unittest.TestCase):
    def test_facial_hair_supports_beard_avatar_part_or_scene_object(self):
        self.assertEqual(
            SUBJECT.REPLACEABLE_AVATAR_PART_SLOTS["facial_hair"],
            "EAvatarPartType_Beard",
        )
        self.assertIn(
            "facial_hair",
            SUBJECT.DUAL_REPRESENTATION_AVATAR_PART_SLOTS,
        )

    def test_body_application_mode_defaults_to_raw_weights(self):
        self.assertEqual(
            SUBJECT.resolve_body_application_mode({}, {}),
            "raw_morph_weights",
        )

    def test_body_application_mode_accepts_library_and_preset_override(self):
        library = {"body_application_mode": "source_project"}
        self.assertEqual(
            SUBJECT.resolve_body_application_mode(library, {}),
            "source_project",
        )
        self.assertEqual(
            SUBJECT.resolve_body_application_mode(
                library,
                {"body_application_mode": "raw_morph_weights"},
            ),
            "raw_morph_weights",
        )

    def test_body_application_mode_rejects_unknown_value(self):
        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "Unsupported body_application_mode",
        ):
            SUBJECT.resolve_body_application_mode(
                {"body_application_mode": "unknown"},
                {},
            )

    def test_only_owned_identity_morphs_are_reset_or_written(self):
        component = FakeShapingComponent()
        avatar = FakeAvatar(component)

        result = SUBJECT.apply_target_face(
            avatar,
            [{"id": "identity_eye", "weight": -0.3}],
            {"identity_eye", "identity_nose"},
        )

        self.assertAlmostEqual(component.weights["identity_eye"], -0.3)
        self.assertAlmostEqual(component.weights["identity_nose"], 0.0)
        self.assertAlmostEqual(component.weights["eye_occlusion"], 0.42)
        self.assertAlmostEqual(component.weights["tearline"], 0.31)
        self.assertEqual(
            {item[0] for item in component.set_calls},
            {"identity_eye", "identity_nose"},
        )
        self.assertIn("eye_occlusion", result["preserved_face_morph_ids"])
        self.assertNotIn(
            "eye_occlusion",
            {item["id"] for item in result["changed"]},
        )

    def test_v3_local_application_preserves_every_unlisted_morph(self):
        component = FakeShapingComponent()
        avatar = FakeAvatar(component)

        result = SUBJECT.apply_local_face_morphs(
            avatar,
            [
                {
                    "baseline_weight": 0.2,
                    "id": "identity_eye",
                    "weight": -0.3,
                }
            ],
            {"identity_eye", "identity_nose"},
        )

        self.assertAlmostEqual(component.weights["identity_eye"], -0.3)
        self.assertAlmostEqual(component.weights["identity_nose"], 0.7)
        self.assertAlmostEqual(component.weights["eye_occlusion"], 0.42)
        self.assertAlmostEqual(component.weights["tearline"], 0.31)
        self.assertEqual(component.set_calls, [("identity_eye", -0.3)])
        self.assertEqual(result["baseline_mismatch_count"], 0)
        self.assertEqual(result["written_morph_ids"], ["identity_eye"])

    def test_primary_support_replaces_only_active_actor_part_domain(self):
        component = FakeShapingComponent()
        avatar = FakeAvatar(component)

        result = SUBJECT.apply_primary_head_support(
            avatar,
            [
                {
                    "categories": [
                        "Actor Parts",
                        "Actor Parts/CC_Base_Eye",
                    ],
                    "id": "primary_eyeball",
                    "weight": 1.0,
                }
            ],
            [
                {
                    "categories": [
                        "Actor Parts",
                        "Actor Parts/CC_Base_Eye",
                    ],
                    "id": "bodyfit_eyeball",
                    "weight": 0.7,
                },
                {
                    "categories": [
                        "Actor Parts",
                        "Actor Parts/CC_Base_EyeOcclusion",
                    ],
                    "id": "eye_occlusion",
                    "weight": 0.42,
                },
            ],
        )

        self.assertAlmostEqual(component.weights["bodyfit_eyeball"], 0.0)
        self.assertAlmostEqual(component.weights["primary_eyeball"], 1.0)
        self.assertAlmostEqual(component.weights["eye_occlusion"], 0.42)
        self.assertAlmostEqual(component.weights["tearline"], 0.31)
        self.assertEqual(
            result["replacement_domain_ids"],
            [
                "bodyfit_eyeball",
                "primary_eyeball",
            ],
        )

    def test_v3_local_application_rejects_primary_baseline_drift(self):
        component = FakeShapingComponent()
        avatar = FakeAvatar(component)

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "baseline mismatch",
        ):
            SUBJECT.apply_local_face_morphs(
                avatar,
                [
                    {
                        "baseline_weight": 0.0,
                        "id": "identity_eye",
                        "weight": -0.3,
                    }
                ],
                {"identity_eye", "identity_nose"},
            )

    def test_teeth_expression_targets_resolve_cc5_extended_names(self):
        targets = SUBJECT.resolve_teeth_expression_targets(
            [
                "Brow_Raise_Inner_L",
                "Mouth_Corner_Pull_L",
                "Mouth_Corner_Pull_R",
                "Mouth_UpperLip_Raise_L",
                "Mouth_UpperLip_Raise_R",
                "Mouth_LowerLip_Depress_L",
                "Mouth_LowerLip_Depress_R",
                "Mouth_Stretch_L",
                "Mouth_Stretch_R",
                "Jaw_Open",
            ]
        )

        self.assertEqual(targets["jaw_open"], "Jaw_Open")
        self.assertEqual(
            targets["smile"],
            ["Mouth_Corner_Pull_L", "Mouth_Corner_Pull_R"],
        )
        self.assertEqual(len(targets["oral_reveal"]), 6)

    def test_teeth_expression_targets_accept_combined_smile(self):
        targets = SUBJECT.resolve_teeth_expression_targets(
            ["Mouth Smile", "Mouth Open"]
        )

        self.assertEqual(targets["jaw_open"], "Mouth Open")
        self.assertEqual(targets["smile"], ["Mouth Smile"])

    def test_teeth_expression_targets_reject_missing_bilateral_smile(self):
        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "bilateral smile",
        ):
            SUBJECT.resolve_teeth_expression_targets(
                ["Jaw_Open", "Mouth_Smile_L"]
            )

    def test_facial_hair_visibility_profile_requires_matching_domain(self):
        plan = SUBJECT.resolve_appearance_validation_plan(
            {
                "appearance_validation_plan": {
                    "domain": "facial_hair",
                    "pose_profile": (
                        SUBJECT.FACIAL_HAIR_VISIBILITY_PROFILE
                    ),
                }
            }
        )
        self.assertEqual(plan["domain"], "facial_hair")

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "facial_hair domain",
        ):
            SUBJECT.resolve_appearance_validation_plan(
                {
                    "appearance_validation_plan": {
                        "domain": "scalp_hair",
                        "pose_profile": (
                            SUBJECT.FACIAL_HAIR_VISIBILITY_PROFILE
                        ),
                    }
                }
            )

    def test_scalp_hair_visibility_profile_requires_matching_domain(self):
        plan = SUBJECT.resolve_appearance_validation_plan(
            {
                "appearance_validation_plan": {
                    "domain": "scalp_hair",
                    "pose_profile": (
                        SUBJECT.SCALP_HAIR_VISIBILITY_PROFILE
                    ),
                }
            }
        )
        self.assertEqual(plan["domain"], "scalp_hair")

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "scalp_hair domain",
        ):
            SUBJECT.resolve_appearance_validation_plan(
                {
                    "appearance_validation_plan": {
                        "domain": "facial_hair",
                        "pose_profile": (
                            SUBJECT.SCALP_HAIR_VISIBILITY_PROFILE
                        ),
                    }
                }
            )

    def test_asset_load_pacing_resolves_slot_overrides(self):
        pacing = SUBJECT.resolve_asset_load_pacing(
            {
                "appearance_validation_plan": {
                    "asset_load_pacing": {
                        "default_after_seconds": 2,
                        "default_before_seconds": 1,
                        "slots": {
                            "scalp_hair": {
                                "after_seconds": 12,
                                "before_seconds": 8,
                            }
                        },
                    },
                    "domain": "scalp_hair",
                }
            }
        )
        self.assertEqual(
            SUBJECT.asset_load_pacing_for_slot(
                pacing, "scalp_hair"
            ),
            {
                "after_seconds": 12.0,
                "before_seconds": 8.0,
            },
        )
        self.assertEqual(
            SUBJECT.asset_load_pacing_for_slot(pacing, "upper"),
            {
                "after_seconds": 2.0,
                "before_seconds": 1.0,
            },
        )

    def test_asset_load_pacing_rejects_unbounded_delay(self):
        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "between 0 and 60 seconds",
        ):
            SUBJECT.resolve_asset_load_pacing(
                {
                    "appearance_validation_plan": {
                        "asset_load_pacing": {
                            "default_after_seconds": 61,
                        },
                        "domain": "scalp_hair",
                    }
                }
            )

    def test_integrated_assembly_can_request_static_hair_views(self):
        plan = SUBJECT.resolve_appearance_validation_plan(
            {
                "appearance_validation_plan": {
                    "domain": "face_identity",
                    "integrated_facial_assembly_validation": {
                        "render_static_hair_views": True,
                    },
                    "pose_profile": (
                        SUBJECT.FACE_IDENTITY_SAFETY_PROFILE
                    ),
                }
            }
        )

        self.assertTrue(
            SUBJECT.render_static_hair_views_enabled(plan)
        )
        self.assertFalse(
            SUBJECT.render_static_hair_views_enabled(
                {
                    "domain": "face_identity",
                    "pose_profile": (
                        SUBJECT.FACE_IDENTITY_SAFETY_PROFILE
                    ),
                }
            )
        )

    def test_dynamic_wrinkle_validation_is_normalized(self):
        plan = SUBJECT.resolve_appearance_validation_plan(
            {
                "appearance_validation_plan": {
                    "domain": "face_identity",
                    "dynamic_wrinkle_validation": {
                        "baseline_strength": 0,
                        "pose_ids": [
                            "blink_bilateral_front",
                            "smile_front",
                        ],
                        "target_strength": 1,
                    },
                    "pose_profile": (
                        SUBJECT.FACE_IDENTITY_SAFETY_PROFILE
                    ),
                }
            }
        )

        self.assertEqual(
            SUBJECT.resolve_dynamic_wrinkle_validation(plan),
            {
                "baseline_strength": 0.0,
                "pose_ids": [
                    "blink_bilateral_front",
                    "smile_front",
                ],
                "target_strength": 1.0,
            },
        )

    def test_dynamic_wrinkle_validation_rejects_unknown_pose(self):
        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "Unsupported dynamic wrinkle pose IDs",
        ):
            SUBJECT.resolve_appearance_validation_plan(
                {
                    "appearance_validation_plan": {
                        "domain": "face_identity",
                        "dynamic_wrinkle_validation": {
                            "baseline_strength": 0,
                            "pose_ids": ["jaw_open_front"],
                            "target_strength": 1,
                        },
                        "pose_profile": (
                            SUBJECT.FACE_IDENTITY_SAFETY_PROFILE
                        ),
                    }
                }
            )

    def test_wrinkle_strength_updates_every_supported_face_region(self):
        for index, constant_name in enumerate(
            SUBJECT.WRINKLE_FACE_PART_CONSTANTS
        ):
            setattr(SUBJECT.RLPy, constant_name, index)
        component = FakeWrinkleMaterialComponent()
        result = SUBJECT.set_dynamic_wrinkle_strength(
            FakeWrinkleAvatar(component),
            0.5,
        )

        self.assertEqual(
            len(component.calls),
            len(SUBJECT.WRINKLE_FACE_PART_CONSTANTS),
        )
        self.assertTrue(
            all(strength == 0.5 for _, strength in component.calls)
        )
        self.assertEqual(result["strength"], 0.5)

    def test_eyebrow_expression_targets_resolve_cc5_names(self):
        targets = SUBJECT.resolve_eyebrow_expression_targets(
            [
                "Brow_Down_L",
                "Brow_Down_R",
                "Brow_Raise_In_L",
                "Brow_Raise_In_R",
                "Brow_Raise_Outer_L",
                "Brow_Raise_Outer_R",
            ]
        )

        self.assertEqual(
            targets["raise_bilateral"],
            [
                "Brow_Raise_In_L",
                "Brow_Raise_In_R",
                "Brow_Raise_Outer_L",
                "Brow_Raise_Outer_R",
            ],
        )
        self.assertEqual(
            targets["down_bilateral"],
            ["Brow_Down_L", "Brow_Down_R"],
        )

    def test_eyelash_expression_targets_resolve_cc5_names(self):
        targets = SUBJECT.resolve_eyelash_expression_targets(
            [
                "Eye_Blink_L",
                "Eye_Blink_R",
                "Eye_Widen_L",
                "Eye_Widen_R",
                "C_BlinkL",
                "C_BlinkR",
                "Eyelashes_Down_IN_L",
                "Eyelashes_Down_OUT_L",
                "Eyelashes_Down_IN_R",
                "Eyelashes_Down_OUT_R",
                "Eyelashes_Up_IN_L",
                "Eyelashes_Up_OUT_L",
                "Eyelashes_Up_IN_R",
                "Eyelashes_Up_OUT_R",
            ]
        )

        self.assertEqual(
            targets["blink_bilateral"],
            [
                "Eye_Blink_L",
                "C_BlinkL",
                "Eyelashes_Down_IN_L",
                "Eyelashes_Down_OUT_L",
                "Eye_Blink_R",
                "C_BlinkR",
                "Eyelashes_Down_IN_R",
                "Eyelashes_Down_OUT_R",
            ],
        )
        self.assertEqual(
            targets["blink_left"],
            [
                "Eye_Blink_L",
                "C_BlinkL",
                "Eyelashes_Down_IN_L",
                "Eyelashes_Down_OUT_L",
            ],
        )
        self.assertEqual(
            targets["widen_bilateral"],
            [
                "Eye_Widen_L",
                "Eyelashes_Up_IN_L",
                "Eyelashes_Up_OUT_L",
                "Eye_Widen_R",
                "Eyelashes_Up_IN_R",
                "Eyelashes_Up_OUT_R",
            ],
        )

    def test_unowned_target_is_rejected(self):
        component = FakeShapingComponent()
        avatar = FakeAvatar(component)

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "outside identity ownership",
        ):
            SUBJECT.apply_target_face(
                avatar,
                [{"id": "eye_occlusion", "weight": 0.1}],
                {"identity_eye", "identity_nose"},
            )

    def test_context_uses_primary_preset_and_same_sex_identity_union(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = pathlib.Path(root)
            head_path = root_path / "Primary.ccAvatarPreset"
            head_path.write_bytes(b"head")
            seed_path = root_path / "seeds.json"
            policy_path = root_path / "policy.json"
            seed_path.write_text(
                json.dumps(
                    {
                        "library_id": "seeds",
                        "seeds": [
                            {
                                "seed_id": "F_PRIMARY",
                                "sex": "female",
                                "source_head_preset": {
                                    "path": str(head_path),
                                    "sha256": "abc",
                                },
                                "target_face_morphs": [
                                    {"id": "female_seed_eye", "weight": 1.0}
                                ],
                            },
                            {
                                "seed_id": "M_PRIMARY",
                                "sex": "male",
                                "source_head_preset": {
                                    "path": str(head_path),
                                    "sha256": "def",
                                },
                                "target_face_morphs": [
                                    {"id": "male_seed_eye", "weight": 1.0}
                                ],
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            policy_path.write_text(
                json.dumps(
                    {
                        "policy_id": "identity",
                        "approved_morphs": [{"id": "local_eye_width"}],
                    }
                ),
                encoding="utf-8",
            )
            context = SUBJECT.resolve_face_application_context(
                {
                    "face_resources": {
                        "seed_library": str(seed_path),
                        "identity_policy": str(policy_path),
                    }
                },
                {
                    "sex": "female",
                    "face_generation": {"primary_seed_id": "F_PRIMARY"},
                    "target_face_morphs": [
                        {"id": "female_seed_eye", "weight": 0.7},
                        {"id": "local_eye_width", "weight": -0.2},
                    ],
                },
            )

        self.assertEqual(context["primary_seed_id"], "F_PRIMARY")
        self.assertEqual(
            context["source_head_preset"]["path"],
            os.path.realpath(str(head_path)),
        )
        self.assertIn("female_seed_eye", context["owned_morph_ids"])
        self.assertIn("local_eye_width", context["owned_morph_ids"])
        self.assertNotIn("male_seed_eye", context["owned_morph_ids"])

    def test_v3_context_owns_only_explicit_local_morphs(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = pathlib.Path(root)
            head_path = root_path / "Primary.ccAvatarPreset"
            head_path.write_bytes(b"complete-head")
            head_hash = hashlib.sha256(b"complete-head").hexdigest()
            profile_path = root_path / "Primary.ccFacialProfile"
            profile_path.write_bytes(b"facial-profile")
            profile_hash = hashlib.sha256(
                b"facial-profile"
            ).hexdigest()
            seed_path = root_path / "seeds.json"
            policy_path = root_path / "policy.json"
            seed_path.write_text(
                json.dumps(
                    {
                        "library_id": "seeds",
                        "facial_profile_policy": {
                            "application_mode": (
                                "selected_avatar_content_load"
                            ),
                            "default_by_sex": {
                                "female": {
                                    "path": str(profile_path),
                                    "sha256": profile_hash,
                                }
                            },
                        },
                        "seeds": [
                            {
                                "seed_id": "F_PRIMARY",
                                "sex": "female",
                                "source_head_preset": {
                                    "path": str(head_path),
                                    "sha256": head_hash,
                                },
                                "target_face_morphs": [
                                    {
                                        "categories": [
                                            "Actor",
                                            "Actor/Head",
                                        ],
                                        "id": "local_eye_width",
                                        "weight": 0.2,
                                    },
                                    {
                                        "categories": [
                                            "Actor Parts",
                                            "Actor Parts/CC_Base_Eye",
                                        ],
                                        "id": "support_blink",
                                        "weight": 1.0,
                                    },
                                ],
                                "face_delta": [
                                    {
                                        "after": 0.2,
                                        "before": 0.0,
                                        "delta": 0.2,
                                        "id": "local_eye_width",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            policy_path.write_text(
                json.dumps(
                    {
                        "policy_id": "identity",
                        "approved_morphs": [
                            {"id": "local_eye_width"}
                        ],
                        "neutral_policy": {"neutral_seed_ids": []},
                    }
                ),
                encoding="utf-8",
            )
            context = SUBJECT.resolve_face_application_context(
                {
                    "face_resources": {
                        "seed_library": str(seed_path),
                        "identity_policy": str(policy_path),
                    }
                },
                {
                    "sex": "female",
                    "face_generation": {
                        "pipeline": (
                            SUBJECT.COMPLETE_PRIMARY_FACE_PIPELINE
                        ),
                        "primary_seed_id": "F_PRIMARY",
                    },
                    "source_head_preset": {
                        "path": str(head_path),
                        "sha256": head_hash,
                    },
                    "source_facial_profile": {
                        "application_mode": (
                            "selected_avatar_content_load"
                        ),
                        "path": str(profile_path),
                        "policy_binding": "default_by_sex",
                        "sha256": profile_hash,
                    },
                    "local_face_morphs": [
                        {
                            "baseline_weight": 0.2,
                            "id": "local_eye_width",
                            "weight": -0.1,
                        }
                    ],
                },
            )

        self.assertEqual(
            context["mode"], SUBJECT.COMPLETE_PRIMARY_FACE_PIPELINE
        )
        self.assertEqual(
            context["source_facial_profile"]["path"],
            os.path.realpath(str(profile_path)),
        )
        self.assertEqual(
            context["modified_morph_ids"], ["local_eye_width"]
        )
        self.assertEqual(
            context["modifiable_morph_ids"], ["local_eye_width"]
        )
        self.assertNotIn(
            "support_blink", context["primary_identity_morph_ids"]
        )
        self.assertEqual(
            context["primary_expected_head_morphs"],
            [{"id": "local_eye_width", "weight": 0.2}],
        )
        self.assertEqual(
            [
                item["id"]
                for item in context["primary_support_target_morphs"]
            ],
            ["support_blink"],
        )

    def test_content_reference_rejects_policy_binding_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            profile_path = pathlib.Path(root) / "Profile.ccFacialProfile"
            profile_path.write_bytes(b"profile")
            with self.assertRaisesRegex(
                SUBJECT.ReconstructionError,
                "binding differs from policy",
            ):
                SUBJECT.require_matching_content_reference(
                    {
                        "application_mode": (
                            "selected_avatar_content_load"
                        ),
                        "path": str(profile_path),
                        "policy_binding": "default_by_sex",
                        "sha256": "a" * 64,
                    },
                    os.path.realpath(str(profile_path)),
                    "a" * 64,
                    "Primary face Facial Profile",
                    application_mode=(
                        "selected_avatar_content_load"
                    ),
                    policy_binding="seed_override",
                )

    def test_profile_file_types_are_not_interchangeable(self):
        self.assertEqual(
            SUBJECT.require_file_extension(
                "Identity.ccFacialProfile",
                ".ccFacialProfile",
                "Facial Profile",
            ),
            "Identity.ccFacialProfile",
        )
        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "must use the .rlWrinkle file type",
        ):
            SUBJECT.require_file_extension(
                "Identity.ccFacialProfile",
                ".rlWrinkle",
                "Wrinkle profile probe",
            )

    def test_face_identity_safety_targets_cover_dynamic_gate(self):
        targets = SUBJECT.resolve_face_identity_safety_targets(
            [
                "Eye_Blink_L",
                "Eye_Blink_R",
                "C_BlinkL",
                "C_BlinkR",
                "Eyelashes_Down_IN_L",
                "Eyelashes_Down_OUT_L",
                "Eyelashes_Down_IN_R",
                "Eyelashes_Down_OUT_R",
                "Eye_Widen_L",
                "Eye_Widen_R",
                "Eyelashes_Up_IN_L",
                "Eyelashes_Up_OUT_L",
                "Eyelashes_Up_IN_R",
                "Eyelashes_Up_OUT_R",
                "Eye_Look_Left_L",
                "Eye_Look_Left_R",
                "Eye_Look_Right_L",
                "Eye_Look_Right_R",
                "Eye_Look_Up_L",
                "Eye_Look_Up_R",
                "Eye_Look_Down_L",
                "Eye_Look_Down_R",
                "Eye_Squint_Inner_L",
                "Eye_Squint_Inner_R",
                "Brow_Down_L",
                "Brow_Down_R",
                "Brow_Raise_In_L",
                "Brow_Raise_In_R",
                "Brow_Raise_Outer_L",
                "Brow_Raise_Outer_R",
                "Mouth_Corner_Pull_L",
                "Mouth_Corner_Pull_R",
                "Jaw_Open",
            ]
        )

        self.assertEqual(len(targets["blink_bilateral"]), 8)
        self.assertEqual(len(targets["gaze_down"]), 2)
        self.assertEqual(len(targets["squint_bilateral"]), 2)
        self.assertEqual(len(targets["smile"]), 2)

    def test_quality_benchmark_supports_cc4_extended_base_blinks(self):
        targets = SUBJECT.resolve_quality_benchmark_targets(
            [
                "Eye_Blink_L",
                "Eye_Blink_R",
                "Mouth_Corner_Pull_L",
                "Mouth_Corner_Pull_R",
                "Jaw_Open",
            ]
        )

        self.assertEqual(
            ["Eye_Blink_L", "Eye_Blink_R"],
            targets["blink_bilateral"],
        )
        self.assertEqual(
            "base_profile_only",
            targets["blink_correction_mode"],
        )
        self.assertEqual(6, len(targets["missing_optional_blink_target_ids"]))

    def test_quality_benchmark_uses_available_cc5_blink_corrections(self):
        targets = SUBJECT.resolve_quality_benchmark_targets(
            [
                "Eye_Blink_L",
                "Eye_Blink_R",
                "C_BlinkL",
                "C_BlinkR",
                "Eyelashes_Down_IN_L",
                "Eyelashes_Down_OUT_L",
                "Eyelashes_Down_IN_R",
                "Eyelashes_Down_OUT_R",
                "Mouth_Corner_Pull_L",
                "Mouth_Corner_Pull_R",
                "Jaw_Open",
            ]
        )

        self.assertEqual(8, len(targets["blink_bilateral"]))
        self.assertEqual(
            "base_plus_available_correctives",
            targets["blink_correction_mode"],
        )
        self.assertEqual([], targets["missing_optional_blink_target_ids"])

    def test_profile_upgrade_builds_tiered_supported_smiles(self):
        pose_specs, targets = SUBJECT.profile_upgrade_pose_specs(
            [
                "Eye_Blink_L",
                "Eye_Blink_R",
                "C_BlinkL",
                "C_BlinkR",
                "Eyelashes_Down_IN_L",
                "Eyelashes_Down_OUT_L",
                "Eyelashes_Down_IN_R",
                "Eyelashes_Down_OUT_R",
                "Eye_Cheek_Raise_L",
                "Eye_Cheek_Raise_R",
                "Eye_Squint_Inner_L",
                "Eye_Squint_Inner_R",
                "Mouth_Corner_Pull_L",
                "Mouth_Corner_Pull_R",
                "Jaw_Open",
            ]
        )

        self.assertEqual(
            {
                "cheek_raise_left": "Eye_Cheek_Raise_L",
                "cheek_raise_right": "Eye_Cheek_Raise_R",
                "squint_inner_left": "Eye_Squint_Inner_L",
                "squint_inner_right": "Eye_Squint_Inner_R",
            },
            targets["natural_smile_support"],
        )
        subtle = pose_specs["smile_subtle_front"]
        medium = pose_specs["smile_medium_front"]
        broad = pose_specs["smile_broad_front"]
        self.assertNotIn("Jaw_Open", subtle)
        self.assertEqual(0.04, medium["Jaw_Open"])
        self.assertEqual(0.10, broad["Jaw_Open"])
        self.assertLess(
            subtle["Mouth_Corner_Pull_L"],
            medium["Mouth_Corner_Pull_L"],
        )
        self.assertLess(
            medium["Mouth_Corner_Pull_L"],
            broad["Mouth_Corner_Pull_L"],
        )

    def test_profile_upgrade_smiles_remain_valid_without_optional_support(self):
        pose_specs, targets = SUBJECT.profile_upgrade_pose_specs(
            [
                "Eye_Blink_L",
                "Eye_Blink_R",
                "Mouth_Corner_Pull_L",
                "Mouth_Corner_Pull_R",
                "Jaw_Open",
            ]
        )

        self.assertEqual({}, targets["natural_smile_support"])
        self.assertEqual(
            {"Mouth_Corner_Pull_L", "Mouth_Corner_Pull_R"},
            set(pose_specs["smile_subtle_front"]),
        )

    def test_vector_filter_includes_owned_entries_from_all_groups(self):
        vectors = {
            "groups": {
                "face": {
                    "entries": [
                        {"id": "identity_eye", "weight": 0.2},
                        {"id": "eye_occlusion", "weight": 0.4},
                    ]
                },
                "other": {
                    "entries": [{"id": "identity_other", "weight": 0.1}]
                },
            }
        }
        selected = SUBJECT.vector_entries_for_ids(
            vectors,
            {"identity_eye", "identity_other"},
        )
        self.assertEqual(
            [item["id"] for item in selected],
            ["identity_eye", "identity_other"],
        )

    def test_head_preset_domains_keep_actor_parts_as_support(self):
        vectors = {
            "groups": {
                "face": {
                    "entries": [
                        {
                            "categories": ["Actor", "Actor/Head"],
                            "id": "primary_head",
                            "weight": 1.0,
                        },
                        {
                            "categories": [
                                "Actor Parts",
                                "Actor Parts/CC_Base_Eye",
                            ],
                            "id": "bodyfit_eyeball_support",
                            "weight": 0.7,
                        },
                    ]
                },
                "other": {
                    "entries": [
                        {
                            "categories": ["Actor/Support"],
                            "id": "other_support",
                            "weight": 0.3,
                        }
                    ]
                },
            }
        }

        self.assertEqual(
            [
                item["id"]
                for item in SUBJECT.head_preset_identity_entries(vectors)
            ],
            ["primary_head"],
        )
        self.assertEqual(
            [
                item["id"]
                for item in SUBJECT.head_preset_support_entries(vectors)
            ],
            ["bodyfit_eyeball_support", "other_support"],
        )


if __name__ == "__main__":
    unittest.main()
