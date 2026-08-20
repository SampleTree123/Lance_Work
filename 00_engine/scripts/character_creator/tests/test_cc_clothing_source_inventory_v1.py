import importlib.util
import io
import json
import pathlib
import shutil
import tempfile
import unittest
import zipfile

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INVENTORY = load_module(
    "cc_inventory_clothing_sources_v1",
    "cc_inventory_clothing_sources_v1.py",
)
REVIEW = load_module(
    "cc_make_clothing_source_inventory_review_v1",
    "cc_make_clothing_source_inventory_review_v1.py",
)


def png_bytes(color=(100, 150, 200)):
    stream = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(stream, format="PNG")
    return stream.getvalue()


class ClothingSourceInventoryTests(unittest.TestCase):
    def make_sources(self, root):
        female = root / "female"
        male = root / "male"
        female.mkdir()
        male.mkdir()

        archive = female / "mixed_clothing.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
            output.writestr("Pack/Cloth/Shirts/top.ccCloth", b"shirt")
            output.writestr("Pack/Actor/base.ccAvatar", b"avatar")
            output.writestr("Pack/preview.png", png_bytes())
            output.writestr("../../evil.png", png_bytes((200, 50, 50)))
        shutil.copyfile(archive, male / "duplicate_mixed_clothing.zip")

        with zipfile.ZipFile(
            male / "character_only.zip", "w", compression=zipfile.ZIP_STORED
        ) as output:
            output.writestr("Actor/person.ccProject", b"project")

        loose = female / "Extracted Pack" / "Coats"
        loose.mkdir(parents=True)
        (loose / "jacket.ccCloth").write_bytes(b"coat")
        (loose / "preview.jpg").write_bytes(png_bytes((20, 180, 80)))
        return female, male

    def test_inventory_classifies_actual_contents_and_exact_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            female, male = self.make_sources(root)
            output = root / "output"
            result = INVENTORY.build_inventory(
                {"female": female, "male": male},
                output,
                max_previews=2,
            )
            self.assertEqual(4, result["summary"]["package_count"])
            self.assertTrue(result["validation"]["success"])
            self.assertEqual(3, result["validation"]["checked_archive_count"])
            self.assertEqual(3, result["summary"]["clothing_candidate_count"])
            self.assertEqual(1, result["summary"]["non_clothing_package_count"])
            self.assertEqual(1, len(result["duplicate_archive_groups"]))

            by_label = {package["label"]: package for package in result["packages"]}
            mixed = by_label["mixed_clothing"]
            self.assertEqual("clothing_with_character", mixed["content_class"])
            self.assertIn("upper", mixed["slots"])
            self.assertEqual("swap_group_candidate", mixed["look_policy_hint"])
            self.assertEqual(
                "all_wearables_suspected_placeholders", mixed["payload_gate"]
            )
            self.assertFalse(mixed["pilot_candidate"])
            self.assertTrue(mixed["preview_paths"])
            for preview in mixed["preview_paths"]:
                self.assertTrue(pathlib.Path(preview).is_relative_to(output.resolve()))
            self.assertFalse((root / "evil.png").exists())

            character = by_label["character_only"]
            self.assertEqual("character_only", character["content_class"])
            self.assertFalse(character["clothing_candidate"])
            self.assertTrue((output / "inventory.json").is_file())
            persisted = json.loads((output / "inventory.json").read_text("utf-8"))
            self.assertEqual(result["inventory_id"], persisted["inventory_id"])

    def test_wearable_payload_size_marks_only_small_files_as_suspected(self):
        placeholder = INVENTORY.entry_record("shirt.ccCloth", 6 * 1024)
        payload = INVENTORY.entry_record(
            "shirt.ccCloth", INVENTORY.MIN_PLAUSIBLE_WEARABLE_BYTES
        )
        self.assertEqual("suspected_placeholder", placeholder["payload_status"])
        self.assertEqual("payload_present", payload["payload_status"])

    def test_review_renders_every_package_without_requiring_a_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            female, male = self.make_sources(root)
            inventory_dir = root / "inventory"
            INVENTORY.build_inventory(
                {"female": female, "male": male}, inventory_dir, max_previews=1
            )
            review_dir = inventory_dir / "review"
            result = REVIEW.build_review(inventory_dir / "inventory.json", review_dir)
            self.assertEqual(4, result["package_count"])
            self.assertEqual(3, len(result["groups"]))
            cards = list((review_dir / "cards").rglob("*.png"))
            self.assertEqual(4, len(cards))
            self.assertTrue((review_dir / "README.md").is_file())
            self.assertTrue((review_dir / "index.json").is_file())


if __name__ == "__main__":
    unittest.main()
