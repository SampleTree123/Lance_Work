"""Confirm the superseded 35-package visual pilot has no UE referencers."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(r"D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\asset_restructure_full_20260929_v1")
PILOT = "/Game/DataMake/CharacterFactory/RestructurePilot"


def run():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions()
    for name in ("include_hard_package_references", "include_soft_package_references",
                 "include_game_package_references", "include_editor_only_package_references"):
        options.set_editor_property(name, True)
    assets = registry.get_assets_by_path(PILOT, recursive=True)
    outside = {}
    for asset in assets:
        package = str(asset.package_name)
        refs = [str(value) for value in registry.get_referencers(package, options) or []]
        outside[package] = [value for value in refs if not value.startswith(PILOT + "/")]
    outside = {key: value for key, value in outside.items() if value}
    report = {"pilot_package_count": len(assets), "external_referencers": outside,
              "success": len(assets) == 35 and not outside}
    (ROOT / "pilot_cleanup_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"DataMake pilot cleanup audit: {report}")
    if not report["success"]:
        raise RuntimeError("pilot cleanup gate failed")


run()
