from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


PORTAL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PORTAL_ROOT / "serve.py"
SPEC = importlib.util.spec_from_file_location("portal_server", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


class PortalRangeRequestTests(unittest.TestCase):
    def test_parses_bounded_open_and_suffix_ranges(self) -> None:
        parse = SUBJECT.ReviewHandler._parse_byte_range
        self.assertEqual(parse("bytes=10-19", 100), (10, 19))
        self.assertEqual(parse("bytes=90-", 100), (90, 99))
        self.assertEqual(parse("bytes=-12", 100), (88, 99))

    def test_rejects_invalid_or_multiple_ranges(self) -> None:
        parse = SUBJECT.ReviewHandler._parse_byte_range
        for value in ("items=0-1", "bytes=100-101", "bytes=5-3", "bytes=0-1,4-5"):
            with self.assertRaises(ValueError):
                parse(value, 100)


if __name__ == "__main__":
    unittest.main()
