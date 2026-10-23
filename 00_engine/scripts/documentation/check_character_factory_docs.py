"""Read-only audit for the Character Factory documentation operating model."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import unquote


MASTER_NAME = "README.md"
COMMON_METADATA = ("文档 ID", "文档类型", "生命周期", "最近核验")
ALLOWED_LIFECYCLES = {
    "current",
    "queued",
    "paused",
    "completed",
    "superseded",
    "compatibility",
    "archived",
}
WORKFLOW_IDS = tuple(f"WF-{value:02d}" for value in range(0, 100, 10))
WORKFLOW_REQUIRED_SECTIONS = (
    "目的与使用时机",
    "前后序与进入条件",
    "输入",
    "正常流程",
    "输出契约",
    "必需验证",
    "Exit Gate",
    "技术与状态",
    "失败与恢复",
)
STATUS_REQUIRED_SECTIONS = (
    "当前能力",
    "计划落实",
    "验证状态",
    "当前输出与证据",
    "缺口与风险",
    "下一 Gate",
)
VALIDATION_STATUSES = {
    "passed",
    "passed_with_accepted_risk",
    "pending",
    "failed",
    "not_applicable",
    "expired",
}
PLAN_LIFECYCLES = {"current", "queued", "paused", "completed", "cancelled"}
PLAN_REQUIREMENT_STATUSES = {
    "pending",
    "in_progress",
    "blocked",
    "deferred",
    "completed",
}
VALIDATION_ID_PATTERN = re.compile(r"\bVAL-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
OUTPUT_ID_PATTERN = re.compile(r"\bOUT-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
REQUIREMENT_ID_PATTERN = re.compile(r"\bR\d{2,}\b")
SCRIPT_SUFFIXES = {".py", ".ps1", ".sh", ".cmd"}
SCRIPT_SCAN_ROOTS = ("00_engine", "20_planning/implementation")
EXCLUDED_SCRIPT_PARTS = {
    ".venv",
    "__pycache__",
    "binaries",
    "intermediate",
    "node_modules",
    "outputs",
    "saved",
}
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
METADATA_PATTERN = re.compile(r"^>\s*([^：\n]+)：\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class AuditReport:
    root: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    subsystems: dict[str, dict[str, object]] = field(default_factory=dict)
    cross_layer: dict[str, object] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["success"] = self.success
        return result


def record_subsystem_result(
    report: AuditReport, name: str, error_start: int, warning_start: int
) -> None:
    errors = report.errors[error_start:]
    warnings = report.warnings[warning_start:]
    report.subsystems[name] = {
        "success": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def record_cross_layer_result(
    report: AuditReport, error_start: int, warning_start: int
) -> None:
    errors = report.errors[error_start:]
    warnings = report.warnings[warning_start:]
    report.cross_layer = {
        "success": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def normalize_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def read_utf8(path: Path, report: AuditReport) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.errors.append(f"cannot read UTF-8 file {path}: {exc}")
        return ""


def metadata(text: str) -> dict[str, str]:
    return {key.strip(): value.strip() for key, value in METADATA_PATTERN.findall(text)}


def clean_metadata_value(value: str) -> str:
    return value.strip().strip("`").strip()


def ids_in(text: str, pattern: re.Pattern[str]) -> set[str]:
    return set(pattern.findall(text))


def first_column_ids(text: str, prefix: str) -> list[str]:
    pattern = re.compile(
        rf"^\|\s*`?({re.escape(prefix)}[A-Z0-9-]*)`?\s*\|", re.MULTILINE
    )
    return pattern.findall(text)


def markdown_table_rows(text: str, first_column_prefix: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if cells and cells[0].startswith(first_column_prefix):
            rows.append(cells)
    return rows


def subsystem_error(report: AuditReport, subsystem: str, message: str) -> None:
    report.errors.append(f"[{subsystem}] {message}")


def has_heading(text: str, required: str) -> bool:
    return any(
        required.lower() in heading.lower()
        for _, heading in HEADING_PATTERN.findall(text)
    )


def section_body(text: str, required: str) -> str:
    """Return the first matching Markdown section body, including child sections."""
    headings = list(HEADING_PATTERN.finditer(text))
    for index, match in enumerate(headings):
        if required.lower() not in match.group(2).lower():
            continue
        level = len(match.group(1))
        end = len(text)
        for following in headings[index + 1 :]:
            if len(following.group(1)) <= level:
                end = following.start()
                break
        return text[match.end() : end]
    return ""


def parse_markdown_target(raw_target: str) -> tuple[str, str]:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif ' "' in target:
        target = target.split(' "', 1)[0]
    target = unquote(target)
    if "#" in target:
        path_part, fragment = target.split("#", 1)
    else:
        path_part, fragment = target, ""
    return path_part, fragment.lower()


def is_external_target(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(
        ("http://", "https://", "mailto:", "app://", "file://")
    )


def slugify_heading(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value).strip().lower()
    chars: list[str] = []
    for char in value:
        category = unicodedata.category(char)
        if char in {" ", "-", "_"} or category[0] in {"L", "N"}:
            chars.append(char)
    return re.sub(r"-+", "-", "".join(chars).replace(" ", "-")).strip("-")


def heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    counts: Counter[str] = Counter()
    for _, heading in HEADING_PATTERN.findall(text):
        base = slugify_heading(heading)
        if not base:
            continue
        suffix = counts[base]
        counts[base] += 1
        anchors.add(base if suffix == 0 else f"{base}-{suffix}")
    return anchors


def collect_docs(root: Path) -> list[Path]:
    return sorted(path.resolve() for path in root.rglob("*.md") if path.is_file())


def infer_repo_root(doc_root: Path) -> Path | None:
    for candidate in (doc_root, *doc_root.parents):
        if (candidate / "00_engine/scripts").is_dir() and (
            candidate / "20_planning"
        ).is_dir():
            return candidate
    return None


def check_metadata(
    docs: list[Path], root: Path, texts: dict[Path, str], report: AuditReport
) -> dict[Path, dict[str, str]]:
    parsed: dict[Path, dict[str, str]] = {}
    document_ids: Counter[str] = Counter()
    for path in docs:
        values = metadata(texts[path])
        parsed[path] = values
        missing = [field for field in COMMON_METADATA if field not in values]
        if missing:
            report.errors.append(
                f"missing metadata in {normalize_relative(path, root)}: "
                + ", ".join(missing)
            )
            continue
        document_id = clean_metadata_value(values["文档 ID"])
        lifecycle = clean_metadata_value(values["生命周期"])
        document_ids[document_id] += 1
        if lifecycle not in ALLOWED_LIFECYCLES:
            report.errors.append(
                f"invalid lifecycle in {normalize_relative(path, root)}: {lifecycle}"
            )
    for document_id, count in sorted(document_ids.items()):
        if count > 1:
            report.errors.append(
                f"document ID is not unique ({count} uses): {document_id}"
            )
    report.stats["document_ids"] = len(document_ids)
    return parsed


def check_links(
    docs: list[Path], root: Path, texts: dict[Path, str], report: AuditReport
) -> tuple[dict[Path, set[Path]], int]:
    graph: dict[Path, set[Path]] = {path: set() for path in docs}
    docs_set = set(docs)
    anchors: dict[Path, set[str]] = {}
    checked = 0
    for source in docs:
        for match in LINK_PATTERN.finditer(texts[source]):
            raw = match.group(1)
            if is_external_target(raw):
                continue
            path_part, fragment = parse_markdown_target(raw)
            checked += 1
            if re.match(r"^[A-Za-z]:[/\\]", path_part):
                target = Path(path_part).resolve()
            else:
                target = source if not path_part else (source.parent / path_part).resolve()
            if not target.exists():
                report.errors.append(
                    f"broken link in {normalize_relative(source, root)}: {raw}"
                )
                continue
            if target.is_dir():
                target = (target / "README.md").resolve()
                if not target.exists():
                    report.errors.append(
                        f"directory link has no README in "
                        f"{normalize_relative(source, root)}: {raw}"
                    )
                    continue
            if target.suffix.lower() == ".md" and fragment:
                anchors.setdefault(target, heading_anchors(read_utf8(target, report)))
                if fragment not in anchors[target]:
                    report.errors.append(
                        f"missing anchor in {normalize_relative(source, root)}: {raw}"
                    )
            if target in docs_set:
                graph[source].add(target)
    return graph, checked


def check_reachability(
    root: Path, docs: list[Path], graph: dict[Path, set[Path]], report: AuditReport
) -> None:
    master = (root / MASTER_NAME).resolve()
    if master not in graph:
        report.errors.append(f"missing Master document: {MASTER_NAME}")
        return
    reached = {master}
    queue: deque[Path] = deque([master])
    while queue:
        source = queue.popleft()
        for target in graph[source]:
            if target not in reached:
                reached.add(target)
                queue.append(target)
    for path in docs:
        if path not in reached:
            report.errors.append(
                f"document is unreachable from Master: {normalize_relative(path, root)}"
            )
    report.stats["reachable_documents"] = len(reached)


def check_directory_indexes(
    root: Path, docs: list[Path], graph: dict[Path, set[Path]], report: AuditReport
) -> None:
    docs_set = set(docs)
    for directory in sorted({path.parent for path in docs if path.parent != root}):
        direct_docs = [
            path
            for path in docs
            if path.parent == directory and path.name != "README.md"
        ]
        if not direct_docs:
            continue
        readme = (directory / "README.md").resolve()
        if readme not in docs_set:
            report.errors.append(
                f"directory has documents but no README: {normalize_relative(directory, root)}"
            )
            continue
        for child in direct_docs:
            if child not in graph.get(readme, set()):
                report.errors.append(
                    f"directory README does not index {normalize_relative(child, root)}"
                )


def find_workflow_file(root: Path, workflow_id: str) -> Path | None:
    matches = sorted((root / "workflow").glob(f"{workflow_id}-*.md"))
    return matches[0].resolve() if len(matches) == 1 else None


def check_workflows(
    root: Path,
    texts: dict[Path, str],
    parsed: dict[Path, dict[str, str]],
    report: AuditReport,
) -> None:
    workflow_files: dict[str, Path] = {}
    for workflow_id in WORKFLOW_IDS:
        path = find_workflow_file(root, workflow_id)
        if path is None:
            report.errors.append(f"missing or duplicate workflow: {workflow_id}")
            continue
        workflow_files[workflow_id] = path
        values = parsed.get(path, {})
        actual_id = clean_metadata_value(values.get("文档 ID", ""))
        if actual_id != workflow_id:
            report.errors.append(f"workflow document ID mismatch: {path.name}")
        headings = [heading for _, heading in HEADING_PATTERN.findall(texts[path])]
        for required in WORKFLOW_REQUIRED_SECTIONS:
            if not any(required.lower() in heading.lower() for heading in headings):
                report.errors.append(f"workflow {path.name} missing section: {required}")
        normal_flow = section_body(texts[path], "正常流程")
        if "| 步骤 |" not in normal_flow or "精确实现" not in normal_flow:
            subsystem_error(
                report,
                "Workflow",
                f"{path.name} normal flow lacks the step-to-implementation table",
            )
        step_rows = re.findall(r"^\|\s*\d+\..*$", normal_flow, re.MULTILINE)
        if not step_rows:
            subsystem_error(
                report, "Workflow", f"{path.name} defines no executable flow steps"
            )
        for row in step_rows:
            if "](" not in row:
                subsystem_error(
                    report,
                    "Workflow",
                    f"{path.name} flow step has no exact implementation navigation: {row}",
                )
        if not re.search(r"\.(?:py|ps1|sh|json)\b", normal_flow, re.IGNORECASE) and not re.search(
            r"尚无|尚未|没有|无单独|人工|手工", normal_flow
        ):
            subsystem_error(
                report,
                "Workflow",
                f"{path.name} does not name an implementation/config file or an explicit manual gap",
            )

        output_section = section_body(texts[path], "输出契约")
        for required_output_semantic in (
            "输出组成、用途与下游",
            "实际内容",
            "为什么需要",
        ):
            if required_output_semantic not in output_section:
                subsystem_error(
                    report,
                    "Workflow",
                    f"{path.name} output contract lacks: {required_output_semantic}",
                )
        if "下游消费者" not in output_section and "下游使用者" not in output_section:
            subsystem_error(
                report,
                "Workflow",
                f"{path.name} output contract lacks downstream consumers",
            )
        if "#当前输出与证据" not in output_section:
            subsystem_error(
                report,
                "Workflow",
                f"{path.name} output contract lacks the current Status owner link",
            )
        gate = clean_metadata_value(values.get("Exit Gate", ""))
        expected_gate = f"GATE-{workflow_id[-2:]}"
        if not gate.startswith(expected_gate):
            report.errors.append(
                f"workflow {path.name} has invalid Exit Gate: {gate or 'missing'}"
            )
    for index, workflow_id in enumerate(WORKFLOW_IDS):
        path = workflow_files.get(workflow_id)
        if not path:
            continue
        values = parsed[path]
        expected_previous = None if index == 0 else WORKFLOW_IDS[index - 1]
        expected_next = None if index == len(WORKFLOW_IDS) - 1 else WORKFLOW_IDS[index + 1]
        previous = clean_metadata_value(values.get("前序", ""))
        following = clean_metadata_value(values.get("后序", ""))
        if expected_previous is not None and previous != expected_previous:
            report.errors.append(f"workflow {path.name} has incorrect previous stage")
        if expected_previous is None and previous.lower() not in {"", "none", "无"}:
            report.errors.append(f"workflow {path.name} should not have a previous stage")
        if expected_next is not None and following != expected_next:
            report.errors.append(f"workflow {path.name} has incorrect next stage")
        if expected_next is None and following.lower() not in {"", "none", "无"}:
            report.errors.append(f"workflow {path.name} should not have a next stage")


def require_files(
    root: Path, relatives: tuple[str, ...], report: AuditReport, subsystem: str
) -> None:
    for relative in relatives:
        if not (root / relative).is_file():
            subsystem_error(report, subsystem, f"missing required file: {relative}")


def check_master_subsystem(root: Path, texts: dict[Path, str], report: AuditReport) -> None:
    path = (root / "README.md").resolve()
    text = texts.get(path, "")
    for section in (
        "项目定义",
        "如何使用本文",
        "核心边界与术语",
        "文档体系",
        "端到端生产流程",
        "状态、计划、决定与历史",
        "从哪里开始",
        "维护原则",
    ):
        if not has_heading(text, section):
            subsystem_error(report, "Master", f"missing section: {section}")
    required_targets = (
        "./workflow/README.md",
        "./technical/README.md",
        "./technical/validation/README.md",
        "./technical/output/README.md",
        "./project_management/README.md",
        "./reference/README.md",
        "./registry/README.md",
        "./GOVERNANCE.md",
    )
    for target in required_targets:
        if target not in text:
            subsystem_error(report, "Master", f"missing subsystem entry: {target}")
    for workflow_id in WORKFLOW_IDS:
        if text.count(workflow_id) < 2:
            subsystem_error(report, "Master", f"missing lifecycle navigation: {workflow_id}")


def check_governance_subsystem(
    root: Path, texts: dict[Path, str], report: AuditReport
) -> None:
    path = (root / "GOVERNANCE.md").resolve()
    text = texts.get(path, "")
    for section in (
        "冲突裁决",
        "信息所有权",
        "文档类型与元数据",
        "子系统独立闭环",
        "变更同步矩阵",
        "审计顺序",
    ):
        if not has_heading(text, section):
            subsystem_error(report, "Governance", f"missing section: {section}")
    for subsystem in (
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
    ):
        if f"| {subsystem} |" not in text:
            subsystem_error(
                report, "Governance", f"independent closure contract missing: {subsystem}"
            )
    if "`unclassified`" not in text:
        subsystem_error(report, "Governance", "unclassified output protection is missing")


def check_validation_subsystem(
    root: Path, texts: dict[Path, str], report: AuditReport
) -> set[str]:
    require_files(
        root,
        (
            "technical/validation/README.md",
            "technical/validation/VALIDATION_CATALOG.md",
            "technical/validation/DOCUMENTATION_VALIDATION.md",
            "technical/validation/RECOVERY.md",
            "technical/validation/VISUAL_REVIEW.md",
        ),
        report,
        "Validation",
    )
    catalog_path = (root / "technical/validation/VALIDATION_CATALOG.md").resolve()
    text = texts.get(catalog_path, "")
    validation_ids = first_column_ids(text, "VAL-")
    duplicates = sorted(
        validation_id
        for validation_id, count in Counter(validation_ids).items()
        if count > 1
    )
    if not validation_ids:
        subsystem_error(report, "Validation", "catalog defines no VAL-* IDs")
    if duplicates:
        subsystem_error(
            report, "Validation", f"duplicate catalog IDs: {', '.join(duplicates)}"
        )
    for row in markdown_table_rows(text, "VAL-"):
        if len(row) < 6:
            subsystem_error(
                report, "Validation", f"catalog row lacks required owners/evidence: {row[0]}"
            )
    for status in VALIDATION_STATUSES:
        if f"`{status}`" not in text:
            subsystem_error(report, "Validation", f"missing status semantics: {status}")
    return set(validation_ids)


def check_output_subsystem(
    root: Path, texts: dict[Path, str], report: AuditReport
) -> set[str]:
    require_files(
        root,
        (
            "technical/output/README.md",
            "technical/output/OUTPUT_CONTRACTS.md",
            "technical/output/INVENTORY_AND_RETENTION.md",
        ),
        report,
        "Output",
    )
    contracts_path = (root / "technical/output/OUTPUT_CONTRACTS.md").resolve()
    text = texts.get(contracts_path, "")
    output_ids = first_column_ids(text, "OUT-")
    duplicates = sorted(
        output_id for output_id, count in Counter(output_ids).items() if count > 1
    )
    if not output_ids:
        subsystem_error(report, "Output", "catalog defines no OUT-* IDs")
    if duplicates:
        subsystem_error(report, "Output", f"duplicate catalog IDs: {', '.join(duplicates)}")
    for row in markdown_table_rows(text, "OUT-"):
        if len(row) < 4:
            subsystem_error(
                report, "Output", f"catalog row lacks producer/status contract: {row[0]}"
            )
    for required in (
        "Run Root 契约",
        "晋升、失效与不可变性",
        "authoritative",
        "retained_evidence",
        "superseded",
        "disposable",
        "unclassified",
    ):
        if required not in text:
            subsystem_error(report, "Output", f"missing output semantics: {required}")
    for output_id in output_ids:
        contract = section_body(text, output_id)
        if not contract:
            subsystem_error(
                report, "Output", f"missing independent output definition: {output_id}"
            )
            continue
        for required in ("最小内容", "作用", "当前位置所有者", "主要下游"):
            if required not in contract:
                subsystem_error(
                    report,
                    "Output",
                    f"{output_id} independent definition lacks: {required}",
                )
    return set(output_ids)


def check_technical_subsystem(
    root: Path,
    texts: dict[Path, str],
    parsed: dict[Path, dict[str, str]],
    report: AuditReport,
) -> None:
    technical_root = root / "technical"
    if not technical_root.is_dir():
        subsystem_error(report, "Technical", "technical directory is missing")
        return
    for directory in sorted(path for path in technical_root.iterdir() if path.is_dir()):
        if not (directory / "README.md").is_file():
            subsystem_error(
                report, "Technical", f"area has no README: {directory.name}"
            )
    for path in sorted(technical_root.rglob("*.md")):
        path = path.resolve()
        if path.name == "README.md":
            continue
        values = parsed.get(path, {})
        for field_name in ("实现所有权", "验证所有权", "输出契约"):
            if field_name not in values:
                subsystem_error(
                    report,
                    "Technical",
                    f"{normalize_relative(path, root)} missing metadata: {field_name}",
                )


def check_status_subsystem(
    root: Path, texts: dict[Path, str], report: AuditReport
) -> dict[str, object] | None:
    require_files(
        root,
        (
            "project_management/status/README.md",
            "project_management/status/PROJECT_STATUS.md",
            "project_management/status/PROJECT_STATE.json",
            "project_management/status/workflows/README.md",
            "project_management/status/batches/README.md",
        ),
        report,
        "Status",
    )
    for workflow_id in WORKFLOW_IDS:
        status_path = (
            root / f"project_management/status/workflows/{workflow_id}.md"
        ).resolve()
        if not status_path.is_file():
            subsystem_error(report, "Status", f"missing workflow status: {workflow_id}")
            continue
        text = texts.get(status_path, "")
        for section in STATUS_REQUIRED_SECTIONS:
            if not has_heading(text, section):
                subsystem_error(
                    report, "Status", f"{workflow_id} missing section: {section}"
                )
        current_outputs = section_body(text, "当前输出与证据")
        if "当前作用" not in current_outputs:
            subsystem_error(
                report,
                "Status",
                f"{workflow_id} current outputs do not explain each location's role",
            )
    state_path = root / "project_management/status/PROJECT_STATE.json"
    if not state_path.is_file():
        return None
    state = load_json(state_path, report, "PROJECT_STATE.json")
    if state is None:
        return None
    for error in active_workflow_errors(state):
        subsystem_error(report, "Status", error)
    workflow_status = state.get("workflow_status", {})
    if not isinstance(workflow_status, dict) or set(workflow_status) != set(WORKFLOW_IDS):
        subsystem_error(report, "Status", "workflow_status keys do not match workflow set")
    validation_status = state.get("validation_status", {})
    if not isinstance(validation_status, dict):
        subsystem_error(report, "Status", "validation_status must be an object")
    else:
        for validation_id, scopes in validation_status.items():
            if not isinstance(scopes, list) or not scopes:
                subsystem_error(
                    report, "Status", f"{validation_id} has no scoped result"
                )
                continue
            for item in scopes:
                status = item.get("status") if isinstance(item, dict) else None
                if status not in VALIDATION_STATUSES:
                    subsystem_error(
                        report,
                        "Status",
                        f"{validation_id} has invalid result status: {status}",
                    )
    current_outputs = state.get("current_outputs")
    if not isinstance(current_outputs, dict):
        subsystem_error(report, "Status", "current_outputs must be an object")
    return state


def active_workflow_errors(state: dict[str, object]) -> list[str]:
    """An explicit completed-plan idle state can have no executing workflow."""
    active = state.get("active_workflow_id")
    if active in WORKFLOW_IDS:
        return []
    if (state.get("project_phase") == "idle_after_completed_plan"
            and "current_plan_id" in state and state["current_plan_id"] is None
            and "active_workflow_id" in state and active is None):
        return []
    return [f"invalid active_workflow_id: {active}"]


def plan_cardinality_errors(state: dict[str, object] | None, count: int) -> list[str]:
    """Only an explicitly recorded post-completion idle state has no current plan."""
    state = state or {}
    errors: list[str] = []
    if state.get("project_phase") == "idle_after_completed_plan":
        if "current_plan_id" not in state or state["current_plan_id"] is not None:
            errors.append("idle_after_completed_plan requires explicit current_plan_id=null")
        if count != 0:
            errors.append(f"idle_after_completed_plan expected zero current plans, found {count}")
    elif count != 1:
        errors.append(f"expected exactly one current plan, found {count}")
    return errors


def check_plan_subsystem(
    root: Path,
    docs: list[Path],
    texts: dict[Path, str],
    parsed: dict[Path, dict[str, str]],
    report: AuditReport,
    state: dict[str, object] | None = None,
) -> tuple[Path | None, dict[str, set[str]]]:
    require_files(
        root,
        (
            "project_management/plans/README.md",
            "project_management/plans/PLAN_INDEX.md",
            "project_management/plans/active/README.md",
            "project_management/plans/queued/README.md",
            "project_management/plans/paused/README.md",
        ),
        report,
        "Plan",
    )
    plan_docs = [
        path
        for path in docs
        if clean_metadata_value(parsed.get(path, {}).get("文档类型", "")) == "plan"
    ]
    current_plans = [
        path
        for path in plan_docs
        if clean_metadata_value(parsed[path].get("生命周期", "")) == "current"
    ]
    for error in plan_cardinality_errors(state, len(current_plans)):
        subsystem_error(report, "Plan", error)
    for path in plan_docs:
        lifecycle = clean_metadata_value(parsed[path].get("生命周期", ""))
        if lifecycle not in PLAN_LIFECYCLES:
            subsystem_error(
                report,
                "Plan",
                f"invalid plan lifecycle in {normalize_relative(path, root)}: {lifecycle}",
            )
        declared = clean_metadata_value(parsed[path].get("计划状态", ""))
        if not declared:
            subsystem_error(
                report,
                "Plan",
                f"{normalize_relative(path, root)} missing metadata: 计划状态",
            )
        elif declared != lifecycle:
            subsystem_error(
                report,
                "Plan",
                f"plan status/lifecycle mismatch in {normalize_relative(path, root)}",
            )
    requirement_workflows: dict[str, set[str]] = {}
    if current_plans:
        text = texts[current_plans[0]]
        rows = markdown_table_rows(text, "R")
        seen: Counter[str] = Counter()
        for row in rows:
            requirement_id = row[0]
            if not REQUIREMENT_ID_PATTERN.fullmatch(requirement_id):
                continue
            seen[requirement_id] += 1
            if len(row) < 5:
                subsystem_error(
                    report, "Plan", f"requirement row is incomplete: {requirement_id}"
                )
                continue
            status = row[3]
            if status not in PLAN_REQUIREMENT_STATUSES:
                subsystem_error(
                    report,
                    "Plan",
                    f"{requirement_id} has invalid requirement status: {status}",
                )
            requirement_workflows[requirement_id] = set(
                workflow_id for workflow_id in WORKFLOW_IDS if workflow_id in row[2]
            )
        for requirement_id, count in seen.items():
            if count > 1:
                subsystem_error(report, "Plan", f"duplicate requirement: {requirement_id}")
    index_path = (root / "project_management/plans/PLAN_INDEX.md").resolve()
    if "Paused / Blocked" in texts.get(index_path, ""):
        subsystem_error(
            report, "Plan", "PLAN_INDEX treats blocked as a plan lifecycle"
        )
    return (current_plans[0] if len(current_plans) == 1 else None, requirement_workflows)


def check_history_subsystem(
    root: Path, texts: dict[Path, str], parsed: dict[Path, dict[str, str]], report: AuditReport
) -> None:
    require_files(
        root,
        (
            "project_management/history/README.md",
            "project_management/history/MILESTONE_LOG.md",
            "project_management/history/completed_plans/README.md",
        ),
        report,
        "History",
    )
    completed_root = root / "project_management/history/completed_plans"
    if not completed_root.is_dir():
        return
    for path in completed_root.glob("PLAN-*.md"):
        resolved = path.resolve()
        values = parsed.get(resolved, {})
        if clean_metadata_value(values.get("生命周期", "")) != "completed":
            subsystem_error(report, "History", f"completed plan is not completed: {path.name}")
        text = texts.get(resolved, "")
        if not ("证据" in text and ("未纳入" in text or "后续" in text)):
            subsystem_error(
                report, "History", f"completed plan lacks evidence/scope closure: {path.name}"
            )


def check_decisions_subsystem(
    root: Path, texts: dict[Path, str], parsed: dict[Path, dict[str, str]], report: AuditReport
) -> None:
    decisions_root = root / "project_management/decisions"
    require_files(
        root,
        ("project_management/decisions/README.md",),
        report,
        "Decisions",
    )
    for path in sorted(decisions_root.glob("ADR-*.md")):
        resolved = path.resolve()
        values = parsed.get(resolved, {})
        lifecycle = clean_metadata_value(values.get("生命周期", ""))
        status = clean_metadata_value(values.get("状态", ""))
        text = texts.get(resolved, "")
        if lifecycle == "current" and status != "accepted":
            subsystem_error(report, "Decisions", f"current ADR is not accepted: {path.name}")
        if lifecycle == "superseded":
            successors = [value for value in re.findall(r"ADR-\d{4}", text) if value not in path.name]
            if not successors:
                subsystem_error(report, "Decisions", f"superseded ADR has no successor: {path.name}")
        if status == "accepted":
            for section in ("背景", "决定", "复审条件"):
                if not has_heading(text, section):
                    subsystem_error(
                        report, "Decisions", f"{path.name} missing section: {section}"
                    )
            if not (has_heading(text, "后果") or has_heading(text, "影响")):
                subsystem_error(
                    report, "Decisions", f"{path.name} missing section: 后果/影响"
                )


def check_reference_subsystem(root: Path, report: AuditReport) -> None:
    require_files(
        root,
        (
            "reference/README.md",
            "reference/GLOSSARY.md",
            "reference/PATH_ALIASES.md",
        ),
        report,
        "Reference",
    )
    registry_in_reference = root / "reference/REGISTRY_INDEX.md"
    if registry_in_reference.exists():
        subsystem_error(report, "Reference", "Registry is still stored inside Reference")


def check_registry_subsystem(
    root: Path, repo: Path | None, texts: dict[Path, str], report: AuditReport
) -> None:
    require_files(root, ("registry/README.md",), report, "Registry")
    path = (root / "registry/README.md").resolve()
    text = texts.get(path, "")
    for column in ("当前机器权威", "当前范围", "Technical 所有者", "主要 Workflow"):
        if column not in text:
            subsystem_error(report, "Registry", f"missing registry column: {column}")
    if repo is not None:
        for relative in sorted(set(re.findall(r"repo://([^`、|\s]+)", text))):
            if not (repo / Path(relative)).exists():
                subsystem_error(report, "Registry", f"repo authority does not exist: {relative}")


def check_templates_subsystem(
    root: Path, texts: dict[Path, str], report: AuditReport
) -> None:
    template_root = root / "project_management/templates"
    expected = {
        "README.md",
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
    }
    actual = {path.name for path in template_root.glob("*.md")} if template_root.is_dir() else set()
    if actual != expected:
        subsystem_error(
            report,
            "Templates",
            f"template set mismatch; missing={sorted(expected - actual)}, extra={sorted(actual - expected)}",
        )
    workflow_template = (template_root / "WORKFLOW_TEMPLATE.md").resolve()
    text = texts.get(workflow_template, "")
    for section in WORKFLOW_REQUIRED_SECTIONS:
        if not has_heading(text, section):
            subsystem_error(report, "Templates", f"Workflow template missing: {section}")


def check_cross_layer_contracts(
    root: Path,
    texts: dict[Path, str],
    parsed: dict[Path, dict[str, str]],
    validation_ids: set[str],
    output_ids: set[str],
    state: dict[str, object] | None,
    current_plan: Path | None,
    requirement_workflows: dict[str, set[str]],
    report: AuditReport,
) -> None:
    workflow_output_ids: set[str] = set()
    for workflow_id in WORKFLOW_IDS:
        workflow_path = find_workflow_file(root, workflow_id)
        if workflow_path is None:
            continue
        workflow_text = texts.get(workflow_path, "")
        required_validations = ids_in(workflow_text, VALIDATION_ID_PATTERN)
        produced_outputs = ids_in(workflow_text, OUTPUT_ID_PATTERN)
        workflow_output_ids.update(produced_outputs)
        for validation_id in sorted(required_validations - validation_ids):
            report.errors.append(
                f"[CrossLayer] {workflow_id} references undefined validation: {validation_id}"
            )
        for output_id in sorted(produced_outputs - output_ids):
            report.errors.append(
                f"[CrossLayer] {workflow_id} references undefined output: {output_id}"
            )
        status_path = (
            root / f"project_management/status/workflows/{workflow_id}.md"
        ).resolve()
        status_text = texts.get(status_path, "")
        for validation_id in sorted(required_validations):
            if validation_id not in status_text:
                report.errors.append(
                    f"[CrossLayer] {workflow_id} status omits validation: {validation_id}"
                )
        for output_id in sorted(produced_outputs):
            if output_id not in status_text:
                report.errors.append(
                    f"[CrossLayer] {workflow_id} status omits output: {output_id}"
                )

    technical_root = root / "technical"
    for path in technical_root.rglob("*.md"):
        resolved = path.resolve()
        if path.name == "README.md":
            continue
        values = parsed.get(resolved, {})
        validation_value = values.get("验证所有权", "")
        output_value = values.get("输出契约", "")
        for validation_id in ids_in(validation_value, VALIDATION_ID_PATTERN) - validation_ids:
            report.errors.append(
                f"[CrossLayer] Technical references undefined validation: "
                f"{normalize_relative(resolved, root)}: {validation_id}"
            )
        for output_id in ids_in(output_value, OUTPUT_ID_PATTERN) - output_ids:
            report.errors.append(
                f"[CrossLayer] Technical references undefined output: "
                f"{normalize_relative(resolved, root)}: {output_id}"
            )

    if state is not None:
        state_validation_ids = set(state.get("validation_status", {}))
        if state_validation_ids != validation_ids:
            report.errors.append(
                "[CrossLayer] PROJECT_STATE validation IDs differ from Validation Catalog: "
                f"missing={sorted(validation_ids - state_validation_ids)}, "
                f"extra={sorted(state_validation_ids - validation_ids)}"
            )
        current_output_ids = set(state.get("current_outputs", {}))
        expected_current_outputs = {
            output_id for output_id in output_ids if output_id.startswith("OUT-WF")
        }
        if current_output_ids != expected_current_outputs:
            report.errors.append(
                "[CrossLayer] PROJECT_STATE output IDs differ from Workflow Output Catalog: "
                f"missing={sorted(expected_current_outputs - current_output_ids)}, "
                f"extra={sorted(current_output_ids - expected_current_outputs)}"
            )
        plan_count = sum(
            clean_metadata_value(values.get("文档类型", "")) == "plan"
            and clean_metadata_value(values.get("生命周期", "")) == "current"
            for values in parsed.values()
        )
        for error in plan_cardinality_errors(state, plan_count):
            report.errors.append("[CrossLayer] " + error)
        if current_plan is not None:
            plan_id = clean_metadata_value(parsed[current_plan].get("文档 ID", ""))
            if state.get("current_plan_id") != plan_id:
                report.errors.append(
                    "[CrossLayer] PROJECT_STATE current_plan_id does not match current plan"
                )

    status_root = root / "project_management/status/workflows"
    for requirement_id, workflows in sorted(requirement_workflows.items()):
        for workflow_id in sorted(workflows):
            status_path = status_root / f"{workflow_id}.md"
            status_text = status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
            if f"/{requirement_id}" not in status_text:
                report.errors.append(
                    f"[CrossLayer] {workflow_id} status omits plan requirement: {requirement_id}"
                )


def check_status_and_plans(
    root: Path,
    docs: list[Path],
    parsed: dict[Path, dict[str, str]],
    report: AuditReport,
) -> None:
    current_plans = [
        path
        for path in docs
        if clean_metadata_value(parsed.get(path, {}).get("文档类型", "")) == "plan"
        and clean_metadata_value(parsed[path].get("生命周期", "")) == "current"
    ]
    state_path = root / "project_management/status/PROJECT_STATE.json"
    if not state_path.is_file():
        report.errors.append("missing project_management/status/PROJECT_STATE.json")
        return
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.errors.append(f"invalid PROJECT_STATE.json: {exc}")
        return
    report.errors.extend(plan_cardinality_errors(state, len(current_plans)))
    if current_plans:
        plan_id = clean_metadata_value(parsed[current_plans[0]]["文档 ID"])
        if state.get("current_plan_id") != plan_id:
            report.errors.append("PROJECT_STATE current_plan_id does not match current plan")
    report.errors.extend(active_workflow_errors(state))
    workflow_status = state.get("workflow_status", {})
    if set(workflow_status) != set(WORKFLOW_IDS):
        report.errors.append("PROJECT_STATE workflow_status keys do not match workflow set")
    for workflow_id in WORKFLOW_IDS:
        status_doc = root / f"project_management/status/workflows/{workflow_id}.md"
        if not status_doc.is_file():
            report.errors.append(f"missing workflow status document: {workflow_id}")


def load_json(path: Path, report: AuditReport, label: str) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.errors.append(f"invalid {label}: {exc}")
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_script_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def tracked_scripts(repo: Path, scan_root_relative: str) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--cached", "--others",
             "--exclude-standard", "-z", "--", scan_root_relative],
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result is not None and result.returncode == 0:
        return [
            repo / relative.decode("utf-8", errors="surrogateescape")
            for relative in result.stdout.split(b"\0")
            if relative
        ]
    scan_root = repo / scan_root_relative
    return sorted(scan_root.rglob("*")) if scan_root.is_dir() else []


def check_script_catalog(repo: Path | None, root: Path, report: AuditReport) -> None:
    if repo is None:
        report.warnings.append("repository root not found; script catalog check skipped")
        return
    catalog_path = repo / "00_engine/scripts/SCRIPT_CATALOG.json"
    if not catalog_path.is_file():
        report.errors.append("missing 00_engine/scripts/SCRIPT_CATALOG.json")
        return
    payload = load_json(catalog_path, report, "SCRIPT_CATALOG.json")
    if payload is None:
        return
    entries = list(payload.get("scripts", []))
    catalog_paths = {str(item.get("path")) for item in entries}
    if tuple(payload.get("script_roots", [])) != SCRIPT_SCAN_ROOTS:
        report.errors.append(
            f"script catalog roots must be {SCRIPT_SCAN_ROOTS}: "
            f"{payload.get('script_roots')}"
        )
    if payload.get("content_normalization") != "text_lf_v1":
        report.errors.append("script catalog must use text_lf_v1 normalization")
    actual_paths: set[str] = set()
    for scan_root_relative in SCRIPT_SCAN_ROOTS:
        scan_root = repo / scan_root_relative
        if not scan_root.is_dir():
            report.errors.append(f"script scan root missing: {scan_root_relative}")
            continue
        actual_paths.update(
            path.relative_to(repo).as_posix()
            for path in tracked_scripts(repo, scan_root_relative)
            if path.is_file()
            and path.suffix.lower() in SCRIPT_SUFFIXES
            and not any(
                part.lower() in EXCLUDED_SCRIPT_PARTS
                for part in path.relative_to(scan_root).parts
            )
        )
    missing = sorted(actual_paths - catalog_paths)
    stale = sorted(catalog_paths - actual_paths)
    if missing:
        report.errors.append(f"script catalog missing {len(missing)} scripts")
    if stale:
        report.errors.append(f"script catalog contains {len(stale)} missing scripts")
    allowed = {
        "production",
        "validated_pilot",
        "utility",
        "experimental",
        "deprecated",
        "archived",
    }
    for item in entries:
        relative = str(item.get("path"))
        target = repo / relative
        scan_root = str(item.get("scan_root"))
        lifecycle = str(item.get("lifecycle"))
        owner = str(item.get("owner_document"))
        mentions = {str(value) for value in item.get("document_mentions", [])}
        if scan_root not in SCRIPT_SCAN_ROOTS or not relative.startswith(
            scan_root + "/"
        ):
            report.errors.append(
                f"invalid script scan root: {relative}: {scan_root}"
            )
        if lifecycle not in allowed:
            report.errors.append(f"invalid script lifecycle: {relative}: {lifecycle}")
        if target.is_file():
            normalized = normalized_script_bytes(target)
            if item.get("bytes") != len(normalized):
                report.errors.append(f"script catalog byte count is stale: {relative}")
            if item.get("sha256") != hashlib.sha256(normalized).hexdigest():
                report.errors.append(f"script catalog SHA-256 is stale: {relative}")
        if not (root / owner).is_file():
            report.errors.append(f"script owner document missing: {relative}: {owner}")
        if lifecycle == "production" and owner not in mentions:
            report.errors.append(
                f"production script is not directly documented by its owner: "
                f"{relative}: {owner}"
            )
    report.stats["catalogued_scripts"] = len(entries)


def check_output_catalog(repo: Path | None, root: Path, report: AuditReport) -> None:
    if repo is None:
        return
    outputs = repo / "00_engine/outputs"
    policy_path = outputs / "RETENTION_POLICY.json"
    inventory_path = outputs / "OUTPUT_INVENTORY.json"
    if not policy_path.is_file() or not inventory_path.is_file():
        report.errors.append("missing output retention policy or output inventory")
        return
    policy = load_json(policy_path, report, "RETENTION_POLICY.json")
    inventory = load_json(inventory_path, report, "OUTPUT_INVENTORY.json")
    if policy is None or inventory is None:
        return
    allowed = set(policy.get("retention_classes", {}))
    inventory_by_path = {
        str(item.get("path")): item for item in inventory.get("entries", [])
    }
    expected_paths: set[str] = set()
    for output_root in outputs.iterdir():
        if output_root.name in {"OUTPUT_INVENTORY.json", "RETENTION_POLICY.json"}:
            continue
        children = sorted(output_root.iterdir()) if output_root.is_dir() else []
        for target in children or [output_root]:
            expected_paths.add(target.relative_to(outputs).as_posix())
    for rule in policy.get("rules", []):
        relative = str(rule.get("path_prefix"))
        if (outputs / relative).exists():
            expected_paths.add(relative)
    missing_scopes = sorted(expected_paths - set(inventory_by_path))
    stale_scopes = sorted(set(inventory_by_path) - expected_paths)
    if missing_scopes:
        report.errors.append(
            f"output inventory missing {len(missing_scopes)} direct scopes"
        )
    if stale_scopes:
        report.errors.append(
            f"output inventory contains {len(stale_scopes)} missing scopes"
        )
    for rule in policy.get("rules", []):
        relative = str(rule.get("path_prefix"))
        target = outputs / relative
        if not target.exists():
            report.errors.append(f"retention rule target missing: {relative}")
        item = inventory_by_path.get(relative)
        if item is None:
            report.errors.append(f"retention rule absent from inventory: {relative}")
            continue
        if item.get("retention") != rule.get("retention"):
            report.errors.append(f"retention mismatch in inventory: {relative}")
        owner = str(rule.get("owner_document"))
        owner_path = root / owner
        if not owner_path.is_file():
            report.errors.append(f"output owner document missing: {relative}: {owner}")
        elif relative not in read_utf8(owner_path, report):
            report.errors.append(
                f"retained output is not directly documented by its owner: "
                f"{relative}: {owner}"
            )
    for rule in policy.get("ownership_rules", []):
        relative = str(rule.get("path_prefix"))
        owner = str(rule.get("owner_document"))
        owner_path = root / owner
        if not owner_path.is_file():
            report.errors.append(
                f"output ownership rule document missing: "
                f"{relative}: {owner}"
            )
        elif relative not in read_utf8(owner_path, report):
            report.errors.append(
                f"output category is not directly documented by its owner: "
                f"{relative}: {owner}"
            )
    for item in inventory.get("entries", []):
        if item.get("retention") not in allowed:
            report.errors.append(
                f"invalid output retention: {item.get('path')}: {item.get('retention')}"
            )
        owner = item.get("owner_document")
        if not owner:
            report.errors.append(f"output scope missing owner: {item.get('path')}")
        elif not (root / str(owner)).is_file():
            report.errors.append(
                f"output scope owner document missing: {item.get('path')}: {owner}"
            )
    report.stats["inventoried_output_scopes"] = len(inventory_by_path)


def audit_docs(root: Path, repo_root: Path | None = None) -> AuditReport:
    root = root.resolve()
    report = AuditReport(root=str(root))
    if not root.is_dir():
        report.errors.append(f"documentation root does not exist: {root}")
        return report

    error_start, warning_start = len(report.errors), len(report.warnings)
    docs = collect_docs(root)
    texts = {path: read_utf8(path, report) for path in docs}
    record_subsystem_result(report, "DocumentIO", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    parsed = check_metadata(docs, root, texts, report)
    record_subsystem_result(report, "Metadata", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    graph, links = check_links(docs, root, texts, report)
    check_reachability(root, docs, graph, report)
    check_directory_indexes(root, docs, graph, report)
    record_subsystem_result(report, "Navigation", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_master_subsystem(root, texts, report)
    record_subsystem_result(report, "Master", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_workflows(root, texts, parsed, report)
    record_subsystem_result(report, "Workflow", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    validation_ids = check_validation_subsystem(root, texts, report)
    record_subsystem_result(report, "Validation", error_start, warning_start)

    repo = repo_root.resolve() if repo_root else infer_repo_root(root)

    error_start, warning_start = len(report.errors), len(report.warnings)
    output_ids = check_output_subsystem(root, texts, report)
    check_output_catalog(repo, root, report)
    record_subsystem_result(report, "Output", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_technical_subsystem(root, texts, parsed, report)
    check_script_catalog(repo, root, report)
    record_subsystem_result(report, "Technical", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    state = check_status_subsystem(root, texts, report)
    record_subsystem_result(report, "Status", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    current_plan, requirement_workflows = check_plan_subsystem(
        root, docs, texts, parsed, report, state=state
    )
    record_subsystem_result(report, "Plan", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_history_subsystem(root, texts, parsed, report)
    record_subsystem_result(report, "History", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_decisions_subsystem(root, texts, parsed, report)
    record_subsystem_result(report, "Decisions", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_reference_subsystem(root, report)
    record_subsystem_result(report, "Reference", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_registry_subsystem(root, repo, texts, report)
    record_subsystem_result(report, "Registry", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_governance_subsystem(root, texts, report)
    record_subsystem_result(report, "Governance", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_templates_subsystem(root, texts, report)
    record_subsystem_result(report, "Templates", error_start, warning_start)

    error_start, warning_start = len(report.errors), len(report.warnings)
    check_cross_layer_contracts(
        root,
        texts,
        parsed,
        validation_ids,
        output_ids,
        state,
        current_plan,
        requirement_workflows,
        report,
    )
    record_cross_layer_result(report, error_start, warning_start)

    report.stats.update({"documents": len(docs), "local_links": links})
    return report


def default_root() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "20_planning/data_design/character_creator/full_process"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_docs(args.root, args.repo_root)
    if args.as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        state = "PASS" if report.success else "FAIL"
        print(f"Character Factory documentation audit: {state}")
        print(f"Root: {report.root}")
        for key, value in sorted(report.stats.items()):
            print(f"{key}: {value}")
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        for error in report.errors:
            print(f"ERROR: {error}")
    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
