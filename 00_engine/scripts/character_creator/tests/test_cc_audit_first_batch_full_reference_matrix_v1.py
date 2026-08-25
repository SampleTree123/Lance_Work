import os
import sys
import tempfile
import unittest


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import cc_audit_first_batch_full_reference_matrix_v1 as audit


class OptionalDirectoryAuditTest(unittest.TestCase):
    def test_absent_zero_sized_directory_is_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = os.path.join(temporary, "textures")
            result = audit.verify_optional_directory_record(
                {
                    "path": path,
                    "present": False,
                    "file_count": 0,
                    "total_bytes": 0,
                },
                "textures",
            )
        self.assertEqual(0, result["file_count"])
        self.assertEqual(0, result["total_bytes"])

    def test_absent_directory_cannot_claim_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(audit.MatrixAuditError):
                audit.verify_optional_directory_record(
                    {
                        "path": os.path.join(temporary, "textures"),
                        "present": False,
                        "file_count": 1,
                        "total_bytes": 128,
                    },
                    "textures",
                )

    def test_present_directory_is_still_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(audit.MatrixAuditError):
                audit.verify_optional_directory_record(
                    {
                        "path": os.path.join(temporary, "missing"),
                        "present": True,
                        "file_count": 0,
                        "total_bytes": 0,
                    },
                    "textures",
                )


if __name__ == "__main__":
    unittest.main()
