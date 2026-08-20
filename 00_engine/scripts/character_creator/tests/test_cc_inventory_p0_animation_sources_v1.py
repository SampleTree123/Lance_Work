import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INVENTORY = load_module(
    "cc_inventory_p0_animation_sources_v1",
    "cc_inventory_p0_animation_sources_v1.py",
)


class P0AnimationSourceInventoryTests(unittest.TestCase):
    def make_sources(self, root):
        first = root / "Everyday.zip"
        with zipfile.ZipFile(first, "w", compression=zipfile.ZIP_STORED) as output:
            output.writestr("Walk/Walk_Loop_F.rlMotion", b"walk")
            output.writestr("Social/Chat_Stand_M.rlMotion", b"chat")
            output.writestr("Home/Dining_CheckPhone_M.rlMotion", b"phone")
            output.writestr("nested/payload.rar", b"nested")

        directory = root / "Travel Bundle"
        directory.mkdir()
        with zipfile.ZipFile(
            directory / "travel.zip", "w", compression=zipfile.ZIP_STORED
        ) as output:
            output.writestr(
                "Interaction/Greet_Friend_F.rlMotion", b"paired"
            )
        (directory / "Stand_Idle.iMotion").write_bytes(b"idle")

    def test_build_inventory_keeps_every_motion_unapproved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "P0_Core_Everyday"
            source.mkdir()
            self.make_sources(source)
            output = root / "output"
            result = INVENTORY.build_inventory(
                source,
                output,
                expected_package_count=2,
            )

            self.assertTrue(result["validation"]["success"])
            self.assertEqual(2, result["summary"]["package_count"])
            self.assertEqual(2, result["summary"]["archive_count"])
            self.assertEqual(5, result["summary"]["motion_count"])
            self.assertEqual(1, result["summary"]["nested_archive_entry_count"])
            self.assertEqual(0, result["summary"]["production_approved_count"])
            self.assertTrue(
                all(
                    motion["production_status"] == "not_approved"
                    for motion in result["motions"]
                )
            )

            persisted = json.loads(
                (output / "inventory.json").read_text(encoding="utf-8")
            )
            queue = json.loads(
                (output / "review_queue.json").read_text(encoding="utf-8")
            )
            self.assertEqual(result["inventory_id"], persisted["inventory_id"])
            self.assertEqual(5, sum(queue["counts"].values()))

    def test_filename_hints_are_conservative_candidates(self):
        walk = INVENTORY.infer_motion_hints("Walk/Walk_Loop_F.rlMotion")
        self.assertEqual("standalone_candidate", walk["dependency_class"])
        self.assertEqual("standalone_first", walk["review_bucket"])
        self.assertIn("locomotion", walk["semantic_tags"])

        phone = INVENTORY.infer_motion_hints(
            "Dinner/Dining_CheckPhone_M.rlMotion"
        )
        self.assertEqual("prop_candidate", phone["dependency_class"])
        self.assertIn("prop:phone", phone["dependency_hints"])
        self.assertIn("scene:seating", phone["dependency_hints"])

        paired = INVENTORY.infer_motion_hints(
            "Interaction/Greet_Friend_F.rlMotion"
        )
        self.assertEqual("paired_candidate", paired["dependency_class"])
        self.assertEqual("dependency_review_later", paired["review_bucket"])

        held_item = INVENTORY.infer_motion_hints(
            "City Life/Walk/Walk_HoldItem_M.rlMotion"
        )
        self.assertEqual("prop_candidate", held_item["dependency_class"])

        retail = INVENTORY.infer_motion_hints(
            "Shopping/Department Store/Corridor_Idle_F.rlMotion"
        )
        self.assertEqual("scene_locked_candidate", retail["dependency_class"])

        camera = INVENTORY.infer_motion_hints(
            "City Life/Travel/Photo_DSLR_M.rlMotion"
        )
        self.assertEqual("prop_candidate", camera["dependency_class"])

    def test_sex_hint_uses_suffix_or_explicit_female_package(self):
        self.assertEqual(
            "female",
            INVENTORY.infer_sex_hint("Walk/Walk_Loop_F.rlMotion", "Pack"),
        )
        self.assertEqual(
            "male",
            INVENTORY.infer_sex_hint("Audience M 01.rlMotion", "Pack"),
        )
        self.assertEqual(
            "female",
            INVENTORY.infer_sex_hint(
                "Walk/Walk_Loop.iMotion", "Female Casual Moves.zip"
            ),
        )


if __name__ == "__main__":
    unittest.main()
