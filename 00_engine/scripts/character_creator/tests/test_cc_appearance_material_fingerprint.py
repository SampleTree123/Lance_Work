import importlib.util
import os
import pathlib
import sys
import tempfile
import types
import unittest


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_validate_body_reconstruction.py"
)


def load_subject():
    os.environ["CC_BODY_RECONSTRUCTOR_IMPORT_ONLY"] = "1"
    rlpy = types.ModuleType("RLPy")
    for index, name in enumerate(
        (
            "Diffuse",
            "Normal",
            "Roughness",
            "Specular",
            "Metallic",
            "AmbientOcclusion",
            "Opacity",
            "Bump",
            "Displacement",
            "Glow",
        )
    ):
        setattr(rlpy, "EMaterialTextureChannel_" + name, index)
    sys.modules["RLPy"] = rlpy

    pyside = types.ModuleType("PySide2")
    pyside.QtCore = types.SimpleNamespace()
    pyside.QtWidgets = types.SimpleNamespace()
    sys.modules["PySide2"] = pyside

    spec = importlib.util.spec_from_file_location(
        "cc_validate_body_reconstruction_test_subject", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class FakeQImage:
    def __init__(self, pixel_seed):
        self.pixel_seed = pixel_seed

    def isNull(self):
        return False

    def width(self):
        return 8

    def height(self):
        return 8

    def pixel(self, x, y):
        return 0xFF000000 | ((self.pixel_seed + x * 17 + y * 31) & 0x00FFFFFF)


class FakeImage:
    def __init__(self, pixel_seed):
        self.pixel_seed = pixel_seed

    def GetQImage(self):
        return FakeQImage(self.pixel_seed)


class FakeMaterialComponent:
    def __init__(self, pixel_seed=1, tint=0.25):
        self.pixel_seed = pixel_seed
        self.tint = tint

    def GetMaterialNames(self, mesh_name):
        return ["Skin"]

    def GetAmbientColor(self, mesh_name, material_name):
        return (0.1, 0.1, 0.1, 1.0)

    def GetDiffuseColor(self, mesh_name, material_name):
        return (0.8, 0.7, 0.6, 1.0)

    def GetSpecularColor(self, mesh_name, material_name):
        return (0.2, 0.2, 0.2, 1.0)

    def GetGlossinessWeight(self, mesh_name, material_name):
        return 0.4

    def GetSpecularWeight(self, mesh_name, material_name):
        return 0.5

    def GetSelfIlluminationWeight(self, mesh_name, material_name):
        return 0.0

    def GetOpacity(self, mesh_name, material_name):
        return 1.0

    def GetTextureWeights(self, mesh_name, material_name):
        return [1.0, 0.75]

    def GetRefraction(self, mesh_name, material_name):
        return 0.0

    def GetReflection(self, mesh_name, material_name):
        return 0.1

    def GetShader(self, mesh_name, material_name):
        return "Digital_Human_Skin"

    def GetShaderParameterNames(self, mesh_name, material_name):
        return ["Tint"]

    def GetShaderParameter(self, mesh_name, material_name, parameter_name):
        return self.tint

    def GetImage(self, mesh_name, material_name, channel):
        if channel != 0:
            return None
        return FakeImage(self.pixel_seed)


class FakeAvatar:
    def __init__(self, component):
        self.component = component

    def GetMaterialComponent(self):
        return self.component

    def GetMeshNames(self):
        return ["CC_Base_Body"]


class MaterialFingerprintTests(unittest.TestCase):
    def test_eyelash_uses_exact_character_preset_dialog_policy(self):
        self.assertIn(
            "eyelashes",
            SUBJECT.CHARACTER_PRESET_DIALOG_SLOTS,
        )
        self.assertNotIn(
            "eyelashes",
            SUBJECT.MATERIAL_ONLY_DIALOG_SLOTS,
        )

    def test_direct_part_signature_ignores_world_bounds(self):
        base = {
            "id": 42,
            "name": "CC_Base_Eye",
            "python_type": "RIAvatarPart",
            "avatar_part_type": "Eye",
            "mesh_names": ["CC_Base_Eye"],
            "geometry": {
                "bounds": {"center": [1.0, 2.0, 3.0]},
                "local_transform": {"translation": [0.0, 0.0, 0.0]},
            },
        }
        rotated = {
            "id": 42,
            "name": "CC_Base_Eye",
            "python_type": "RIAvatarPart",
            "avatar_part_type": "Eye",
            "mesh_names": ["CC_Base_Eye"],
            "geometry": {
                "bounds": {"center": [-2.0, 1.0, 3.0]},
                "local_transform": {"translation": [0.0, 0.0, 0.0]},
            },
        }
        self.assertEqual(
            SUBJECT.direct_avatar_part_signature([base]),
            SUBJECT.direct_avatar_part_signature([rotated]),
        )

    def test_direct_part_signature_detects_part_replacement(self):
        before = {
            "id": 42,
            "name": "CC_Base_Eye",
            "python_type": "RIAvatarPart",
            "avatar_part_type": "Eye",
            "mesh_names": ["CC_Base_Eye"],
            "geometry": {"local_transform": {}},
        }
        after = dict(before, id=43)
        self.assertNotEqual(
            SUBJECT.direct_avatar_part_signature([before]),
            SUBJECT.direct_avatar_part_signature([after]),
        )

    def test_digest_is_stable_for_identical_material_state(self):
        avatar = FakeAvatar(FakeMaterialComponent(pixel_seed=11, tint=0.25))
        first = SUBJECT.avatar_material_fingerprint(avatar)
        second = SUBJECT.avatar_material_fingerprint(avatar)
        self.assertEqual(first["digest"], second["digest"])
        self.assertEqual(first["observation_error_count"], 0)
        self.assertEqual(first["texture_count"], 1)
        self.assertEqual(first["mesh_names"], ["CC_Base_Body"])
        self.assertEqual(
            set(first["mesh_digests"]), {"CC_Base_Body"}
        )

    def test_digest_changes_when_texture_samples_change(self):
        component = FakeMaterialComponent(pixel_seed=11, tint=0.25)
        avatar = FakeAvatar(component)
        before = SUBJECT.avatar_material_fingerprint(avatar)
        component.pixel_seed = 99
        after = SUBJECT.avatar_material_fingerprint(avatar)
        self.assertNotEqual(before["digest"], after["digest"])

    def test_digest_changes_when_shader_parameter_changes(self):
        component = FakeMaterialComponent(pixel_seed=11, tint=0.25)
        avatar = FakeAvatar(component)
        before = SUBJECT.avatar_material_fingerprint(avatar)
        component.tint = 0.75
        after = SUBJECT.avatar_material_fingerprint(avatar)
        self.assertNotEqual(before["digest"], after["digest"])

    def test_skin_material_change_is_verified_on_body(self):
        result = SUBJECT.evaluate_skin_material_change(
            {
                "digest": "before",
                "mesh_digests": {"CC_Base_Body": "body-before"},
                "texture_count": 0,
            },
            {
                "digest": "after",
                "mesh_digests": {"CC_Base_Body": "body-after"},
                "texture_count": 0,
            },
        )
        self.assertEqual(result["status"], "verified_by_material_api")
        self.assertEqual(result["changed_meshes"], ["CC_Base_Body"])

    def test_skin_material_change_defers_when_textures_are_unobservable(self):
        result = SUBJECT.evaluate_skin_material_change(
            {
                "digest": "same",
                "mesh_digests": {"CC_Base_Body": "same"},
                "texture_count": 0,
            },
            {
                "digest": "same",
                "mesh_digests": {"CC_Base_Body": "same"},
                "texture_count": 0,
            },
        )
        self.assertEqual(
            result["status"], "render_confirmation_required"
        )
        self.assertFalse(result["texture_observable"])

    def test_skin_material_change_fails_when_observable_state_is_unchanged(self):
        result = SUBJECT.evaluate_skin_material_change(
            {
                "digest": "same",
                "mesh_digests": {"CC_Base_Body": "same"},
                "texture_count": 1,
            },
            {
                "digest": "same",
                "mesh_digests": {"CC_Base_Body": "same"},
                "texture_count": 1,
            },
        )
        self.assertEqual(result["status"], "failed")

    def test_skin_material_change_rejects_wrong_material_scope(self):
        result = SUBJECT.evaluate_skin_material_change(
            {
                "digest": "before",
                "mesh_digests": {
                    "CC_Base_Body": "body",
                    "Hair": "hair-before",
                },
                "texture_count": 1,
            },
            {
                "digest": "after",
                "mesh_digests": {
                    "CC_Base_Body": "body",
                    "Hair": "hair-after",
                },
                "texture_count": 1,
            },
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["changed_meshes"], ["Hair"])

    def test_resolver_assigns_domain_specific_verification_modes(self):
        with tempfile.TemporaryDirectory() as root:
            skin_path = os.path.join(root, "skin.ccSkin")
            glasses_path = os.path.join(root, "glasses.ccAcc")
            pathlib.Path(skin_path).write_bytes(b"skin")
            pathlib.Path(glasses_path).write_bytes(b"glasses")
            catalog = {
                "roots": [root],
                "assets": {
                    "skin": {
                        "asset_id": "skin",
                        "asset_type": "skin",
                        "automation_status": "candidate",
                        "display_name": "Skin",
                        "asset_form": "asset",
                        "extension": ".ccskin",
                        "preferred_path": skin_path,
                        "sex_hint": "female",
                        "slot": "skin",
                    },
                    "glasses": {
                        "asset_id": "glasses",
                        "asset_type": "accessory",
                        "automation_status": "candidate",
                        "display_name": "Glasses",
                        "asset_form": "asset",
                        "extension": ".ccacc",
                        "preferred_path": glasses_path,
                        "sex_hint": "unknown",
                        "slot": "accessory_head",
                    },
                },
            }
            resolved = SUBJECT.resolve_appearance_assets(
                {
                    "appearance_asset_ids": ["glasses", "skin"],
                    "sex": "female",
                },
                catalog,
            )
        self.assertEqual(
            [item["asset_id"] for item in resolved], ["skin", "glasses"]
        )
        self.assertEqual(resolved[0]["verification_mode"], "material_fingerprint")
        self.assertEqual(resolved[1]["verification_mode"], "scene_inventory")

    def test_material_step_matches_without_scene_inventory_change(self):
        self.assertTrue(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "material_fingerprint",
                    "material_changed": True,
                    "scene_changed": False,
                }
            )
        )

    def test_replaced_teeth_match_when_material_digest_is_unchanged(self):
        self.assertTrue(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "material_fingerprint",
                    "material_changed": False,
                    "replacement_verified": True,
                    "scene_changed": False,
                }
            )
        )

    def test_material_only_eye_step_requires_geometry_and_material_scope(self):
        self.assertTrue(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "material_fingerprint",
                    "material_changed": True,
                    "material_only_dialog": True,
                    "material_only_verified": True,
                }
            )
        )
        self.assertFalse(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "material_fingerprint",
                    "material_changed": True,
                    "material_only_dialog": True,
                    "material_only_verified": False,
                }
            )
        )

    def test_eye_part_morph_detection_is_category_scoped(self):
        self.assertTrue(
            SUBJECT.is_eye_part_morph(
                {
                    "categories": [
                        "Actor Parts/CC_Base_Eye/Eye/CC Embed Morphs"
                    ]
                }
            )
        )
        self.assertFalse(
            SUBJECT.is_eye_part_morph(
                {
                    "categories": [
                        "Actor/HD Head/CC Embed Morphs/Eyes"
                    ]
                }
            )
        )

    def test_scene_step_requires_scene_inventory_change(self):
        self.assertFalse(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "scene_inventory",
                    "material_changed": True,
                    "scene_changed": False,
                }
            )
        )

    def test_scene_step_accepts_verified_avatar_part_replacement(self):
        self.assertTrue(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "scene_inventory",
                    "scene_changed": False,
                    "replacement_verified": True,
                }
            )
        )

    def test_scene_step_accepts_verified_character_preset(self):
        self.assertTrue(
            SUBJECT.appearance_step_matches(
                {
                    "verification_mode": "scene_inventory",
                    "scene_changed": False,
                    "replacement_verified": False,
                    "character_preset_verified": True,
                }
            )
        )

    def test_teeth_asset_allows_only_oral_support_morph_changes(self):
        before = {
            "groups": {
                "face": {
                    "entries": [
                        {
                            "id": "teeth_shape",
                            "display": "HD Neutral Teeth",
                            "categories": ["Actor Parts/CC_Base_Teeth"],
                            "weight": 1.0,
                        }
                    ]
                }
            }
        }
        after = {
            "groups": {
                "face": {
                    "entries": [
                        {
                            "id": "teeth_shape",
                            "display": "HD Neutral Teeth",
                            "categories": ["Actor Parts/CC_Base_Teeth"],
                            "weight": 0.0,
                        }
                    ]
                }
            }
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "teeth"}],
            before,
            after,
            {
                "body": [],
                "junction": [],
                "face": [
                    {
                        "id": "teeth_shape",
                        "expected": 1.0,
                        "actual": 0.0,
                        "delta": -1.0,
                    }
                ],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "accepted")
        self.assertEqual(policy["allowed_change_count"], 1)
        self.assertEqual(policy["disallowed_change_count"], 0)

    def test_teeth_asset_rejects_body_morph_changes(self):
        entry = {
            "id": "body_shape",
            "display": "Body Shape",
            "categories": ["Actor/Body"],
            "weight": 1.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "teeth"}],
            {"groups": {"body": {"entries": [entry]}}},
            {"groups": {"body": {"entries": [dict(entry, weight=0.0)]}}},
            {
                "body": [
                    {
                        "id": "body_shape",
                        "expected": 1.0,
                        "actual": 0.0,
                        "delta": -1.0,
                    }
                ],
                "junction": [],
                "face": [],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "rejected")
        self.assertEqual(policy["disallowed_change_count"], 1)

    def test_eyelash_asset_allows_style_and_replaced_identity_lash(self):
        style = {
            "id": "lash_style",
            "display": "Dense Extended",
            "categories": ["Actor/Eyelash/HD Natural"],
            "weight": 0.0,
        }
        identity = {
            "id": "identity_lash",
            "display": "HD Ariana_Eyelash",
            "categories": [
                "Actor/Eyelash/CC Embed Morphs/CC5 Characters/Eyelash"
            ],
            "weight": 1.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "eyelashes"}],
            {
                "groups": {
                    "face": {"entries": [style, identity]},
                }
            },
            {
                "groups": {
                    "face": {
                        "entries": [
                            dict(style, weight=1.0),
                            dict(identity, weight=0.0),
                        ]
                    },
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [
                    {
                        "id": "lash_style",
                        "expected": 0.0,
                        "actual": 1.0,
                        "delta": 1.0,
                    },
                    {
                        "id": "identity_lash",
                        "expected": 1.0,
                        "actual": 0.0,
                        "delta": -1.0,
                    },
                ],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "accepted")
        self.assertEqual(policy["allowed_change_count"], 2)
        self.assertEqual(policy["disallowed_change_count"], 0)
        self.assertEqual(
            policy["allowed_changes"][0]["allowed_reason"],
            "eyelash_asset_style_morph",
        )
        self.assertEqual(
            policy["allowed_changes"][1]["allowed_reason"],
            "eyelash_asset_replaces_identity_eyelash_component",
        )

    def test_eyelash_asset_still_rejects_eye_identity_changes(self):
        eye_identity = {
            "id": "identity_eye",
            "display": "HD Ariana_Eyes",
            "categories": [
                "Actor/Eye/CC Embed Morphs/CC5 Characters/Eyes"
            ],
            "weight": 1.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "eyelashes"}],
            {"groups": {"face": {"entries": [eye_identity]}}},
            {
                "groups": {
                    "face": {
                        "entries": [dict(eye_identity, weight=0.0)]
                    }
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [
                    {
                        "id": "identity_eye",
                        "expected": 1.0,
                        "actual": 0.0,
                        "delta": -1.0,
                    }
                ],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "rejected")
        self.assertEqual(policy["allowed_change_count"], 0)
        self.assertEqual(policy["disallowed_change_count"], 1)

    def test_scalp_hair_allows_actor_parts_style_morph_only(self):
        hairline = {
            "id": "Hairline_High_All",
            "display": "Hairline_High_All",
            "categories": [
                "Actor Parts",
                "Actor Parts/Crew Cut",
                "Actor Parts/Back-swept Top",
            ],
            "weight": 0.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "scalp_hair"}],
            {"groups": {"other": {"entries": [hairline]}}},
            {
                "groups": {
                    "other": {
                        "entries": [dict(hairline, weight=1.0)]
                    }
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [],
                "other": [
                    {
                        "id": "Hairline_High_All",
                        "expected": 0.0,
                        "actual": 1.0,
                        "delta": 1.0,
                    }
                ],
            },
        )

        self.assertEqual(policy["status"], "accepted")
        self.assertEqual(policy["allowed_change_count"], 1)
        self.assertEqual(
            policy["allowed_changes"][0]["allowed_reason"],
            "scalp_hair_asset_style_morph",
        )

    def test_scalp_hair_allows_accessory_component_morph(self):
        accessory = {
            "id": "Upper Angle",
            "display": "Upper Angle",
            "categories": [
                "Accessory",
                "Accessory/Pigtail braid",
            ],
            "weight": 0.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "scalp_hair"}],
            {"groups": {"other": {"entries": [accessory]}}},
            {
                "groups": {
                    "other": {
                        "entries": [dict(accessory, weight=0.08)]
                    }
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [],
                "other": [
                    {
                        "id": "Upper Angle",
                        "expected": 0.0,
                        "actual": 0.08,
                        "delta": 0.08,
                    }
                ],
            },
        )

        self.assertEqual(policy["status"], "accepted")
        self.assertEqual(policy["allowed_change_count"], 1)
        self.assertEqual(
            policy["allowed_changes"][0]["allowed_reason"],
            "scalp_hair_asset_accessory_morph",
        )

    def test_scalp_hair_allows_actor_part_morph_in_face_bucket(self):
        hair = {
            "id": "Hair Tail_In_Rear",
            "display": "Hair Tail_In_Rear",
            "categories": [
                "Actor Parts",
                "Actor Parts/Messy Curly Top",
            ],
            "weight": 0.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "scalp_hair"}],
            {"groups": {"face": {"entries": [hair]}}},
            {
                "groups": {
                    "face": {
                        "entries": [dict(hair, weight=1.0)]
                    }
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [
                    {
                        "id": "Hair Tail_In_Rear",
                        "expected": 0.0,
                        "actual": 1.0,
                        "delta": 1.0,
                    }
                ],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "accepted")
        self.assertEqual(policy["allowed_change_count"], 1)
        self.assertEqual(
            policy["allowed_changes"][0]["allowed_reason"],
            "scalp_hair_asset_style_morph",
        )

    def test_scalp_hair_rejects_anatomical_actor_part_morph(self):
        eye = {
            "id": "Eye Support",
            "display": "Eye Support",
            "categories": [
                "Actor Parts",
                "Actor Parts/CC_Base_Eye",
            ],
            "weight": 0.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "scalp_hair"}],
            {"groups": {"face": {"entries": [eye]}}},
            {
                "groups": {
                    "face": {
                        "entries": [dict(eye, weight=1.0)]
                    }
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [
                    {
                        "id": "Eye Support",
                        "expected": 0.0,
                        "actual": 1.0,
                        "delta": 1.0,
                    }
                ],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "rejected")
        self.assertEqual(policy["disallowed_change_count"], 1)

    def test_scalp_hair_rejects_unowned_other_morph(self):
        unowned = {
            "id": "Unknown Control",
            "display": "Unknown Control",
            "categories": ["Actor/Unknown"],
            "weight": 0.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "scalp_hair"}],
            {"groups": {"other": {"entries": [unowned]}}},
            {
                "groups": {
                    "other": {
                        "entries": [dict(unowned, weight=1.0)]
                    }
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [],
                "other": [
                    {
                        "id": "Unknown Control",
                        "expected": 0.0,
                        "actual": 1.0,
                        "delta": 1.0,
                    }
                ],
            },
        )

        self.assertEqual(policy["status"], "rejected")
        self.assertEqual(policy["disallowed_change_count"], 1)

    def test_scalp_hair_rejects_face_morph_changes(self):
        face = {
            "id": "face_shape",
            "display": "Face Shape",
            "categories": ["Actor/Head"],
            "weight": 0.0,
        }
        policy = SUBJECT.evaluate_appearance_morph_policy(
            [{"slot": "scalp_hair"}],
            {"groups": {"face": {"entries": [face]}}},
            {
                "groups": {
                    "face": {"entries": [dict(face, weight=1.0)]}
                }
            },
            {
                "body": [],
                "junction": [],
                "face": [
                    {
                        "id": "face_shape",
                        "expected": 0.0,
                        "actual": 1.0,
                        "delta": 1.0,
                    }
                ],
                "other": [],
            },
        )

        self.assertEqual(policy["status"], "rejected")
        self.assertEqual(policy["disallowed_change_count"], 1)


if __name__ == "__main__":
    unittest.main()
