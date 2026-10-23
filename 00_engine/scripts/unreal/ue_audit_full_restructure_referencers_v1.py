"""Read-only UE Asset Registry scan for consumers of old imported case trees."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")


def run():
    plan = json.loads((ROOT / "migration_plan.json").read_text(encoding="utf-8"))
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    for name in ("include_hard_package_references", "include_soft_package_references",
                 "include_game_package_references", "include_editor_only_package_references"):
        options.set_editor_property(name, True)
    cases = []
    all_external = defaultdict(set)
    classes = Counter()
    for index, case in enumerate(plan["cases"], 1):
        root = case["old_root"]
        external = []
        assets = registry.get_assets_by_path(root, recursive=True)
        for asset in assets:
            package = str(asset.package_name)
            classes[str(asset.asset_class_path.asset_name)] += 1
            for ref in map(str, registry.get_referencers(package, options) or []):
                if not ref.startswith(root + "/"):
                    external.append({"asset": package, "referencer": ref})
                    all_external[ref].add(package)
        cases.append({"id": case["id"], "old_root": root,
                      "package_count": len(assets), "external_referencers": external})
        if index % 25 == 0:
            unreal.log(f"DataMake referencer scan {index}/{len(plan['cases'])}")
    report = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "summary": {"cases": len(cases), "old_packages": sum(c["package_count"] for c in cases),
                          "classes": dict(sorted(classes.items())),
                          "external_referencer_packages": len(all_external),
                          "cases_with_external_referencers": sum(bool(c["external_referencers"]) for c in cases)},
              "external_referencers": {key: sorted(value) for key, value in sorted(all_external.items())},
              "cases": cases}
    target = ROOT / "old_case_referencer_audit.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake old case referencer audit: {report['summary']}")


run()
