from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from build_output_inventory import build_inventory  # noqa: E402
from build_script_lifecycle_catalog import (  # noqa: E402
    build_catalog,
    owner_for,
    scripts_in_scan_root,
)
from check_character_factory_docs import (  # noqa: E402
    AuditReport,
    check_output_catalog,
    check_script_catalog,
    tracked_scripts,
)


class ScriptDiscoveryTests(unittest.TestCase):
    def test_git_discovery_includes_untracked_and_excludes_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            scripts = root / "00_engine/scripts"
            scripts.mkdir(parents=True)
            (scripts / "tracked.py").write_text("pass\n", encoding="utf-8")
            (scripts / "untracked.py").write_text("pass\n", encoding="utf-8")
            (scripts / "ignored.py").write_text("pass\n", encoding="utf-8")
            (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

            subprocess.run(
                ["git", "-C", str(root), "init", "--quiet"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "add", "00_engine/scripts/tracked.py"],
                check=True,
            )

            for discover in (scripts_in_scan_root, tracked_scripts):
                actual = {
                    path.relative_to(root).as_posix()
                    for path in discover(root, "00_engine")
                }
                self.assertIn("00_engine/scripts/tracked.py", actual)
                self.assertIn("00_engine/scripts/untracked.py", actual)
                self.assertNotIn("00_engine/scripts/ignored.py", actual)


def test_ownership_is_independent_from_retention(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    run = outputs / "cc" / "run_001"
    accepted = run / "accepted"
    accepted.mkdir(parents=True)
    (run / "log.txt").write_text("log", encoding="utf-8")
    (accepted / "manifest.json").write_text("{}", encoding="utf-8")

    policy = {
        "default_retention": "unclassified",
        "ownership_rules": [
            {
                "path_prefix": "cc",
                "workflow": "WF-30",
                "owner_document": "technical/cc.md",
                "output_contract_id": "OUT-WF30-CC-ASSETS",
                "reason": "CC outputs",
            }
        ],
        "rules": [
            {
                "path_prefix": "cc/run_001/accepted",
                "retention": "authoritative",
                "workflow": "WF-70",
                "owner_document": "technical/dataset.md",
                "output_contract_id": "OUT-WF70-JOB-GRAPH",
                "reason": "Accepted manifest",
            }
        ],
    }

    inventory = build_inventory(outputs, policy)
    entries = {entry["path"]: entry for entry in inventory["entries"]}

    run_entry = entries["cc/run_001"]
    assert run_entry["retention"] == "unclassified"
    assert run_entry["owner_document"] == "technical/cc.md"
    assert run_entry["workflow"] == "WF-30"
    assert run_entry["output_contract_id"] == "OUT-WF30-CC-ASSETS"
    assert "Do not delete" in run_entry["classification_reason"]

    accepted_entry = entries["cc/run_001/accepted"]
    assert accepted_entry["retention"] == "authoritative"
    assert accepted_entry["owner_document"] == "technical/dataset.md"
    assert accepted_entry["workflow"] == "WF-70"
    assert accepted_entry["output_contract_id"] == "OUT-WF70-JOB-GRAPH"


def test_script_catalog_covers_engine_subsystems_and_excludes_outputs(
    tmp_path: Path,
) -> None:
    doc_root = tmp_path / "docs"
    for relative in (
        "technical/bridge/CC_BRIDGE_OPERATIONS.md",
        "technical/validation/VISUAL_REVIEW.md",
        "technical/dataset/CONFIG_GRAPH_AND_CHAINS.md",
        "technical/rendering_release/SERVER_EXECUTION.md",
    ):
        path = doc_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")

    paths = (
        "00_engine/scripts/dataset/build_graph.py",
        "00_engine/character_creator_bridge/plugin/main.py",
        "00_engine/visualization_portal/serve.py",
        "00_engine/outputs/copied_tool.py",
        "20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh",
    )
    for relative in paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n", encoding="utf-8")

    catalog = build_catalog(tmp_path, doc_root)
    entries = {entry["path"]: entry for entry in catalog["scripts"]}

    assert "00_engine/scripts/dataset/build_graph.py" in entries
    assert "00_engine/character_creator_bridge/plugin/main.py" in entries
    assert "00_engine/visualization_portal/serve.py" in entries
    assert "20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh" in entries
    assert "00_engine/outputs/copied_tool.py" not in entries
    assert entries["00_engine/character_creator_bridge/plugin/main.py"][
        "owner_document"
    ] == "technical/bridge/CC_BRIDGE_OPERATIONS.md"
    assert entries["00_engine/visualization_portal/serve.py"][
        "owner_document"
    ] == "technical/validation/VISUAL_REVIEW.md"
    assert entries["20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh"][
        "owner_document"
    ] == "technical/rendering_release/SERVER_EXECUTION.md"
    assert entries["20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh"][
        "scan_root"
    ] == "20_planning/implementation"


def test_specific_transfer_and_catalog_owners() -> None:
    assert owner_for(
        "00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh"
    ) == "technical/rendering_release/SERVER_EXECUTION.md"
    assert owner_for(
        "00_engine/scripts/unreal/run_first_batch_full_reference_import.py"
    ) == "technical/transfer/CC_TO_UE_FULLREFERENCE.md"
    assert owner_for(
        "00_engine/scripts/unreal/run_first_batch_motion_import.py"
    ) == "technical/transfer/MOTION_TRANSFER.md"
    assert owner_for(
        "00_engine/scripts/documentation/build_output_inventory.py"
    ) == "technical/output/INVENTORY_AND_RETENTION.md"


def test_script_catalog_rejects_undocumented_production_entry(tmp_path: Path) -> None:
    script = tmp_path / "00_engine/scripts/demo.py"
    script.parent.mkdir(parents=True)
    script.write_text("pass\n", encoding="utf-8")
    (tmp_path / "20_planning/implementation").mkdir(parents=True)

    doc_root = tmp_path / "docs"
    owner = doc_root / "technical/demo.md"
    owner.parent.mkdir(parents=True)
    owner.write_text("# Demo\n", encoding="utf-8")

    catalog_path = tmp_path / "00_engine/scripts/SCRIPT_CATALOG.json"
    catalog_path.write_text(
        json.dumps(
            {
                "script_roots": ["00_engine", "20_planning/implementation"],
                "scripts": [
                    {
                        "path": "00_engine/scripts/demo.py",
                        "scan_root": "00_engine",
                        "lifecycle": "production",
                        "owner_document": "technical/demo.md",
                        "document_mentions": [],
                        "bytes": script.stat().st_size,
                        "sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = AuditReport(root=str(doc_root))
    check_script_catalog(tmp_path, doc_root, report)
    assert any("not directly documented" in error for error in report.errors)


def test_script_catalog_rejects_stale_digest(tmp_path: Path) -> None:
    script = tmp_path / "00_engine/scripts/demo.py"
    script.parent.mkdir(parents=True)
    script.write_text("pass\n", encoding="utf-8")
    (tmp_path / "20_planning/implementation").mkdir(parents=True)

    doc_root = tmp_path / "docs"
    owner = doc_root / "technical/demo.md"
    owner.parent.mkdir(parents=True)
    owner.write_text("# Demo\n`demo.py`\n", encoding="utf-8")
    catalog_path = tmp_path / "00_engine/scripts/SCRIPT_CATALOG.json"
    catalog_path.write_text(
        json.dumps(
            {
                "script_roots": ["00_engine", "20_planning/implementation"],
                "scripts": [
                    {
                        "path": "00_engine/scripts/demo.py",
                        "scan_root": "00_engine",
                        "lifecycle": "production",
                        "owner_document": "technical/demo.md",
                        "document_mentions": ["technical/demo.md"],
                        "bytes": script.stat().st_size,
                        "sha256": "0" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = AuditReport(root=str(doc_root))
    check_script_catalog(tmp_path, doc_root, report)
    assert any("SHA-256 is stale" in error for error in report.errors)


def test_output_catalog_rejects_undocumented_category_owner(tmp_path: Path) -> None:
    outputs = tmp_path / "00_engine/outputs"
    (outputs / "demo/run_001").mkdir(parents=True)
    doc_root = tmp_path / "docs"
    owner = doc_root / "technical/demo.md"
    owner.parent.mkdir(parents=True)
    owner.write_text("# Demo\n", encoding="utf-8")

    policy = {
        "retention_classes": {"unclassified": "protected"},
        "ownership_rules": [
            {
                "path_prefix": "demo",
                "owner_document": "technical/demo.md",
            }
        ],
        "rules": [],
    }
    inventory = {
        "entries": [
            {
                "path": "demo/run_001",
                "retention": "unclassified",
                "owner_document": "technical/demo.md",
            }
        ]
    }
    (outputs / "RETENTION_POLICY.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    (outputs / "OUTPUT_INVENTORY.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )

    report = AuditReport(root=str(doc_root))
    check_output_catalog(tmp_path, doc_root, report)
    assert any("not directly documented" in error for error in report.errors)
