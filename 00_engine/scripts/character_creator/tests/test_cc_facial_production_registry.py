import importlib.util
import json
import pathlib
import unittest


SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SCRIPT_DIR / "cc_build_facial_production_registry.py"
REGISTRY_PATH = SCRIPT_DIR / "cc_facial_production_registry_v1.json"
SPEC = importlib.util.spec_from_file_location(
    "cc_build_facial_production_registry_under_test",
    SCRIPT_PATH,
)
SUBJECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUBJECT)


class FacialProductionRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            cls.registry = json.load(handle)

    def test_component_pool_counts(self):
        pools = self.registry["component_pools"]
        self.assertEqual(21, len(pools["skins"]))
        self.assertEqual(12, len(pools["eyes"]))
        self.assertEqual(13, len(pools["eyebrows"]))
        self.assertEqual(9, len(pools["eyelashes"]))
        self.assertEqual(2, len(pools["teeth"]))
        self.assertEqual(5, len(pools["facial_hair"]))
        self.assertEqual(58, len(pools["scalp_hair"]))
        self.assertEqual(2, len(pools["dynamic_wrinkles"]["profiles"]))

    def test_every_skin_has_explicit_pigmentation_profile(self):
        profiles = self.registry["pigmentation"]["profiles"]
        skins = self.registry["component_pools"]["skins"]
        self.assertEqual(
            21,
            len({item["asset_id"] for item in skins}),
        )
        self.assertTrue(
            all(
                item["pigmentation_profile_id"] in profiles
                for item in skins
            )
        )

    def test_dynamic_wrinkle_profiles_have_complete_age_evidence(self):
        profiles = self.registry["component_pools"][
            "dynamic_wrinkles"
        ]["profiles"]
        self.assertEqual(2, len(profiles))
        self.assertTrue(
            all(
                item["validation_status"] == "approved_age_matrix"
                and item["validated_age_labels"]
                == ["young", "middle", "older"]
                for item in profiles
            )
        )

    def test_eyelashes_require_source_and_v3_extreme_evidence(self):
        eyelashes = self.registry["component_pools"]["eyelashes"]
        self.assertEqual(9, len(eyelashes))
        self.assertTrue(
            all(
                item["validation_status"]
                == "approved_source_faces_and_v3_extreme_matrix"
                and set(item["evidence"])
                == {
                    "source_face_visual_review",
                    "v3_extreme_automation",
                }
                for item in eyelashes
            )
        )

    def test_color_distributions_are_normalized(self):
        pigmentation = self.registry["pigmentation"]
        self.assertAlmostEqual(
            1.0,
            sum(pigmentation["mode_weights"].values()),
        )
        for profile in pigmentation["profiles"].values():
            for mode in ("natural_common", "natural_rare"):
                self.assertAlmostEqual(
                    1.0,
                    sum(profile[mode].values()),
                )

    def test_problem_hair_assets_are_not_in_production_pool(self):
        production = {
            item["display_name"]
            for item in self.registry["component_pools"]["scalp_hair"]
        }
        rejected = {
            item["display_name"]
            for item in self.registry["rejected_assets"]["scalp_hair"]
        }
        self.assertEqual(
            {"Bridal-Style Braid", "Graceful half up"},
            rejected,
        )
        self.assertTrue(production.isdisjoint(rejected))

    def test_static_pressure_selection_has_sixteen_production_assets(self):
        production_ids = {
            item["asset_id"]
            for item in self.registry["component_pools"]["scalp_hair"]
        }
        pressure_ids = self.registry["validation_design"][
            "scalp_hair_static_pressure_asset_ids"
        ]
        self.assertEqual(16, len(pressure_ids))
        self.assertEqual(16, len(set(pressure_ids)))
        self.assertTrue(set(pressure_ids).issubset(production_ids))

    def test_scalp_hair_dynamic_review_is_applied(self):
        hair = self.registry["component_pools"]["scalp_hair"]
        self.assertEqual(
            {"dynamic_approved": 52, "rigid_short_approved": 6},
            {
                status: sum(
                    item["production_status"] == status
                    for item in hair
                )
                for status in (
                    "dynamic_approved",
                    "rigid_short_approved",
                )
            },
        )
        by_id = {item["asset_id"]: item for item in hair}
        self.assertIn(
            "nape_component_color_mismatch_pending_pigmentation",
            by_id["CCAPP_SCALP_HAIR_b76abfcd9bdb"]["risk_tags"],
        )

    def test_canonical_assembly_order(self):
        self.assertEqual(
            [
                "bodyfit_project",
                "primary_head_preset",
                "local_face_morphs",
                "skin",
                "age_morph",
                "dynamic_wrinkle_profile",
                "teeth",
                "eyebrows",
                "eyelashes",
                "eyes_material_only",
                "facial_hair",
                "scalp_hair",
                "shared_hair_pigmentation",
                "quality_assurance",
            ],
            self.registry["assembly_order"],
        )


if __name__ == "__main__":
    unittest.main()
