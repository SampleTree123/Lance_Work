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
    "cc_build_headshot_skull_profile_library_v1",
    "cc_build_headshot_skull_profile_library_v1.py",
)


class HeadshotSkullProfileLibraryTests(unittest.TestCase):
    def test_selected_profiles_are_shared_and_dynamic_reviewed(self):
        library = BUILDER.build_library()
        policy = library["canonical_profile_policy"]
        self.assertEqual(
            [
                "H00_BASELINE",
                "H01_LONG_DEEP",
                "H02_LOW_FLAT",
                "H03_NARROW_SHALLOW",
            ],
            policy["canonical_profile_ids"],
        )
        self.assertTrue(policy["human_static_selection_complete"])
        self.assertTrue(policy["dynamic_validation_complete"])
        self.assertFalse(policy["production_approved"])
        self.assertEqual(8, len(library["presets"]))

        by_sex = {
            sex: [preset for preset in library["presets"] if preset["sex"] == sex]
            for sex in ("female", "male")
        }
        self.assertEqual(4, len(by_sex["female"]))
        self.assertEqual(4, len(by_sex["male"]))
        self.assertEqual(
            [item["head_shape_profile"] for item in by_sex["female"]],
            [item["head_shape_profile"] for item in by_sex["male"]],
        )

    def test_dynamic_gate_is_explicit_and_each_preset_has_one_candidate(self):
        library = BUILDER.build_library()
        dynamic = library["targeted_morph_dynamic_pose_review"]
        self.assertTrue(dynamic["enabled"])
        self.assertEqual(
            list(BUILDER.REQUIRED_DYNAMIC_POSES),
            dynamic["required_pose_ids"],
        )
        for preset in library["presets"]:
            review = preset["neck_morph_review"]
            self.assertEqual(1, len(review["morphs"]))
            self.assertEqual(1, len(review["morphs"][0]["values"]))
            self.assertTrue(preset["selection_provenance"]["human_selected"])


if __name__ == "__main__":
    unittest.main()
