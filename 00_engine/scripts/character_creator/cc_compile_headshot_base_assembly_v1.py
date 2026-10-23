"""Compile the limited Headshot base-appearance recipe without driving CC.

Only the four approved appearance pools are selected. This is deliberately not
the old full facial compiler: geometry, age, teeth, hair and clothing tasks are
never emitted. Paths and hashes bind recovery to the exact input and assets.
"""

import argparse
import copy
import json
import math
import os
import re

from cc_compile_character_manifest import (
    CompileError, canonical_path, facial_pool, read_json, requested_component,
    sha256_file, stable_distribution_choice,
)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(SCRIPT_DIR, "cc_facial_production_registry_v1.json")
ASSET_FIELDS = (
    ("skins", "skin_asset_id", "skin", "skin"),
    ("eyebrows", "eyebrow_asset_id", "eyebrows", "eyebrows"),
    ("eyelashes", "eyelash_asset_id", "eyelashes", "eyelashes"),
    ("eyes", "eye_asset_id", "eyes", "eyes"),
)
COLOR_FIELDS = ("root_srgb", "end_srgb", "highlight_a_srgb", "highlight_b_srgb")
COLOR_MODES = ("natural_common", "natural_rare", "dyed")
COMPONENT_FIELDS = {item[1] for item in ASSET_FIELDS} | {
    "hair_color_id", "hair_color_mode", "visible_gray_fraction",
}
THRESHOLDS_MM = {
    "body_outside_head": 0.002, "scalp_mask_zero": 0.002,
    "face_mask_full": 0.002, "transition": 0.002,
}


def _required_string(data, name):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CompileError("{} must be a nonempty string".format(name))
    return value


def _file_reference(path, label, expected_sha256=None):
    resolved = canonical_path(path, label)
    actual = sha256_file(resolved)
    if expected_sha256 is not None and expected_sha256 != actual:
        raise CompileError("{} SHA256 changed".format(label))
    return {"path": resolved, "sha256": actual}


