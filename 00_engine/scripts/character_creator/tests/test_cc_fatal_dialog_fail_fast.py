import ast
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_PATH = ROOT / "cc_validate_body_reconstruction.py"
GUARD_PATH = ROOT.parents[1] / "character_creator_bridge" / "cc_undo_dialog_guard.ps1"


def load_fatal_dialog_checker():
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ReconstructionError":
            selected.append(node)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            names = {
                target.id
                for target in getattr(node, "targets", [])
                if isinstance(target, ast.Name)
            }
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            if names & {"EXPORT_LICENSE_BLOCKER_TEXT", "FATAL_DIALOG_FILENAME"}:
                selected.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "raise_if_fatal_cc_dialog":
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {"os": __import__("os"), "json": json}
    exec(compile(ast.fix_missing_locations(module), str(EXECUTOR_PATH), "exec"), namespace)
    return namespace


class FatalDialogFailFastTests(unittest.TestCase):
    def test_missing_fatal_dialog_is_a_noop(self):
        subject = load_fatal_dialog_checker()
        with tempfile.TemporaryDirectory() as raw:
            self.assertIsNone(subject["raise_if_fatal_cc_dialog"](raw))

    def test_export_license_dialog_fails_with_evidence_path(self):
        subject = load_fatal_dialog_checker()
        with tempfile.TemporaryDirectory() as raw:
            fatal_path = Path(raw) / subject["FATAL_DIALOG_FILENAME"]
            fatal_path.write_text(
                json.dumps(
                    {
                        "message": subject["EXPORT_LICENSE_BLOCKER_TEXT"],
                        "event": "export_license_blocker",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(subject["ReconstructionError"]) as caught:
                subject["raise_if_fatal_cc_dialog"](raw)
            self.assertIn(subject["EXPORT_LICENSE_BLOCKER_TEXT"], str(caught.exception))
            self.assertIn(str(fatal_path), str(caught.exception))

    def test_native_guard_only_acknowledges_exact_ok_button(self):
        source = GUARD_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "You must first purchase the content licenses in order to export FBX files.",
            source,
        )
        self.assertIn('$buttonNames -contains "OK"', source)
        self.assertIn('$buttonNames -contains "Buy"', source)
        self.assertIn('Where-Object { $_.Current.Name -eq "OK" }', source)
        self.assertNotIn('Where-Object { $_.Current.Name -eq "Buy" }', source)


if __name__ == "__main__":
    unittest.main()
