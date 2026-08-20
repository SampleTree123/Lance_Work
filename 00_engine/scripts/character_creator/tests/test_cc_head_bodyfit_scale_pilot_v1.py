import importlib.util
import json
import pathlib
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_head_bodyfit_scale_pilot_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_build_head_bodyfit_scale_pilot_v1_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class HeadBodyFitScalePilotTests(unittest.TestCase):
    def test_inject_head_scale_replaces_existing_target(self):
        policy = {
            "categories": ["Actor", "Actor/Head/Full Head/General"],
            "common_bounds": {"maximum": 1.0, "minimum": -0.5},
            "display": "Head Scale",
            "id": "head_scale",
            "region": "skull",
        }
        existing = [
            {
                "baseline_weight": 0.0,
                "id": "nose",
                "weight": 0.2,
            },
            {
                "baseline_weight": 0.0,
                "id": "head_scale",
                "weight": 0.1,
            },
        ]

        result = SUBJECT.inject_head_scale(
            existing,
            policy,
            baseline_weight=0.05,
            target_weight=-0.1,
        )

        self.assertEqual(
            ["head_scale", "nose"],
            [item["id"] for item in result],
        )
        target = result[0]
        self.assertEqual(0.05, target["baseline_weight"])
        self.assertAlmostEqual(-0.15, target["delta"])
        self.assertEqual(-0.1, target["weight"])

    def test_repository_config_builds_44_isolated_candidates(self):
        config_path = SCRIPT_PATH.parent / (
            "cc_head_bodyfit_scale_pilot_v1_config.json"
        )
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        source_paths = {
            key: SUBJECT.resolve_path(config[key])
            for key in (
                "body_library",
                "identity_policy",
                "recipe_library",
                "seed_library",
            )
        }
        document = SUBJECT.build_document(
            config,
            SUBJECT.read_json(source_paths["body_library"]),
            SUBJECT.read_json(source_paths["seed_library"]),
            SUBJECT.read_json(source_paths["identity_policy"]),
            SUBJECT.read_json(source_paths["recipe_library"]),
            source_paths,
        )

        self.assertEqual(44, document["character_count"])
        self.assertEqual(44, len(document["presets"]))
        average = [
            item
            for item in document["presets"]
            if item["body_class"] == "average"
        ]
        self.assertEqual(2, len(average))
        self.assertTrue(
            all(
                item["head_bodyfit_scale_pilot"][
                    "head_scale_target"
                ]
                == 0.0
                for item in average
            )
        )
        self.assertTrue(
            all("appearance_recipe" not in item for item in document["presets"])
        )
        self.assertTrue(
            all("facial_assembly" not in item for item in document["presets"])
        )
        heavy_targets = sorted(
            item["head_bodyfit_scale_pilot"]["head_scale_target"]
            for item in document["presets"]
            if item["bodyfit_id"] == "M04_Heavy"
        )
        self.assertEqual(
            [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            heavy_targets,
        )
        lean_targets = sorted(
            item["head_bodyfit_scale_pilot"]["head_scale_target"]
            for item in document["presets"]
            if item["bodyfit_id"] == "M01_Lean"
        )
        self.assertEqual(
            [-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3],
            lean_targets,
        )
        head_scale_id = config["head_scale_morph_id"]
        for preset in document["presets"]:
            matches = [
                item
                for item in preset["local_face_morphs"]
                if item["id"] == head_scale_id
            ]
            self.assertEqual(1, len(matches))


if __name__ == "__main__":
    unittest.main()
