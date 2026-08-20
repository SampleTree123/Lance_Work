import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_module(
    "cc_build_headshot_skull_composition_candidates_v1",
    "cc_build_headshot_skull_composition_candidates_v1.py",
)


class HeadshotSkullCompositionCandidateTests(unittest.TestCase):
    def test_candidate_manifest_is_constrained_and_shared(self):
        library = BUILDER.build_library()
        policy = library["composition_candidate_policy"]
        self.assertEqual(9, policy["candidate_profile_count"])
        self.assertEqual(4, policy["final_profile_budget"])
        self.assertTrue(policy["baseline_included_in_final_budget"])
        self.assertFalse(policy["production_approved"])
        self.assertEqual(18, len(library["presets"]))

        by_sex = {
            sex: [preset for preset in library["presets"] if preset["sex"] == sex]
            for sex in ("female", "male")
        }
        self.assertEqual(9, len(by_sex["female"]))
        self.assertEqual(9, len(by_sex["male"]))
        self.assertEqual(
            [preset["head_shape_profile"]["id"] for preset in by_sex["female"]],
            [preset["head_shape_profile"]["id"] for preset in by_sex["male"]],
        )

        for preset in library["presets"]:
            metrics = preset["composition_metrics"]
            self.assertLessEqual(metrics["active_axis_count"], 3)
            self.assertLessEqual(metrics["normalized_l1"], 2.0)
            self.assertLessEqual(metrics["normalized_l2"], 1.2)
            review = preset["neck_morph_review"]
            self.assertEqual(1, len(review["morphs"]))
            self.assertEqual(1, len(review["morphs"][0]["values"]))
            self.assertEqual(6, len(review["fixed_morphs"]))

    def test_baseline_is_zero_and_candidates_are_not_final_ids(self):
        axes = BUILDER.safe_axes(BUILDER.read_json(BUILDER.DEFAULT_SAFE_RANGES))
        metrics = BUILDER.validate_profiles(BUILDER.PROFILES, axes)
        baseline = BUILDER.PROFILES[0]
        self.assertEqual("C00_BASELINE", baseline["id"])
        self.assertEqual(0, metrics[baseline["id"]]["active_axis_count"])
        self.assertTrue(
            all(abs(float(baseline[key])) <= 1e-9 for key in BUILDER.AXIS_ORDER)
        )
        self.assertTrue(all(profile["id"].startswith("C") for profile in BUILDER.PROFILES))


if __name__ == "__main__":
    unittest.main()
