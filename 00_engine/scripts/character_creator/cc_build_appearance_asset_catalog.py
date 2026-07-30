"""Build a stable catalog for local Character Creator appearance assets."""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE_ROOT = r"D:\CharacterCreator_sucai\Reallusion Templates"
DEFAULT_CUSTOM_ROOT = r"D:\CharacterCreator_sucai\Reallusion Custom"
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "cc_appearance_asset_catalog_v1.json")

APPEARANCE_EXTENSIONS = {
    ".ccacc",
    ".ccavatarpreset",
    ".cccloth",
    ".cceye",
    ".ccgloves",
    ".ccshoes",
    ".ccskin",
    ".ccskingenpreset",
    ".ccteeth",
    ".rlhair",
    ".rlhairelement",
    ".rlhairstyle",
}

CLOTHING_PARTS = {
    "shirts": ("clothing", "upper"),
    "pants": ("clothing", "lower"),
    "skirts": ("clothing", "lower"),
    "coats": ("clothing", "outerwear"),
    "full-body": ("clothing", "full_body"),
    "full body": ("clothing", "full_body"),
    "underwear": ("clothing", "underwear"),
    "others": ("clothing", "clothing_other"),
}

HEAD_FIT_SLOTS = {
    "scalp_hair",
    "eyebrows",
    "facial_hair",
    "eyelashes",
    "accessory_head",
}
BODY_FIT_SLOTS = {
    "upper",
    "lower",
    "outerwear",
    "full_body",
    "underwear",
    "clothing_other",
    "footwear",
    "gloves",
    "accessory_torso",
    "accessory_arm",
    "accessory_leg",
}


