import importlib.util
import os
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_build_character_integration_requests_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_build_character_integration_requests_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

COMPILER_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_compile_character_manifest.py",
)
COMPILER_SPEC = importlib.util.spec_from_file_location(
    "cc_compile_character_manifest_for_integration_test",
    COMPILER_PATH,
)
COMPILER = importlib.util.module_from_spec(COMPILER_SPEC)
COMPILER_SPEC.loader.exec_module(COMPILER)


class CharacterIntegrationRequestTests(unittest.TestCase):
    def test_default_inputs_cover_required_component_domains(self):
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, "requests.json")
            document = MODULE.build(output_path=output)

        characters = document["characters"]
        self.assertEqual(len(characters), 24)
        self.assertEqual(
            len({item["character_id"] for item in characters}),
            24,
        )
        body_age = {
            (
                item["bodyfit_id"],
                item["facial_components"]["age_label"],
            )
            for item in characters
        }
        self.assertEqual(len(body_age), 24)
        self.assertEqual(
            {item[1] for item in body_age},
            set(MODULE.AGE_LABELS),
        )

        face_library = MODULE.read_json(MODULE.DEFAULT_FACE_LIBRARY)
        faces = {
            item["face_recipe_id"]: item
            for item in face_library["recipes"]
        }
        covered_seeds = {
            faces[item["face_recipe_id"]]["primary_face_seed_id"]
            for item in characters
        }
        self.assertEqual(len(covered_seeds), 17)

        registry = MODULE.read_json(MODULE.DEFAULT_REGISTRY)
        pools = registry["component_pools"]
        components = [
            item["facial_components"] for item in characters
        ]
        self.assertEqual(
            {item["skin_asset_id"] for item in components},
            {item["asset_id"] for item in pools["skins"]},
        )
        self.assertEqual(
            {item["eye_asset_id"] for item in components},
            {item["asset_id"] for item in pools["eyes"]},
        )
        self.assertEqual(
            {item["eyebrow_asset_id"] for item in components},
            {item["asset_id"] for item in pools["eyebrows"]},
        )
        self.assertEqual(
            {item["eyelash_asset_id"] for item in components},
            {item["asset_id"] for item in pools["eyelashes"]},
        )
        self.assertEqual(
            {item["teeth_asset_id"] for item in components},
            {item["asset_id"] for item in pools["teeth"]},
        )
        self.assertEqual(
            {item["hair_color_mode"] for item in components},
            set(MODULE.HAIR_COLOR_MODES),
        )
        self.assertTrue(
            all(
                item["hair_presentation_mode"] == "default"
                for item in components
            )
        )

        male_components = [
            item["facial_components"]
            for item in characters
            if item["bodyfit_id"].startswith("M")
        ]
        self.assertIn(None, {
            item["facial_hair_asset_id"] for item in male_components
        })
        self.assertEqual(
            {
                item["facial_hair_asset_id"]
                for item in male_components
                if item["facial_hair_asset_id"] is not None
            },
            {item["asset_id"] for item in pools["facial_hair"]},
        )

    def test_generated_requests_compile_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            requests_path = os.path.join(directory, "requests.json")
            first_path = os.path.join(directory, "first.json")
            second_path = os.path.join(directory, "second.json")
            MODULE.build(output_path=requests_path)
            first = COMPILER.compile_manifest(
                requests_path,
                COMPILER.DEFAULT_BODY_LIBRARY,
                COMPILER.DEFAULT_FACE_LIBRARY,
                COMPILER.DEFAULT_COMPATIBILITY,
                COMPILER.DEFAULT_CATALOG,
                first_path,
                COMPILER.DEFAULT_FACIAL_REGISTRY,
            )
            second = COMPILER.compile_manifest(
                requests_path,
                COMPILER.DEFAULT_BODY_LIBRARY,
                COMPILER.DEFAULT_FACE_LIBRARY,
                COMPILER.DEFAULT_COMPATIBILITY,
                COMPILER.DEFAULT_CATALOG,
                second_path,
                COMPILER.DEFAULT_FACIAL_REGISTRY,
            )
            first_document = MODULE.read_json(first_path)
            second_document = MODULE.read_json(second_path)

        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(first["character_count"], 24)
        self.assertEqual(first_document["presets"], second_document["presets"])
        self.assertEqual(
            first_document["request_results"],
            second_document["request_results"],
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"]["verification_mode"]
                == "integrated_facial_assembly"
                for item in first_document["presets"]
            )
        )
        self.assertTrue(
            all(
                isinstance(item["scalp_hair_display_name"], str)
                and item["scalp_hair_display_name"]
                for item in first_document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "integrated_facial_assembly_validation"
                ]["render_static_hair_views"]
                is True
                for item in first_document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "face_camera_reference_top_z"
                ]
                == COMPILER.FACE_CAMERA_REFERENCE_TOP_Z[item["sex"]]
                for item in first_document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["appearance_validation_plan"][
                    "asset_load_pacing"
                ]["slots"]["scalp_hair"]
                == {
                    "after_seconds": 12.0,
                    "before_seconds": 8.0,
                }
                for item in first_document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["facial_assembly"]["application_order"]
                == list(COMPILER.FACIAL_ASSEMBLY_ORDER)
                for item in first_document["presets"]
            )
        )
        self.assertTrue(
            all(
                item["facial_assembly"]["age_morph_id"]
                == "2025-07-04-15-29-03_pack_old_man_face"
                for item in first_document["presets"]
            )
        )


if __name__ == "__main__":
    unittest.main()