def _asset_record(selected, slot):
    if selected.get("slot") != slot:
        raise CompileError("Registry asset has an unexpected slot")
    expected = selected.get("sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise CompileError("Registry asset must have a SHA256")
    reference = _file_reference(selected.get("path"), selected["asset_id"], expected)
    return {
        "asset_id": selected["asset_id"],
        "display_name": selected.get("display_name"),
        "asset_type": selected.get("asset_type"),
        "asset_form": selected.get("asset_form"),
        "application_mode": selected.get("application_mode"),
        "slot": slot,
        "extension": os.path.splitext(reference["path"])[1].lower(),
        "verification_mode": (
            "material_fingerprint" if slot in ("skin", "eyes") else "scene_inventory"
        ),
        **reference,
    }


def registered_allowance_for_sex(policy, eyelash_asset_id, sex):
    """Validate registered evidence and select a sex-specific native-lash bound.

    Overrides can change only the name, bound and its source evidence. They
    inherit the exact base indices and reason; skin thresholds are not involved.
    Compiler and CC runner use this same selector to prevent interpretation drift.
    """
    if sex not in ("male", "female"):
        raise CompileError("Geometry policy requires sex male or female")
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise CompileError("Unsupported geometry policy schema")
    policies = policy.get("policies")
    if not isinstance(policies, dict):
        raise CompileError("geometry policy policies must be an object")
    validated = {}
    for asset_id, registered in policies.items():
        if not isinstance(asset_id, str) or not asset_id or not isinstance(registered, dict):
            raise CompileError("Geometry policy entries must be keyed by asset ID")
        name = _required_string(registered, "name")
        reason = _required_string(registered, "reason")
        indices = registered.get("indices")
        if (not isinstance(indices, list) or not indices
                or any(isinstance(index, bool) or not isinstance(index, int)
                       or not 0 <= index < 14164 for index in indices)
                or len(indices) != len(set(indices))):
            raise CompileError("Geometry policy indices must be unique CC3+ body indices")
        tolerance = registered.get("tolerance_mm")
        if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
                or not math.isfinite(tolerance) or tolerance < 0.001):
            raise CompileError("Geometry policy tolerance_mm is invalid")
        expected = registered.get("evidence_sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise CompileError("Geometry policy evidence must have a SHA256")
        evidence = _file_reference(
            _required_string(registered, "evidence"), "geometry policy evidence", expected
        )
        overrides = registered.get("sex_overrides", {})
        if not isinstance(overrides, dict) or set(overrides) - {"male", "female"}:
            raise CompileError("Geometry policy sex_overrides has unsupported sex")
        allowed_fields = {"name", "tolerance_mm", "evidence", "evidence_sha256"}
        variants = {}
        for override_sex, override in overrides.items():
            if not isinstance(override, dict) or set(override) - allowed_fields:
                raise CompileError("Geometry policy sex override cannot change indices, reason or other fields")
            if ("evidence" in override) != ("evidence_sha256" in override):
                raise CompileError("Sex override evidence requires its own SHA256")
            variant = dict(registered)
            variant.update(override)
            variant_name = _required_string(variant, "name")
            variant_tolerance = variant["tolerance_mm"]
            if (isinstance(variant_tolerance, bool) or not isinstance(variant_tolerance, (int, float))
                    or not math.isfinite(variant_tolerance) or variant_tolerance < 0.001):
                raise CompileError("Geometry policy sex override tolerance_mm is invalid")
            variant_sha = variant["evidence_sha256"]
            if not isinstance(variant_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", variant_sha):
                raise CompileError("Geometry policy sex override evidence must have a SHA256")
            variant_evidence = _file_reference(_required_string(variant, "evidence"),
                                               "geometry policy evidence", variant_sha)
            variants[override_sex] = {variant_name: {
                "indices": list(indices), "tolerance_mm": float(variant_tolerance),
                "reason": reason, "evidence": variant_evidence["path"],
            }}
        base = {name: {
            "indices": list(indices), "tolerance_mm": float(tolerance),
            "reason": reason, "evidence": evidence["path"],
        }}
        validated[asset_id] = variants.get(sex, base)
    return validated.get(eyelash_asset_id, [])


def _registered_geometry_policy(request, eyelash_asset_id):
    """No implicit policy: first representative runs retain zero exemptions."""
    if request.get("geometry_policy_path") is None:
        if request.get("geometry_policy_sha256") is not None:
            raise CompileError("geometry_policy_sha256 requires geometry_policy_path")
        return None, []
    reference = _file_reference(
        _required_string(request, "geometry_policy_path"), "geometry_policy",
        request.get("geometry_policy_sha256"),
    )
    policy = read_json(reference["path"])
    return reference, registered_allowance_for_sex(policy, eyelash_asset_id, request["sex"])


def compile_base_assembly(request, registry_path=DEFAULT_REGISTRY):
    """Return a deterministic manifest; never modify source or CC state.

    Required request fields: character_id, sex, integer seed, source_project,
    output_project and regions_path. Optional facial_components fields are
    explicit asset/color selections. With no gray override the fraction is 0;
    age is not sampled to infer gray hair in this geometry-preserving workflow.
    """
    if not isinstance(request, dict):
        raise CompileError("Request must be an object")
    character_id = _required_string(request, "character_id")
    sex = request.get("sex")
    if sex not in ("male", "female"):
        raise CompileError("sex must be male or female")
    seed = request.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise CompileError("seed must be an integer")
    source = _file_reference(
        _required_string(request, "source_project"), "source_project",
        request.get("source_sha256"),
    )
    output = os.path.realpath(os.path.abspath(_required_string(request, "output_project")))
    if os.path.splitext(source["path"])[1].lower() != ".ccproject":
        raise CompileError("source_project must be a ccProject")
    if os.path.splitext(output)[1].lower() != ".ccproject":
        raise CompileError("output_project must be a ccProject")
    if os.path.normcase(output) == os.path.normcase(source["path"]) or os.path.exists(output):
        raise CompileError("output_project must be a new independent path")
    regions = _file_reference(
        _required_string(request, "regions_path"), "regions_path",
        request.get("regions_sha256"),
    )
    # The invariant module owns parsing/topology validation; do not clone it here.
    registry_ref = _file_reference(registry_path, "facial_registry")
    registry = read_json(registry_ref["path"])
    if registry.get("schema_version") != 1:
        raise CompileError("Unsupported facial registry schema")
    specification = request.get("facial_components", {})
    if not isinstance(specification, dict):
        raise CompileError("facial_components must be an object")
    unknown = set(specification) - COMPONENT_FIELDS
    if unknown:
        raise CompileError("Unsupported base assembly fields: {}".format(sorted(unknown)))

    selections = {}
    assets = []
    for pool_name, field, slot, namespace in ASSET_FIELDS:
        candidates = {
            asset_id: item
            for asset_id, item in facial_pool(registry, pool_name).items()
            if (item.get("sex") or item.get("sex_hint")) not in ("male", "female")
            or (item.get("sex") or item.get("sex_hint")) == sex
        }
        selected = requested_component(
            specification, field, candidates, seed, "{}:{}".format(character_id, namespace)
        )
        selections[field] = selected["asset_id"]
        assets.append(_asset_record(selected, slot))
        if slot == "skin":
            skin = selected

    pigmentation = registry.get("pigmentation") or {}
    mode = specification.get("hair_color_mode")
    if mode is None:
        mode = stable_distribution_choice(
            pigmentation.get("mode_weights") or {}, seed, "{}:hair_color_mode".format(character_id)
        )
    if mode not in COLOR_MODES:
        raise CompileError("Unsupported hair_color_mode")
    profile_id = skin.get("pigmentation_profile_id")
    profile = (pigmentation.get("profiles") or {}).get(profile_id)
    if not isinstance(profile, dict):
        raise CompileError("Skin has no approved pigmentation profile")
    distribution = (
        {key: 1.0 for key in pigmentation.get("dyed_color_ids", [])}
        if mode == "dyed" else profile.get(mode) or {}
    )
    color_id = specification.get("hair_color_id")
    if color_id is None:
        color_id = stable_distribution_choice(distribution, seed, "{}:hair_color".format(character_id))
    if color_id not in distribution:
        raise CompileError("hair_color_id is outside the skin profile and mode")
    palette_color = (pigmentation.get("palette") or {}).get(color_id)
    if not isinstance(palette_color, dict) or set(palette_color) != set(COLOR_FIELDS):
        raise CompileError("Palette color must contain exactly the four semantic fields")
    if any(not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value)
           for value in palette_color.values()):
        raise CompileError("Palette colors must be #RRGGBB strings")
    gray = specification.get("visible_gray_fraction", 0.0)
    if isinstance(gray, bool) or not isinstance(gray, (float, int)) or not math.isfinite(gray) or not 0 <= gray <= 1:
        raise CompileError("visible_gray_fraction must be finite and within [0, 1]")

    quality = registry.get("face_material_quality_profile") or {}
    quality_ref = _file_reference(quality.get("path"), "face_material_quality_profile", quality.get("sha256"))
    quality_profile = read_json(quality_ref["path"])
    if quality_profile.get("profile_id") != quality.get("profile_id") or quality_profile.get("status") != quality.get("required_status"):
        raise CompileError("Face material quality profile approval changed")
    quality_ref.update(profile_id=quality["profile_id"], required_status=quality["required_status"])
    policy_reference, allowances = _registered_geometry_policy(request, selections["eyelash_asset_id"])
    manifest = {
        "schema_version": 1,
        "workflow": "headshot_base_assembly_v1",
        "character_id": character_id, "sex": sex, "seed": seed,
        "source_project": source["path"], "source_sha256": source["sha256"],
        "output_project": output,
        "regions_path": regions["path"], "regions_sha256": regions["sha256"],
        "registry": registry_ref,
        "assets": assets,
        **selections,
        "hair_color": copy.deepcopy(palette_color),
        "hair_color_id": color_id, "hair_color_mode": mode,
        "visible_gray_fraction": float(gray),
        "pigmentation_profile_id": profile_id,
        "color_contract_version": 1,
        "highlight_a_strength": 0.35, "highlight_b_strength": 0.35,
        "face_material_quality_profile": quality_ref,
        "geometry_invariants": {"space": "local", "thresholds_mm": dict(THRESHOLDS_MM), "allowances": allowances},
        "application_order": ["skin", "eyebrows", "eyelashes", "eyes_material_only", "eyebrow_pigmentation", "face_material_quality_profile", "save"],
        "preserve_input_teeth_and_oral": True,
    }
    if policy_reference is not None:
        manifest["geometry_policy"] = policy_reference
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = compile_base_assembly(read_json(args.request), args.registry)
    output = os.path.realpath(os.path.abspath(args.output))
    if os.path.normcase(output) in (os.path.normcase(manifest["source_project"]), os.path.normcase(manifest["output_project"])):
        raise CompileError("Manifest path cannot be a project path")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    # Exclusive creation protects both accepted manifests and interrupted results.
    with open(output, "x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"manifest": output, "character_id": manifest["character_id"], "assets": len(manifest["assets"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
