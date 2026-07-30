import importlib.util
import json
import pathlib
import random
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_generate_face_recipes_v3.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_generate_face_recipes_v3_test_subject", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


def morph(morph_id, region, role="local", categories=None):
    return {
        "bounds_by_sex": {
            "female": {"maximum": 1.0, "minimum": -1.0},
            "male": {"maximum": 1.0, "minimum": -1.0},
        },
        "categories": categories or ["Actor/Head/{}".format(region)],
        "common_bounds": {"maximum": 1.0, "minimum": -1.0},
        "display": morph_id,
        "id": morph_id,
        "namespace": "actor_head",
        "region": region,
        "role": role,
    }


class FaceGenerationV3Tests(unittest.TestCase):
    def setUp(self):
        self.approved = [
            morph("brow", "brow"),
            morph("cheek", "cheek"),
            morph("ear", "ear"),
            morph("eye", "eye"),
            morph("jaw", "jaw"),
            morph("mouth", "mouth"),
            morph("nose", "nose"),
            morph("skull", "skull"),
        ]
        self.policy = {
            "approved_morph_count": len(self.approved),
            "approved_morphs": self.approved,
            "sampling_limits": {
                "extreme_absolute_limit": 1.0,
                "maximum_regions_modified_extreme": 7,
                "maximum_regions_modified_normal": 5,
                "normal_local_delta": 0.32,
                "ordinary_absolute_limit": 0.9,
                "strong_local_delta": 0.48,
            },
        }
        self.primary = {
            "seed_id": "F01_Primary",
            "sex": "female",
            "source_head_preset": {
                "path": "Primary.ccAvatarPreset",
                "sha256": "hash",
            },
            "target_face_morphs": [
                {"id": "eye", "weight": 0.2},
                {"id": "support_blink", "weight": 1.0},
            ],
        }

    def test_candidate_contains_only_explicit_local_edits(self):
        edits = SUBJECT.make_local_candidate(
            self.primary,
            self.approved,
            self.policy,
            "female",
            "normal",
            random.Random(42),
        )
        self.assertGreaterEqual(len({item["region"] for item in edits}), 4)
        self.assertNotIn(
            "support_blink", {item["id"] for item in edits}
        )
        self.assertTrue(
            all(item["id"] in {m["id"] for m in self.approved} for item in edits)
        )
        eye = next((item for item in edits if item["id"] == "eye"), None)
        if eye is not None:
            self.assertEqual(eye["baseline_weight"], 0.2)

    def test_fingerprint_depends_on_primary_head_preset(self):
        edits = [
            {
                "baseline_weight": 0.0,
                "id": "nose",
                "weight": 0.2,
            }
        ]
        self.assertNotEqual(
            SUBJECT.canonical_local_fingerprint("F01", edits),
            SUBJECT.canonical_local_fingerprint("F02", edits),
        )

    def test_facial_profile_prefers_seed_override(self):
        library = {
            "facial_profile_policy": {
                "application_mode": (
                    SUBJECT.FACIAL_PROFILE_APPLICATION_MODE
                ),
                "default_by_sex": {
                    "female": {
                        "path": "Female_Default.ccFacialProfile",
                        "sha256": "a" * 64,
                    }
                },
                "seed_overrides": {
                    "F01_Primary": {
                        "path": "Female_Override.ccFacialProfile",
                        "sha256": "b" * 64,
                    }
                },
            }
        }

        result = SUBJECT.resolve_facial_profile(
            library, self.primary
        )

        self.assertEqual(result["policy_binding"], "seed_override")
        self.assertTrue(
            result["path"].endswith("Female_Override.ccFacialProfile")
        )
        self.assertEqual(result["sha256"], "b" * 64)

    def test_balanced_schedule_differs_by_at_most_one(self):
        seeds = [{"seed_id": "S{}".format(index)} for index in range(9)]
        schedule = SUBJECT.balanced_seed_schedule(
            seeds, 100, random.Random(7)
        )
        counts = {}
        for seed in schedule:
            counts[seed["seed_id"]] = counts.get(seed["seed_id"], 0) + 1
        self.assertEqual(len(schedule), 100)
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)

    def test_local_target_stays_inside_policy_bounds(self):
        target = SUBJECT.bounded_local_target(
            baseline=0.9,
            direction=1.0,
            magnitude=0.48,
            minimum=-1.0,
            maximum=1.0,
            absolute_limit=0.9,
        )
        self.assertGreaterEqual(target, -0.9)
        self.assertLessEqual(target, 0.9)
        self.assertGreater(abs(target - 0.9), 0.07)

    def test_dynamic_screening_removes_rejected_seed_and_macro(self):
        rejected_macro = morph(
            "full_character",
            "skull",
            role="macro",
            categories=[
                "Actor",
                "Actor/Head",
                "Actor/Head/Full Head",
                "Actor/Head/Full Head/Character",
            ],
        )
        policy = dict(self.policy)
        policy["approved_morphs"] = self.approved + [rejected_macro]
        policy["approved_morph_count"] = len(policy["approved_morphs"])
        library = {
            "seeds": [
                {"seed_id": "F01", "sex": "female"},
                {"seed_id": "F09", "sex": "female"},
            ]
        }
        config = {
            "dynamic_screening": {
                "allowed_local_morph_roles": ["local"],
                "excluded_local_morphs": [
                    {
                        "id": "full_character",
                        "reason": "not local",
                    }
                ],
                "excluded_primary_seeds": [
                    {"id": "F09", "reason": "dynamic failure"}
                ],
            }
        }

        self.assertEqual(
            [item["id"] for item in SUBJECT.production_morphs(config, policy)],
            [item["id"] for item in self.approved],
        )
        self.assertEqual(
            [
                item["seed_id"]
                for item in SUBJECT.production_seeds(
                    config, library, "female"
                )
            ],
            ["F01"],
        )

    def test_repository_config_freezes_screened_production_pool(self):
        config_path = SCRIPT_PATH.parent / "cc_generate_face_recipes_v3_config.json"
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
        policy_path = SCRIPT_PATH.parent / pathlib.Path(
            config["identity_policy"]
        ).name
        library_path = SCRIPT_PATH.parent / pathlib.Path(
            config["source_library"]
        ).name
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)
        with library_path.open("r", encoding="utf-8") as handle:
            library = json.load(handle)

        production_morphs = SUBJECT.production_morphs(config, policy)
        self.assertEqual(len(production_morphs), 28)
        self.assertTrue(
            all(item["role"] == "local" for item in production_morphs)
        )
        self.assertNotIn(
            "mouth", {item["region"] for item in production_morphs}
        )
        self.assertNotIn(
            "eye", {item["region"] for item in production_morphs}
        )
        self.assertEqual(
            len(SUBJECT.production_seeds(config, library, "male")), 9
        )
        female_seed_ids = {
            item["seed_id"]
            for item in SUBJECT.production_seeds(
                config, library, "female"
            )
        }
        self.assertEqual(len(female_seed_ids), 8)
        self.assertNotIn("F09_Female_F", female_seed_ids)


if __name__ == "__main__":
    unittest.main()
