import importlib.util
import pathlib
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "cc_bridge_client.py"


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_bridge_client_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class DialogGuardCommandTests(unittest.TestCase):
    def test_builds_hidden_exact_guard_process_command(self):
        command = SUBJECT.build_dialog_guard_command(
            r"D:\repo\cc_undo_dialog_guard.ps1",
            1234,
            r"D:\runtime\results\job.json",
            r"D:\runtime\dialog_guard\job.jsonl",
            r"D:\runtime\artifacts\job",
            900.8,
        )

        self.assertEqual(command[0], "powershell.exe")
        self.assertIn("-WindowStyle", command)
        self.assertIn("Hidden", command)
        self.assertEqual(
            command[command.index("-TargetProcessId") + 1],
            "1234",
        )
        self.assertEqual(
            command[command.index("-TimeoutSeconds") + 1],
            "900",
        )
        self.assertEqual(
            command[command.index("-ProgressRoot") + 1],
            r"D:\runtime\artifacts\job",
        )


if __name__ == "__main__":
    unittest.main()
