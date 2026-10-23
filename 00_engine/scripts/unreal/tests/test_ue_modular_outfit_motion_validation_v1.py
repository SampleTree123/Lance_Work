from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "ue_modular_outfit_motion_validation_v1.py"
)
sys.modules.setdefault("unreal", types.ModuleType("unreal"))
SPEC = importlib.util.spec_from_file_location(
    "ue_modular_outfit_motion_validation_v1_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FrozenMotionContractTests(unittest.TestCase):
    def test_core_motion_contract_allows_omitted_auxiliary_tracks(self) -> None:
        self.assertEqual(MODULE.MIN_CORE_BONE_TRACKS, 70)
        self.assertLess(MODULE.MIN_CORE_BONE_TRACKS, 108)

    def test_selects_one_existing_frozen_action_per_sex(self) -> None:
        required = MODULE.read_json(MODULE.REQUIRED_EXPORTS)
        female = MODULE.source_motion_spec(required, "female")
        male = MODULE.source_motion_spec(required, "male")
        self.assertEqual(female["action_id"], "ACT_F03_AUDIENCE_01")
        self.assertEqual(male["action_id"], "ACT_M02_AUDIENCE_01")
        self.assertTrue(MODULE.validate_source_motion(female).is_file())
        self.assertTrue(MODULE.validate_source_motion(male).is_file())

    def test_rejects_unknown_sex(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unsupported"):
            MODULE.source_motion_spec({"actions": []}, "unknown")

    def test_motion_destination_is_bodyfit_bounded(self) -> None:
        destination = MODULE.motion_destination(
            {"bodyfit_id": "M02_Average", "sex": "male"}
        )
        self.assertEqual(
            destination["asset"],
            "/Game/DataMake/Animations/CC5/ModularOutfitPilot/M02_Average/"
            "A_DM_M02_AUDIENCE_01_ModularPilot_v001",
        )


class VectorMathTests(unittest.TestCase):
    def test_vector_distance_uses_all_axes(self) -> None:
        self.assertAlmostEqual(
            MODULE.vector_distance(
                {"x": 0.0, "y": 0.0, "z": 0.0},
                {"x": 3.0, "y": 4.0, "z": 12.0},
            ),
            13.0,
        )

    def test_quaternion_angular_distance_is_sign_invariant(self) -> None:
        identity = {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
        negative_identity = {"x": 0.0, "y": 0.0, "z": 0.0, "w": -1.0}
        self.assertAlmostEqual(
            MODULE.quaternion_angular_distance_degrees(
                identity, negative_identity
            ),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
