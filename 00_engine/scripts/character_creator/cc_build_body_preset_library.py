"""Promote validated CC5 body projects into a canonical BodyFit library."""

import argparse
import datetime
import hashlib
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "cc_build_body_preset_library_config.json")
EXPECTED_IDS = (
    "M01_Lean", "M02_Average", "M03_Athletic", "M04_Heavy",
    "F01_Lean", "F02_Average", "F03_Athletic", "F04_Heavy",
)


class BuildError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


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


def vector_fingerprint(entries):
    canonical = json.dumps(
        [
            (item["id"], round(float(item["weight"]), 8))
            for item in sorted(entries, key=lambda value: value["id"])
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def require_file(path, label):
    resolved = os.path.realpath(os.path.abspath(path))
    if not os.path.isfile(resolved):
        raise BuildError("{} is missing: {}".format(label, resolved))
    return resolved


def canonical_entries(entries, expected_classification):
    if not isinstance(entries, list):
        raise BuildError("Morph entries must be a list")
    result = []
    seen = set()
    for source in entries:
        morph_id = source.get("id")
        if not isinstance(morph_id, str) or not morph_id:
            raise BuildError("Morph entry has no stable id")
        if morph_id in seen:
            raise BuildError("Duplicate morph id: {}".format(morph_id))
        seen.add(morph_id)
        if source.get("classification") != expected_classification:
            raise BuildError(
                "Morph {} is not classified as {}".format(
                    morph_id, expected_classification
                )
            )
        result.append(
            {
                "id": morph_id,
                "display": str(source.get("display") or morph_id),
                "categories": [str(item) for item in source.get("categories", [])],
                "classification": expected_classification,
                "weight": float(source["weight"]),
                "minimum": source.get("minimum"),
                "maximum": source.get("maximum"),
            }
        )
    return sorted(result, key=lambda value: value["id"])


def neutral_bases(face_library):
    bases = {}
    for seed in face_library.get("seeds", []):
        sex = seed.get("sex")
        if sex not in ("male", "female") or seed.get("source_head_preset") is not None:
            continue
        base = seed.get("base_avatar")
        if not isinstance(base, dict) or not base.get("path") or not base.get("sha256"):
            continue
        value = {"path": base["path"], "sha256": base["sha256"]}
        if sex in bases and bases[sex] != value:
            raise BuildError("Neutral base definitions disagree for {}".format(sex))
        bases[sex] = value
    if set(bases) != {"male", "female"}:
        raise BuildError("Face library does not define both neutral bases")
    return bases


def build_library(config_path):
    config_path = require_file(config_path, "Build config")
    config = read_json(config_path)
    if int(config.get("schema_version", -1)) != 1:
        raise BuildError("Unsupported build config schema")
    configured = config.get("presets")
    configured_ids = [item.get("preset_id") for item in configured or []]
    if tuple(configured_ids) != EXPECTED_IDS:
        raise BuildError("Body presets must use the canonical eight-ID order")
    body_application_mode = config.get("body_application_mode")
    if body_application_mode != "source_project":
        raise BuildError(
            "Canonical BodyFit library must use source_project application"
        )
    expected_eyeball_move_weight = float(
        config.get("expected_eyeball_move_weight", 0.0)
    )

    summary_path = require_file(
        config["source_validation_result"], "Source validation result"
    )
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise BuildError("Source body validation did not succeed")
    if int(summary.get("unique_body_vector_count", -1)) != len(EXPECTED_IDS):
        raise BuildError("Source validation does not contain eight unique bodies")

    face_library_path = require_file(config["face_seed_library"], "Face seed library")
    face_library = read_json(face_library_path)
    bases = neutral_bases(face_library)
    summary_results = dict(
        (item["preset_id"], item) for item in summary.get("results", [])
    )
    run_dir = os.path.dirname(summary_path)
    presets = []
    discarded_faces = {}

    for metadata in configured:
        preset_id = metadata["preset_id"]
        source_summary = summary_results.get(preset_id)
        if not source_summary or source_summary.get("success") is not True:
            raise BuildError("Missing successful validation for {}".format(preset_id))
        if source_summary.get("sex") != metadata["sex"]:
            raise BuildError("Sex mismatch for {}".format(preset_id))
        if source_summary.get("body_class") != metadata["body_class"]:
            raise BuildError("Body class mismatch for {}".format(preset_id))

        preset_dir = os.path.join(run_dir, "presets", preset_id)
        source_result_path = require_file(
            os.path.join(preset_dir, "result.json"), "Preset source result"
        )
        vectors_path = require_file(
            source_summary["artifacts"]["vectors"], "Preset morph vectors"
        )
        source_result = read_json(source_result_path)
        vectors = read_json(vectors_path)
        if source_result.get("success") is not True:
            raise BuildError("Preset inspection failed for {}".format(preset_id))

        groups = vectors.get("groups") or {}
        body = canonical_entries((groups.get("body") or {}).get("entries"), "body")
        junction = canonical_entries(
            (groups.get("junction") or {}).get("entries"), "junction"
        )
        if not body:
            raise BuildError("{} has no body morphs".format(preset_id))
        if set(item["id"] for item in body) & set(item["id"] for item in junction):
            raise BuildError("{} has overlapping body and junction morphs".format(preset_id))
        combined_fingerprint = vector_fingerprint(body + junction)
        if combined_fingerprint != source_summary["body_vector_fingerprint"]:
            raise BuildError("{} BodyFit fingerprint mismatch".format(preset_id))

        project_path = require_file(source_result["source_project"], "Source project")
        project_sha256 = sha256_file(project_path)
        project_bytes = os.path.getsize(project_path)
        if project_sha256 != source_result["source_sha256"]:
            raise BuildError(
                "{} source project changed since validation".format(preset_id)
            )
        if project_bytes != int(source_result["source_bytes"]):
            raise BuildError(
                "{} source project size changed since validation".format(preset_id)
            )
        preview_path = require_file(source_summary["artifacts"]["preview"], "Source preview")
        face_count = int((groups.get("face") or {}).get("nonzero_count", 0))
        discarded_faces[preset_id] = face_count
        presets.append(
            {
                "preset_id": preset_id,
                "sex": metadata["sex"],
                "body_class": metadata["body_class"],
                "review_status": metadata.get("review_status", "accepted"),
                "base_avatar": bases[metadata["sex"]],
                "source_project": {
                    "path": project_path,
                    "sha256": project_sha256,
                    "bytes": project_bytes,
                    "modified_at": source_result["source_modified_at"],
                },
                "source_preview": {
                    "path": preview_path,
                    "sha256": sha256_file(preview_path),
                },
                "source_all_morph_fingerprint": vectors["all_fingerprint_sha256"],
                "source_face_morph_count_discarded": face_count,
                "target_body_morphs": body,
                "target_junction_morphs": junction,
                "body_morph_count": len(body),
                "junction_morph_count": len(junction),
                "body_only_fingerprint": vector_fingerprint(body),
                "junction_fingerprint": vector_fingerprint(junction),
                "body_and_junction_fingerprint": combined_fingerprint,
            }
        )

    fingerprints = [item["body_and_junction_fingerprint"] for item in presets]
    if len(set(fingerprints)) != len(EXPECTED_IDS):
        raise BuildError("Canonical BodyFit fingerprints are not unique")
    library = {
        "schema_version": 1,
        "library_id": config["library_id"],
        "generated_at": now(),
        "status": "validated-source-projects",
        "style_scope": config["style_scope"],
        "body_application_mode": body_application_mode,
        "expected_eyeball_move_weight": expected_eyeball_move_weight,
        "source_validation": {
            "result": summary_path,
            "run_id": summary["run_id"],
            "result_sha256": sha256_file(summary_path),
        },
        "face_seed_library": {
            "path": face_library_path,
            "library_id": face_library.get("library_id"),
            "sha256": sha256_file(face_library_path),
        },
        "preview_lightroom": config.get("preview_lightroom"),
        "ownership": {
            "body": (
                "BodyFit loads the hash-locked source project as the canonical "
                "body state."
            ),
            "junction": "Junction morphs remain separate pending HeadFit ownership.",
            "face": (
                "Source-project face state is only an initialization state and "
                "must be replaced by the selected primary head preset and face "
                "identity recipe."
            ),
        },
        "technical_validation": {
            "success": True,
            "preset_count": len(presets),
            "canonical_source_project_count": len(presets),
            "canonical_source_project_bytes": sum(
                item["source_project"]["bytes"] for item in presets
            ),
            "canonical_source_projects_hash_locked": True,
            "male_count": sum(item["sex"] == "male" for item in presets),
            "female_count": sum(item["sex"] == "female" for item in presets),
            "unique_body_fingerprint_count": len(set(fingerprints)),
            "discarded_source_face_morph_counts": discarded_faces,
        },
        "compliance": face_library.get("compliance", {}),
        "presets": presets,
    }
    output_path = os.path.realpath(os.path.abspath(config["output_library"]))
    write_json(library, output_path)
    return {
        "success": True,
        "library_id": library["library_id"],
        "output_library": output_path,
        "preset_count": len(presets),
        "unique_body_fingerprint_count": len(set(fingerprints)),
        "discarded_source_face_morph_counts": discarded_faces,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(
        json.dumps(
            build_library(os.path.abspath(args.config)),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
