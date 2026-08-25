from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run_first_batch_full_reference_import.py"
SPEC = importlib.util.spec_from_file_location("run_first_batch_full_reference_import", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class InteractiveBatchPolicyTests(unittest.TestCase):
    def test_allows_three_interactive_looks(self) -> None:
        MODULE.validate_interactive_batch_policy(
            selected_ids=["A", "B", "C"],
            interactive=False,
            auto_dialogs=True,
            continue_on_error=False,
        )

    def test_rejects_more_than_three_interactive_looks(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "limited to 3"):
            MODULE.validate_interactive_batch_policy(
                selected_ids=["A", "B", "C", "D"],
                interactive=False,
                auto_dialogs=True,
                continue_on_error=False,
            )

    def test_rejects_continue_on_error_for_interactive_import(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "stop on the first failure"):
            MODULE.validate_interactive_batch_policy(
                selected_ids=["A"],
                interactive=True,
                auto_dialogs=False,
                continue_on_error=True,
            )

    def test_unattended_revalidation_is_not_limited(self) -> None:
        MODULE.validate_interactive_batch_policy(
            selected_ids=[str(index) for index in range(32)],
            interactive=False,
            auto_dialogs=False,
            continue_on_error=True,
        )


if __name__ == "__main__":
    unittest.main()
