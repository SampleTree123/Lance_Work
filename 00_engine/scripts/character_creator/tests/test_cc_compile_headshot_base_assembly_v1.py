"""Targeted deterministic selection, color-contract and recovery protections."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import cc_compile_headshot_base_assembly_v1 as compiler


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def recipe(tmp_path):
    source = tmp_path / "已修正.ccProject"
    source.write_bytes(b"preserved photo identity")
    regions = tmp_path / "regions.json"
    regions.write_text("{}", encoding="utf-8")
    quality = tmp_path / "quality.json"
    quality.write_text(json.dumps({"profile_id": "quality", "status": "approved"}))
    pools = {}
    for pool, field, slot, namespace in compiler.ASSET_FIELDS:
        records = []
        for sex in ("male", "female"):
            for i in range(2):
                path = tmp_path / ("{}_{}_{}.asset".format(slot, sex, i))
                path.write_bytes(path.name.encode())
                records.append({
                    "asset_id": path.stem, "path": str(path), "sha256": digest(path),
                    "slot": slot, "sex_hint": sex, "asset_form": "asset",
                    "pigmentation_profile_id": "profile",
                })
        pools[pool] = records
    color = {
        "root_srgb": "#0123ab", "end_srgb": "#AABBCC",
        "highlight_a_srgb": "#FF0001", "highlight_b_srgb": "#000000",
    }
    registry = {
        "schema_version": 1, "component_pools": pools,
        "face_material_quality_profile": {
            "path": str(quality), "sha256": digest(quality),
            "profile_id": "quality", "required_status": "approved",
        },
        "pigmentation": {
            "mode_weights": {"natural_common": 1},
            "profiles": {"profile": {"natural_common": {"black": 1}, "natural_rare": {"red": 1}}},
            "dyed_color_ids": ["red"], "palette": {"black": color, "red": dict(color)},
        },
    }
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    request = {
        "source_project": str(source), "source_sha256": digest(source),
        "regions_path": str(regions), "sex": "female", "seed": 20261005,
        "character_id": "PHOTO_01", "output_project": str(tmp_path / "独立结果.ccProject"),
    }
    return request, registry_path, registry


def test_deterministic_four_asset_recipe_with_recovery_hashes(recipe):
    request, path, registry = recipe
    first = compiler.compile_base_assembly(request, path)
    assert first == compiler.compile_base_assembly(request, path)
    assert [item["slot"] for item in first["assets"]] == ["skin", "eyebrows", "eyelashes", "eyes"]
    assert all("female" in item["asset_id"] for item in first["assets"])
    assert first["source_sha256"] == request["source_sha256"]
    assert first["registry"]["sha256"] == digest(path)
    assert all(item["sha256"] == digest(Path(item["path"])) for item in first["assets"])
    assert first["preserve_input_teeth_and_oral"] is True
    assert not set(first) & {"age_label", "teeth_asset_id", "scalp_hair_asset_id", "facial_hair_asset_id", "full_face_elder_weight"}
    assert first["geometry_invariants"]["allowances"] == []
    assert set(first["geometry_invariants"]["thresholds_mm"].values()) == {0.002}


def test_male_pool_selection(recipe):
    request, path, registry = recipe
    request["sex"] = "male"
    assert all("male" in item["asset_id"] and "female" not in item["asset_id"] for item in compiler.compile_base_assembly(request, path)["assets"])


def test_color_is_zero_transform_deep_copy_and_has_fixed_highlights(recipe):
    request, path, registry = recipe
    request["facial_components"] = {"visible_gray_fraction": 0.75}
    manifest = compiler.compile_base_assembly(request, path)
    assert manifest["hair_color"] == registry["pigmentation"]["palette"]["black"]
    assert manifest["hair_color"]["root_srgb"] == "#0123ab"
    assert manifest["visible_gray_fraction"] == 0.75
    assert manifest["highlight_a_strength"] == manifest["highlight_b_strength"] == 0.35
    assert manifest["hair_color_id"] == "black"
    assert manifest["hair_color_mode"] == "natural_common"
    manifest["hair_color"]["root_srgb"] = "#FFFFFF"
    assert compiler.compile_base_assembly(request, path)["hair_color"]["root_srgb"] == "#0123ab"


def test_explicit_asset_and_dyed_color_selection(recipe):
    request, path, registry = recipe
    request["facial_components"] = {"skin_asset_id": "skin_female_1", "hair_color_mode": "dyed", "hair_color_id": "red"}
    result = compiler.compile_base_assembly(request, path)
    assert result["skin_asset_id"] == "skin_female_1"
    assert result["hair_color_id"] == "red"
    assert result["visible_gray_fraction"] == 0.0


@pytest.mark.parametrize("gray", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5"])
def test_invalid_gray_rejected(recipe, gray):
    request, path, registry = recipe
    request["facial_components"] = {"visible_gray_fraction": gray}
    with pytest.raises(compiler.CompileError):
        compiler.compile_base_assembly(request, path)


def test_source_hash_mismatch_and_output_overwrite_rejected(recipe):
    request, path, registry = recipe
    request["source_sha256"] = "0" * 64
    with pytest.raises(compiler.CompileError, match="SHA256"):
        compiler.compile_base_assembly(request, path)
    request["source_sha256"] = digest(Path(request["source_project"]))
    request["output_project"] = request["source_project"]
    with pytest.raises(compiler.CompileError, match="independent"):
        compiler.compile_base_assembly(request, path)


def test_existing_independent_output_rejected(recipe):
    request, path, registry = recipe
    Path(request["output_project"]).write_bytes(b"do not overwrite")
    with pytest.raises(compiler.CompileError, match="independent"):
        compiler.compile_base_assembly(request, path)


def test_selected_asset_hash_mismatch_rejected(recipe):
    request, path, registry = recipe
    selected = registry["component_pools"]["skins"][2]
    request["facial_components"] = {"skin_asset_id": selected["asset_id"]}
    Path(selected["path"]).write_bytes(b"changed underneath registry")
    with pytest.raises(compiler.CompileError, match="SHA256"):
        compiler.compile_base_assembly(request, path)


@pytest.mark.parametrize("fields", [{"age_label": "older"}, {"scalp_hair_asset_id": "hair"}, {"hair_color_id": "red"}])
def test_old_tasks_and_profile_ineligible_color_rejected(recipe, fields):
    request, path, registry = recipe
    request["facial_components"] = fields
    with pytest.raises(compiler.CompileError):
        compiler.compile_base_assembly(request, path)


def test_wrong_sex_explicit_asset_rejected(recipe):
    request, path, registry = recipe
    request["facial_components"] = {"skin_asset_id": "skin_male_0"}
    with pytest.raises(Exception, match="not approved"):
        compiler.compile_base_assembly(request, path)


@pytest.mark.parametrize("field,value", [("sex", "both"), ("seed", True), ("seed", "42"), ("character_id", "")])
def test_invalid_core_fields_rejected(recipe, field, value):
    request, path, registry = recipe
    request[field] = value
    with pytest.raises(compiler.CompileError):
        compiler.compile_base_assembly(request, path)


def test_cli_does_not_overwrite_manifest_or_source(recipe, tmp_path):
    request, path, registry = recipe
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    output = tmp_path / "manifest.json"
    args = ["--request", str(request_path), "--registry", str(path), "--output", str(output)]
    assert compiler.main(args) == 0
    assert digest(Path(request["source_project"])) == request["source_sha256"]
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        compiler.main(args)
    assert output.read_bytes() == original


def registered_policy(tmp_path, asset_id="eyelashes_female_0", **overrides):
    evidence = tmp_path / "native_lash_diagnosis.json"
    evidence.write_text('{"native_lash_only": true}', encoding="utf-8")
    record = {
        "name": "native_lash_strip_Lush_Extended", "indices": [13411, 13412],
        "tolerance_mm": 8.2, "reason": "Measured native lash geometry only",
        "evidence": str(evidence), "evidence_sha256": digest(evidence),
    }
    record.update(overrides)
    path = tmp_path / "geometry_policy.json"
    path.write_text(json.dumps({"schema_version": 1, "policies": {asset_id: record}}))
    return path, evidence


def test_registered_policy_matches_only_selected_eyelash_asset(recipe, tmp_path):
    request, registry_path, registry = recipe
    policy, evidence = registered_policy(tmp_path)
    request.update(geometry_policy_path=str(policy), geometry_policy_sha256=digest(policy))
    request["facial_components"] = {"eyelash_asset_id": "eyelashes_female_0"}
    result = compiler.compile_base_assembly(request, registry_path)
    assert result["geometry_policy"] == {"path": str(policy), "sha256": digest(policy)}
    assert result["geometry_invariants"]["allowances"] == {
        "native_lash_strip_Lush_Extended": {
            "indices": [13411, 13412], "tolerance_mm": 8.2,
            "reason": "Measured native lash geometry only", "evidence": str(evidence),
        }
    }
    assert set(result["geometry_invariants"]["thresholds_mm"].values()) == {0.002}
    request["facial_components"]["eyelash_asset_id"] = "eyelashes_female_1"
    assert compiler.compile_base_assembly(request, registry_path)["geometry_invariants"]["allowances"] == []
    request.pop("geometry_policy_path")
    request.pop("geometry_policy_sha256")
    result = compiler.compile_base_assembly(request, registry_path)
    assert result["geometry_invariants"]["allowances"] == []
    assert "geometry_policy" not in result


def test_registered_policy_source_hash_change_rejected(recipe, tmp_path):
    request, registry_path, registry = recipe
    policy, evidence = registered_policy(tmp_path)
    request.update(geometry_policy_path=str(policy), geometry_policy_sha256=digest(policy))
    policy.write_text(policy.read_text() + "\n")
    with pytest.raises(compiler.CompileError, match="SHA256"):
        compiler.compile_base_assembly(request, registry_path)


def test_registered_policy_evidence_hash_change_rejected(recipe, tmp_path):
    request, registry_path, registry = recipe
    policy, evidence = registered_policy(tmp_path)
    request["geometry_policy_path"] = str(policy)
    evidence.write_text('{"native_lash_only": false}')
    with pytest.raises(compiler.CompileError, match="evidence SHA256"):
        compiler.compile_base_assembly(request, registry_path)


@pytest.mark.parametrize("override", [
    {"indices": [1, 1]}, {"indices": [14164]}, {"indices": [True]},
    {"tolerance_mm": float("inf")}, {"tolerance_mm": 0.0001},
    {"reason": ""}, {"evidence_sha256": None},
])
def test_invalid_registered_policy_rejected(recipe, tmp_path, override):
    request, registry_path, registry = recipe
    policy, evidence = registered_policy(tmp_path, **override)
    request["geometry_policy_path"] = str(policy)
    with pytest.raises(compiler.CompileError):
        compiler.compile_base_assembly(request, registry_path)


def test_unsupported_registered_policy_schema_rejected(recipe, tmp_path):
    request, registry_path, registry = recipe
    policy, evidence = registered_policy(tmp_path)
    data = json.loads(policy.read_text())
    data["schema_version"] = 2
    policy.write_text(json.dumps(data))
    request["geometry_policy_path"] = str(policy)
    with pytest.raises(compiler.CompileError, match="schema"):
        compiler.compile_base_assembly(request, registry_path)


def sex_policy(tmp_path, **override_changes):
    policy_path, female_evidence = registered_policy(tmp_path, indices=list(range(13411, 14115)))
    male_evidence = tmp_path / 'male_native_lash.json'
    male_evidence.write_text('{"native_lash_only": true, "sex": "male"}')
    policy = json.loads(policy_path.read_text())
    override = {'name': 'native_lash_strip_Lush_Extended_male', 'tolerance_mm':13.8,
                'evidence':str(male_evidence), 'evidence_sha256':digest(male_evidence)}
    override.update(override_changes)
    policy['policies']['eyelashes_female_0']['sex_overrides'] = {'male':override}
    policy_path.write_text(json.dumps(policy))
    return policy, policy_path, female_evidence, male_evidence


def test_registered_sex_override_preserves_female_and_exact_indices(tmp_path):
    policy, path, female, male = sex_policy(tmp_path)
    female_result = compiler.registered_allowance_for_sex(policy, 'eyelashes_female_0', 'female')
    male_result = compiler.registered_allowance_for_sex(policy, 'eyelashes_female_0', 'male')
    assert female_result['native_lash_strip_Lush_Extended']['tolerance_mm'] == 8.2
    assert female_result['native_lash_strip_Lush_Extended']['evidence'] == str(female)
    assert male_result['native_lash_strip_Lush_Extended_male']['tolerance_mm'] == 13.8
    assert male_result['native_lash_strip_Lush_Extended_male']['evidence'] == str(male)
    assert list(male_result.values())[0]['indices'] == list(female_result.values())[0]['indices'] == list(range(13411,14115))
    assert compiler.registered_allowance_for_sex(policy, 'another_lash', 'male') == []


def test_compiler_uses_request_sex_for_registered_variant(recipe, tmp_path):
    request, registry_path, _ = recipe
    policy, policy_path, _, _ = sex_policy(tmp_path)
    policy['policies']['eyelashes_male_0'] = policy['policies'].pop('eyelashes_female_0')
    policy_path.write_text(json.dumps(policy))
    request.update(sex='male', geometry_policy_path=str(policy_path),
                   facial_components={'eyelash_asset_id':'eyelashes_male_0'})
    manifest = compiler.compile_base_assembly(request, registry_path)
    assert manifest['geometry_invariants']['allowances']['native_lash_strip_Lush_Extended_male']['tolerance_mm'] == 13.8
    assert set(manifest['geometry_invariants']['thresholds_mm'].values()) == {0.002}


@pytest.mark.parametrize('illegal', [
    {'indices':list(range(13411,14115))}, {'indices':[42]}, {'mask':'all'}, {'reason':'replace skin reason'},
    {'tolerance_mm':True}, {'tolerance_mm':float('inf')}, {'evidence_sha256':'bad'}, {'name':''},
])
def test_sex_override_cannot_change_domain_or_use_invalid_bound(tmp_path, illegal):
    policy, _, _, _ = sex_policy(tmp_path, **illegal)
    with pytest.raises(compiler.CompileError):
        compiler.registered_allowance_for_sex(policy, 'eyelashes_female_0', 'male')


@pytest.mark.parametrize('sex', ['both', 'unisex', None])
def test_unknown_sex_is_rejected(tmp_path, sex):
    policy, _, _, _ = sex_policy(tmp_path)
    with pytest.raises(compiler.CompileError, match='sex'):
        compiler.registered_allowance_for_sex(policy, 'eyelashes_female_0', sex)


def test_unknown_registered_override_sex_is_rejected(tmp_path):
    policy, _, _, _ = sex_policy(tmp_path)
    record = policy['policies']['eyelashes_female_0']
    record['sex_overrides']['other'] = record['sex_overrides']['male']
    with pytest.raises(compiler.CompileError, match='sex_overrides'):
        compiler.registered_allowance_for_sex(policy, 'eyelashes_female_0', 'male')


def test_override_evidence_hash_is_checked_even_for_base_selection(tmp_path):
    policy, _, _, male = sex_policy(tmp_path)
    male.write_bytes(b'tampered evidence')
    with pytest.raises(compiler.CompileError, match='evidence SHA256'):
        compiler.registered_allowance_for_sex(policy, 'eyelashes_female_0', 'female')
