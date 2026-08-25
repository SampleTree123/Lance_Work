from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from check_character_factory_docs import audit_docs  # noqa: E402


WORKFLOW_IDS = tuple(f"WF-{value:02d}" for value in range(0, 100, 10))


def meta(document_id: str, document_type: str, lifecycle: str = "current") -> str:
    return "\n".join(
        [
            f"> 文档 ID：`{document_id}`",
            f"> 文档类型：`{document_type}`",
            f"> 生命周期：`{lifecycle}`",
            "> 最近核验：2026-08-25",
        ]
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def technical_meta(document_id: str) -> str:
    return "\n".join(
        [
            meta(document_id, "technical"),
            "> 实现所有权：fixture",
            "> 验证所有权：`VAL-WF00-FIXTURE`",
            "> 输出契约：`OUT-WF00-FIXTURE`",
        ]
    )


def build_valid_tree(root: Path) -> None:
    workflow_master_links = "\n".join(
        f"[{workflow_id}](workflow/{workflow_id}-FIXTURE.md) "
        f"[{workflow_id} status](project_management/status/workflows/{workflow_id}.md)"
        for workflow_id in WORKFLOW_IDS
    )
    write(
        root / "README.md",
        "\n".join(
            [
                "# Master",
                meta("MASTER", "master"),
                "## 1. 项目定义",
                "fixture",
                "## 2. 如何使用本文",
                "fixture",
                "## 3. 核心边界与术语",
                "fixture",
                "## 4. 文档体系",
                "[Governance](./GOVERNANCE.md)",
                "[Workflow](./workflow/README.md)",
                "[Technical](./technical/README.md)",
                "[Validation](./technical/validation/README.md)",
                "[Output](./technical/output/README.md)",
                "[Project management](./project_management/README.md)",
                "[Reference](./reference/README.md)",
                "[Registry](./registry/README.md)",
                "## 5. 端到端生产流程",
                workflow_master_links,
                "## 6. 状态、计划、决定与历史",
                "fixture",
                "## 7. 从哪里开始",
                "fixture",
                "## 8. 维护原则",
                "fixture",
            ]
        ),
    )
    closure_rows = "\n".join(
        f"| {name} | fixture |"
        for name in (
            "Workflow",
            "Validation",
            "Output",
            "Technical",
            "Status",
            "Plan",
            "History",
            "Decisions",
            "Reference",
            "Registry",
            "Governance",
            "Templates",
            "Master",
        )
    )
    write(
        root / "GOVERNANCE.md",
        "\n".join(
            [
                "# Governance",
                meta("GOV", "governance"),
                "## 2. 冲突裁决",
                "fixture",
                "## 3. 信息所有权",
                "fixture",
                "## 4. 文档类型与元数据",
                "fixture",
                "## 11. 子系统独立闭环",
                "| 子系统 | 契约 |",
                "| --- | --- |",
                closure_rows,
                "`unclassified`",
                "## 12. 变更同步矩阵",
                "fixture",
                "## 13. 审计顺序",
                "fixture",
            ]
        ),
    )

    workflow_links: list[str] = []
    for index, workflow_id in enumerate(WORKFLOW_IDS):
        path = root / "workflow" / f"{workflow_id}-FIXTURE.md"
        workflow_links.append(f"[{workflow_id}]({path.name})")
        previous = "none" if index == 0 else WORKFLOW_IDS[index - 1]
        following = "none" if index == len(WORKFLOW_IDS) - 1 else WORKFLOW_IDS[index + 1]
        sections = [
            "目的与使用时机",
            "前后序与进入条件",
            "输入",
            "正常流程",
            "输出契约",
            "必需验证",
            "Exit Gate",
            "技术与状态",
            "失败与恢复",
        ]
        body = [
            f"# {workflow_id}",
            meta(workflow_id, "workflow"),
            f"> 前序：`{previous}`",
            f"> 后序：`{following}`",
            f"> Exit Gate：`GATE-{workflow_id[-2:]} TEST`",
        ]
        for number, section in enumerate(sections, 1):
            body.append(f"## {number}. {section}")
            if section == "正常流程":
                body.extend(
                    [
                        "| 步骤 | 操作 | 精确实现入口 | 本步输出 |",
                        "| --- | --- | --- | --- |",
                        "| 1. fixture | fixture | "
                        "[fixture.py](../technical/demo/fixture.py) | fixture |",
                    ]
                )
            elif section == "输出契约":
                output_id = f"OUT-{workflow_id.replace('-', '')}-FIXTURE"
                body.extend(
                    [
                        f"`{output_id}`",
                        "### 输出组成、用途与下游",
                        "| 组成 | 实际内容 | 为什么需要 | 下游消费者 |",
                        "| --- | --- | --- | --- |",
                        "| fixture | fixture | fixture | "
                        f"[Status](../project_management/status/workflows/{workflow_id}.md#当前输出与证据) |",
                    ]
                )
            elif section == "必需验证":
                body.append(f"`VAL-{workflow_id.replace('-', '')}-FIXTURE`")
            else:
                body.append("fixture")
        write(path, "\n".join(body))
    write(
        root / "workflow" / "README.md",
        "# Workflow\n" + meta("WF-INDEX", "workflow_index") + "\n" + "\n".join(workflow_links),
    )

    validation_rows = "\n".join(
        f"| `VAL-{workflow_id.replace('-', '')}-FIXTURE` | `{workflow_id}` | required | "
        "[Implementation](../demo/IMPLEMENTATION.md) | "
        f"`OUT-{workflow_id.replace('-', '')}-FIXTURE` | "
        f"[Status](../../project_management/status/workflows/{workflow_id}.md) |"
        for workflow_id in WORKFLOW_IDS
    )
    validation_index = "\n".join(
        "[" + name + "](" + name + ")"
        for name in (
            "VALIDATION_CATALOG.md",
            "DOCUMENTATION_VALIDATION.md",
            "RECOVERY.md",
            "VISUAL_REVIEW.md",
        )
    )
    write(
        root / "technical/validation/README.md",
        "# Validation\n" + meta("TECH-VALIDATION-INDEX", "technical_index") + "\n" + validation_index,
    )
    write(
        root / "technical/validation/VALIDATION_CATALOG.md",
        "\n".join(
            [
                "# Validation catalog",
                technical_meta("TECH-VALIDATION-CATALOG"),
                "| ID | Workflow | Role | Owner | Evidence | Status |",
                "| --- | --- | --- | --- | --- | --- |",
                validation_rows,
                *[f"`{status}`" for status in (
                    "passed",
                    "passed_with_accepted_risk",
                    "pending",
                    "failed",
                    "not_applicable",
                    "expired",
                )],
            ]
        ),
    )
    for name, document_id in (
        ("DOCUMENTATION_VALIDATION.md", "TECH-DOC-VALIDATION"),
        ("RECOVERY.md", "TECH-RECOVERY"),
        ("VISUAL_REVIEW.md", "TECH-VISUAL"),
    ):
        write(root / "technical/validation" / name, f"# {name}\n" + technical_meta(document_id))

    output_rows = "\n".join(
        f"| `OUT-{workflow_id.replace('-', '')}-FIXTURE` | `{workflow_id}` | fixture | "
        "[Implementation](../demo/IMPLEMENTATION.md) | "
        f"[Status](../../project_management/status/workflows/{workflow_id}.md) |"
        for workflow_id in WORKFLOW_IDS
    )
    output_definitions = "\n".join(
        "\n".join(
            [
                f"## OUT-{workflow_id.replace('-', '')}-FIXTURE",
                "| 部分 | 最小内容 | 作用 | 当前位置所有者 |",
                "| --- | --- | --- | --- |",
                "| fixture | fixture | fixture | "
                f"[Status](../../project_management/status/workflows/{workflow_id}.md#当前输出与证据) |",
                "主要下游：fixture。",
            ]
        )
        for workflow_id in WORKFLOW_IDS
    )
    write(
        root / "technical/output/README.md",
        "# Output\n"
        + meta("TECH-OUTPUT-INDEX", "technical_index")
        + "\n[Contracts](OUTPUT_CONTRACTS.md)\n[Inventory](INVENTORY_AND_RETENTION.md)",
    )
    write(
        root / "technical/output/OUTPUT_CONTRACTS.md",
        "\n".join(
            [
                "# Output contracts",
                technical_meta("TECH-OUTPUT-CONTRACTS"),
                "| ID | Workflow | Storage | Producer | Status |",
                "| --- | --- | --- | --- | --- |",
                output_rows,
                output_definitions,
                "## Run Root 契约",
                "## 晋升、失效与不可变性",
                "`authoritative` `retained_evidence` `superseded` `disposable` `unclassified`",
            ]
        ),
    )
    write(
        root / "technical/output/INVENTORY_AND_RETENTION.md",
        "# Inventory\n" + technical_meta("TECH-OUTPUT-INVENTORY"),
    )
    write(
        root / "technical/demo/README.md",
        "# Demo\n" + meta("TECH-DEMO-INDEX", "technical_index") + "\n[Implementation](IMPLEMENTATION.md)",
    )
    write(
        root / "technical/demo/IMPLEMENTATION.md",
        "# Implementation\n" + technical_meta("TECH-DEMO"),
    )
    write(root / "technical/demo/fixture.py", "# fixture")
    write(
        root / "technical/README.md",
        "# Technical\n"
        + meta("TECH-INDEX", "technical_index")
        + "\n[Validation](validation/README.md)\n[Output](output/README.md)\n[Demo](demo/README.md)",
    )

    write(
        root / "project_management" / "README.md",
        "# Management\n"
        + meta("PM-INDEX", "project_management_index")
        + "\n[Status](status/README.md)\n[Plans](plans/README.md)"
        + "\n[Decisions](decisions/README.md)\n[History](history/README.md)"
        + "\n[Templates](templates/README.md)",
    )
    write(
        root / "project_management/status/README.md",
        "# Status\n"
        + meta("STATUS-INDEX", "status_index")
        + "\n[Project](PROJECT_STATUS.md)\n[Workflows](workflows/README.md)\n[Batches](batches/README.md)",
    )
    write(
        root / "project_management/status/PROJECT_STATUS.md",
        "# Project status\n" + meta("PROJECT-STATUS", "status"),
    )
    status_links: list[str] = []
    for workflow_id in WORKFLOW_IDS:
        requirement = "\n`PLAN-CURRENT/R01`" if workflow_id == "WF-80" else ""
        write(
            root / f"project_management/status/workflows/{workflow_id}.md",
            "\n".join(
                [
                    f"# {workflow_id} status",
                    meta(f"STATUS-{workflow_id}", "workflow_status"),
                    "## 当前能力",
                    "fixture",
                    "## 计划落实",
                    f"fixture{requirement}",
                    "## 验证状态",
                    f"`VAL-{workflow_id.replace('-', '')}-FIXTURE`",
                    "## 当前输出与证据",
                    "| 输出 | 当前位置 | 当前作用 | 状态 |",
                    "| --- | --- | --- | --- |",
                    f"| `OUT-{workflow_id.replace('-', '')}-FIXTURE` | fixture | fixture | authoritative |",
                    "## 缺口与风险",
                    "fixture",
                    "## 下一 Gate",
                    "fixture",
                ]
            ),
        )
        status_links.append(f"[{workflow_id}]({workflow_id}.md)")
    write(
        root / "project_management/status/workflows/README.md",
        "# Workflow status\n"
        + meta("STATUS-WF-INDEX", "status_index")
        + "\n"
        + "\n".join(status_links),
    )
    write(
        root / "project_management/status/batches/README.md",
        "# Batches\n" + meta("STATUS-BATCH-INDEX", "status_index"),
    )
    state = {
        "current_plan_id": "PLAN-CURRENT",
        "active_workflow_id": "WF-80",
        "workflow_status": {workflow_id: "fixture" for workflow_id in WORKFLOW_IDS},
        "validation_status": {
            f"VAL-{workflow_id.replace('-', '')}-FIXTURE": [
                {"scope": "fixture", "status": "passed"}
            ]
            for workflow_id in WORKFLOW_IDS
        },
        "current_outputs": {
            f"OUT-{workflow_id.replace('-', '')}-FIXTURE": "fixture"
            for workflow_id in WORKFLOW_IDS
        },
    }
    (root / "project_management/status/PROJECT_STATE.json").write_text(
        json.dumps(state), encoding="utf-8"
    )
    write(
        root / "project_management/plans/README.md",
        "# Plans\n"
        + meta("PLAN-INDEX", "plan_index")
        + "\n[Index](PLAN_INDEX.md)\n[Current](active/README.md)"
        + "\n[Queued](queued/README.md)\n[Paused](paused/README.md)",
    )
    write(
        root / "project_management/plans/PLAN_INDEX.md",
        "# Plan index\n" + meta("PLAN-LIFECYCLE-INDEX", "plan_index") + "\n[Current](active/README.md)\n## Paused",
    )
    write(
        root / "project_management/plans/active/README.md",
        "# Active\n"
        + meta("PLAN-ACTIVE-INDEX", "plan_index")
        + "\n[Plan](PLAN-CURRENT.md)",
    )
    write(
        root / "project_management/plans/active/PLAN-CURRENT.md",
        "# Current plan\n"
        + meta("PLAN-CURRENT", "plan")
        + "\n> 计划状态：`current`\n| ID | Requirement | Workflow | Status | Evidence |"
        + "\n| --- | --- | --- | --- | --- |\n| `R01` | fixture | `WF-80` | `in_progress` | fixture |",
    )
    write(root / "project_management/plans/queued/README.md", "# Queued\n" + meta("PLAN-QUEUED", "plan_index"))
    write(root / "project_management/plans/paused/README.md", "# Paused\n" + meta("PLAN-PAUSED", "plan_index"))

    write(
        root / "project_management/history/README.md",
        "# History\n" + meta("HISTORY-INDEX", "history_index") + "\n[Milestones](MILESTONE_LOG.md)\n[Completed](completed_plans/README.md)",
    )
    write(root / "project_management/history/MILESTONE_LOG.md", "# Milestones\n" + meta("HISTORY-MILESTONES", "history"))
    write(root / "project_management/history/completed_plans/README.md", "# Completed\n" + meta("HISTORY-COMPLETED", "history_index"))
    write(root / "project_management/decisions/README.md", "# Decisions\n" + meta("ADR-INDEX", "decision_index"))

    template_names = (
        "WORKFLOW_TEMPLATE.md",
        "TECHNICAL_TEMPLATE.md",
        "STATUS_TEMPLATE.md",
        "PLAN_TEMPLATE.md",
        "VALIDATION_TEMPLATE.md",
        "OUTPUT_TEMPLATE.md",
        "ADR_TEMPLATE.md",
        "HISTORY_TEMPLATE.md",
        "REFERENCE_TEMPLATE.md",
        "REGISTRY_TEMPLATE.md",
    )
    template_links = "\n".join(f"[{name}]({name})" for name in template_names)
    write(root / "project_management/templates/README.md", "# Templates\n" + meta("TEMPLATE-INDEX", "template_index") + "\n" + template_links)
    for index, name in enumerate(template_names):
        sections = ""
        if name == "WORKFLOW_TEMPLATE.md":
            template_sections = []
            for number, section in enumerate((
                "目的与使用时机",
                "前后序与进入条件",
                "输入",
                "正常流程",
                "输出契约",
                "必需验证",
                "Exit Gate",
                "技术与状态",
                "失败与恢复",
            ), 1):
                template_sections.append(f"## {number}. {section}")
                if section == "正常流程":
                    template_sections.append("| 步骤 | 操作 | 精确实现入口 | 本步输出 |")
                if section == "输出契约":
                    template_sections.append("### 输出组成、用途与下游")
            sections = "\n" + "\n".join(template_sections)
        write(root / "project_management/templates" / name, f"# {name}\n" + meta(f"TEMPLATE-{index:02d}", "template") + sections)

    write(
        root / "reference/README.md",
        "# Reference\n" + meta("REFERENCE-INDEX", "reference_index") + "\n[Glossary](GLOSSARY.md)\n[Paths](PATH_ALIASES.md)",
    )
    write(root / "reference/GLOSSARY.md", "# Glossary\n" + meta("REFERENCE-GLOSSARY", "reference"))
    write(root / "reference/PATH_ALIASES.md", "# Paths\n" + meta("REFERENCE-PATHS", "reference"))
    write(
        root / "registry/README.md",
        "\n".join(
            [
                "# Registry",
                meta("REGISTRY-INDEX", "registry_index"),
                "| 对象 | 当前机器权威 | 当前范围 | Technical 所有者 | 主要 Workflow |",
                "| --- | --- | --- | --- | --- |",
                "| fixture | fixture | fixture | fixture | fixture |",
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
        self.assertTrue(all(item["success"] for item in report.subsystems.values()))
        self.assertTrue(report.cross_layer["success"])

    def test_undefined_workflow_validation_is_cross_layer_failure(self):
        def mutate(root: Path) -> None:
            path = root / "workflow/WF-80-FIXTURE.md"
            text = path.read_text(encoding="utf-8").replace(
                "VAL-WF80-FIXTURE", "VAL-UNDEFINED-01"
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.cross_layer["success"])
        self.assertTrue(
            any("undefined validation" in error for error in report.cross_layer["errors"])
        )

    def test_status_must_reference_workflow_output(self):
        def mutate(root: Path) -> None:
            path = root / "project_management/status/workflows/WF-80.md"
            text = path.read_text(encoding="utf-8").replace(
                "OUT-WF80-FIXTURE", "OUT-OMITTED"
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(
            any("status omits output" in error for error in report.cross_layer["errors"])
        )

    def test_workflow_requires_exact_step_implementation_navigation(self):
        def mutate(root: Path) -> None:
            path = root / "workflow/WF-80-FIXTURE.md"
            text = path.read_text(encoding="utf-8").replace(
                "精确实现入口", "抽象说明"
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.subsystems["Workflow"]["success"])
        self.assertTrue(
            any(
                "step-to-implementation" in error
                for error in report.subsystems["Workflow"]["errors"]
            )
        )

    def test_workflow_requires_output_purpose_and_downstream_contract(self):
        def mutate(root: Path) -> None:
            path = root / "workflow/WF-80-FIXTURE.md"
            text = path.read_text(encoding="utf-8").replace(
                "为什么需要", "缺失用途字段"
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.subsystems["Workflow"]["success"])
        self.assertTrue(
            any(
                "output contract lacks: 为什么需要" in error
                for error in report.subsystems["Workflow"]["errors"]
            )
        )

    def test_output_catalog_requires_independent_downstream_definition(self):
        def mutate(root: Path) -> None:
            path = root / "technical/output/OUTPUT_CONTRACTS.md"
            text = path.read_text(encoding="utf-8").replace(
                "主要下游：fixture。", "消费者：fixture。", 1
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.subsystems["Output"]["success"])
        self.assertTrue(
            any(
                "independent definition lacks: 主要下游" in error
                for error in report.subsystems["Output"]["errors"]
            )
        )

    def test_status_output_locations_require_current_role(self):
        def mutate(root: Path) -> None:
            path = root / "project_management/status/workflows/WF-80.md"
            text = path.read_text(encoding="utf-8").replace(
                "当前作用", "未定义字段"
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.subsystems["Status"]["success"])
        self.assertTrue(
            any(
                "current outputs do not explain" in error
                for error in report.subsystems["Status"]["errors"]
            )
        )

    def test_plan_index_cannot_treat_blocked_as_lifecycle(self):
        def mutate(root: Path) -> None:
            path = root / "project_management/plans/PLAN_INDEX.md"
            text = path.read_text(encoding="utf-8").replace(
                "## Paused", "## Paused / Blocked"
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.subsystems["Plan"]["success"])
        self.assertTrue(
            any("blocked as a plan lifecycle" in error for error in report.subsystems["Plan"]["errors"])
        )

    def test_technical_document_requires_validation_and_output_metadata(self):
        def mutate(root: Path) -> None:
            path = root / "technical/demo/IMPLEMENTATION.md"
            text = path.read_text(encoding="utf-8").replace(
                "> 输出契约：`OUT-WF00-FIXTURE`\n", ""
            )
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertFalse(report.subsystems["Technical"]["success"])
        self.assertTrue(
            any("输出契约" in error for error in report.subsystems["Technical"]["errors"])
        )

    def test_broken_link_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "README.md"
            path.write_text(path.read_text(encoding="utf-8") + "[Bad](missing.md)\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("broken link" in error for error in report.errors))

    def test_missing_anchor_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "README.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "[Bad](workflow/README.md#missing)\n",
                encoding="utf-8",
            )

        report = self.run_fixture(mutate)
        self.assertTrue(any("missing anchor" in error for error in report.errors))

    def test_orphan_is_reported(self):
        def mutate(root: Path) -> None:
            write(root / "ORPHAN.md", "# Orphan\n" + meta("ORPHAN", "technical"))

        report = self.run_fixture(mutate)
        self.assertTrue(any("unreachable from Master" in error for error in report.errors))

    def test_duplicate_document_id_is_reported(self):
        def mutate(root: Path) -> None:
            write(root / "DUPLICATE.md", "# Duplicate\n" + meta("GOV", "technical"))
            master = root / "README.md"
            master.write_text(master.read_text(encoding="utf-8") + "[Duplicate](DUPLICATE.md)\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("document ID is not unique" in error for error in report.errors))

    def test_missing_workflow_is_reported(self):
        def mutate(root: Path) -> None:
            (root / "workflow/WF-90-FIXTURE.md").unlink()

        report = self.run_fixture(mutate)
        self.assertTrue(any("missing or duplicate workflow: WF-90" in error for error in report.errors))

    def test_wrong_workflow_neighbor_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "workflow/WF-20-FIXTURE.md"
            text = path.read_text(encoding="utf-8").replace("> 前序：`WF-10`", "> 前序：`WF-00`")
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("incorrect previous stage" in error for error in report.errors))

    def test_missing_metadata_is_reported(self):
        def mutate(root: Path) -> None:
            path = root / "GOVERNANCE.md"
            text = path.read_text(encoding="utf-8").replace("> 最近核验：2026-08-25\n", "")
            path.write_text(text, encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("missing metadata" in error for error in report.errors))

    def test_multiple_current_plans_are_reported(self):
        def mutate(root: Path) -> None:
            path = root / "project_management/plans/active/PLAN-SECOND.md"
            write(path, "# Second\n" + meta("PLAN-SECOND", "plan"))
            readme = root / "project_management/plans/active/README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "[Second](PLAN-SECOND.md)\n", encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("exactly one current plan" in error for error in report.errors))

    def test_state_plan_mismatch_is_reported(self):
        def mutate(root: Path) -> None:
            state_path = root / "project_management/status/PROJECT_STATE.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["current_plan_id"] = "PLAN-OTHER"
            state_path.write_text(json.dumps(state), encoding="utf-8")

        report = self.run_fixture(mutate)
        self.assertTrue(any("current_plan_id" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
