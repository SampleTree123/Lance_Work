import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("probe_comparison", Path(__file__).resolve().parents[1] / "validate_wardrobe_fbx_probe_v1.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProbeComparisonTests(unittest.TestCase):
    def test_matrix_roundoff_allowed(self):
        errors, rounding = MODULE.compare({"transform": [1.]}, {"transform": [1. + 1e-14]})
        self.assertFalse(errors)
        self.assertEqual(len(rounding), 1)

    def test_meaningful_matrix_change_rejected(self):
        self.assertTrue(MODULE.compare({"global": [1.]}, {"global": [1.001]})[0])

    def test_even_tiny_weight_change_rejected(self):
        self.assertTrue(MODULE.compare({"weights": [.5]}, {"weights": [.5 + 1e-14]})[0])

    def test_vertex_change_rejected(self):
        self.assertTrue(MODULE.compare({"vertices": [[1.]]}, {"vertices": [[1. + 1e-14]]})[0])

    def test_nonfinite_rejected(self):
        self.assertTrue(MODULE.compare({"global": [float('inf')]}, {"global": [float('inf')]})[0])

    def test_type_and_count_changes_rejected(self):
        self.assertTrue(MODULE.compare([1], [True])[0])
        self.assertTrue(MODULE.compare([1], [1, 2])[0])


if __name__ == '__main__':
    unittest.main()