class CatalogError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def normalized_relative(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def classify(relative_path, extension):
    parts = [part.casefold() for part in relative_path.replace("\\", "/").split("/")]
    part_set = set(parts)
    if extension == ".ccavatarpreset":
        rendered = "/".join(parts)
        if "eyelash" in rendered:
            return "hair", "eyelashes"
        raise CatalogError(
            "Unsupported appearance AvatarPreset: {}".format(relative_path)
        )
    if extension in {".rlhair", ".rlhairelement", ".rlhairstyle"}:
        rendered = "/".join(parts)
        if "eyebrow" in rendered or "brow" in part_set:
            return "hair", "eyebrows"
        if any(label in rendered for label in ("beard", "mustache", "moustache", "goatee")):
            return "hair", "facial_hair"
        if "eyelash" in rendered or "lash" in part_set:
            return "hair", "eyelashes"
        return "hair", "scalp_hair"
    if extension == ".ccshoes":
        return "clothing", "footwear"
    if extension == ".ccgloves":
        return "clothing", "gloves"
    if extension == ".cccloth":
        for name, classification in CLOTHING_PARTS.items():
            if name in part_set:
                return classification
        return "clothing", "clothing_other"
    if extension == ".ccacc":
        if "head" in part_set:
            return "accessory", "accessory_head"
        if "torso" in part_set:
            return "accessory", "accessory_torso"
        if "arm" in part_set:
            return "accessory", "accessory_arm"
        if "leg" in part_set:
            return "accessory", "accessory_leg"
        return "accessory", "accessory_other"
    if extension == ".cceye":
        return "anatomy", "eyes"
    if extension == ".ccteeth":
        return "anatomy", "teeth"
    if extension == ".ccskin":
        return "skin", "skin"
    if extension == ".ccskingenpreset":
        if "makeup" in part_set:
            return "makeup", "makeup"
        return "skin", "skin_preset"
    raise CatalogError("Unsupported appearance extension: {}".format(extension))


def infer_sex(relative_path):
    rendered = relative_path.replace("\\", "/").casefold()
    tokens = set(filter(None, re.split(r"[^a-z0-9]+", rendered)))
    if "unisex" in tokens:
        return "unisex"
    female = bool(tokens.intersection({"f", "female", "females", "woman", "women", "girl"}))
    male = bool(tokens.intersection({"m", "male", "males", "man", "men", "boy"}))
    if female and not male:
        return "female"
    if male and not female:
        return "male"
    return "unknown"


def fit_requirement(slot):
    return {
        "body_fit": "unverified" if slot in BODY_FIT_SLOTS else "not_applicable",
        "head_fit": "unverified" if slot in HEAD_FIT_SLOTS else "not_applicable",
    }


def audit_index(path, audit):
    if not audit:
        return None
    return audit.get(os.path.normcase(os.path.realpath(path)))


def load_audit(path):
    if not path:
        return {}, None
    path = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(path):
        raise CatalogError("Audit file is missing: {}".format(path))
    document = read_json(path)
    index = {}
    for item in document.get("assets") or []:
        source = item.get("source")
        if source:
            index[os.path.normcase(os.path.realpath(source))] = item
    return index, {
        "path": path,
        "created_at": document.get("created_at"),
        "schema_version": document.get("schema_version"),
        "asset_count": document.get("asset_count"),
    }


def discover(root, origin, audit):
    root = os.path.realpath(os.path.abspath(root))
    if not os.path.isdir(root):
        raise CatalogError("Appearance root is missing: {}".format(root))
    items = []
    for current_root, unused_dirs, files in os.walk(root):
        for filename in files:
            extension = os.path.splitext(filename)[1].casefold()
            if extension not in APPEARANCE_EXTENSIONS:
                continue
            path = os.path.join(current_root, filename)
            relative = normalized_relative(path, root)
            if (
                extension == ".ccavatarpreset"
                and "eyelash" not in relative.replace("\\", "/").casefold()
            ):
                continue
            asset_type, slot = classify(relative, extension)
            audited = audit_index(path, audit)
            content_id = (audited or {}).get("content_id") or {}
            items.append(
                {
                    "origin": origin,
                    "root": root,
                    "path": os.path.realpath(path),
                    "relative_path": relative,
                    "extension": extension,
                    "bytes": os.path.getsize(path),
                    "asset_type": asset_type,
                    "slot": slot,
                    "asset_form": {
                        ".ccavatarpreset": "preset",
                        ".rlhair": "group",
                        ".rlhairelement": "element",
                        ".rlhairstyle": "style",
                    }.get(extension, "asset"),
                    "audit": {
                        "available": audited is not None,
                        "database_indexed": (audited or {}).get("database_indexed"),
                        "content_id_registered": content_id.get("registered"),
                        "content_id": content_id.get("value"),
                    },
                }
            )
    items.sort(key=lambda item: (item["relative_path"].casefold(), item["origin"]))
    return items


def logical_key(item):
    return item["relative_path"].replace("\\", "/").casefold()


def asset_id(slot, key):
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    slot_label = re.sub(r"[^A-Z0-9]+", "_", slot.upper()).strip("_")
    return "CCAPP_{}_{}".format(slot_label, digest)


def make_asset(key, variants):
    variants = sorted(variants, key=lambda item: (item["origin"] != "custom", item["path"].casefold()))
    preferred = variants[0]
    origins = sorted({item["origin"] for item in variants})
    fit = fit_requirement(preferred["slot"])
    return {
        "asset_id": asset_id(preferred["slot"], key),
        "display_name": os.path.splitext(os.path.basename(preferred["path"]))[0],
        "asset_type": preferred["asset_type"],
        "slot": preferred["slot"],
        "asset_form": preferred["asset_form"],
        "extension": preferred["extension"],
        "sex_hint": infer_sex(preferred["relative_path"]),
        "logical_relative_path": preferred["relative_path"],
        "preferred_origin": preferred["origin"],
        "preferred_path": preferred["path"],
        "source_origins": origins,
        "has_template_and_custom_variants": origins == ["custom", "template"],
        "fit_requirements": fit,
        "compatibility": {
            "bodyfit_ids": [],
            "headfit_ids": [],
            "review_status": "unverified"
            if "unverified" in fit.values()
            else "not_required",
        },
        "automation_status": "component-only"
        if preferred["asset_form"] == "element"
        else "candidate",
        "visual_review_status": "pending",
        "license_status": "prototype-only",
        "variants": variants,
    }


def summarize(assets, physical_count):
    slot_counts = collections.Counter(item["slot"] for item in assets)
    type_counts = collections.Counter(item["asset_type"] for item in assets)
    sex_counts = collections.Counter(item["sex_hint"] for item in assets)
    origin_counts = collections.Counter(item["preferred_origin"] for item in assets)
    return {
        "logical_asset_count": len(assets),
        "physical_file_count": physical_count,
        "template_and_custom_pair_count": sum(
            1 for item in assets if item["has_template_and_custom_variants"]
        ),
        "counts_by_asset_type": dict(sorted(type_counts.items())),
        "counts_by_slot": dict(sorted(slot_counts.items())),
        "counts_by_sex_hint": dict(sorted(sex_counts.items())),
        "counts_by_preferred_origin": dict(sorted(origin_counts.items())),
        "unverified_fit_count": sum(
            1 for item in assets if item["compatibility"]["review_status"] == "unverified"
        ),
    }


def build_catalog(template_root, custom_root, output_path, audit_path=None):
    output_path = os.path.realpath(os.path.abspath(output_path))
    audit, audit_source = load_audit(audit_path)
    physical = []
    physical.extend(discover(template_root, "template", audit))
    physical.extend(discover(custom_root, "custom", audit))
    grouped = collections.defaultdict(list)
    for item in physical:
        grouped[logical_key(item)].append(item)
    assets = [make_asset(key, grouped[key]) for key in sorted(grouped)]
    assets.sort(key=lambda item: (item["slot"], item["display_name"].casefold(), item["asset_id"]))

    catalog = {
        "schema_version": 1,
        "catalog_id": "cc_appearance_assets_v1",
        "generated_at": now(),
        "roots": {
            "template": os.path.realpath(os.path.abspath(template_root)),
            "custom": os.path.realpath(os.path.abspath(custom_root)),
        },
        "audit_source": audit_source,
        "policy": {
            "spec_reference": "asset_id_only",
            "arbitrary_paths_allowed": False,
            "preferred_origin_order": ["custom", "template"],
            "default_license_status": "prototype-only",
            "compatibility_requires_cc_validation": True,
        },
        "summary": summarize(assets, len(physical)),
        "candidate_pools": {
            slot: [
                item["asset_id"]
                for item in assets
                if item["slot"] == slot and item["automation_status"] == "candidate"
            ]
            for slot in sorted({item["slot"] for item in assets})
        },
        "component_pools": {
            slot: [
                item["asset_id"]
                for item in assets
                if item["slot"] == slot and item["automation_status"] == "component-only"
            ]
            for slot in sorted({item["slot"] for item in assets})
            if any(
                item["slot"] == slot and item["automation_status"] == "component-only"
                for item in assets
            )
        },
        "assets": assets,
    }
    write_json(catalog, output_path)
    return {
        "success": True,
        "output": output_path,
        "catalog_id": catalog["catalog_id"],
        "summary": catalog["summary"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-root", default=DEFAULT_TEMPLATE_ROOT)
    parser.add_argument("--custom-root", default=DEFAULT_CUSTOM_ROOT)
    parser.add_argument("--audit")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(
        json.dumps(
            build_catalog(
                args.template_root,
                args.custom_root,
                args.output,
                audit_path=args.audit,
            ),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
