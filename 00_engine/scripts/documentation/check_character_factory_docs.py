"""Read-only structural audit for the Character Factory documentation tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote


MASTER_NAME = "CHARACTER_FACTORY_MASTER_SPEC.md"
METADATA_FIELDS = (
    "文档角色",
    "状态",
    "适用阶段",
    "权威范围",
    "上级入口",
    "上游",
    "下游",
    "最近核验",
)
WORKFLOW_HEADINGS = (
    "目的与使用时机",
    "当前范围与非目标",
    "进入条件",
    "输入与输出",
    "执行环境",
    "执行步骤",
    "退出门禁",
    "失败与恢复",
    "技术依据与下一阶段",
)
ID_PATTERN = re.compile(
    r"\b(?:WF-\d{2}|GATE-\d{2}|VAL-[A-Z]+-\d{2}|"
    r"VIS-[A-Z]+-\d{2}|REC-[A-Z]+-\d{2}|RM-\d+[A-Z]?)\b"
)
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
ARCHIVE_ROW_PATTERN = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*`([0-9A-Fa-f]{64})`\s*\|\s*$",
    re.MULTILINE,
)
ARCHIVE_PART_PATTERN = re.compile(
    r"^history/(?:legacy_|pre_lifecycle_)[^/]+/", re.IGNORECASE
)


@dataclass
class AuditReport:
    root: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["success"] = self.success
        return payload


def normalize_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_archive_snapshot(relative: str) -> bool:
    return bool(ARCHIVE_PART_PATTERN.match(relative))


def read_utf8(path: Path, report: AuditReport) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        report.errors.append(f"cannot read UTF-8 file {path}: {exc}")
        return ""


def parse_markdown_target(raw_target: str) -> tuple[str, str]:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " \"" in target:
        target = target.split(" \"", 1)[0]
    target = unquote(target)
    if "#" in target:
        path_part, fragment = target.split("#", 1)
    else:
        path_part, fragment = target, ""
    return path_part, fragment.lower()


def is_external_target(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith((
        "http://",
        "https://",
        "mailto:",
        "app://",
        "file://",
    ))


def slugify_heading(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.strip().lower()
    kept: list[str] = []
    for char in value:
        category = unicodedata.category(char)
        if char in {" ", "-", "_"} or category[0] in {"L", "N"}:
            kept.append(char)
    slug = "".join(kept).replace(" ", "-")
    return re.sub(r"-+", "-", slug).strip("-")


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


def markdown_links(path: Path, text: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for match in LINK_PATTERN.finditer(text):
        raw = match.group(1)
        if is_external_target(raw):
            continue
        links.append(parse_markdown_target(raw))
    return links


def collect_current_docs(root: Path) -> list[Path]:
    docs: list[Path] = []
    for path in root.rglob("*.md"):
        relative = normalize_relative(path, root)
        if not is_archive_snapshot(relative):
            docs.append(path)
    return sorted(docs)


def check_metadata(
    docs: Iterable[Path], root: Path, texts: dict[Path, str], report: AuditReport
) -> None:
    for path in docs:
        text = texts[path]
        missing = [
            field_name
            for field_name in METADATA_FIELDS
            if not re.search(
                rf"^>\s*{re.escape(field_name)}：\s*.+$", text, re.MULTILINE
            )
        ]
        if missing:
            relative = normalize_relative(path, root)
            report.errors.append(
                f"missing metadata in {relative}: {', '.join(missing)}"
            )


def check_links(
    docs: Iterable[Path], root: Path, texts: dict[Path, str], report: AuditReport
) -> tuple[dict[Path, set[Path]], int]:
    graph: dict[Path, set[Path]] = {path: set() for path in docs}
    current_set = set(graph)
    anchor_cache: dict[Path, set[str]] = {}
    checked = 0
    for source in docs:
        for path_part, fragment in markdown_links(source, texts[source]):
            checked += 1
            target = source if not path_part else (source.parent / path_part).resolve()
            if not target.exists():
                report.errors.append(
                    f"broken link in {normalize_relative(source, root)}: "
                    f"{path_part or '#'}{('#' + fragment) if fragment else ''}"
                )
                continue
            if target.is_dir():
                target = target / "README.md"
                if not target.exists():
                    report.errors.append(
                        f"directory link has no README in {normalize_relative(source, root)}: {path_part}"
                    )
                    continue
            if target.suffix.lower() == ".md" and fragment:
                if target not in anchor_cache:
                    anchor_cache[target] = heading_anchors(read_utf8(target, report))
                if fragment not in anchor_cache[target]:
                    report.errors.append(
                        f"missing anchor in {normalize_relative(source, root)}: "
                        f"{path_part}#{fragment}"
                    )
            if target in current_set:
                graph[source].add(target)
    return graph, checked


def check_reachability(
    root: Path, docs: list[Path], graph: dict[Path, set[Path]], report: AuditReport
) -> None:
    master = root / MASTER_NAME
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


def check_directory_indexes(
    root: Path, docs: list[Path], graph: dict[Path, set[Path]], report: AuditReport
) -> None:
    directories = sorted({path.parent for path in docs if path.parent != root})
    for directory in directories:
        readme = directory / "README.md"
        direct_children = [
            path for path in docs if path.parent == directory and path.name != "README.md"
        ]
        if not direct_children:
            continue
        if readme not in graph:
            report.errors.append(
                f"directory has current documents but no README: "
                f"{normalize_relative(directory, root)}"
            )
            continue
        for child in direct_children:
            if child not in graph[readme]:
                report.errors.append(
                    f"directory README does not index {normalize_relative(child, root)}"
                )


def check_workflow(
    root: Path, docs: list[Path], texts: dict[Path, str], report: AuditReport
) -> None:
    workflow_dir = root / "workflow"
    expected = {
        index: next(
            (path for path in docs if path.parent == workflow_dir and path.name.startswith(f"WF-{index:02d}-")),
            None,
        )
        for index in range(10)
    }
    for index, path in expected.items():
        if path is None:
            report.errors.append(f"missing workflow stage WF-{index:02d}")
            continue
        text = texts[path]
        if f"`WF-{index:02d}`" not in text:
            report.errors.append(f"workflow metadata does not name WF-{index:02d}: {path.name}")
        for heading in WORKFLOW_HEADINGS:
            if not re.search(rf"^##\s+\d+\.\s+{re.escape(heading)}$", text, re.MULTILINE):
                report.errors.append(f"workflow {path.name} missing section: {heading}")
        if index in {8, 9}:
            if "`planned`" not in text:
                report.errors.append(f"planned workflow lacks planned status: {path.name}")
            if re.search(r"```(?:powershell|python|bash|cmd)\b", text, re.IGNORECASE):
                report.errors.append(f"planned workflow contains executable command block: {path.name}")
        if index > 0 and expected[index - 1] is not None:
            if expected[index - 1].name not in text:
                report.errors.append(f"workflow {path.name} does not link previous stage")
        if index < 9 and expected[index + 1] is not None:
            if expected[index + 1].name not in text:
                report.errors.append(f"workflow {path.name} does not link next stage")


def collect_definitions(root: Path, texts: dict[Path, str]) -> Counter[str]:
    definitions: Counter[str] = Counter()
    workflow_dir = root / "workflow"
    for path in texts:
        if path.parent == workflow_dir:
            match = re.match(r"(WF-\d{2})-", path.name)
            if match:
                definitions[match.group(1)] += 1
    owners = {
        root / "validation" / "README.md": re.compile(r"^\|\s*`(GATE-\d{2})\b", re.MULTILINE),
        root / "validation" / "VALIDATION_CATALOG.md": re.compile(r"^##\s+(VAL-[A-Z]+-\d{2})\b", re.MULTILINE),
        root / "validation" / "VISUAL_ACCEPTANCE.md": re.compile(r"^##\s+(VIS-[A-Z]+-\d{2})\b", re.MULTILINE),
        root / "validation" / "RECOVERY_RUNBOOK.md": re.compile(r"^##\s+(REC-[A-Z]+-\d{2})\b", re.MULTILINE),
        root / "planning" / "ROADMAP.md": re.compile(r"^##\s+\d+\.\s+(RM-\d+[A-Z]?)\b", re.MULTILINE),
        root / "history" / "MILESTONE_LOG.md": re.compile(
            r"^##\s+\d{4}-\d{2}-\d{2}[：:]\s*(RM-\d+[A-Z]?)\b",
            re.MULTILINE,
        ),
    }
    for path, pattern in owners.items():
        if path in texts:
            definitions.update(pattern.findall(texts[path]))
    return definitions


def check_ids(
    root: Path, texts: dict[Path, str], report: AuditReport
) -> None:
    definitions = collect_definitions(root, texts)
    for identifier, count in sorted(definitions.items()):
        if count != 1:
            report.errors.append(f"identifier defined {count} times: {identifier}")
    references: set[str] = set()
    for path, text in texts.items():
        # Milestones and dated reports may name retired work packages. They are
        # immutable evidence, not active references that require a Roadmap owner.
        if normalize_relative(path, root).startswith("history/"):
            continue
        references.update(ID_PATTERN.findall(text))
    for identifier in sorted(references):
        if identifier not in definitions:
            report.errors.append(f"identifier referenced without definition: {identifier}")
    report.stats["defined_ids"] = len(definitions)


def check_archive_manifests(root: Path, report: AuditReport) -> int:
    checked = 0
    for manifest in sorted((root / "history").glob("*/ARCHIVE_MANIFEST.md")):
        text = read_utf8(manifest, report)
        rows = ARCHIVE_ROW_PATTERN.findall(text)
        if not rows:
            report.errors.append(f"archive manifest has no hash rows: {manifest}")
            continue
        for relative, expected_size, expected_hash in rows:
            checked += 1
            target = manifest.parent / Path(relative.replace("\\", "/"))
            if not target.is_file():
                report.errors.append(f"archive file missing: {target}")
                continue
            data = target.read_bytes()
            actual_hash = hashlib.sha256(data).hexdigest().upper()
            if len(data) != int(expected_size):
                report.errors.append(f"archive size mismatch: {target}")
            if actual_hash != expected_hash.upper():
                report.errors.append(f"archive hash mismatch: {target}")
    return checked


def audit_docs(root: Path) -> AuditReport:
    root = root.resolve()
    report = AuditReport(root=str(root))
    if not root.is_dir():
        report.errors.append(f"documentation root does not exist: {root}")
        return report
    docs = collect_current_docs(root)
    texts = {path: read_utf8(path, report) for path in docs}
    check_metadata(docs, root, texts, report)
    graph, link_count = check_links(docs, root, texts, report)
    check_reachability(root, docs, graph, report)
    check_directory_indexes(root, docs, graph, report)
    check_workflow(root, docs, texts, report)
    check_ids(root, texts, report)
    archive_count = check_archive_manifests(root, report)
    report.stats.update(
        {
            "current_documents": len(docs),
            "local_links": link_count,
            "archive_files": archive_count,
        }
    )
    return report


def default_root() -> Path:
    lance_root = Path(__file__).resolve().parents[3]
    return lance_root / "20_planning" / "data_design" / "character_creator" / "full_process"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the Character Factory documentation without modifying files."
    )
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_docs(args.root)
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
