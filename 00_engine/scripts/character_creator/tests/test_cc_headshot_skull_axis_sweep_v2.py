import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
SAFE_RANGES_PATH = ROOT / "cc_headshot_skull_safe_ranges_v1.json"


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_module(
    "cc_build_headshot_skull_axis_sweep_v2",
    "cc_build_headshot_skull_axis_sweep_v2.py",
)
SHEETS = load_module(
    "cc_make_headshot_skull_axis_sweep_sheets_v2",
    "cc_make_headshot_skull_axis_sweep_sheets_v2.py",
)


class HeadshotSkullAxisSweepV2Tests(unittest.TestCase):
    def test_manifest_has_single_axis_cases(self):
        library = BUILDER.build_library()
        self.assertEqual("targeted_morph_visual_matrix", library["diagnostic_mode"])
        self.assertEqual(16, len(library["presets"]))
        self.assertEqual(30, sum(len(preset["axis_sweep"]["values"]) for preset in library["presets"]))
        self.assertEqual(16, len({preset["preset_id"] for preset in library["presets"]}))
        for preset in library["presets"]:
            review = preset["neck_morph_review"]
            self.assertEqual(1, len(review["morphs"]))
            active = review["morphs"][0]["morph_id"]
            fixed = {item["morph_id"] for item in review["fixed_morphs"]}
            self.assertNotIn(active, fixed)
            self.assertEqual(6, len(fixed))

    def test_review_sheets_flatten_negative_and_positive_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = BUILDER.build_library()
            manifest["presets"] = [
                preset
                for preset in manifest["presets"]
                if preset["sex"] == "female"
            ]
            manifest_path = os.path.join(directory, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle)

            results = []
            for preset in manifest["presets"]:
                candidates = []
                for value in preset["axis_sweep"]["values"]:
                    views = {}
                    for index, (view_id, unused_label) in enumerate(SHEETS.VIEW_ORDER):
                        path = os.path.join(directory, "{}_{}_{}.png".format(preset["preset_id"], value, view_id))
                        Image.new("RGB", (64, 64), (40 + index * 20, 30, 50)).save(path)
                        views[view_id] = path
                    candidates.append({"value": value, "views": views})
                results.append(
                    {
                        "preset_id": preset["preset_id"],
                        "sex": "female",
                        "success": True,
                        "neck_morph_review": {"morphs": [{"candidates": candidates}]},
                    }
                )
            result_path = os.path.join(directory, "result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump({"diagnostic_mode": "targeted_morph_visual_matrix", "results": results}, handle)

            output = os.path.join(directory, "review")
            index = SHEETS.create_review_sheets(manifest_path, [result_path], output)
            self.assertEqual(15, index["case_count"])
            self.assertEqual(45, index["image_count"])
            self.assertTrue(os.path.isfile(os.path.join(output, "female", "overview.png")))
            self.assertEqual(1, sum(item["case_id"] == "BASELINE" for item in index["profiles"]))

    def test_human_reviewed_safe_ranges_preserve_scan_evidence(self):
        safe_ranges = json.loads(SAFE_RANGES_PATH.read_text(encoding="utf-8"))
        self.assertEqual("human_visual_approved", safe_ranges["status"])
        self.assertEqual(7, len(safe_ranges["axes"]))
        self.assertTrue(safe_ranges["composition_policy"]["single_axis_ranges_approved"])
        self.assertFalse(
            safe_ranges["composition_policy"]["multi_axis_extreme_combinations_approved"]
        )

        by_id = {axis["axis_id"]: axis for axis in safe_ranges["axes"]}
        self.assertEqual(-0.5, by_id["SKULL_BACK_DEPTH"]["minimum"])
        self.assertEqual(0.5, by_id["SKULL_BACK_DEPTH"]["maximum"])
        self.assertEqual(-0.7, by_id["SKULL_BACK_DEPTH"]["reviewed_minimum"])
        self.assertEqual(0.7, by_id["SKULL_BACK_DEPTH"]["reviewed_maximum"])

        scanned = {axis["axis_id"]: tuple(axis["values"]) for axis in BUILDER.AXES}
        self.assertEqual((-0.7, 0.7), scanned["SKULL_BACK_DEPTH"])
        for axis in safe_ranges["axes"]:
            self.assertLessEqual(-1.0, axis["minimum"])
            self.assertLessEqual(axis["minimum"], 0.0)
            self.assertGreaterEqual(axis["maximum"], 0.0)
            self.assertLessEqual(axis["maximum"], 1.0)


if __name__ == "__main__":
    unittest.main()
