import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "first_batch_expression_profile_20260820_v1.json"


class FirstBatchExpressionProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))

    def test_profile_has_three_dynamic_non_neutral_expressions(self):
        expressions = self.profile["expressions"]
        self.assertEqual({"happy", "angry", "sad"}, {item["expression_id"] for item in expressions})
        for expression in expressions:
            self.assertTrue(expression["curves"])
            self.assertTrue(
                any(keys["values"][0] > 0.0 for keys in expression["curves"].values())
            )
            self.assertTrue(
                any(len(set(keys["values"])) > 1 for keys in expression["curves"].values())
            )

    def test_curve_keys_cover_exact_three_second_clip(self):
        self.assertEqual(3.0, self.profile["duration_seconds"])
        self.assertEqual(24, self.profile["render_fps"])
        self.assertEqual(60, self.profile["animation_sample_fps"])
        self.assertEqual(180, self.profile["frame_count"])
        curve_groups = [self.profile["common_curves"]]
        curve_groups.extend(item["curves"] for item in self.profile["expressions"])
        for curves in curve_groups:
            for keys in curves.values():
                self.assertEqual(len(keys["times"]), len(keys["values"]))
                self.assertEqual(0.0, keys["times"][0])
                self.assertEqual(3.0, keys["times"][-1])
                self.assertEqual(sorted(keys["times"]), keys["times"])
                self.assertTrue(all(0.0 <= value <= 1.0 for value in keys["values"]))

    def test_forbids_head_neck_and_eye_gaze_curves(self):
        names = set(self.profile["common_curves"])
        for expression in self.profile["expressions"]:
            names.update(expression["curves"])
        lowered = [name.lower() for name in names]
        self.assertFalse(any("head" in name or "neck" in name for name in lowered))
        self.assertFalse(any("eyelook" in name or "gaze" in name for name in lowered))

    def test_two_actors_use_separate_skeleton_sources(self):
        actors = self.profile["actors"]
        self.assertEqual({"F02", "M02"}, {item["actor_id"] for item in actors})
        self.assertEqual(2, len({item["source_animation"] for item in actors}))
        self.assertTrue(all(item["target_folder"].startswith("/Game/") for item in actors))


if __name__ == "__main__":
    unittest.main()
