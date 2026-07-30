import importlib.util
import json
import os
import tempfile
import unittest

from PIL import Image


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(
    SCRIPT_DIR,
    "cc_make_face_profile_matrix_contact_sheets_v1.py",
)
SPEC = importlib.util.spec_from_file_location(
    "cc_make_face_profile_matrix_contact_sheets_v1",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FaceProfileMatrixContactSheetTests(unittest.TestCase):
    def test_creates_one_sheet_from_bridge_result(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts = {}
            for index, (artifact_key, _) in enumerate(MODULE.VIEWS):
                path = os.path.join(directory, "{}.png".format(artifact_key))
                Image.new("RGB", (24, 24), (index, 0, 0)).save(path)
                artifacts[artifact_key] = path
            result_path = os.path.join(directory, "result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "result": {
                            "validation": {
                                "results": [
                                    {
                                        "artifacts": artifacts,
                                        "preset_id": "FACE_01",
                                        "sex": "female",
                                        "success": True,
                                    }
                                ]
                            }
                        }
                    },
                    handle,
                )
            output_dir = os.path.join(directory, "review")

            records = MODULE.create_contact_sheets(
                [result_path],
                output_dir,
                visual_review_status="passed",
            )

            self.assertEqual(1, len(records))
            self.assertTrue(
                os.path.isfile(os.path.join(output_dir, "FACE_01.png"))
            )
            with open(
                os.path.join(output_dir, "index.json"),
                "r",
                encoding="utf-8",
            ) as handle:
                index = json.load(handle)
            self.assertEqual(1, index["case_count"])
            self.assertEqual(
                "passed",
                index["cases"][0]["visual_review_status"],
            )


if __name__ == "__main__":
    unittest.main()
