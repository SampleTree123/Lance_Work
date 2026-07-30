import importlib.util
import json
import pathlib
import unittest
import tempfile


SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "cc_build_scalp_hair_visual_review_v1.py"
)


def load_subject():
    spec = importlib.util.spec_from_file_location(
        "cc_scalp_hair_review_test_subject",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SUBJECT = load_subject()


class ScalpHairReviewTests(unittest.TestCase):
    def test_silhouette_families_are_stable(self):
        self.assertEqual(
            SUBJECT.silhouette_family("Bridal-Style Braid"),
            "braid",
        )
        self.assertEqual(
            SUBJECT.silhouette_family("Modern Mullet"),
            "mullet",
        )
        self.assertEqual(
            SUBJECT.silhouette_family("Curly Fringe Undercut"),
            "undercut",
        )
        self.assertEqual(
            SUBJECT.silhouette_family("Classic half up"),
            "half_up",
        )

    def test_style_tags_keep_multiple_traits(self):
        self.assertEqual(
            SUBJECT.style_tags("Side-swept long Mullet"),
            ["long", "mullet", "side_styled"],
        )

    def test_build_expands_asset_decisions_to_dual_sex_reviews(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            image_path = root / "preview.png"
            image_path.write_bytes(b"preview")
            assets = []
            presets = []
            results = []
            for index in range(60):
                asset_id = "ASSET_{:02d}".format(index)
                assets.append(
                    {
                        "asset_id": asset_id,
                        "display_name": "Hair {:02d}".format(index),
                        "hair_builder_pack": {
                            "asset_index": index + 1,
                            "pack_code": "HBX",
                            "pack_id": "synthetic",
                        },
                        "presentation_prior": {
                            "female_presentation_score": 0.85,
                            "label": "female_primary",
                            "source": "test_prior",
                        },
                    }
                )
                for sex in ("male", "female"):
                    preset_id = "P_{:02d}_{}".format(index, sex)
                    presets.append(
                        {
                            "appearance_asset_ids": [asset_id],
                            "preset_id": preset_id,
                            "sex": sex,
                        }
                    )
                    artifacts = {
                        key: str(image_path)
                        for key in SUBJECT.REQUIRED_ARTIFACT_KEYS
                    }
                    results.append(
                        {
                            "appearance_application": {
                                "steps": [
                                    {
                                        "added_objects": [
                                            {
                                                "collection": "GetHairs",
                                                "name": "Hair",
                                            }
                                        ]
                                    }
                                ]
                            },
                            "appearance_matches_recipe": True,
                            "appearance_morphs_within_policy": True,
                            "artifacts": artifacts,
                            "preset_id": preset_id,
                            "success": True,
                        }
                    )

            decisions = {
                "asset_overrides": {
                    "ASSET_00": {
                        "accepted_sexes": [],
                        "notes": ["Synthetic conditional asset."],
                        "production_status": (
                            "conditional_cleanup_required"
                        ),
                        "risk_tags": ["synthetic_risk"],
                    }
                },
                "default_accepted_sexes": ["male", "female"],
                "default_production_status": (
                    "approved_static_dynamic_pending"
                ),
                "presentation_overrides": {
                    "ASSET_01": {
                        "female_presentation_score": 0.5,
                        "label": "unisex",
                        "source": "test_review",
                    }
                },
                "review_complete": True,
                "schema_version": 1,
            }

            paths = {
                "catalog": root / "catalog.json",
                "batch": root / "batch.json",
                "validation": root / "validation.json",
                "decisions": root / "decisions.json",
                "output": root / "review.json",
            }
            documents = {
                "catalog": {"assets": assets},
                "batch": {"presets": presets},
                "validation": {"results": results},
                "decisions": decisions,
            }
            for key, document in documents.items():
                paths[key].write_text(
                    json.dumps(document),
                    encoding="utf-8",
                )

            built = SUBJECT.build(
                str(paths["catalog"]),
                str(paths["batch"]),
                str(paths["validation"]),
                str(paths["decisions"]),
                str(paths["output"]),
            )
            self.assertTrue(built["success"])
            self.assertEqual(
                built["summary"]["accepted_combination_count"],
                118,
            )
            review = json.loads(
                paths["output"].read_text(encoding="utf-8")
            )
            status_counts = review["summary"][
                "production_status_counts"
            ]
            self.assertEqual(
                status_counts["approved_static_dynamic_pending"],
                59,
            )
            self.assertEqual(
                status_counts["conditional_cleanup_required"],
                1,
            )
            visual_counts = {
                status: sum(
                    item["visual_status"] == status
                    for item in review["reviews"]
                )
                for status in ("accepted", "rejected")
            }
            self.assertEqual(
                visual_counts,
                {"accepted": 118, "rejected": 2},
            )


if __name__ == "__main__":
    unittest.main()
