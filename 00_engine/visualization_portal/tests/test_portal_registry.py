from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from portal_registry import (  # noqa: E402
    PortalDataError,
    register_run,
    validate_local_assets,
    validate_run,
)


def sample_run(run_id: str, created_at: str) -> dict:
    return {
        "schema_version": 1,
        "id": run_id,
        "title": "Sample",
        "task": "CC / Test",
        "created_at": created_at,
        "status": "pending_review",
        "summary": "Sample run",
        "thumbnail": "/outputs/thumb.png",
        "groups": {
            "female": {
                "label": "Female",
                "overview": "/outputs/overview.png",
                "comparisons": {},
                "cases": [
                    {
                        "id": "P00",
                        "label": "Baseline",
                        "parameters": {},
                        "images": {"front": "/outputs/front.png"},
                    }
                ],
            }
        },
    }


class RegistryTests(unittest.TestCase):
    def test_rejects_invalid_run_id(self) -> None:
        run = sample_run("Invalid ID", "2026-08-09T10:00:00+08:00")
        with self.assertRaises(PortalDataError):
            validate_run(run)

    def test_registers_and_sorts_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            portal = root / "portal"
            source_a = root / "a.json"
            source_b = root / "b.json"
            source_a.write_text(
                json.dumps(sample_run("2026-08-08-sample-a", "2026-08-08T10:00:00+08:00")),
                encoding="utf-8",
            )
            source_b.write_text(
                json.dumps(sample_run("2026-08-09-sample-b", "2026-08-09T10:00:00+08:00")),
                encoding="utf-8",
            )
            register_run(source_a, portal)
            register_run(source_b, portal)
            registry = json.loads((portal / "data" / "registry.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [entry["id"] for entry in registry["runs"]],
                ["2026-08-09-sample-b", "2026-08-08-sample-a"],
            )

    def test_local_asset_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outputs = root / "outputs"
            outputs.mkdir()
            for name in ("thumb.png", "overview.png", "front.png"):
                (outputs / name).write_bytes(b"image")
            run = sample_run("2026-08-09-assets", "2026-08-09T10:00:00+08:00")
            self.assertEqual(validate_local_assets(run, root), [])
            (outputs / "front.png").unlink()
            self.assertEqual(validate_local_assets(run, root), ["/outputs/front.png"])

    def test_frontend_exposes_approved_ranges_and_scan_evidence(self) -> None:
        portal_root = Path(__file__).resolve().parents[1]
        app_source = (portal_root / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("approved_single_axis_ranges", app_source)
        self.assertIn("批准的单轴范围", app_source)
        self.assertIn("扫描证据，超出批准范围", app_source)

    def test_frontend_keeps_full_group_labels_and_zoomable_lightbox(self) -> None:
        portal_root = Path(__file__).resolve().parents[1]
        index_source = (portal_root / "index.html").read_text(encoding="utf-8")
        app_source = (portal_root / "assets" / "app.js").read_text(encoding="utf-8")
        style_source = (portal_root / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('id="dialogZoomIn"', index_source)
        self.assertIn('id="dialogZoomOut"', index_source)
        self.assertIn('class="segmented segmented--groups"', app_source)
        self.assertIn('addEventListener("wheel"', app_source)
        self.assertIn("min-width: max-content", style_source)
        self.assertIn("image-dialog__canvas--dragging", style_source)

    def test_frontend_rebuilds_detail_views_after_group_change(self) -> None:
        portal_root = Path(__file__).resolve().parents[1]
        app_source = (portal_root / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function commonImageViews(caseA, caseB)", app_source)
        self.assertIn("function rebuildCompareViews()", app_source)
        self.assertIn("compareView.innerHTML = compareViewOptions", app_source)
        self.assertIn(
            'compareA.addEventListener("change", rebuildCompareViews)',
            app_source,
        )
        self.assertNotIn("const compareViews =", app_source)

    def test_candidate_review_schema_and_frontend_are_available(self) -> None:
        run = sample_run("2026-08-18-review", "2026-08-18T23:00:00+08:00")
        run["review"] = {
            "schema_version": 1,
            "mode": "candidate_review",
            "review_id": "cc-animation-offline-review-v1",
            "source_fingerprint": "sha256:test",
        }
        validate_run(run)
        portal_root = Path(__file__).resolve().parents[1]
        app_source = (portal_root / "assets" / "app.js").read_text(encoding="utf-8")
        review_source = (portal_root / "assets" / "review-workspace.js").read_text(encoding="utf-8")
        self.assertIn('run.review?.mode === "candidate_review"', app_source)
        self.assertIn("localStorage", review_source)
        self.assertIn("downloadJson", review_source)
        self.assertIn("applyImportedState", review_source)

    def test_candidate_review_rejects_duplicate_case_ids(self) -> None:
        run = sample_run("2026-08-18-review-dup", "2026-08-18T23:00:00+08:00")
        run["review"] = {
            "schema_version": 1,
            "mode": "candidate_review",
            "review_id": "cc-animation-offline-review-dup-v1",
        }
        run["groups"]["male"] = {
            "label": "Male",
            "overview": "/outputs/overview.png",
            "comparisons": {},
            "cases": [run["groups"]["female"]["cases"][0].copy()],
        }
        with self.assertRaises(PortalDataError):
            validate_run(run)

    def test_offline_review_launcher_and_full_candidate_names_are_preserved(self) -> None:
        portal_root = Path(__file__).resolve().parents[1]
        launcher = (portal_root / "OPEN_OFFLINE_ANIMATION_REVIEW.cmd").read_text(
            encoding="utf-8"
        )
        guide = (portal_root / "OFFLINE_ANIMATION_REVIEW.md").read_text(
            encoding="utf-8"
        )
        review_source = (portal_root / "assets" / "review-workspace.js").read_text(
            encoding="utf-8"
        )
        style_source = (portal_root / "assets" / "styles.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("2026-08-18-cc-animation-p0-offline-review-v1", launcher)
        self.assertIn("导出决定", guide)
        self.assertIn("candidate.label} | ${candidate.groupLabel", review_source)
        self.assertIn("overflow-wrap: anywhere", style_source)


if __name__ == "__main__":
    unittest.main()
