import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "run_modular_outfit_pilot_import_v1.py"
SPEC = importlib.util.spec_from_file_location("modular_import_runner", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


class ModularImportRunnerTests(unittest.TestCase):
    def test_dialog_guard_covers_long_fbx_parsing(self):
        with patch.object(SUBJECT.subprocess, "Popen") as popen:
            SUBJECT.start_dialog_watcher("datatry_02")
        args = popen.call_args.args[0]
        self.assertEqual(args[args.index("--timeout-seconds") + 1], "3600")
        self.assertEqual(args[args.index("--project-title") + 1], "datatry_02")

    def test_remote_command_injects_mode_and_case(self):
        command = SUBJECT.remote_command("import_split", "M_1920_LAYERED")
        self.assertIn("DM_MODULAR_MODE='import_split'", command)
        self.assertIn("DM_MODULAR_CASE_ID='M_1920_LAYERED'", command)
        self.assertIn("ue_modular_outfit_pilot_import_v1.py", command)

    def test_interactive_reference_command_marks_worker_interactive(self):
        command = SUBJECT.remote_command("import_reference", "M_BASE", True)
        self.assertIn("DM_MODULAR_INTERACTIVE=True", command)

    def test_cleanup_phase_is_explicitly_supported(self):
        self.assertEqual(SUBJECT.PHASE_TO_MODE["cleanup"], "cleanup_case")

    def test_select_case_ids_preserves_manifest_order(self):
        manifest = {"cases": [{"case_id": "A"}, {"case_id": "B"}]}
        self.assertEqual(["A", "B"], SUBJECT.select_case_ids(manifest, []))
        self.assertEqual(["B"], SUBJECT.select_case_ids(manifest, ["B"]))

    def test_select_case_ids_rejects_unknown_or_duplicate(self):
        manifest = {"cases": [{"case_id": "A"}, {"case_id": "B"}]}
        with self.assertRaisesRegex(RuntimeError, "Unknown"):
            SUBJECT.select_case_ids(manifest, ["C"])
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            SUBJECT.select_case_ids(manifest, ["A", "A"])


if __name__ == "__main__":
    unittest.main()
