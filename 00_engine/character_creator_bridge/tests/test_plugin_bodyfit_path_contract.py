import ast
import pathlib
import unittest


PLUGIN_PATH = pathlib.Path(__file__).parents[1] / "plugin" / "main.py"


def _load_path_contract():
    tree = ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))
    selected = []
    wanted = {
        "SOURCE_PROJECT_ONLY_BODYFIT_MODES",
        "bodyfit_preset_input_paths",
    }
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {"frozenset": frozenset}
    exec(compile(module, str(PLUGIN_PATH), "exec"), namespace)
    return namespace["bodyfit_preset_input_paths"]


class BodyFitPathContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.required_paths = staticmethod(_load_path_contract())

    def test_outfit_gate_requires_only_source_project(self):
        document = {"diagnostic_mode": "outfit_compatibility_gate"}
        preset = {"source_project": {"path": r"D:\source.ccProject"}}
        self.assertEqual(
            self.required_paths(document, preset),
            (r"D:\source.ccProject",),
        )

    def test_outfit_motion_gate_requires_only_source_project(self):
        document = {"diagnostic_mode": "outfit_motion_stress_gate"}
        preset = {"source_project": {"path": r"D:\source.ccProject"}}
        self.assertEqual(
            self.required_paths(document, preset),
            (r"D:\source.ccProject",),
        )

    def test_standard_bodyfit_still_requires_base_and_source(self):
        document = {"diagnostic_mode": "bodyfit_reconstruction"}
        preset = {
            "base_avatar": {"path": r"D:\base.ccAvatar"},
            "source_project": {"path": r"D:\source.ccProject"},
        }
        self.assertEqual(
            self.required_paths(document, preset),
            (r"D:\base.ccAvatar", r"D:\source.ccProject"),
        )

    def test_standard_bodyfit_rejects_missing_base(self):
        with self.assertRaises(ValueError):
            self.required_paths(
                {"diagnostic_mode": "bodyfit_reconstruction"},
                {"source_project": {"path": r"D:\source.ccProject"}},
            )

    def test_outfit_gate_rejects_missing_source(self):
        with self.assertRaises(ValueError):
            self.required_paths(
                {"diagnostic_mode": "outfit_compatibility_gate"},
                {},
            )


if __name__ == "__main__":
    unittest.main()
