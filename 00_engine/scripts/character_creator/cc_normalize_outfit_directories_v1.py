#!/usr/bin/env python3
"""Normalize selected CC clothing families into canonical slot directories.

The command is dry-run by default. It only considers wearable files located
directly in each family root; already organized subdirectories are preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable


CANONICAL_SLOTS = (
    "Coats",
    "Shirts",
    "Pants",
    "Skirts",
    "Full-body",
    "Shoes",
    "_Accessories-Pending",
)

WEARABLE_EXTENSIONS = {
    ".ccacc",
    ".cccloth",
    ".ccgloves",
    ".cchair",
    ".ccshoes",
    ".iacc",
    ".icloth",
    ".ihair",
    ".rlhair",
}

ACCESSORY_EXTENSIONS = {
    ".ccacc",
    ".ccgloves",
    ".cchair",
    ".iacc",
    ".icloth",
    ".ihair",
    ".rlhair",
}

LOCKED_COMPONENT_FAMILIES = {
    ("female", "Elise"),
    ("female", "Misaki"),
    ("male", "\u8d5b\u535a\u670b\u514b\u4e00\u5957\u670d\u88c5"),
}

LOCKED_BUNDLE_SLOT = "Full-body/Locked-Bundle"

FULL_BODY_FALLBACK_FAMILIES = {
    ("female", "\u8fde\u8863\u88d9"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_name(path: Path) -> str:
    return " ".join(
        path.stem.lower().replace("_", " ").replace("-", " ").split()
    )


def contains_any(value: str, terms: Iterable[str]) -> bool:
    return any(term in value for term in terms)


def classify_asset(sex: str, family: str, path: Path) -> str | None:
    extension = path.suffix.lower()
    if extension not in WEARABLE_EXTENSIONS:
        return None
    if extension == ".ccshoes":
        return "Shoes"
    if extension in ACCESSORY_EXTENSIONS:
        return "_Accessories-Pending"
    if (sex, family) in LOCKED_COMPONENT_FAMILIES:
        return LOCKED_BUNDLE_SLOT

    name = normalized_name(path)

    if contains_any(
        name,
        (
            "belt",
            "bracelet",
            "earring",
            "necklace",
            "ring",
            "collar",
            " tie",
            "tie ",
            "bow",
            "glove",
            "hat",
            "hood",
            "harness",
            "pocket",
            "scarf",
            "neck string",
            "waist bag",
        ),
    ) or name in {"tie", "neck"}:
        return "_Accessories-Pending"
    if contains_any(
        name,
        ("jacket", "coat", "cloak", "robe", "cover up", "ruana"),
    ):
        return "Coats"
    if contains_any(name, ("dress", "jumpsuit", "outfit", "uniform", "suit")):
        return "Full-body"
    if contains_any(name, ("skirt", "kilt")):
        return "Skirts"
    if contains_any(name, ("pants", "shorts", "bottom")):
        return "Pants"
    if contains_any(name, ("shirt", "top", "sweater", "bra", "bustier", "vest")):
        return "Shirts"
    if (sex, family) in FULL_BODY_FALLBACK_FAMILIES:
        return "Full-body"
    return None


def atomic_json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def build_plan(root: Path) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    moves: list[dict[str, object]] = []
    unclassified: list[dict[str, str]] = []
    destinations: set[Path] = set()

    for sex in ("female", "male"):
        section = root / sex
        if not section.is_dir():
            raise RuntimeError(f"Missing section: {section}")
        for family_path in sorted(
            (item for item in section.iterdir() if item.is_dir()),
            key=lambda item: item.name.lower(),
        ):
            if family_path.name in CANONICAL_SLOTS:
                continue
            for source in sorted(
                (item for item in family_path.iterdir() if item.is_file()),
                key=lambda item: item.name.lower(),
            ):
                if source.suffix.lower() not in WEARABLE_EXTENSIONS:
                    continue
                slot = classify_asset(sex, family_path.name, source)
                if slot is None:
                    unclassified.append(
                        {
                            "sex": sex,
                            "family": family_path.name,
                            "source": str(source),
                        }
                    )
                    continue
                destination = family_path / slot / source.name
                if destination in destinations or destination.exists():
                    raise RuntimeError(f"Destination collision: {destination}")
                destinations.add(destination)
                moves.append(
                    {
                        "sex": sex,
                        "family": family_path.name,
                        "slot": slot,
                        "source": str(source),
                        "destination": str(destination),
                        "bytes": source.stat().st_size,
                        "sha256": sha256(source),
                    }
                )
    return moves, unclassified


def execute_plan(moves: list[dict[str, object]]) -> None:
    completed: list[tuple[Path, Path]] = []
    try:
        for item in moves:
            source = Path(str(item["source"]))
            destination = Path(str(item["destination"]))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            completed.append((source, destination))
        for item in moves:
            destination = Path(str(item["destination"]))
            if not destination.is_file():
                raise RuntimeError(f"Moved file is missing: {destination}")
            if sha256(destination) != item["sha256"]:
                raise RuntimeError(f"Hash mismatch after move: {destination}")
    except Exception:
        for source, destination in reversed(completed):
            if destination.exists() and not source.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination), str(source))
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    moves, unclassified = build_plan(root)
    if unclassified:
        manifest = {
            "schema_version": 1,
            "success": False,
            "execution_requested": args.execute,
            "root": str(root),
            "unclassified": unclassified,
            "planned_moves": moves,
        }
        atomic_json_write(args.manifest.resolve(), manifest)
        print(json.dumps({"success": False, "unclassified": unclassified}, ensure_ascii=False))
        return 2

    if args.execute:
        execute_plan(moves)

    counts = Counter(str(item["slot"]) for item in moves)
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "success": True,
        "execution_requested": args.execute,
        "root": str(root),
        "planned_move_count": len(moves),
        "planned_bytes": sum(int(item["bytes"]) for item in moves),
        "counts_by_slot": dict(sorted(counts.items())),
        "moves": moves,
    }
    atomic_json_write(args.manifest.resolve(), manifest)
    print(
        json.dumps(
            {
                "success": True,
                "execution_requested": args.execute,
                "move_count": len(moves),
                "counts_by_slot": dict(sorted(counts.items())),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
