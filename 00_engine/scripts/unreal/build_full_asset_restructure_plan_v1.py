"""Build a deterministic, read-only migration map for imported wardrobe and hair.

The map includes only selected runtime meshes and their audited local dependency
closure. No Unreal assets are changed by this script.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ENGINE = Path(r"D:\UE\Lance_Work\00_engine")
SOURCE = Path(r"D:\UE\exports\character_creator\wardrobe_average_20260906_v1\manifests\v3\wardrobe_registry.json")
AUDIT_ROOT = ENGINE / "outputs/unreal_character_import/asset_restructure_pilot_20260928_v1"
OUT = ENGINE / "outputs/unreal_character_import/asset_restructure_full_20260929_v1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(value):
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value or "Module"


def object_path(package):
    return package + "." + package.rsplit("/", 1)[-1]


def unique_package(base, old_package, occupied):
    candidate = base
    if candidate in occupied and occupied[candidate] != old_package:
        candidate = base + "_" + hashlib.sha1(old_package.encode()).hexdigest()[:8]
    if candidate in occupied and occupied[candidate] != old_package:
        raise ValueError(f"destination collision: {candidate}")
    occupied[candidate] = old_package
    return candidate


def main():
    source = read(SOURCE)
    inventory_path = AUDIT_ROOT / "full_import_inventory.json"
    audit_path = AUDIT_ROOT / "full_dependency_audit.json"
    inventory, audit = read(inventory_path), read(audit_path)
    units = {row["unit_id"]: row for row in source["units"]}
    inventory_cases = {row["case_root"]: row for key in ("wardrobe_cases", "hair_cases") for row in inventory[key]}
    assert len(inventory_cases) == 365 and len(audit["cases"]) == 365
    assert set(inventory_cases) == {row["case_root"] for row in audit["cases"]}
    occupied_roots, occupied_packages = {}, {}
    cases = []
    for row in audit["cases"]:
        old_root = row["case_root"]
        src_case = inventory_cases[old_root]
        if row["kind"] == "hair":
            hair_key = re.search(r"(HB[123]_\d\d)_Interchange$", old_root).group(1)
            base = f"/Game/DataMake/CharacterFactory/Hair/{hair_key}"
            labels = [hair_key]
        else:
            unit = units[row["id"]]
            parts = old_root.split("/")
            # Vendor/CC5/Wardrobe/<sex>/Average/<family>/<slot>/<case id>
            assert parts[2:5] == ["Vendor", "Reallusion", "CC5"]
            sex = "Female" if unit["sex"] == "female" else "Male"
            family, slot = parts[-3:-1]
            labels = [module["display_name"] for module in unit["modules"]]
            name = slug(labels[0]) if len(labels) == 1 else "Bundle_" + slug(labels[0])
            base = f"/Game/DataMake/CharacterFactory/Wardrobe/{sex}/{slug(family)}/{slug(slot)}/{name}"
        root = base
        if root in occupied_roots:
            root = base + "_" + hashlib.sha1(old_root.encode()).hexdigest()[:8]
        if root in occupied_roots:
            raise ValueError(f"root collision: {root}")
        occupied_roots[root] = old_root
        assets = []
        for item in row["local_dependencies"]:
            kind = item["class"]
            folder = {"Texture2D": "Textures", "MaterialInstanceConstant": "Materials", "SubsurfaceProfile": "Profiles"}.get(kind)
            if folder is None:
                raise ValueError(f"unsupported local asset: {item}")
            old_package = item["package"]
            target = unique_package(root + "/" + folder + "/" + old_package.rsplit("/", 1)[-1], old_package, occupied_packages)
            assets.append({"class": kind, "old": object_path(old_package), "new": object_path(target)})
        for item in src_case["selected_meshes"]:
            old = item["path"]
            old_package = old.rsplit(".", 1)[0]
            target = unique_package(root + "/Meshes/" + old_package.rsplit("/", 1)[-1], old_package, occupied_packages)
            assets.append({"class": "SkeletalMesh", "old": old, "new": object_path(target)})
        cases.append({"kind": row["kind"], "id": row["id"], "old_root": old_root,
                      "new_root": root, "labels": labels, "assets": assets})
    classes = Counter(asset["class"] for case in cases for asset in case["assets"])
    assert len(cases) == 365 and classes["SkeletalMesh"] == 506
    result = {"schema_version": 1, "scope": "full_wardrobe_hair_selected_runtime_assets",
              "inputs": {str(path): digest(path) for path in (SOURCE, inventory_path, audit_path)},
              "summary": {"cases": len(cases), "classes": dict(sorted(classes.items())),
                          "total_assets": sum(classes.values())}, "cases": cases}
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "migration_plan.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"plan": str(target), **result["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
