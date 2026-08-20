"""Generate a line-numbered reference trace for Character Factory Markdown docs."""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote


MASTER_NAME = "CHARACTER_FACTORY_MASTER_SPEC.md"
TRACE_RELATIVE = Path("reference/DOCUMENT_LINK_TRACE.md")
LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
ARCHIVE_PART_PATTERN = re.compile(
    r"^history/(?:legacy_|pre_lifecycle_)[^/]+/", re.IGNORECASE
)
ARCHIVE_ROW_PATTERN = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*`([0-9A-Fa-f]{64})`\s*\|\s*$",
    re.MULTILINE,
)
FOLDER_ORDER = {
    "": 0,
    "workflow": 1,
    "cc_details": 2,
    "bridge_details": 3,
    "cc_ue_transfer": 4,
    "ue_details": 5,
    "validation": 6,
    "planning": 7,
    "decisions": 8,
    "reference": 9,
    "history": 10,
}
ROOT_FILE_ORDER = {
    MASTER_NAME: 0,
    "README.md": 1,
    "CURRENT_STATUS.md": 2,
    "DOCUMENTATION_RULES.md": 3,
}
MAX_PREFIX_PATHS = 10_000


@dataclass(frozen=True)
class Mention:
    occurrence: int
    source: Path
    target: Path
    line: int
    label: str
    fragment: str
    context: str
    kind: str


def normalize_relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_archive_snapshot(relative: str) -> bool:
    return bool(ARCHIVE_PART_PATTERN.match(relative))


def collect_current_docs(root: Path) -> list[Path]:
    return sorted(
        (
            path.resolve()
            for path in root.rglob("*.md")
            if not is_archive_snapshot(path.relative_to(root).as_posix())
        ),
        key=lambda path: document_order(path, root),
    )


def document_order(path: Path, root: Path) -> tuple[int, int, str]:
    relative = path.resolve().relative_to(root.resolve())
    folder = relative.parts[0] if len(relative.parts) > 1 else ""
    folder_rank = FOLDER_ORDER.get(folder, 99)
    if folder == "":
        file_rank = ROOT_FILE_ORDER.get(path.name, 99)
    else:
        file_rank = 0 if path.name == "README.md" else 1
    return folder_rank, file_rank, relative.as_posix().lower()


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
    return path_part, fragment


