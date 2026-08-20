import importlib.util
import json
import pathlib
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_short_male_final_candidate_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_short_male_final_candidate_v1_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class ShortMaleFinalCandidateTests(unittest.TestCase):
    def test_repository_inputs_build_accepted_m05_save(self):
        with open(SUBJECT.DEFAULT_SOURCE, "r", encoding="utf-8") as handle:
            source = json.load(handle)
        with open(SUBJECT.DEFAULT_DECISIONS, "r", encoding="utf-8") as handle:
            decisions = json.load(handle)

        document = SUBJECT.build(
            source,
            decisions,
            "D:\\Temp\\M05.ccProject",
        )
        preset = document["presets"][0]
        review = preset["neck_morph_review"]

        self.assertEqual("SHORT_MALE_FINAL_SAVE", preset["preset_id"])
        self.assertEqual(0.0, review["head_scale"]["target"])
        self.assertEqual([0.3], review["morphs"][0]["values"])
        self.assertEqual(
            0.3,
            review["save_selected_candidate"]["value"],
        )


if __name__ == "__main__":
    unittest.main()
