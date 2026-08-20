#!/usr/bin/env python3
"""Rebase absolute paths after promoting a P0 CC export from staging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


class P0ExportRebaseError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--work-order", type=Path, required=True)
    return parser.parse_args()


def replace_paths(value, old_root: str, new_root: str):
    if isinstance(value, dict):
        return {
            key: replace_paths(item, old_root, new_root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [replace_paths(item, old_root, new_root) for item in value]
    if isinstance(value, str):
        return value.replace(old_root, new_root)
    return value


def rebase_export(export_root: Path, old_root: Path, work_order_path: Path) -> dict:
    export_root = export_root.resolve()
    old_root = old_root.resolve()
    work_order_path = work_order_path.resolve()
    if not export_root.is_dir():
        raise P0ExportRebaseError(f"Promoted export root is missing: {export_root}")
    if old_root.exists():
        raise P0ExportRebaseError(f"Staging root still exists after move: {old_root}")
    work_order = json.loads(work_order_path.read_text(encoding="utf-8-sig"))
    expected_root = Path(work_order["export"]["root"]).resolve()
    if export_root != expected_root:
        raise P0ExportRebaseError(
            f"Promoted root does not match work order: {export_root} != {expected_root}"
        )

    old_text = str(old_root)
    new_text = str(export_root)
    changed_files = []
    for path in sorted(export_root.rglob("*.json")):
        raw = path.read_text(encoding="utf-8-sig")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise P0ExportRebaseError(f"Invalid JSON in export: {path}") from exc
        updated = replace_paths(value, old_text, new_text)
        if updated != value:
            path.write_text(
                json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            changed_files.append(str(path))

    remaining = []
    for path in sorted(export_root.rglob("*.json")):
        if old_text in path.read_text(encoding="utf-8-sig"):
            remaining.append(str(path))
    if remaining:
        raise P0ExportRebaseError(
            "Staging paths remain after rebase: " + ", ".join(remaining)
        )
    result = {
        "schema_version": 1,
        "success": True,
        "old_root": old_text,
        "export_root": new_text,
        "changed_file_count": len(changed_files),
        "changed_files": changed_files,
    }
    report_path = export_root / "promotion_rebase.json"
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    args = parse_args()
    result = rebase_export(args.export_root, args.old_root, args.work_order)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
