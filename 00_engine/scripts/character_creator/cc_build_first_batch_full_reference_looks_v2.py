"""Build revision 2 of the 16 frozen FullReference Looks."""

import argparse
import copy
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IDENTITY_LIBRARY = os.path.join(
    SCRIPT_DIR, "cc_first_batch_identity_library_20260820_v1.json"
)
DEFAULT_OUTFIT_GATE = os.path.join(
    SCRIPT_DIR, "cc_outfit_compatibility_gate_20260816_v3.json"
)
DEFAULT_IDENTITY_ROOT = os.path.join(
    r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts",
    "first_batch_identity_assembly",
    "run_20260820_v1",
)
DEFAULT_EXPORT_ROOT = r"D:\UE\exports\character_creator\first_data_batch_20260820_v1"
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_first_batch_full_reference_looks_20260820_v2.json"
)

OUTFIT_ROWS = {
    "female": (
        ("O01", "female.summer_girl_four_colors::default"),
        ("O02", "female.jumpsuits_accessories::default"),
        ("O03", "female.dress_collection::full_body"),
        ("O04", "female.streetwear_collection::pants_with_windbreaker"),
    ),
    "male": (
        ("O01", "male.casual_01_04::default"),
        ("O02", "male.dash::default"),
        ("O03", "male.white_tie::default"),
        ("O04", "male.1920s_collection::separates"),
    ),
}

RING = {
    "01": ("O01", "O02"),
    "02": ("O02", "O03"),
    "03": ("O03", "O04"),
    "04": ("O04", "O01"),
}

OUTFIT_ASSET_OVERRIDES = {
    ("female", "O04"): {
        "override_id": "female_o04_casual_jacket_c_20260820",
        "slots": {
            "coats": {
                "asset_id": "female.streetwear_collection.asset.61567c93b0f3",
                "cloth_options_policy": "keep_cloth_shape",
                "display_name": "CasualJacket_C",
                "path": os.path.join(
                    r"D:\BaiduNetdiskDownload",
                    "\u4eba\u7269\u548c\u670d\u88c5_newest50pct_sorted",
                    "female",
                    "\u6f6e\u724c\u670d\u88c5",
                    "Coats",
                    "CasualJacket_C.ccCloth",
                ),
                "sha256": (
                    "978b11a02c72f3a0ef293fd82934112aa"
                    "177012459ac61075ea3fad0dd5444a2"
                ),
                "size_bytes": 10652105,
                "slot": "coats",
                "source": "family_override",
            }
        },
    }
}


class FirstBatchLookBuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def canonical_path(path):
    return os.path.realpath(os.path.abspath(path))


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(temporary, path)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_record(path, verify=True):
    path = canonical_path(path)
    if not verify:
        return {"path": path, "sha256": "0" * 64, "size_bytes": 1}
    if not os.path.isfile(path):
        raise FirstBatchLookBuildError(
            "Identity project is missing: {}".format(path)
        )
    return {
        "path": path,
        "sha256": sha256_file(path),
        "size_bytes": os.path.getsize(path),
    }


def selected_asset_signature(preset):
    return [
        (
            item.get("asset_id"),
            item.get("slot"),
            item.get("sha256"),
            item.get("cloth_options_policy"),
        )
        for item in preset.get("selected_assets") or []
    ]


def apply_asset_overrides(sex, outfit_id, selected_assets):
    assets = copy.deepcopy(selected_assets)
    override = OUTFIT_ASSET_OVERRIDES.get((sex, outfit_id))
    if not override:
        return assets, None

    for slot, replacement in override["slots"].items():
        indices = [
            index
            for index, item in enumerate(assets)
            if item.get("slot") == slot
        ]
        if len(indices) != 1:
            raise FirstBatchLookBuildError(
                "Expected exactly one {} asset for {} {}".format(
                    slot, sex, outfit_id
                )
            )
        path = canonical_path(replacement["path"])
        if not os.path.isfile(path):
            raise FirstBatchLookBuildError(
                "Outfit override asset is missing: {}".format(path)
            )
        if os.path.getsize(path) != replacement["size_bytes"]:
            raise FirstBatchLookBuildError(
                "Outfit override size changed: {}".format(path)
            )
        if sha256_file(path) != replacement["sha256"]:
            raise FirstBatchLookBuildError(
                "Outfit override hash changed: {}".format(path)
            )
        replacement = copy.deepcopy(replacement)
        replacement["path"] = path
        assets[indices[0]] = replacement
    return assets, override["override_id"]


