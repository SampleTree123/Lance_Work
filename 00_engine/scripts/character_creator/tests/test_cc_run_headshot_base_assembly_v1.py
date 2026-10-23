"""Failure containment and input protection of the bounded CC assembly runner."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "cc_run_headshot_base_assembly_v1.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("headshot_base_assembly_runner_test", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
THRESHOLDS = dict.fromkeys(
    ("body_outside_head", "scalp_mask_zero", "face_mask_full", "transition"), 0.002
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "authorized"
    output = root / "representative_01"
    output.mkdir(parents=True)
    monkeypatch.setattr(RUNNER, "RUN_ROOT", str(root))
    source = tmp_path / "immutable_source.ccProject"
    source.write_bytes(b"corrected photo identity, average body and fixed scalp")
    regions = tmp_path / "regions.json"
    regions.write_text("{}", encoding="utf-8")
    assets = []
    for slot in ("skin", "eyebrows", "eyelashes", "eyes"):
        path = tmp_path / (slot + ".ccAsset")
        path.write_bytes(slot.encode())
        assets.append(dict(slot=slot, path=str(path), sha256=sha(path), asset_id=slot))
    config = dict(
        source_project=str(source), source_sha256=sha(source),
        output_project=str(output / "assembled.ccProject"),
        regions_path=str(regions), regions_sha256=sha(regions), assets=assets,
        character_id="photo_01", sex="female", geometry_invariants=dict(
            space="local", thresholds_mm=copy.deepcopy(THRESHOLDS), allowances=[]),
        hair_color=dict(root_srgb="#123456", end_srgb="#123456",
                        highlight_a_srgb="#123456", highlight_b_srgb="#123456"),
        visible_gray_fraction=0.0, face_material_quality_profile="neutral",
    )
    calls = []
    captures = []
    comparisons = []
    control = dict(fail_at=None)
    avatar = types.SimpleNamespace(GetHairs=lambda: [], GetSubdivMeshLevel=lambda: 0)

    def load(path, label):
        calls.append(("load", path, label))
        return {"is_error": False}, []

    def apply(avatar, selected, **kwargs):
        calls.append(("apply", selected[0]["slot"]))
        return avatar, {"success": True}

    def pigmentation(avatar, color, fraction, *, target_domains):
        calls.append(("color", target_domains))
        return {"success": True}

    def save(path):
        calls.append(("save", path))
        Path(path).write_bytes(b"assembled character")

    def capture(avatar, *, api, include_world, output_path):
        assert include_world is False
        step = Path(output_path).name.removesuffix("_geometry.json")
        snapshot = dict(step=step, working_subdivision_level=0)
        captures.append(snapshot)
        return snapshot

    def compare(before, after, regions, *, space, tolerance_mm, allowances):
        assert space == "local"
        assert tolerance_mm == THRESHOLDS and allowances == []
        comparisons.append((before, after))
        passed = after["step"] != control["fail_at"]
        return dict(passed=passed, failed_regions=[] if passed else ["face_mask_full"],
                    worst_offenders=[] if passed else [{"index": 1337, "displacement_mm": 0.1}])

    def write(data, path):
        Path(path).write_text(json.dumps(data), encoding="utf-8")

    api = types.SimpleNamespace(
        sha256_file=sha, now=lambda: "2026-10-05T16:00:00+08:00", write_json=write,
        load_file_with_optional_undo_warning=load,
        avatar_asset_inventory=lambda avatar: {"object_count": 0},
        apply_appearance_assets=apply, apply_shared_hair_pigmentation=pigmentation,
        apply_face_material_quality_profile=lambda avatar, profile: calls.append(("quality", profile)),
        checked=lambda label, status: None,
        RLPy=types.SimpleNamespace(
            RScene=types.SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=lambda avatar: None),
            RFileIO=types.SimpleNamespace(SaveProject=save)),
        QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(processEvents=lambda: None)),
    )
    modules = (types.SimpleNamespace(capture_body_snapshot=capture),
               types.SimpleNamespace(DEFAULT_TOLERANCE_MM=THRESHOLDS, load_regions=lambda path: {},
                                     compare_assembly_snapshots=compare))
    monkeypatch.setattr(RUNNER, "geometry_modules", lambda: modules)
    return types.SimpleNamespace(config=config, api=api, calls=calls, captures=captures,
        comparisons=comparisons, control=control, output=output, source=source, avatar=avatar)


def run(rig):
    return RUNNER.run({"base_assembly": rig.config}, str(rig.output), lambda message: None, rig.api)


def receipt(rig, name="assembly_report.json"):
    return json.loads((rig.output / name).read_text(encoding="utf-8"))


def test_lash_geometry_drift_stops_followup_and_restores_immutable_source(setup):
    rig = setup
    rig.control["fail_at"] = "apply_eyelashes"
    result = run(rig)
    assert result["success"] is False
    assert result["failed_phase"] == "apply_eyelashes"
    assert "face_mask_full" in result["error"]["message"]
    assert [call[1] for call in rig.calls if call[0] == "apply"] == ["skin", "eyebrows", "eyelashes"]
    assert not any(call[0] in {"color", "quality", "save"} for call in rig.calls)
    assert not Path(rig.config["output_project"]).exists()
    loads = [call for call in rig.calls if call[0] == "load"]
    assert len(loads) == 2 and all(call[1] == str(rig.source) for call in loads)
    assert "Restore immutable input" in loads[1][2]
    assert result["recovery"]["status"] == "restored_input"
    assert sha(rig.source) == rig.config["source_sha256"]
    assert receipt(rig)["success"] is False
    geometry = receipt(rig, "assembly_geometry_invariants.json")
    assert geometry["passed"] is False
    assert geometry["steps"][-1]["step"] == "apply_eyelashes"
    assert geometry["steps"][-1]["worst_offenders"][0]["index"] == 1337


def test_success_gates_each_step_against_initial_identity_and_saves_independent_copy(setup):
    rig = setup
    result = run(rig)
    assert result["success"] is True and result["source_unchanged"] is True
    assert result["visual_acceptance"] == "pending"
    assert sha(rig.source) == rig.config["source_sha256"]
    assert Path(rig.config["output_project"]).is_file()
    assert [call[1] for call in rig.calls if call[0] == "apply"] == ["skin", "eyebrows", "eyelashes", "eyes"]
    assert ("color", ("eyebrows",)) in rig.calls
    assert len([call for call in rig.calls if call[0] == "load"]) == 1
    assert len([call for call in rig.calls if call[0] == "save"]) == 1
    assert len(rig.comparisons) == 8
    assert all(before is rig.captures[0] for before, after in rig.comparisons)
    assert receipt(rig, "assembly_geometry_invariants.json")["passed"] is True
    # The fake API exposes no identity/head/body morph, SubD setter, garment or
    # hair loader: a call to any such method would fail this successful run.


def test_existing_output_is_rejected_without_loading_or_modification(setup):
    rig = setup
    target = Path(rig.config["output_project"])
    target.write_bytes(b"accepted character, must not overwrite")
    with pytest.raises(ValueError, match="must be new"):
        run(rig)
    assert target.read_bytes() == b"accepted character, must not overwrite"
    assert rig.calls == []


def test_source_as_output_is_rejected_and_input_preserved(setup):
    rig = setup
    rig.config["output_project"] = str(rig.source)
    with pytest.raises(ValueError, match="Output project"):
        run(rig)
    assert sha(rig.source) == rig.config["source_sha256"] and rig.calls == []


def test_asset_sha_change_is_rejected_before_cc_load(setup):
    rig = setup
    Path(rig.config["assets"][2]["path"]).write_bytes(b"replacement eyelashes asset")
    with pytest.raises(ValueError, match="Asset SHA changed: eyelashes"):
        run(rig)
    assert rig.calls == []


@pytest.mark.parametrize("mutation", ["allowance", "threshold"])
def test_unapproved_geometric_policy_is_rejected_before_cc_load(setup, mutation):
    rig = setup
    if mutation == "allowance":
        rig.config["geometry_invariants"]["allowances"] = [
            {"name": "unmeasured eyelid", "indices": [1337], "tolerance_mm": 1.0}]
    else:
        rig.config["geometry_invariants"]["thresholds_mm"]["face_mask_full"] = 0.01
    with pytest.raises(ValueError, match="registered asset-specific allowances"):
        run(rig)
    assert rig.calls == []


def test_postsave_drift_cannot_publish_a_completed_character(setup):
    rig = setup
    rig.control["fail_at"] = "post_save"
    result = run(rig)
    assert Path(rig.config["output_project"]).exists()  # Failure artifact retained.
    assert result["success"] is False
    assert "post_save" in result["error"]["message"]
    assert result["recovery"]["status"] == "restored_input"
    assert receipt(rig)["success"] is False
    assert receipt(rig, "assembly_geometry_invariants.json")["passed"] is False


def register_policy(rig, tmp_path, monkeypatch, version='v1'):
    script = tmp_path / 'runner.py'
    script.write_bytes(SCRIPT.read_bytes())
    monkeypatch.setattr(RUNNER, '__file__', str(script))
    evidence = tmp_path / 'measured.json'
    evidence.write_text('{"native_lash_geometry_only": true}', encoding='utf-8')
    record = dict(name='measured_native_lash', indices=[1337], tolerance_mm=.1,
                  reason='Measured native lash only', evidence=str(evidence), evidence_sha256=sha(evidence))
    policy_path = tmp_path / ('cc_base_assembly_geometry_policy_' + version + '.json')
    policy_path.write_text(json.dumps(dict(schema_version=1, policies={'eyelashes': record})), encoding='utf-8')
    rig.api.read_json = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
    rig.config['eyelash_asset_id'] = 'eyelashes'
    rig.config['geometry_policy'] = dict(path=str(policy_path), sha256=sha(policy_path))
    allowed = {record['name']: {key:record[key] for key in ('indices','tolerance_mm','reason','evidence')}}
    rig.config['geometry_invariants']['allowances'] = copy.deepcopy(allowed)
    return allowed, evidence


@pytest.mark.parametrize('version', ['v1', 'v2'])
def test_registered_asset_policy_is_forwarded_to_every_geometry_gate(setup, tmp_path, monkeypatch, version):
    rig = setup
    allowed, _ = register_policy(rig, tmp_path, monkeypatch, version)
    capture, comparator = RUNNER.geometry_modules()
    gated = []
    def compare(before, after, regions, **kwargs):
        assert kwargs['allowances'] == allowed
        assert kwargs['tolerance_mm'] == THRESHOLDS
        gated.append(after['step'])
        return dict(passed=True, failed_regions=[])
    comparator.compare_assembly_snapshots = compare
    assert run(rig)['success'] is True
    assert len(gated) == 8
    assert receipt(rig, 'assembly_geometry_invariants.json')['allowances'] == allowed


@pytest.mark.parametrize('mutation', ['indices', 'evidence', 'wrong_asset'])
def test_registered_allowance_cannot_expand_or_transfer_to_another_asset(setup, tmp_path, monkeypatch, mutation):
    rig = setup
    _, evidence = register_policy(rig, tmp_path, monkeypatch)
    if mutation == 'indices':
        rig.config['geometry_invariants']['allowances']['measured_native_lash']['indices'].append(42)
    elif mutation == 'evidence':
        evidence.write_text('changed evidence', encoding='utf-8')
    else:
        rig.config['eyelash_asset_id'] = 'unmeasured_other_lash'
    with pytest.raises(ValueError):
        run(rig)
    assert rig.calls == []


def test_runner_uses_same_registered_male_override_at_all_gates(setup, tmp_path, monkeypatch):
    rig = setup
    _, female_evidence = register_policy(rig, tmp_path, monkeypatch)
    path = Path(rig.config['geometry_policy']['path'])
    policy = json.loads(path.read_text())
    record = policy['policies']['eyelashes']
    male_evidence = tmp_path / 'male_measured.json'
    male_evidence.write_text('{"sex":"male","native_lash_only":true}')
    record['sex_overrides'] = {'male':dict(name='male_native_lash', tolerance_mm=13.8,
        evidence=str(male_evidence), evidence_sha256=sha(male_evidence))}
    path.write_text(json.dumps(policy))
    rig.config['geometry_policy']['sha256'] = sha(path)
    rig.config['sex'] = 'male'
    import cc_compile_headshot_base_assembly_v1 as compiler
    allowed = compiler.registered_allowance_for_sex(policy, 'eyelashes', 'male')
    rig.config['geometry_invariants']['allowances'] = allowed
    _, comparator = RUNNER.geometry_modules()
    gates = []
    def compare(before, after, regions, **kwargs):
        assert kwargs['allowances'] == allowed
        assert kwargs['tolerance_mm'] == THRESHOLDS
        gates.append(after['step'])
        return dict(passed=True, failed_regions=[])
    comparator.compare_assembly_snapshots = compare
    assert run(rig)['success'] is True
    assert len(gates) == 8
    assert receipt(rig, 'assembly_geometry_invariants.json')['allowances'] == allowed


def test_runner_rejects_female_bound_used_for_male_override(setup, tmp_path, monkeypatch):
    rig = setup
    _, evidence = register_policy(rig, tmp_path, monkeypatch)
    path = Path(rig.config['geometry_policy']['path'])
    policy = json.loads(path.read_text())
    policy['policies']['eyelashes']['sex_overrides'] = {'male':{'tolerance_mm':13.8}}
    path.write_text(json.dumps(policy))
    rig.config['geometry_policy']['sha256'] = sha(path)
    rig.config['sex'] = 'male'
    with pytest.raises(ValueError, match='registered asset-specific allowances'):
        run(rig)
    assert rig.calls == []


def test_runner_rejects_unregistered_policy_path_with_matching_sha(setup, tmp_path, monkeypatch):
    rig = setup
    _, _ = register_policy(rig, tmp_path, monkeypatch)
    registered = Path(rig.config['geometry_policy']['path'])
    arbitrary = tmp_path / 'unregistered_policy.json'
    arbitrary.write_bytes(registered.read_bytes())
    rig.config['geometry_policy'] = {'path':str(arbitrary), 'sha256':sha(arbitrary)}
    with pytest.raises(ValueError, match='registered assembly policy'):
        run(rig)
    assert rig.calls == []


def test_runner_reloads_stale_compiler_selector_in_long_lived_session(setup, tmp_path, monkeypatch):
    rig = setup
    allowed, _ = register_policy(rig, tmp_path, monkeypatch)
    import cc_compile_headshot_base_assembly_v1 as compiler
    def stale(*args):
        raise AssertionError('Cached selector must be replaced by the on-disk implementation')
    monkeypatch.setattr(compiler, 'registered_allowance_for_sex', stale)
    _, comparator = RUNNER.geometry_modules()
    comparator.compare_assembly_snapshots = lambda before, after, regions, **kw: (
        dict(passed=True, failed_regions=[]) if kw['allowances'] == allowed else
        dict(passed=False, failed_regions=['unexpected']))
    assert run(rig)['success'] is True
    assert compiler.registered_allowance_for_sex is not stale