def is_external_target(target: str) -> bool:
    return target.lower().startswith(
        ("http://", "https://", "mailto:", "app://", "file://")
    )


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def source_line(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end < 0:
        end = len(text)
    return text[start:end].strip()


def clean_context(value: str, limit: int = 260) -> str:
    value = LINK_PATTERN.sub(lambda match: match.group(1), value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        value = value[: limit - 1].rstrip() + "…"
    return value.replace("“", "‘").replace("”", "’")


def clean_label(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    return value


def mention_kind(value: str) -> str:
    stripped = value.lstrip()
    if stripped.startswith(">"):
        return "元数据"
    if stripped.startswith("|"):
        return "索引表"
    return "正文"


def resolve_local_target(source: Path, raw_target: str) -> tuple[Path, str] | None:
    if is_external_target(raw_target):
        return None
    path_part, fragment = parse_markdown_target(raw_target)
    target = source if not path_part else (source.parent / path_part).resolve()
    if target.is_dir():
        target = target / "README.md"
    return target.resolve(), fragment


def scan_mentions(docs: list[Path]) -> list[Mention]:
    mentions: list[Mention] = []
    occurrence = 0
    for source in docs:
        text = source.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(text):
            resolved = resolve_local_target(source, match.group(2))
            if resolved is None:
                continue
            target, fragment = resolved
            raw_line = source_line(text, match.start())
            mentions.append(
                Mention(
                    occurrence=occurrence,
                    source=source,
                    target=target,
                    line=line_number(text, match.start()),
                    label=clean_label(match.group(1)),
                    fragment=fragment,
                    context=clean_context(raw_line),
                    kind=mention_kind(raw_line),
                )
            )
            occurrence += 1
    return mentions


def shortest_distances(
    root_node: Path, docs: set[Path], mentions: list[Mention]
) -> dict[Path, int]:
    outgoing: dict[Path, set[Path]] = defaultdict(set)
    for mention in mentions:
        if mention.source in docs and mention.target in docs:
            outgoing[mention.source].add(mention.target)
    distances = {root_node: 0}
    queue: deque[Path] = deque([root_node])
    while queue:
        source = queue.popleft()
        for target in sorted(outgoing[source], key=str):
            if target not in distances:
                distances[target] = distances[source] + 1
                queue.append(target)
    return distances


def build_shortest_path_resolver(
    master: Path,
    docs: set[Path],
    mentions: list[Mention],
    distances: dict[Path, int],
):
    predecessors: dict[Path, list[Mention]] = defaultdict(list)
    for mention in mentions:
        if mention.source not in docs or mention.target not in docs:
            continue
        source_distance = distances.get(mention.source)
        target_distance = distances.get(mention.target)
        if source_distance is None or target_distance is None:
            continue
        if source_distance + 1 == target_distance:
            predecessors[mention.target].append(mention)
    for target in predecessors:
        predecessors[target].sort(
            key=lambda item: (str(item.source).lower(), item.line, item.occurrence)
        )

    @lru_cache(maxsize=None)
    def resolve(node: Path) -> tuple[tuple[Mention, ...], ...]:
        if node == master:
            return ((),)
        paths: list[tuple[Mention, ...]] = []
        for mention in predecessors.get(node, []):
            for prefix in resolve(mention.source):
                paths.append(prefix + (mention,))
                if len(paths) > MAX_PREFIX_PATHS:
                    raise RuntimeError(
                        f"more than {MAX_PREFIX_PATHS} shortest prefixes for {node}"
                    )
        return tuple(paths)

    return resolve


def path_nodes(master: Path, path: tuple[Mention, ...]) -> set[Path]:
    nodes = {master}
    nodes.update(mention.target for mention in path)
    return nodes


def render_chain(path: tuple[Mention, ...], root: Path) -> str:
    if not path:
        return f"`{MASTER_NAME}`"
    tokens = [
        f"{normalize_relative(path[0].source, root)}:L{path[0].line}"
    ]
    for index, mention in enumerate(path):
        target = normalize_relative(mention.target, root)
        if index + 1 < len(path):
            target = f"{target}:L{path[index + 1].line}"
        elif mention.fragment:
            target = f"{target}#{mention.fragment}"
        tokens.append(target)
    return " → ".join(f"`{token}`" for token in tokens)


def format_mention_routes(
    mention: Mention,
    master: Path,
    root: Path,
    shortest_paths,
) -> tuple[list[str], int]:
    if mention.source == master:
        prefixes = ((),)
    else:
        prefixes = shortest_paths(mention.source)
    lines: list[str] = []
    back_routes = 0
    for prefix in prefixes:
        is_back_route = mention.target in path_nodes(master, prefix)
        full_path = prefix + (mention,)
        suffix = " **[回链，不继续递归]**" if is_back_route else ""
        if is_back_route:
            back_routes += 1
        lines.append(f"    - {render_chain(full_path, root)}{suffix}")
    return lines, back_routes


def render_current_document(
    target: Path,
    master: Path,
    root: Path,
    incoming: list[Mention],
    distances: dict[Path, int],
    shortest_paths,
) -> tuple[list[str], int, int]:
    relative = normalize_relative(target, root)
    lines = [f"### `{Path(relative).name}`", ""]
    if target == master:
        lines.append("- 定位：递归根节点。")
    else:
        distance = distances.get(target)
        state = "可达" if distance is not None else "不可达"
        lines.append(f"- 定位：`{relative}`；从 Master 的最短层级为 `{distance}`；状态：**{state}**。")
    lines.append(f"- 直接入站提及：`{len(incoming)}` 次。")
    lines.append("")
    chain_count = 0
    back_count = 0
    if not incoming:
        lines.append("  - 无入站提及。")
        lines.append("")
        return lines, chain_count, back_count
    for index, mention in enumerate(incoming, start=1):
        source = normalize_relative(mention.source, root)
        label = mention.label or "同页锚点"
        lines.append(
            f"{index}. **{mention.kind}提及**：`{source}:L{mention.line}`，链接文字 `{label}`。"
        )
        lines.append(f"   - 用途原句：{mention.context}")
        routes, back_routes = format_mention_routes(
            mention, master, root, shortest_paths
        )
        lines.extend(routes)
        chain_count += len(routes)
        back_count += back_routes
    lines.append("")
    return lines, chain_count, back_count


def archive_route_prefixes(
    manifest: Path,
    mentions: list[Mention],
    master: Path,
    root: Path,
    shortest_paths,
) -> list[tuple[Mention, ...]]:
    routes: list[tuple[Mention, ...]] = []
    for mention in mentions:
        if mention.target != manifest:
            continue
        prefixes = ((),) if mention.source == master else shortest_paths(mention.source)
        routes.extend(prefix + (mention,) for prefix in prefixes)
    return routes


def render_archives(
    root: Path,
    mentions: list[Mention],
    master: Path,
    shortest_paths,
) -> tuple[list[str], int, int]:
    lines = ["## 历史快照（Manifest 追溯）", ""]
    lines.append(
        "归档正文不是现行规范，不参与当前链接图；以下链条通过 `history/README.md` 和 Manifest 的路径行定位。"
    )
    lines.append("")
    manifest_count = 0
    payload_count = 0
    for manifest in sorted((root / "history").glob("*/ARCHIVE_MANIFEST.md")):
        manifest = manifest.resolve()
        manifest_count += 1
        manifest_relative = normalize_relative(manifest, root)
        lines.extend([f"### `{manifest_relative}`", ""])
        prefixes = archive_route_prefixes(
            manifest, mentions, master, root, shortest_paths
        )
        if prefixes:
            for prefix in prefixes:
                lines.append(f"- Manifest 入口：{render_chain(prefix, root)}")
        else:
            lines.append("- Manifest 入口：**未从现行文档链接**。")
        text = manifest.read_text(encoding="utf-8")
        rows = list(ARCHIVE_ROW_PATTERN.finditer(text))
        lines.append(f"- 归档正文：`{len(rows)}` 份。")
        lines.append("")
        for row_index, match in enumerate(rows, start=1):
            payload_count += 1
            row_line = line_number(text, match.start())
            payload = (manifest.parent / match.group(1).replace("\\", "/")).resolve()
            payload_relative = normalize_relative(payload, root)
            if prefixes:
                for prefix_index, prefix in enumerate(prefixes, start=1):
                    chain = render_chain(prefix, root)
                    lines.append(
                        f"{row_index}.{prefix_index}. {chain} → "
                        f"`{manifest_relative}:L{row_line}` → `{payload_relative}`"
                    )
            else:
                lines.append(
                    f"{row_index}. `{manifest_relative}:L{row_line}` → `{payload_relative}`"
                )
        lines.append("")
    return lines, manifest_count, payload_count


def generate(root: Path, output: Path, verified_on: str) -> dict[str, int]:
    root = root.resolve()
    output = output.resolve()
    docs = collect_current_docs(root)
    doc_set = set(docs)
    master = (root / MASTER_NAME).resolve()
    if master not in doc_set:
        raise RuntimeError(f"missing Master: {master}")
    if output not in doc_set:
        raise RuntimeError(
            "trace output must already exist so its inbound links are included: "
            f"{output}"
        )

    all_mentions = scan_mentions(docs)
    current_mentions = [
        mention for mention in all_mentions if mention.target in doc_set
    ]
    distances = shortest_distances(master, doc_set, current_mentions)
    shortest_paths = build_shortest_path_resolver(
        master, doc_set, current_mentions, distances
    )
    incoming: dict[Path, list[Mention]] = defaultdict(list)
    for mention in current_mentions:
        incoming[mention.target].append(mention)
    for target in incoming:
        incoming[target].sort(
            key=lambda item: (
                document_order(item.source, root),
                item.line,
                item.occurrence,
            )
        )

    body: list[str] = [
        "# Character Factory 文档递归提及树",
        "",
        "> 文档角色：`generated_link_trace`",
        "> 状态：`current`",
        "> 适用阶段：`global`",
        "> 权威范围：从 Master 到现行文档及历史 Manifest 的行号级导航证明",
        "> 上级入口：`CHARACTER_FACTORY_MASTER_SPEC.md`",
        "> 上游：现行 Markdown 链接与历史 `ARCHIVE_MANIFEST.md`",
        "> 下游：全部现行文档和不可变历史快照",
        f"> 最近核验：{verified_on}",
        "> 生成器：`00_engine/scripts/documentation/generate_character_factory_link_trace.py`",
        "",
        "## 1. 读取规则",
        "",
        "- 根节点固定为 `CHARACTER_FACTORY_MASTER_SPEC.md`。",
        "- 每个“直接入站提及”对应源 Markdown 中一次真实链接，保留源文件、行号、链接文字和用途原句。",
        "- 为避免 `子文档 → Master → 子文档` 造成无限递归，每次提及展开其源文件的**全部最短根路径**；会返回已经出现节点的链标为“回链”并停止。",
        "- 因此本报告完整登记所有直接链接及全部最短前缀，但不枚举人为绕行的非最短循环路径。",
        "- 报告自身不创建 Markdown 导航链接，避免生成结果反过来改变被统计的链接图。",
        "- 历史快照不具有当前元数据，通过 Manifest 的路径行和 SHA-256 管理，在末尾单列。",
        "",
        "## 2. 可达性结论",
        "",
        f"- 现行文档：`{len(docs)}` 份。",
        f"- 从 Master 可达：`{len(distances)}` 份。",
        f"- 不可达：`{len(doc_set - set(distances))}` 份。",
        f"- 指向现行文档的直接提及：`{len(current_mentions)}` 次。",
        "",
    ]

    chain_count = 0
    back_count = 0
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in docs:
        relative = path.relative_to(root)
        folder = relative.parts[0] if len(relative.parts) > 1 else "(root)"
        grouped[folder].append(path)
    folder_names = ["(root)"] + [
        name for name, _ in sorted(FOLDER_ORDER.items(), key=lambda item: item[1]) if name
    ]
    folder_names.extend(sorted(set(grouped) - set(folder_names)))
    for folder in folder_names:
        paths = grouped.get(folder)
        if not paths:
            continue
        body.extend([f"## {folder}", ""])
        for target in paths:
            rendered, target_chains, target_back = render_current_document(
                target,
                master,
                root,
                incoming.get(target, []),
                distances,
                shortest_paths,
            )
            body.extend(rendered)
            chain_count += target_chains
            back_count += target_back

    archive_lines, manifest_count, payload_count = render_archives(
        root, all_mentions, master, shortest_paths
    )
    body.extend(archive_lines)
    body.extend(
        [
            "## 生成统计",
            "",
            f"- 展开的提及链：`{chain_count}` 条。",
            f"- 其中回链：`{back_count}` 条。",
            f"- 历史 Manifest：`{manifest_count}` 份。",
            f"- Manifest 登记的归档正文：`{payload_count}` 份。",
            "",
            "重新生成后必须运行文档审计器；两者退出码均为 0 才能提交文档结构变更。",
            "",
        ]
    )
    output.write_text("\n".join(body), encoding="utf-8", newline="\n")
    return {
        "current_documents": len(docs),
        "reachable_documents": len(distances),
        "current_mentions": len(current_mentions),
        "expanded_chains": chain_count,
        "back_chains": back_count,
        "archive_manifests": manifest_count,
        "archive_payloads": payload_count,
    }


def default_root() -> Path:
    lance_root = Path(__file__).resolve().parents[3]
    return (
        lance_root
        / "20_planning"
        / "data_design"
        / "character_creator"
        / "full_process"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Character Factory Markdown link trace."
    )
    parser.add_argument("--root", type=Path, default=default_root())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verified-on", default=date.today().isoformat())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    output = (
        args.output.resolve()
        if args.output
        else (root / TRACE_RELATIVE).resolve()
    )
    try:
        stats = generate(root, output, args.verified_on)
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote: {output}")
    for key, value in stats.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
