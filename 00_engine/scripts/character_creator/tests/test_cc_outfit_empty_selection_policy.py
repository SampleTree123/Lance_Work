import importlib.util
import os
import pathlib
import sys
import types
import unittest


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "cc_validate_body_reconstruction.py"


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
    sys.modules["RLPy"] = rlpy
    pyside = types.ModuleType("PySide2")
    pyside.QtCore = types.SimpleNamespace()
    pyside.QtGui = types.SimpleNamespace()
    pyside.QtWidgets = types.SimpleNamespace()
    sys.modules["PySide2"] = pyside
    spec = importlib.util.spec_from_file_location("cc_empty_outfit_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class EmptyOutfitSelectionPolicyTests(unittest.TestCase):
    def test_nonempty_selection_preserves_default_behavior(self):
        assets = [{"asset_id": "shirt"}]
        self.assertIs(
            assets,
            SUBJECT._outfit_gate_selected_assets(
                {"preset_id": "normal", "selected_assets": assets}, {}
            ),
        )

    def test_empty_selection_requires_case_and_global_opt_in(self):
        preset = {
            "preset_id": "base",
            "selected_assets": [],
            "allow_empty_selected_assets": True,
        }
        with self.assertRaises(SUBJECT.ReconstructionError):
            SUBJECT._outfit_gate_selected_assets(preset, {})
        with self.assertRaises(SUBJECT.ReconstructionError):
            SUBJECT._outfit_gate_selected_assets(
                {"preset_id": "base", "selected_assets": []},
                {"allow_empty_selected_assets": True},
            )
        self.assertEqual(
            [],
            SUBJECT._outfit_gate_selected_assets(
                preset, {"allow_empty_selected_assets": True}
            ),
        )

    def test_selected_assets_must_be_a_list(self):
        with self.assertRaises(SUBJECT.ReconstructionError):
            SUBJECT._outfit_gate_selected_assets(
                {"preset_id": "bad", "selected_assets": None},
                {"allow_empty_selected_assets": True},
            )


if __name__ == "__main__":
    unittest.main()
