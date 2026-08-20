from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from check_character_factory_docs import (  # noqa: E402
    AuditReport,
    audit_docs,
    check_ids,
    collect_definitions,
)


def metadata(role: str, stage: str, parent: str) -> str:
    return "\n".join(
        [
            f"> 文档角色：`{role}`",
            "> 状态：`current`",
            f"> 适用阶段：`{stage}`",
            "> 权威范围：test fixture",
            f"> 上级入口：{parent}",
            "> 上游：fixture input",
            "> 下游：fixture output",
            "> 最近核验：2026-08-06",
        ]
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def build_valid_tree(root: Path) -> None:
    master = "\n".join(
        [
            "# Master",
            metadata("current_authoritative_master", "WF-00..WF-09", "root"),
            "[Workflow](workflow/README.md)",
            "[Validation](validation/README.md)",
        ]
    )
    write(root / "CHARACTER_FACTORY_MASTER_SPEC.md", master)

    workflow_links = []
    for index in range(10):
        name = f"WF-{index:02d}-STAGE.md"
        workflow_links.append(f"[{name}]({name})")
        status = "planned" if index in {8, 9} else "current"
        previous = f"WF-{index - 1:02d}-STAGE.md" if index else "none"
        following = f"WF-{index + 1:02d}-STAGE.md" if index < 9 else "none"
        body = [
            f"# WF-{index:02d} Stage",
            metadata("workflow_runbook", f"WF-{index:02d}", "[README](README.md)"),
            f"> 状态：`{status}`",
            f"Previous: {previous}",
            f"Next: {following}",
        ]
        for section_index, heading in enumerate(
            (
                "目的与使用时机",
                "当前范围与非目标",
                "进入条件",
                "输入与输出",
                "执行环境",
                "执行步骤",
                "退出门禁",
                "失败与恢复",
                "技术依据与下一阶段",
            ),
            start=1,
        ):
            body.extend([f"## {section_index}. {heading}", "fixture"])
        write(root / "workflow" / name, "\n".join(body))

    workflow_readme = "\n".join(
        [
            "# Workflow",
            metadata("workflow_index", "WF-00..WF-09", "[Master](../CHARACTER_FACTORY_MASTER_SPEC.md)"),
            *workflow_links,
        ]
    )
    write(root / "workflow" / "README.md", workflow_readme)

    gate_rows = [
        f"| `GATE-{index:02d} TEST` | `VAL-TEST-01` |" for index in range(10)
    ]
    validation_readme = "\n".join(
        [
            "# Validation",
            metadata("validation_index", "WF-00..WF-09", "[Master](../CHARACTER_FACTORY_MASTER_SPEC.md)"),
            "[Catalog](VALIDATION_CATALOG.md)",
            "[Visual](VISUAL_ACCEPTANCE.md)",
            "[Recovery](RECOVERY_RUNBOOK.md)",
            *gate_rows,
        ]
    )
    write(root / "validation" / "README.md", validation_readme)
    write(
        root / "validation" / "VALIDATION_CATALOG.md",
        "\n".join(
            [
                "# Catalog",
                metadata("validation_catalog", "WF-00", "[README](README.md)"),
                "## VAL-TEST-01 Fixture validation",
            ]
        ),
    )
    write(
        root / "validation" / "VISUAL_ACCEPTANCE.md",
        "\n".join(
            [
                "# Visual",
                metadata("visual_acceptance_catalog", "WF-00", "[README](README.md)"),
                "## VIS-TEST-01 Fixture visual",
            ]
        ),
    )
    write(
        root / "validation" / "RECOVERY_RUNBOOK.md",
        "\n".join(
            [
                "# Recovery",
                metadata("recovery_runbook", "WF-00", "[README](README.md)"),
                "## REC-TEST-01 Fixture recovery",
            ]
        ),
    )


class DocumentationAuditTests(unittest.TestCase):
    def run_fixture(self, mutator=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_valid_tree(root)
            if mutator:
                mutator(root)
            return audit_docs(root)

    def test_valid_tree_passes(self):
        report = self.run_fixture()
        self.assertTrue(report.success, report.errors)

    def test_broken_link_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "CHARACTER_FACTORY_MASTER_SPEC.md"
            path.write_text(path.read_text(encoding="utf-8") + "[bad](missing.md)\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("broken link" in error for error in report.errors))

    def test_missing_anchor_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "CHARACTER_FACTORY_MASTER_SPEC.md"
            path.write_text(path.read_text(encoding="utf-8") + "[bad](workflow/README.md#missing)\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("missing anchor" in error for error in report.errors))

    def test_orphan_document_is_reported(self):
        def mutate(root: Path) -> None:
            write(
                root / "ORPHAN.md",
                "# Orphan\n" + metadata("technical_specification", "global", "none"),
            )

        report = self.run_fixture(mutate)
        self.assertTrue(any("unreachable from Master" in error for error in report.errors))

    def test_duplicate_identifier_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "validation" / "VALIDATION_CATALOG.md"
            path.write_text(path.read_text(encoding="utf-8") + "## VAL-TEST-01 Duplicate\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("defined 2 times" in error for error in report.errors))

    def test_completed_roadmap_identifier_can_be_defined_by_milestone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            milestone = root / "history" / "MILESTONE_LOG.md"
            texts = {
                milestone: "## 2026-08-10：RM-05B 人工验收通过\n",
            }

            definitions = collect_definitions(root, texts)

            self.assertEqual(definitions["RM-05B"], 1)

    def test_retired_identifier_in_history_does_not_require_active_definition(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history = root / "history" / "MILESTONE_LOG.md"
            report = AuditReport(root=str(root))

            check_ids(root, {history: "Retired package RM-77\n"}, report)

            self.assertFalse(
                any("RM-77" in error for error in report.errors), report.errors
            )

    def test_undefined_identifier_in_active_document_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            active = root / "CURRENT_STATUS.md"
            report = AuditReport(root=str(root))

            check_ids(root, {active: "Active package RM-77\n"}, report)

            self.assertTrue(
                any("RM-77" in error for error in report.errors), report.errors
            )

    def test_missing_workflow_stage_is_reported(self):
        def mutate(root: Path) -> None:
            (root / "workflow" / "WF-09-STAGE.md").unlink()

        report = self.run_fixture(mutate)
        self.assertTrue(any("missing workflow stage WF-09" in error for error in report.errors))

    def test_missing_metadata_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "validation" / "VISUAL_ACCEPTANCE.md"
            text = path.read_text(encoding="utf-8").replace("> 上游：fixture input\n", "")
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("missing metadata" in error for error in report.errors))

    def test_planned_workflow_cannot_contain_commands(self):
        def mutate(root: Path) -> None:
            path = root / "workflow" / "WF-08-STAGE.md"
            path.write_text(path.read_text(encoding="utf-8") + "```powershell\nWrite-Host bad\n```\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("planned workflow contains" in error for error in report.errors))

    def test_archive_hash_change_is_reported(self):
        def mutate(root: Path) -> None:
            archive = root / "history" / "legacy_fixture"
            write(archive / "OLD.md", "old")
            write(
                archive / "ARCHIVE_MANIFEST.md",
                "\n".join(
                    [
                        "# Manifest",
                        "| File | Bytes | SHA-256 |",
                        "| --- | ---: | --- |",
                        "| `OLD.md` | 4 | `" + ("0" * 64) + "` |",
                    ]
                ),
            )

        report = self.run_fixture(mutate)
        self.assertTrue(any("archive hash mismatch" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
