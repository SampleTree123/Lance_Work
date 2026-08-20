import importlib.util
import os
import pathlib
import sys
import types
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_validate_body_reconstruction.py"
)


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
        GetStartTime=lambda: 0,
        ObjectModified=lambda avatar, modification: FakeStatus(),
        SetTime=lambda time, force: FakeStatus(),
    )
    sys.modules["RLPy"] = rlpy

    pyside = types.ModuleType("PySide2")
    pyside.QtCore = types.SimpleNamespace()
    pyside.QtWidgets = types.SimpleNamespace(
        QApplication=types.SimpleNamespace(processEvents=lambda: None)
    )
    sys.modules["PySide2"] = pyside

    spec = importlib.util.spec_from_file_location(
        "cc_targeted_morph_initialization_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class FakeStatus:
    def IsError(self):
        return False

    def GetStatusCode(self):
        return 0


class Bounds:
    def __init__(self, minimum, maximum):
        self.first = minimum
        self.second = maximum


class LazyBoundsComponent:
    def __init__(self):
        self.catalog_primed = False

    def GetShapingMorphCatergoryNames(self):
        return ["Actor/Head"]

    def GetShapingMorphIDs(self, category):
        self.catalog_primed = True
        return ["cc embed morphs/embed_full_head9"]

    def GetShapingMorphDisplayNames(self, category):
        return ["Head Scale"]

    def GetShapingMorphMinMax(self, morph_id):
        minimum = -0.5 if self.catalog_primed else 0.0
        return Bounds(minimum, 1.0)

    def GetShapingMorphWeight(self, morph_id):
        return getattr(self, "weight", 0.0)

    def SetShapingMorphWeight(self, morph_id, weight):
        self.weight = float(weight)
        return FakeStatus()


class LazyNeckBoundsComponent(LazyBoundsComponent):
    MORPH_ID = "2019-08-30-20-14-55_neck height"

    def GetShapingMorphCatergoryNames(self):
        return ["Actor/Body/Neck"]

    def GetShapingMorphIDs(self, category):
        self.catalog_primed = True
        return [self.MORPH_ID]

    def GetShapingMorphDisplayNames(self, category):
        return ["Neck Height"]

    def GetShapingMorphMinMax(self, morph_id):
        minimum = -1.0 if self.catalog_primed else 0.0
        return Bounds(minimum, 1.0)


class CatalogFilterComponent(LazyBoundsComponent):
    def GetShapingMorphCatergoryNames(self):
        return ["Actor/Head/Headshot Morph 1000+"]

    def GetShapingMorphIDs(self, category):
        return ["skull_width_id", "nose_width_id"]

    def GetShapingMorphDisplayNames(self, category):
        return ["Skull Width", "Nose Width"]

    def GetShapingMorphMinMax(self, morph_id):
        return Bounds(-1.0, 1.0)


class MisreportedNeckBoundsComponent(LazyNeckBoundsComponent):
    def GetShapingMorphMinMax(self, morph_id):
        return Bounds(0.0, 1.0)


class MisreportedSkullBoundsComponent(MisreportedNeckBoundsComponent):
    MORPH_ID = "2019-08-13-15-25-44_skull height"


class FakeAvatar:
    def __init__(self, component):
        self.component = component

    def GetAvatarShapingComponent(self):
        return self.component


class TargetedMorphInitializationTests(unittest.TestCase):
    def test_filtered_morph_catalog_matches_display_and_records_bounds(self):
        avatar = FakeAvatar(CatalogFilterComponent())

        report = SUBJECT.capture_filtered_morph_catalog(avatar, ["skull"])

        self.assertEqual(2, report["catalog_morph_count"])
        self.assertEqual(1, report["matched_morph_count"])
        self.assertEqual("skull_width_id", report["entries"][0]["id"])
        self.assertEqual(-1.0, report["entries"][0]["minimum"])
        self.assertEqual(1.0, report["entries"][0]["maximum"])

    def test_filtered_morph_catalog_rejects_empty_terms(self):
        avatar = FakeAvatar(CatalogFilterComponent())

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "non-empty strings",
        ):
            SUBJECT.capture_filtered_morph_catalog(avatar, [""])

    def test_catalog_is_primed_before_signed_bounds_are_read(self):
        component = LazyBoundsComponent()
        avatar = FakeAvatar(component)

        self.assertEqual(
            0.0,
            component.GetShapingMorphMinMax(
                "cc embed morphs/embed_full_head9"
            ).first,
        )

        resolved_component, states = (
            SUBJECT._prepare_targeted_morph_states(
                avatar,
                {"cc embed morphs/embed_full_head9"},
            )
        )

        self.assertIs(component, resolved_component)
        self.assertTrue(component.catalog_primed)
        self.assertEqual(
            -0.5,
            states["cc embed morphs/embed_full_head9"]["minimum"],
        )

    def test_missing_targeted_morph_is_rejected(self):
        component = LazyBoundsComponent()
        avatar = FakeAvatar(component)

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "Targeted Morphs are unavailable",
        ):
            SUBJECT._prepare_targeted_morph_states(
                avatar,
                {"missing morph"},
            )

    def test_signed_embed_can_prove_a_target_beyond_reported_bounds(self):
        component = LazyBoundsComponent()
        avatar = FakeAvatar(component)
        original_settle = SUBJECT.settle_cc_ui
        SUBJECT.settle_cc_ui = lambda seconds: None
        try:
            states = SUBJECT._apply_targeted_morph_weights(
                component,
                avatar,
                {"cc embed morphs/embed_full_head9": -0.1},
                "test candidate",
            )
        finally:
            SUBJECT.settle_cc_ui = original_settle

        state = states["cc embed morphs/embed_full_head9"]
        self.assertAlmostEqual(-0.1, state["actual"])
        self.assertTrue(state["reported_out_of_bounds"])
        self.assertTrue(state["signed_embed_bounds_override"])

    def test_regular_morph_still_rejects_a_target_outside_bounds(self):
        component = LazyBoundsComponent()
        avatar = FakeAvatar(component)

        with self.assertRaisesRegex(
            SUBJECT.ReconstructionError,
            "is outside",
        ):
            SUBJECT._apply_targeted_morph_weights(
                component,
                avatar,
                {"regular morph": -0.1},
                "test candidate",
            )

    def test_regular_neck_bounds_are_primed_before_negative_target(self):
        component = LazyNeckBoundsComponent()
        avatar = FakeAvatar(component)
        component, states = SUBJECT._prepare_targeted_morph_states(
            avatar,
            {LazyNeckBoundsComponent.MORPH_ID},
        )
        original_settle = SUBJECT.settle_cc_ui
        SUBJECT.settle_cc_ui = lambda seconds: None
        try:
            applications = SUBJECT._apply_targeted_morph_weights(
                component,
                avatar,
                {LazyNeckBoundsComponent.MORPH_ID: -0.4},
                "height test",
            )
        finally:
            SUBJECT.settle_cc_ui = original_settle

        self.assertEqual(
            -1.0,
            states[LazyNeckBoundsComponent.MORPH_ID]["minimum"],
        )
        self.assertAlmostEqual(
            -0.4,
            applications[LazyNeckBoundsComponent.MORPH_ID]["actual"],
        )

    def test_known_neck_morph_can_prove_value_beyond_reported_bounds(self):
        component = MisreportedNeckBoundsComponent()
        avatar = FakeAvatar(component)
        original_settle = SUBJECT.settle_cc_ui
        SUBJECT.settle_cc_ui = lambda seconds: None
        try:
            applications = SUBJECT._apply_targeted_morph_weights(
                component,
                avatar,
                {MisreportedNeckBoundsComponent.MORPH_ID: -0.4},
                "height test",
            )
        finally:
            SUBJECT.settle_cc_ui = original_settle

        state = applications[MisreportedNeckBoundsComponent.MORPH_ID]
        self.assertAlmostEqual(-0.4, state["actual"])
        self.assertTrue(state["reported_bounds_override"])

    def test_production_single_morph_path_uses_known_neck_exception(self):
        component = MisreportedNeckBoundsComponent()
        avatar = FakeAvatar(component)

        application = SUBJECT.apply_single_morph_weight(
            avatar,
            MisreportedNeckBoundsComponent.MORPH_ID,
            -0.2,
            "production test",
        )

        self.assertAlmostEqual(-0.2, application["actual"])
        self.assertTrue(application["reported_bounds_override"])

    def test_review_path_uses_single_axis_proven_skull_exception(self):
        component = MisreportedSkullBoundsComponent()
        avatar = FakeAvatar(component)
        original_settle = SUBJECT.settle_cc_ui
        SUBJECT.settle_cc_ui = lambda seconds: None
        try:
            applications = SUBJECT._apply_targeted_morph_weights(
                component,
                avatar,
                {MisreportedSkullBoundsComponent.MORPH_ID: -0.3},
                "composition test",
            )
        finally:
            SUBJECT.settle_cc_ui = original_settle

        state = applications[MisreportedSkullBoundsComponent.MORPH_ID]
        self.assertAlmostEqual(-0.3, state["actual"])
        self.assertTrue(state["reported_bounds_override"])


if __name__ == "__main__":
    unittest.main()
