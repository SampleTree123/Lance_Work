"""Build a non-destructive inventory of 00_engine/outputs.

The inventory measures top-level output roots and their direct children. It
applies retention and ownership rules by longest matching path prefix. Unknown
retention remains unclassified and therefore cannot be removed by policy.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def measure(path: Path) -> tuple[int, int, str | None]:
    files = 0
    total_bytes = 0
    latest: float | None = None
    if path.is_file():
        stat = path.stat()
        return 1, stat.st_size, datetime.fromtimestamp(
            stat.st_mtime, timezone.utc
        ).isoformat()
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        files += 1
        total_bytes += stat.st_size
        latest = stat.st_mtime if latest is None else max(latest, stat.st_mtime)
    latest_iso = (
        datetime.fromtimestamp(latest, timezone.utc).isoformat()
        if latest is not None
        else None
    )
    return files, total_bytes, latest_iso


def matching_rule(relative: str, rules: list[dict[str, object]]) -> dict[str, object] | None:
    matches = [
        rule
        for rule in rules
        if relative == str(rule["path_prefix"])
        or relative.startswith(str(rule["path_prefix"]) + "/")
    ]
    if not matches:
        return None
    return max(matches, key=lambda item: len(str(item["path_prefix"])))


def build_inventory(outputs_root: Path, policy: dict[str, object]) -> dict[str, object]:
    rules = list(policy.get("rules", []))
    ownership_rules = list(policy.get("ownership_rules", []))
    default = str(policy.get("default_retention", "unclassified"))
    entries: list[dict[str, object]] = []
    targets_by_relative: dict[str, tuple[Path, str]] = {}
    for root in sorted(outputs_root.iterdir(), key=lambda item: item.name.lower()):
        if root.name in {"OUTPUT_INVENTORY.json", "RETENTION_POLICY.json"}:
            continue
        children = (
            sorted(root.iterdir(), key=lambda item: item.name.lower())
            if root.is_dir()
            else []
        )
        targets = children or [root]
        for target in targets:
            relative = target.relative_to(outputs_root).as_posix()
            targets_by_relative[relative] = (target, "direct_child")

    # Retention rules may intentionally identify a deeper run than the direct
    # child inventory level. Add those exact paths so authoritative evidence is
    # visible without expanding every historical directory recursively.
    for rule in rules:
        relative = str(rule["path_prefix"])
        target = outputs_root / Path(relative)
        if target.exists():
            targets_by_relative.setdefault(relative, (target, "policy_path"))

    for relative in sorted(targets_by_relative):
        target, scope = targets_by_relative[relative]
        rule = matching_rule(relative, rules)
        ownership_rule = matching_rule(relative, ownership_rules)
        owner_source = rule or ownership_rule
        files, total_bytes, latest = measure(target)
        entries.append(
            {
                "path": relative,
                "scope": scope,
                "kind": "directory" if target.is_dir() else "file",
                "file_count": files,
                "bytes": total_bytes,
                "latest_mtime_utc": latest,
                "retention": str(rule["retention"]) if rule else default,
                "workflow": owner_source.get("workflow") if owner_source else None,
                "owner_document": owner_source.get("owner_document")
                if owner_source
                else None,
                "output_contract_id": owner_source.get("output_contract_id")
                if owner_source
                else None,
                "ownership_reason": owner_source.get("reason")
                if owner_source
                else None,
                "classification_reason": rule.get("reason")
                if rule
                else "No reviewed retention rule. Do not delete.",
            }
        )
    counts = Counter(str(item["retention"]) for item in entries)
    root_files, root_bytes, _ = measure(outputs_root)
    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "00_engine/scripts/documentation/build_output_inventory.py",
        "output_root": "00_engine/outputs",
        "policy_file": "00_engine/outputs/RETENTION_POLICY.json",
        "total_bytes": root_bytes,
        "total_files": root_files,
        "retention_counts": dict(sorted(counts.items())),
        "entries": entries,
    }


def parse_args() -> argparse.Namespace:
    root = repo_root()
    outputs = root / "00_engine/outputs"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs-root", type=Path, default=outputs)
    parser.add_argument(
        "--policy", type=Path, default=outputs / "RETENTION_POLICY.json"
    )
    parser.add_argument(
        "--output", type=Path, default=outputs / "OUTPUT_INVENTORY.json"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    payload = build_inventory(args.outputs_root.resolve(), policy)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(payload['entries'])} output records "
        f"({payload['total_files']} files) to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
