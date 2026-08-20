import importlib.util
import os
import pathlib
import sys
import tempfile
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
    sys.modules["RLPy"] = rlpy

    pyside = types.ModuleType("PySide2")
    pyside.QtCore = types.SimpleNamespace()
    pyside.QtGui = types.SimpleNamespace()
    pyside.QtWidgets = types.SimpleNamespace()
    sys.modules["PySide2"] = pyside

    spec = importlib.util.spec_from_file_location(
        "cc_outfit_export_optional_textures_test_subject", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class OutfitExportOptionalTexturesTest(unittest.TestCase):
    def test_missing_optional_directory_is_valid(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "textures")
            state = SUBJECT._outfit_gate_optional_directory_state(path)
        self.assertFalse(state["present"])
        self.assertEqual(0, state["file_count"])
        self.assertEqual(0, state["total_bytes"])

    def test_present_optional_directory_is_measured(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "textures")
            os.makedirs(path)
            with open(os.path.join(path, "weight.jpg"), "wb") as handle:
                handle.write(b"weight-map")
            state = SUBJECT._outfit_gate_optional_directory_state(path)
        self.assertTrue(state["present"])
        self.assertEqual(1, state["file_count"])
        self.assertEqual(len(b"weight-map"), state["total_bytes"])

    def test_required_directory_remains_required(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "fbm")
            with self.assertRaises(SUBJECT.ReconstructionError):
                SUBJECT._outfit_gate_directory_state(path)


if __name__ == "__main__":
    unittest.main()
