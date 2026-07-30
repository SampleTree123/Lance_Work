import importlib.util
import json
import pathlib
import unittest


SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = SCRIPT_DIR / "cc_compile_character_manifest.py"
REGISTRY_PATH = SCRIPT_DIR / "cc_facial_production_registry_v1.json"
SPEC = importlib.util.spec_from_file_location(
    "cc_compile_facial_components_under_test",
    SCRIPT_PATH,
)
SUBJECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUBJECT)


class CompileFacialComponentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            cls.registry = json.load(handle)

    def compile(self, sex="female", request=None, character_id="C001"):
        return SUBJECT.compile_facial_components(
            request or {},
            self.registry,
            sex,
            20260728,
            character_id,
        )

    def test_selection_is_deterministic(self):
        first = self.compile()
        second = self.compile()
        self.assertEqual(first, second)

    def test_female_never_receives_facial_hair(self):
        for index in range(50):
            result = self.compile(
                sex="female",
                character_id="F{:03d}".format(index),
            )
            self.assertIsNone(result["facial_hair_asset_id"])

    def test_default_hair_presentation_is_hard_filtered(self):
        hair_by_id = {
            item["asset_id"]: item
            for item in self.registry["component_pools"]["scalp_hair"]
        }
        for sex in ("male", "female"):
            for index in range(200):
                result = self.compile(
                    sex=sex,
                    character_id="{}{:03d}".format(
                        sex[0].upper(), index
                    ),
                )
                hair = hair_by_id[result["scalp_hair_asset_id"]]
                score = float(hair["female_presentation_score"])
                if sex == "male":
                    self.assertLessEqual(score, 0.5)
                else:
                    self.assertGreaterEqual(score, 0.5)
                self.assertEqual(
                    "default",
                    result["hair_presentation_mode"],
                )
                self.assertEqual(
                    hair["silhouette_family"],
                    result["scalp_hair_silhouette_family"],
                )

    def test_default_rejects_explicit_cross_presentation_hair(self):
        female_primary = next(
            item
            for item in self.registry["component_pools"]["scalp_hair"]
            if float(item["female_presentation_score"]) > 0.5
            and "male" in item["accepted_sexes"]
        )
        with self.assertRaises(SUBJECT.RequestCompileError) as context:
            self.compile(
                sex="male",
                request={
                    "facial_components": {
                        "scalp_hair_asset_id": female_primary["asset_id"],
                    }
                },
            )
        self.assertEqual(
            "scalp_hair_presentation_mismatch",
            context.exception.code,
        )

    def test_cross_presentation_requires_explicit_mode(self):
        female_primary = next(
            item
            for item in self.registry["component_pools"]["scalp_hair"]
            if float(item["female_presentation_score"]) > 0.5
            and "male" in item["accepted_sexes"]
        )
        result = self.compile(
            sex="male",
            request={
                "facial_components": {
                    "hair_presentation_mode": "cross_presentation",
                    "scalp_hair_asset_id": female_primary["asset_id"],
                }
            },
        )
        self.assertEqual(
            female_primary["asset_id"],
            result["scalp_hair_asset_id"],
        )
        self.assertEqual(
            "cross_presentation",
            result["hair_presentation_mode"],
        )

    def test_neutral_only_selects_exactly_neutral_hair(self):
        for sex in ("male", "female"):
            result = self.compile(
                sex=sex,
                request={
                    "facial_components": {
                        "hair_presentation_mode": "neutral_only",
                    }
                },
            )
            self.assertEqual(
                0.5,
                result["scalp_hair_female_presentation_score"],
            )

    def test_explicit_component_ids_are_honored(self):
        pools = self.registry["component_pools"]
        skin = next(
            item for item in pools["skins"] if item["sex"] == "male"
        )
        brow = next(
            item
            for item in pools["eyebrows"]
            if item["sex_hint"] == "male"
        )
        request = {
            "facial_components": {
                "age_label": "older",
                "eyebrow_asset_id": brow["asset_id"],
                "facial_hair_asset_id": None,
                "gray_fraction": 0.8,
                "hair_color_id": "black",
                "hair_color_mode": "natural_common",
                "skin_asset_id": skin["asset_id"],
            }
        }
        result = self.compile(sex="male", request=request)
        self.assertEqual("older", result["age_label"])
        self.assertEqual(1.0, result["full_face_elder_weight"])
        self.assertEqual(brow["asset_id"], result["eyebrow_asset_id"])
        self.assertEqual(skin["asset_id"], result["skin_asset_id"])
        self.assertEqual(0.8, result["gray_fraction"])
        self.assertIsNone(result["facial_hair_asset_id"])

    def test_dyed_hair_hides_age_gray(self):
        result = self.compile(
            request={
                "facial_components": {
                    "age_label": "older",
                    "gray_fraction": 0.9,
                    "hair_color_id": "blue",
                    "hair_color_mode": "dyed",
                }
            }
        )
        self.assertEqual(0.9, result["gray_fraction"])
        self.assertEqual(0.0, result["visible_gray_fraction"])

    def test_component_namespaces_do_not_cascade(self):
        baseline = self.compile()
        eyes = self.registry["component_pools"]["eyes"]
        replacement = next(
            item["asset_id"]
            for item in eyes
            if item["asset_id"] != baseline["eye_asset_id"]
        )
        changed = self.compile(
            request={
                "facial_components": {
                    "eye_asset_id": replacement,
                }
            }
        )
        self.assertEqual(replacement, changed["eye_asset_id"])
        for field in (
            "skin_asset_id",
            "age_label",
            "eyebrow_asset_id",
            "eyelash_asset_id",
            "teeth_asset_id",
            "scalp_hair_asset_id",
            "hair_color_mode",
            "hair_presentation_mode",
            "hair_color_id",
            "gray_fraction",
        ):
            self.assertEqual(baseline[field], changed[field])


if __name__ == "__main__":
    unittest.main()
