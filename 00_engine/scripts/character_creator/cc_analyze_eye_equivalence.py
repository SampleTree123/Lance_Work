"""Audit CC eye material variants and summarize their compatibility family."""

import argparse
import collections
import hashlib
import json
import os


class AuditError(RuntimeError):
    pass


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


def write_markdown(report, path):
    lines = [
        "# CC Eye Equivalence Audit",
        "",
        "- Samples: {}/{} passed".format(
            report["passed_sample_count"], report["sample_count"]
        ),
        "- Assets: {}".format(report["asset_count"]),
        "- Material-only geometry family: {}".format(
            "yes" if report["material_only_geometry_family"] else "no"
        ),
        "- Unique eye material fingerprints: {}".format(
            report["unique_eye_material_fingerprint_count"]
        ),
        "- Unique source file SHA-256 values: {}".format(
            report["unique_source_file_sha256_count"]
        ),
        "",
        "| Asset | Male | Female | Source SHA-256 | Result |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for asset in report["assets"]:
        lines.append(
            "| {display_name} | {male_count} | {female_count} | "
            "`{source_sha256_short}` | {status} |".format(**asset)
        )
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend("- {}".format(item) for item in report["failures"])
    lines.append(
        "- Material fingerprint comparison authoritative: {}".format(
            "yes"
            if report["material_fingerprint_comparison_authoritative"]
            else "no (CC texture paths were not observable through RLPy)"
        )
    )
    if report["apparent_duplicate_material_groups"]:
        lines.extend(["", "## Apparent Duplicate Material Fingerprints", ""])
        for item in report["apparent_duplicate_material_groups"]:
            lines.append(
                "- `{}`: {}".format(
                    item["fingerprint"], ", ".join(item["asset_ids"])
                )
            )
    lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def get_eye_step(result):
    steps = (result.get("appearance_application") or {}).get("steps") or []
    eye_steps = [item for item in steps if item.get("slot") == "eyes"]
    if len(eye_steps) != 1:
        raise AuditError(
            "{} expected one eye step, found {}".format(
                result.get("preset_id"), len(eye_steps)
            )
        )
    return eye_steps[0]


def part_digests(step, key):
    return [
        item.get("geometry_digest")
        for item in step.get(key) or []
        if item.get("geometry_digest")
    ]


def eye_move_weight(result):
    return (
        (((result.get("eye_integrity") or {}).get("phases") or {}).get("final") or {})
        .get("eyeball_move", {})
        .get("weight")
    )


def check_sample(result):
    failures = []
    preset_id = result.get("preset_id") or "<unknown>"
    if result.get("success") is not True:
        failures.append("{}: validation did not succeed".format(preset_id))
    step = get_eye_step(result)
    dialog = step.get("dialog_policy") or {}
    policy = result.get("appearance_morph_policy") or {}
    before_digests = part_digests(step, "eye_part_before")
    after_digests = part_digests(step, "eye_part_after")
    eye_mesh_digest = (
        (step.get("material_after") or {}).get("mesh_digests") or {}
    ).get("CC_Base_Eye")
    material_after = step.get("material_after") or {}
    material_fingerprint_complete = (
        material_after.get("texture_count", 0) > 0
        and material_after.get("observation_error_count", 0) == 0
    )

    checks = {
        "dialog_clicked_once": dialog.get("clicked_count") == 1,
        "dialog_target_material_only": dialog.get("target_button") == "Material Only",
        "eye_geometry_preserved": step.get("eye_geometry_preserved") is True,
        "eye_geometry_digest_preserved": bool(before_digests)
        and before_digests == after_digests,
        "eye_support_preserved": step.get("eye_support_preserved") is True,
        "material_changed": step.get("material_changed") is True,
        "material_changed_only_eye_mesh": step.get("material_changed_meshes")
        == ["CC_Base_Eye"],
        "material_only_verified": step.get("material_only_verified") is True,
        "morph_policy_accepted": policy.get("status") == "accepted",
        "protected_morphs_unchanged": policy.get("protected_morphs_unchanged")
        is True,
        "no_disallowed_morph_changes": policy.get("disallowed_change_count") == 0,
        "eyeball_move_zero": eye_move_weight(result) == 0.0,
        "eye_material_fingerprint_present": bool(eye_mesh_digest),
    }
    for name, passed in checks.items():
        if not passed:
            failures.append("{}: {}".format(preset_id, name))
    return {
        "asset_id": step.get("asset_id"),
        "display_name": step.get("display_name"),
        "eye_material_fingerprint": eye_mesh_digest,
        "material_fingerprint_complete": material_fingerprint_complete,
        "resolved_path": step.get("resolved_path"),
        "failures": failures,
        "passed": not failures,
        "preset_id": preset_id,
        "sex": result.get("sex"),
    }


def analyze(validation_path, expected_male_per_asset=1, expected_female_per_asset=1):
    validation_path = os.path.realpath(os.path.abspath(validation_path))
    data = read_json(validation_path)
    samples = [check_sample(item) for item in data.get("results") or []]
    failures = [
        failure for sample in samples for failure in sample.get("failures") or []
    ]
    grouped = collections.defaultdict(list)
    for sample in samples:
        grouped[sample["asset_id"]].append(sample)

    assets = []
    fingerprint_assets = collections.defaultdict(set)
    source_hash_assets = collections.defaultdict(set)
    for asset_id, entries in sorted(grouped.items()):
        fingerprints = sorted(
            set(
                item["eye_material_fingerprint"]
                for item in entries
                if item["eye_material_fingerprint"]
            )
        )
        for fingerprint in fingerprints:
            fingerprint_assets[fingerprint].add(asset_id)
        source_paths = sorted(
            set(item["resolved_path"] for item in entries if item["resolved_path"])
        )
        source_path = source_paths[0] if len(source_paths) == 1 else None
        source_sha256 = None
        source_size_bytes = None
        if source_path and os.path.isfile(source_path):
            source_sha256 = sha256_file(source_path)
            source_size_bytes = os.path.getsize(source_path)
            source_hash_assets[source_sha256].add(asset_id)
        sexes = collections.Counter(item.get("sex") for item in entries)
        expected_pair = (
            sexes.get("male", 0) == expected_male_per_asset
            and sexes.get("female", 0) == expected_female_per_asset
        )
        consistent_material = len(fingerprints) == 1
        source_valid = len(source_paths) == 1 and source_sha256 is not None
        status = (
            "accepted"
            if expected_pair
            and consistent_material
            and source_valid
            and all(item["passed"] for item in entries)
            else "rejected"
        )
        if not expected_pair:
            failures.append(
                "{}: expected male={} and female={} samples, found male={} "
                "and female={}".format(
                    asset_id,
                    expected_male_per_asset,
                    expected_female_per_asset,
                    sexes.get("male", 0),
                    sexes.get("female", 0),
                )
            )
        if not consistent_material:
            failures.append(
                "{}: material fingerprint differs across representative faces".format(
                    asset_id
                )
            )
        if len(source_paths) != 1:
            failures.append(
                "{}: expected one stable source path, found {}".format(
                    asset_id, source_paths
                )
            )
        elif source_sha256 is None:
            failures.append(
                "{}: source file is missing: {}".format(asset_id, source_path)
            )
        assets.append(
            {
                "asset_id": asset_id,
                "display_name": entries[0].get("display_name"),
                "female_count": sexes.get("female", 0),
                "male_count": sexes.get("male", 0),
                "material_fingerprint_count": len(fingerprints),
                "material_fingerprints": fingerprints,
                "preset_ids": sorted(item["preset_id"] for item in entries),
                "source_path": source_path,
                "source_sha256": source_sha256,
                "source_sha256_short": (
                    source_sha256[:12] if source_sha256 else "missing"
                ),
                "source_size_bytes": source_size_bytes,
                "status": status,
            }
        )

    duplicate_groups = [
        {"fingerprint": fingerprint, "asset_ids": sorted(asset_ids)}
        for fingerprint, asset_ids in sorted(fingerprint_assets.items())
        if len(asset_ids) > 1
    ]
    fingerprint_comparison_authoritative = bool(samples) and all(
        item["material_fingerprint_complete"] for item in samples
    )
    expected_sample_count = len(assets) * (
        expected_male_per_asset + expected_female_per_asset
    )
    if len(samples) != expected_sample_count:
        failures.append(
            "expected {} samples for {} assets, found {}".format(
                expected_sample_count, len(assets), len(samples)
            )
        )
    material_only_family = bool(samples) and not failures and all(
        item["status"] == "accepted" for item in assets
    )
    return {
        "schema_version": 1,
        "source_validation": validation_path,
        "sample_count": len(samples),
        "passed_sample_count": sum(item["passed"] for item in samples),
        "asset_count": len(assets),
        "accepted_asset_count": sum(
            item["status"] == "accepted" for item in assets
        ),
        "unique_eye_material_fingerprint_count": len(fingerprint_assets),
        "unique_source_file_sha256_count": len(source_hash_assets),
        "source_file_duplicate_groups": [
            {"sha256": sha256, "asset_ids": sorted(asset_ids)}
            for sha256, asset_ids in sorted(source_hash_assets.items())
            if len(asset_ids) > 1
        ],
        "material_fingerprint_comparison_authoritative": (
            fingerprint_comparison_authoritative
        ),
        "apparent_duplicate_material_groups": duplicate_groups,
        "duplicate_material_groups": (
            duplicate_groups if fingerprint_comparison_authoritative else []
        ),
        "material_only_geometry_family": material_only_family,
        "failures": failures,
        "assets": assets,
        "samples": samples,
        "success": material_only_family,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md")
    parser.add_argument("--expected-male-per-asset", type=int, default=1)
    parser.add_argument("--expected-female-per-asset", type=int, default=1)
    args = parser.parse_args()
    report = analyze(
        args.validation,
        expected_male_per_asset=args.expected_male_per_asset,
        expected_female_per_asset=args.expected_female_per_asset,
    )
    write_json(report, os.path.realpath(os.path.abspath(args.output_json)))
    if args.output_md:
        write_markdown(report, os.path.realpath(os.path.abspath(args.output_md)))
    print(
        json.dumps(
            {
                "success": report["success"],
                "samples": report["sample_count"],
                "passed_samples": report["passed_sample_count"],
                "assets": report["asset_count"],
                "accepted_assets": report["accepted_asset_count"],
                "unique_material_fingerprints": report[
                    "unique_eye_material_fingerprint_count"
                ],
                "unique_source_file_sha256_values": report[
                    "unique_source_file_sha256_count"
                ],
                "duplicate_material_groups": len(
                    report["duplicate_material_groups"]
                ),
                "material_fingerprint_comparison_authoritative": report[
                    "material_fingerprint_comparison_authoritative"
                ],
                "failures": report["failures"],
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )
    if not report["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
