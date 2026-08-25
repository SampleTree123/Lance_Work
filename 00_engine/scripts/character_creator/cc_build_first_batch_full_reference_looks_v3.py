"""Build the complete 32-Look first-batch identity/outfit matrix.

The existing v2 ring remains the frozen source of the first 16 Looks. This
builder expands each of the eight identities to all four same-sex outfits and
also emits a delta manifest containing only the 16 missing combinations.
"""

import argparse
import copy
import json
import os

import cc_build_first_batch_full_reference_looks_v2 as v2


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_first_batch_full_reference_looks_20260822_v3.json"
)
DEFAULT_DELTA_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_first_batch_full_reference_missing_looks_20260822_v1.json"
)
DEFAULT_MATRIX_OUTPUT = os.path.join(
    SCRIPT_DIR, "cc_first_batch_look_matrix_20260822_v1.json"
)
DEFAULT_EXISTING_CONFIG = os.path.join(
    SCRIPT_DIR, "cc_first_batch_full_reference_looks_20260820_v2.json"
)
DEFAULT_IDENTITY_ROOT = os.path.join(
    SCRIPT_DIR, "runtime_assets", "first_batch_identities_20260820_v1"
)

FULL_MATRIX = {
    "01": ("O01", "O02", "O03", "O04"),
    "02": ("O01", "O02", "O03", "O04"),
    "03": ("O01", "O02", "O03", "O04"),
    "04": ("O01", "O02", "O03", "O04"),
}


def build_delta(full_document, existing_config_path):
    existing = v2.read_json(existing_config_path)
    existing_ids = {item["look_id"] for item in existing.get("presets") or []}
    full_ids = {item["look_id"] for item in full_document["presets"]}
    if len(existing_ids) != 16 or not existing_ids < full_ids:
        raise v2.FirstBatchLookBuildError(
            "Existing v2 config must be a strict 16-Look subset of the full matrix"
        )

    missing_ids = sorted(full_ids - existing_ids)
    if len(missing_ids) != 16:
        raise v2.FirstBatchLookBuildError(
            "Complete matrix must contain exactly 16 missing Looks"
        )

    delta = copy.deepcopy(full_document)
    delta["gate_id"] = "cc_first_batch_full_reference_missing_looks_20260822_v1"
    delta["library_id"] = delta["gate_id"]
    delta["status"] = "ready-for-cc-production-missing-looks-only"
    delta["presets"] = [
        item for item in delta["presets"] if item["look_id"] in missing_ids
    ]
    delta["look_rows"] = [
        item for item in delta["look_rows"] if item["look_id"] in missing_ids
    ]
    delta["counts"] = {
        "identity_count": 8,
        "look_count": 16,
        "looks_per_identity": 2,
        "outfit_count": 8,
    }
    delta["matrix_context"] = {
        "complete_matrix_look_count": 32,
        "existing_look_count": 16,
        "missing_look_count": 16,
        "existing_config": v2.source_record(existing_config_path),
        "existing_look_ids": sorted(existing_ids),
        "missing_look_ids": missing_ids,
    }
    return delta, sorted(existing_ids), missing_ids


def build_matrix_document(full_document, existing_ids, missing_ids):
    rows = []
    existing_set = set(existing_ids)
    for item in full_document["look_rows"]:
        row = copy.deepcopy(item)
        row["matrix_state"] = (
            "frozen_existing" if row["look_id"] in existing_set else "export_required"
        )
        rows.append(row)
    return {
        "schema_version": 1,
        "matrix_id": "cc_first_batch_look_matrix_20260822_v1",
        "generated_at": v2.now(),
        "status": "missing-16-ready-for-cc-production",
        "policy": {
            "same_sex_outfits_only": True,
            "identity_count_per_sex": 4,
            "outfit_count_per_sex": 4,
            "looks_per_identity": 4,
            "preserve_existing_exports": True,
        },
        "counts": {
            "total": 32,
            "existing": len(existing_ids),
            "export_required": len(missing_ids),
        },
        "existing_look_ids": existing_ids,
        "missing_look_ids": missing_ids,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-library", default=v2.DEFAULT_IDENTITY_LIBRARY)
    parser.add_argument("--outfit-gate", default=v2.DEFAULT_OUTFIT_GATE)
    parser.add_argument("--identity-root", default=DEFAULT_IDENTITY_ROOT)
    parser.add_argument("--export-root", default=v2.DEFAULT_EXPORT_ROOT)
    parser.add_argument("--existing-config", default=DEFAULT_EXISTING_CONFIG)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--delta-output", default=DEFAULT_DELTA_OUTPUT)
    parser.add_argument("--matrix-output", default=DEFAULT_MATRIX_OUTPUT)
    args = parser.parse_args()

    full_document = v2.build(
        args.identity_library,
        args.outfit_gate,
        args.identity_root,
        args.export_root,
        verify_identity_projects=True,
        identity_outfit_map=FULL_MATRIX,
        document_id="cc_first_batch_full_reference_looks_20260822_v3",
    )
    full_document["status"] = "complete-matrix-defined"
    delta, existing_ids, missing_ids = build_delta(
        full_document, v2.canonical_path(args.existing_config)
    )
    matrix = build_matrix_document(full_document, existing_ids, missing_ids)

    outputs = {
        "full": v2.canonical_path(args.output),
        "delta": v2.canonical_path(args.delta_output),
        "matrix": v2.canonical_path(args.matrix_output),
    }
    v2.write_json(full_document, outputs["full"])
    v2.write_json(delta, outputs["delta"])
    v2.write_json(matrix, outputs["matrix"])
    print(
        json.dumps(
            {
                "success": True,
                "full_look_count": 32,
                "existing_look_count": 16,
                "missing_look_count": 16,
                "missing_look_ids": missing_ids,
                "outputs": outputs,
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
