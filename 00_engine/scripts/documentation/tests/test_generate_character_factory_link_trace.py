from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from generate_character_factory_link_trace import generate  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


class DocumentationLinkTraceTests(unittest.TestCase):
    def test_multiple_mentions_and_backlink_are_rendered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            master = root / "CHARACTER_FACTORY_MASTER_SPEC.md"
            index = root / "area" / "README.md"
            detail = root / "area" / "DETAIL.md"
            trace = root / "reference" / "DOCUMENT_LINK_TRACE.md"
            write(
                master,
                "\n".join(
                    [
                        "# Master",
                        "[Area](area/README.md)",
                        "[Detail direct A](area/DETAIL.md)",
                        "[Detail direct B](area/DETAIL.md)",
                        "[Trace](reference/DOCUMENT_LINK_TRACE.md)",
                    ]
                ),
            )
            write(index, "# Area\n[Detail](DETAIL.md)\n[Master](../CHARACTER_FACTORY_MASTER_SPEC.md)")
            write(detail, "# Detail\n[Area](README.md)\n[Master](../CHARACTER_FACTORY_MASTER_SPEC.md)")
            write(trace, "# Trace placeholder")

            stats = generate(root, trace, "2026-08-06")
            rendered = trace.read_text(encoding="utf-8")

            self.assertEqual(stats["current_documents"], 4)
            self.assertEqual(stats["reachable_documents"], 4)
            self.assertIn("CHARACTER_FACTORY_MASTER_SPEC.md:L3", rendered)
            self.assertIn("CHARACTER_FACTORY_MASTER_SPEC.md:L4", rendered)
            self.assertIn("area/README.md:L2", rendered)
            self.assertIn("[回链，不继续递归]", rendered)

    def test_archive_manifest_payload_is_rendered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            master = root / "CHARACTER_FACTORY_MASTER_SPEC.md"
            history = root / "history" / "README.md"
            archive = root / "history" / "legacy_fixture"
            manifest = archive / "ARCHIVE_MANIFEST.md"
            payload = archive / "OLD.md"
            trace = root / "reference" / "DOCUMENT_LINK_TRACE.md"
            write(master, "# Master\n[History](history/README.md)\n[Trace](reference/DOCUMENT_LINK_TRACE.md)")
            write(history, "# History\n[Manifest](legacy_fixture/ARCHIVE_MANIFEST.md)")
            write(payload, "# Old")
            payload_bytes = payload.read_bytes()
            import hashlib

            write(
                manifest,
                "\n".join(
                    [
                        "# Manifest",
                        "| File | Bytes | SHA-256 |",
                        "| --- | ---: | --- |",
                        f"| `OLD.md` | {len(payload_bytes)} | `{hashlib.sha256(payload_bytes).hexdigest()}` |",
                    ]
                ),
            )
            write(trace, "# Trace placeholder")

            stats = generate(root, trace, "2026-08-06")
            rendered = trace.read_text(encoding="utf-8")

            self.assertEqual(stats["archive_manifests"], 1)
            self.assertEqual(stats["archive_payloads"], 1)
            self.assertIn("history/legacy_fixture/ARCHIVE_MANIFEST.md:L4", rendered)
            self.assertIn("history/legacy_fixture/OLD.md", rendered)


if __name__ == "__main__":
    unittest.main()
