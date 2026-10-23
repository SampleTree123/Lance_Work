"""Check that old UE import trees contain only the 365 inventoried cases."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")
CONTENT = Path(r"D:\UE\projects\datatry_02\Content")
OLD_ROOTS = [
    CONTENT / "Vendor/Reallusion/CC5/Wardrobe",
    CONTENT / "Vendor/Reallusion/CC5/ScalpHairBatch",
]
NEW_ROOT = CONTENT / "DataMake/CharacterFactory"


def main():
    plan = json.loads((ROOT / "migration_plan.json").read_text(encoding="utf-8"))
    expected = [CONTENT / case["old_root"].removeprefix("/Game/") for case in plan["cases"]]
    assert len(expected) == 365 and len(set(expected)) == 365
    expected_set = set(expected)
    old_counts = Counter()
    old_bytes = 0
    unexpected = []
    for tree in OLD_ROOTS:
        if not tree.is_dir():
            raise FileNotFoundError(tree)
        for item in tree.rglob("*"):
            if not item.is_file():
                continue
            relative = item.relative_to(CONTENT)
            if not any(parent in expected_set for parent in item.parents):
                unexpected.append(str(relative))
            old_counts[item.suffix.lower()] += 1
            old_bytes += item.stat().st_size
    new_counts = Counter()
    new_bytes = 0
    for item in NEW_ROOT.rglob("*"):
        if item.is_file():
            new_counts[item.suffix.lower()] += 1
            new_bytes += item.stat().st_size
    result = {"old_case_count": len(expected), "old_file_counts": dict(old_counts),
              "old_total_bytes": old_bytes, "unexpected_files": unexpected,
              "new_file_counts": dict(new_counts), "new_total_bytes": new_bytes,
              "safe_scope": not unexpected}
    (ROOT / "filesystem_scope_before_cleanup.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if unexpected:
        raise RuntimeError("old import root contains files outside inventoried cases")


if __name__ == "__main__":
    main()
