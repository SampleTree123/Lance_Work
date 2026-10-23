from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run_modular_outfit_runtime_v2.py"
SPEC = importlib.util.spec_from_file_location(
    "run_modular_outfit_runtime_v2_under_test", SCRIPT
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RuntimeCommandV2Tests(unittest.TestCase):
    def test_build_command_uses_v002_worker_contract(self) -> None:
        command = MODULE.runtime_command("build_bodyfit", "M02_Average", None)
        self.assertIn("DM_MODULAR_RUNTIME_V2_MODE='build_bodyfit'", command)
        self.assertIn("DM_MODULAR_V2_BODYFIT_ID='M02_Average'", command)
        self.assertIn("ue_build_modular_outfit_runtime_v2.py", command)
        self.assertNotIn("DM_MODULAR_V2_VARIANT_ID", command)

    def test_stage_command_includes_qualified_variant(self) -> None:
        command = MODULE.runtime_command(
            "stage_variant", "F02_Average", "F_CASE::default"
        )
        self.assertIn(
            "DM_MODULAR_V2_VARIANT_ID='F_CASE::default'", command
        )

    def test_review_command_uses_v002_worker(self) -> None:
        command = MODULE.review_command()
        self.assertIn("DM_BUILD_MODULAR_REVIEW_LEVEL_V2=True", command)
        self.assertIn("ue_build_modular_outfit_review_level_v2.py", command)


if __name__ == "__main__":
    unittest.main()
