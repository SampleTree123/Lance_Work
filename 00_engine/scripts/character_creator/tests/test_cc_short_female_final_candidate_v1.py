import importlib.util
import json
import pathlib
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_short_female_final_candidate_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_short_female_final_candidate_v1_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class ShortFemaleFinalCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SUBJECT.DEFAULT_SOURCE, "r", encoding="utf-8") as handle:
            cls.source = json.load(handle)
        with open(SUBJECT.DEFAULT_DECISIONS, "r", encoding="utf-8") as handle:
            cls.decisions = json.load(handle)

    def test_review_keeps_all_three_shoulder_candidates(self):
        document = SUBJECT.build(self.source, self.decisions)
        review = document["presets"][0]["neck_morph_review"]

        self.assertEqual(-0.1, review["head_scale"]["target"])
        self.assertEqual(0.3, review["fixed_morphs"][0]["target"])
        self.assertEqual(
            [0.25, 0.5, 0.75],
            review["morphs"][0]["values"],
        )

    def test_save_uses_selected_shoulder_and_restores_source_head_scale(self):
        document = SUBJECT.build(
            self.source,
            self.decisions,
            save=True,
            project_output="D:\\Temp\\F05.ccProject",
            selected_shoulder_value=0.25,
        )
        review = document["presets"][0]["neck_morph_review"]

        self.assertEqual(0.0, review["head_scale"]["target"])
        self.assertEqual([0.25], review["morphs"][0]["values"])
        self.assertEqual(
            0.25,
            review["save_selected_candidate"]["value"],
        )


if __name__ == "__main__":
    unittest.main()
