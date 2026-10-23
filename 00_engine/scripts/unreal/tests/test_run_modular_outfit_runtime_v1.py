from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run_modular_outfit_runtime_v1.py"
SPEC = importlib.util.spec_from_file_location(
    "run_modular_outfit_runtime_v1_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RuntimeCommandTests(unittest.TestCase):
    def test_build_command_sets_bounded_globals(self) -> None:
        command = MODULE.runtime_command("build_bodyfit", "M02_Average", None)
        self.assertIn("DM_MODULAR_RUNTIME_MODE='build_bodyfit'", command)
        self.assertIn("DM_MODULAR_BODYFIT_ID='M02_Average'", command)
        self.assertIn("__file__=", command)
        self.assertIn("ue_build_modular_outfit_runtime_v1.py", command)
        self.assertNotIn("DM_MODULAR_VARIANT_ID", command)

    def test_stage_command_includes_qualified_variant(self) -> None:
        command = MODULE.runtime_command(
            "stage_variant", "F02_Average", "F_BIKINI_LAYERED::cover_barefoot"
        )
        self.assertIn("DM_MODULAR_RUNTIME_MODE='stage_variant'", command)
        self.assertIn(
            "DM_MODULAR_VARIANT_ID='F_BIKINI_LAYERED::cover_barefoot'", command
        )

    def test_motion_command_uses_the_motion_worker_contract(self) -> None:
        command = MODULE.motion_command(
            "validate_motion", "M02_Average", None
        )
        self.assertIn("DM_MODULAR_MOTION_MODE='validate_motion'", command)
        self.assertIn("__file__=", command)
        self.assertIn("ue_modular_outfit_motion_validation_v1.py", command)

    def test_review_command_uses_the_review_worker_contract(self) -> None:
        command = MODULE.review_command()
        self.assertIn("DM_BUILD_MODULAR_REVIEW_LEVEL=True", command)
        self.assertIn("__file__=", command)
        self.assertIn("ue_build_modular_outfit_review_level_v1.py", command)

    def test_default_selection_contains_both_average_bodyfits(self) -> None:
        self.assertEqual(
            MODULE.selected_bodyfits(None), ["M02_Average", "F02_Average"]
        )

    def test_duplicate_bodyfit_selection_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            MODULE.selected_bodyfits(["M02_Average", "M02_Average"])


if __name__ == "__main__":
    unittest.main()
