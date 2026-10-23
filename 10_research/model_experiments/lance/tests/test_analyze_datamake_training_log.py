import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analyze_datamake_training_log.py"
SPEC = importlib.util.spec_from_file_location("analyze_datamake_training_log", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AnalyzeTrainingLogTest(unittest.TestCase):
    def test_deduplicates_tqdm_final_render_and_compares_windows(self):
        text = (
            "\rTraining loss=(step=0000000) Train Loss mse: 0.4, "
            "Train Loss ce: 0.0, lr=1e-5\n"
            "\rTraining loss=(step=0000001) Train Loss mse: 0.2, "
            "Train Loss ce: 0.0, lr=1e-5\n"
            "\rTraining loss=(step=0000001) Train Loss mse: 0.2, "
            "Train Loss ce: 0.0, lr=1e-5\nDone!\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "launcher.log"
            log.write_text(text, encoding="utf-8")
            report = MODULE.summarize(log, expected_steps=2, window=1)
        self.assertTrue(report["integrity_passed"])
        self.assertEqual(report["completed_metric_steps"], 2)
        self.assertAlmostEqual(report["mse"]["last_vs_first_relative_change"], -0.5)
        self.assertAlmostEqual(
            report["mse"]["last_vs_first_median_relative_change"], -0.5
        )

    def test_training_exception_fails_integrity(self):
        text = (
            "loss=(step=0000000) Train Loss mse: 0.4, Train Loss ce: 0, lr=1e-5\n"
            "[TRAINING EXCEPTION]\nDone!\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "launcher.log"
            log.write_text(text, encoding="utf-8")
            report = MODULE.summarize(log, expected_steps=1, window=1)
        self.assertFalse(report["integrity_passed"])


if __name__ == "__main__":
    unittest.main()