def build(
    identity_library_path,
    outfit_gate_path,
    identity_root,
    export_root,
    verify_identity_projects=True,
    identity_outfit_map=None,
    document_id="cc_first_batch_full_reference_looks_20260820_v2",
):
    identity_library_path = canonical_path(identity_library_path)
    outfit_gate_path = canonical_path(outfit_gate_path)
    identity_root = canonical_path(identity_root)
    export_root = canonical_path(export_root)
    identities = read_json(identity_library_path)
    outfit_gate = read_json(outfit_gate_path)

    identity_rows = identities.get("presets") or []
    if len(identity_rows) != 8:
        raise FirstBatchLookBuildError("First-batch identity library must contain 8")
    identity_by_id = {item.get("preset_id"): item for item in identity_rows}
    if len(identity_by_id) != 8 or None in identity_by_id:
        raise FirstBatchLookBuildError("Identity IDs are invalid or duplicated")

    outfit_presets = outfit_gate.get("presets") or []
    source_by_look = {}
    for sex, rows in OUTFIT_ROWS.items():
        for outfit_id, look_id in rows:
            candidates = [
                item
                for item in outfit_presets
                if item.get("sex") == sex and item.get("look_id") == look_id
            ]
            if not candidates:
                raise FirstBatchLookBuildError(
                    "Validated outfit Look is missing: {}".format(look_id)
                )
            signatures = {tuple(selected_asset_signature(item)) for item in candidates}
            if len(signatures) != 1:
                raise FirstBatchLookBuildError(
                    "Outfit assets vary across validated BodyFits: {}".format(
                        look_id
                    )
                )
            source_by_look[(sex, outfit_id)] = candidates[0]

    identity_outfit_map = identity_outfit_map or RING
    presets = []
    look_rows = []
    for identity_id in sorted(identity_by_id):
        identity = identity_by_id[identity_id]
        sex = identity.get("sex")
        if sex not in OUTFIT_ROWS:
            raise FirstBatchLookBuildError(
                "Identity has invalid sex: {}".format(identity_id)
            )
        suffix = identity_id[-2:]
        if suffix not in identity_outfit_map:
            raise FirstBatchLookBuildError(
                "Identity cannot be mapped into the ring: {}".format(identity_id)
            )
        identity_project = os.path.join(
            identity_root, identity_id, identity_id + ".ccProject"
        )
        identity_project_record = source_record(
            identity_project, verify=verify_identity_projects
        )
        for outfit_id in identity_outfit_map[suffix]:
            source = source_by_look[(sex, outfit_id)]
            selected_assets, outfit_override_id = apply_asset_overrides(
                sex, outfit_id, source["selected_assets"]
            )
            look_id = "{}_{}".format(identity_id, outfit_id)
            export_basename = "CC_FB_{}".format(look_id)
            preset = {
                "base_avatar": copy.deepcopy(identity.get("base_avatar")),
                "bodyfit_id": identity.get("bodyfit_id"),
                "capture_views": [
                    {"view_id": "front", "yaw_degrees": 0.0}
                ],
                "case_id": "first_batch::{}".format(look_id),
                "expected_image_count": 1,
                "first_batch_identity_id": identity_id,
                "first_batch_outfit_id": outfit_id,
                "footwear_selection": copy.deepcopy(
                    source.get("footwear_selection")
                ),
                "look_id": look_id,
                "preset_id": look_id,
                "production_output": {
                    "export_basename": export_basename,
                    "export_root": os.path.join(
                        export_root, "full_reference", look_id
                    ),
                    "export_timeout_seconds": 900.0,
                    "project_path": os.path.join(
                        export_root,
                        "projects",
                        look_id + ".ccProject",
                    ),
                    "skip_preview_capture": True,
                },
                "outfit_asset_override_id": outfit_override_id,
                "selected_assets": selected_assets,
                "sex": sex,
                "source_project": identity_project_record,
                "source_validated_look_id": source.get("look_id"),
                "subject_id": identity_id,
            }
            presets.append(preset)
            look_rows.append(
                {
                    "bodyfit_id": identity.get("bodyfit_id"),
                    "identity_id": identity_id,
                    "look_id": look_id,
                    "outfit_id": outfit_id,
                    "outfit_asset_override_id": outfit_override_id,
                    "sex": sex,
                    "source_validated_look_id": source.get("look_id"),
                }
            )

    expected_look_count = sum(
        len(identity_outfit_map[item["preset_id"][-2:]]) for item in identity_rows
    )
    if (
        len(presets) != expected_look_count
        or len({item["look_id"] for item in presets}) != expected_look_count
    ):
        raise FirstBatchLookBuildError(
            "First-batch matrix must produce {} Looks".format(expected_look_count)
        )

    execution_policy = copy.deepcopy(outfit_gate.get("execution_policy") or {})
    execution_policy.update(
        {
            "asset_load_after_seconds": 2.5,
            "asset_load_before_seconds": 0.5,
            "checkpoint_after_each_case": True,
            "coats_load_after_seconds": 4.0,
            "continue_after_visual_or_load_failure": False,
            "project_load_settle_seconds": 12.0,
            "record_asset_load_undo": False,
            "remove_existing_clothing_before_apply": True,
            "remove_source_accessories": True,
            "stop_on_blocking_dialog": True,
        }
    )
    document = {
        "capture_policy": {
            "framing": "full_body_centered_with_fixed_margin",
            "neutral_pose_required": True,
            "resolution": [640, 640],
            "transparent_background": False,
            "views": [{"view_id": "front", "yaw_degrees": 0.0}],
        },
        "counts": {
            "identity_count": 8,
            "look_count": expected_look_count,
            "looks_per_identity": expected_look_count // 8,
            "outfit_count": 8,
        },
        "diagnostic_mode": "outfit_compatibility_gate",
        "execution_policy": execution_policy,
        "full_body_camera": outfit_gate["full_body_camera"],
        "generated_at": now(),
        "gate_id": document_id,
        "library_id": document_id,
        "look_rows": look_rows,
        "presets": presets,
        "preview_lightroom": outfit_gate["preview_lightroom"],
        "preview_resolution": [640, 640],
        "schema_version": 1,
        "source_identity_library": {
            "path": identity_library_path,
            "sha256": sha256_file(identity_library_path),
        },
        "source_outfit_gate": {
            "path": outfit_gate_path,
            "sha256": sha256_file(outfit_gate_path),
        },
        "status": (
            "ready-for-cc-production"
            if verify_identity_projects
            else "planned-awaiting-identity-projects"
        ),
    }
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-library", default=DEFAULT_IDENTITY_LIBRARY)
    parser.add_argument("--outfit-gate", default=DEFAULT_OUTFIT_GATE)
    parser.add_argument("--identity-root", default=DEFAULT_IDENTITY_ROOT)
    parser.add_argument("--export-root", default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_path = canonical_path(args.output)
    document = build(
        args.identity_library,
        args.outfit_gate,
        args.identity_root,
        args.export_root,
        verify_identity_projects=True,
    )
    write_json(document, output_path)
    print(
        json.dumps(
            {
                "look_count": document["counts"]["look_count"],
                "output": output_path,
                "status": document["status"],
                "success": True,
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
