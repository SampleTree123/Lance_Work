"""One identity call must preserve source geometry, normals and UV exactly."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_probe_eye_support_identity_v5 as identity
import cc_eye_support_inverse_affine_v1 as inverse
import cc_refresh_eyelash_probe_v2 as lash
import cc_refresh_eye_support_diagnostic_v1 as queries
import cc_repair_headshot_support_materials_v1 as support

NAME = 'CC_Base_EyeOcclusion'
FACES = [[0, 1, 2]]
OBJ = ('g CC_Base_EyeOcclusion\nv 0 0 0\nv 1 0 0\nv 0 1 0\n'
       'vt 0 0\nvt 1 0\nvt 0 1\nvn 0 0 1\nusemtl EyeOcclusion\nf 1/1/1 2/2/1 3/3/1\n')


def test_identity_world_obj_retains_uv_normals_materials_and_corner_assignments(tmp_path):
    native = tmp_path / 'native.obj'; native.write_text(OBJ)
    parsed = identity.parse_native_obj(native, NAME, 3, FACES)
    output = tmp_path / 'identity.obj'
    result = identity.write_identity_world_obj(parsed, [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]], output)
    after = identity.parse_native_obj(output, NAME, 3, FACES)
    assert result['replace_uv'] is False
    assert after['uv_normal_material_corner_sha256'] == parsed['uv_normal_material_corner_sha256']
    with pytest.raises(ValueError, match='existing'):
        identity.write_identity_world_obj(parsed, parsed['vertices'], output)
    shifted = tmp_path / 'different_domain.obj'
    diagnostic = identity.write_identity_world_obj(parsed, [[0., .01, 0.], [1., 0., 0.], [0., 1., 0.]], shifted)
    assert diagnostic['native_obj_vs_submitted_input_max_mm'] == pytest.approx(.1)
    assert diagnostic['native_obj_vs_submitted_input_is_acceptance_gate'] is False
    assert identity.parse_native_obj(shifted, NAME, 3, FACES)['uv_normal_material_corner_sha256'] == parsed['uv_normal_material_corner_sha256']


@pytest.mark.parametrize('text', [OBJ.replace('1/1/1', '1//1'), OBJ.replace('vn 0 0 1', 'vn 0 0 0'),
                                OBJ.replace(NAME, 'WrongMesh'), OBJ.replace('3/3/1', '3/4/1')])
def test_missing_or_invalid_native_corner_data_cannot_reach_replacement(tmp_path, text):
    path = tmp_path / 'native.obj'; path.write_text(text)
    with pytest.raises(ValueError): identity.parse_native_obj(path, NAME, 3, FACES)


def test_whole_avatar_extraction_reindexes_independent_sparse_corner_arrays(tmp_path):
    text = ('g Other\n' + ''.join('v {} 0 0\n'.format(i) for i in range(6))
        + ''.join('vt {} 0\n'.format(i) for i in range(5))
        + 'vn 1 0 0\nvn 0 1 0\nvn 0 0 1\n'
        + 'usemtl OriginalSupport\ns 1\ng ' + NAME + '\nf 2/5/3 6/2/1 4/4/2\n'
        + 'g OtherAgain\nf 1/1/1 3/2/1 5/3/1\n')
    whole = tmp_path / 'whole.obj'; whole.write_text(text)
    target = tmp_path / 'target.obj'
    record = identity.extract_native_group(whole, target, NAME, 3, [[0, 2, 1]])
    assert record['source_vertex_indices_1based'] == [2, 4, 6]
    assert record['source_uv_indices_1based'] == [2, 4, 5]
    assert record['source_normal_indices_1based'] == [1, 2, 3]
    output = target.read_text()
    assert 'f 1/3/3 3/1/1 2/2/2' in output
    assert 'usemtl OriginalSupport' in output and 's 1' in output
    assert not record['normals_generated'] and not record['uv_generated']
    # Same semantic source with independent negative v/vt/vn indices.
    whole.write_text(text.replace('2/5/3 6/2/1 4/4/2', '-5/-1/-1 -1/-4/-3 -3/-2/-2'))
    other = tmp_path / 'negative.obj'
    negative = identity.extract_native_group(whole, other, NAME, 3, [[0, 2, 1]])
    assert negative['uv_normal_material_corner_sha256'] == record['uv_normal_material_corner_sha256']


@pytest.mark.parametrize('text', [OBJ.replace('g ' + NAME, 'g Wrong'),
    OBJ + 'g Other\nf 1/1/1 2/2/1 3/3/1\ng ' + NAME + '\nf 1/1/1 2/2/1 3/3/1\n',
    OBJ.replace('1/1/1', '1//1'), OBJ.replace('3/3/1', '4/3/1')])
def test_extraction_refuses_absent_duplicate_missing_attributes_or_bad_global_refs(tmp_path, text):
    source = tmp_path / 'whole.obj'; source.write_text(text)
    with pytest.raises(ValueError):
        identity.extract_native_group(source, tmp_path / 'target.obj', NAME, 3, FACES)


def test_actual_three_whole_avatar_exports_preserve_exact_both_support_topologies(tmp_path):
    root = Path(__file__).resolve().parents[4]
    runs = root / '00_engine/outputs/character_creator_bridge/artifacts/headshot_route_compare_20261002_v1'
    files = [runs / p for p in ('female01_hair_obj_template_v1/avatar_with_hair_native.obj',
        'female02_inverse_fixed_hair_geometry_v1/avatar_with_hair_native.obj',
        'male02_inverse_fixed_hair_geometry_v1/avatar_with_hair_native.obj')]
    diagnosis = root / '00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1/eye_support_WF003_Delicate_diagnostic_v1/fresh_raw_snapshot.json'
    if not all(p.exists() for p in files) or not diagnosis.exists():
        pytest.skip('Archived true CC exports and faces unavailable')
    levels = json.loads(diagnosis.read_text())['support_queries']['levels']
    for i, source in enumerate(files):
        for name, count in ((NAME, 182), ('CC_Base_TearLine', 190)):
            row = next(r for r in levels if r['name'] == name and r['vertex_count'] == count)
            target = tmp_path / '{}_{}.obj'.format(i, name)
            record = identity.extract_native_group(source, target, name, count, row['faces'])
            parsed = identity.parse_native_obj(target, name, count, row['faces'])
            assert record['vertex_count'] == count and parsed['uv_count'] > 0 and parsed['normal_count'] > 0
            assert len(parsed['faces']) == row['face_count']


def test_actual_v2_mismatch_becomes_template_diagnostic_but_submitted_world_is_exact(tmp_path):
    root = Path(__file__).resolve().parents[4]
    output = root / '00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1/eye_occlusion_WF003_identity_v2'
    if not (output / 'post_source_export_snapshot.json').exists():
        pytest.skip('Actual v2 source snapshot unavailable')
    snapshot = json.loads((output / 'post_source_export_snapshot.json').read_text())
    world = snapshot['target_world']['world']; faces = snapshot['target_world']['faces']
    native = identity.parse_native_obj(output / 'native_source.obj', NAME, 182, faces)
    target = tmp_path / 'source_sdk_world_identity.obj'
    result = identity.write_identity_world_obj(native, world, target)
    parsed = identity.parse_native_obj(target, NAME, 182, faces)
    assert result['native_obj_vs_submitted_input_max_mm'] == pytest.approx(72.89966423195243)
    assert result['native_obj_vs_submitted_input_is_acceptance_gate'] is False
    assert parsed['uv_normal_material_corner_sha256'] == native['uv_normal_material_corner_sha256']
    assert max(lash._distances(parsed['vertices'], world)) < 1e-8


@pytest.mark.parametrize('world', [[[float('nan'), 0., 0.]] * 3, [[0., 0., 0.]], [[0., 0.]] * 3])
def test_cross_domain_change_does_not_disable_finite_shape_requirements(tmp_path, world):
    path = tmp_path / 'native.obj'; path.write_text(OBJ)
    parsed = identity.parse_native_obj(path, NAME, 3, FACES)
    with pytest.raises(ValueError, match='finite'):
        identity.write_identity_world_obj(parsed, world, tmp_path / 'bad.obj')


@pytest.mark.parametrize('failure', [None, 'unsupported_export', 'mutation_after_replace'])
def test_complete_runtime_candidate_only_one_call_and_restores_source(tmp_path, monkeypatch, failure):
    root = tmp_path / 'refresh'; root.mkdir()
    source = root / 'source.ccProject'; source.write_bytes(b'original')
    state = {'mutated': False}; calls = []
    def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    record = lambda p: dict(path=str(p), sha256=sha(p), bytes=Path(p).stat().st_size)
    evidence = root / 'diagnostic.json'
    evidence.write_text(json.dumps(dict(capture_complete=True, geometry_accepted=False, source_project=record(source))))
    failed = root / 'single_part_failed.json'
    failed.write_text(json.dumps(dict(success=False, replace_status=None, restored_source=True, source_project=record(source), error=dict(message="status_code: '7'"))))
    mismatch = root / 'native_world_mismatch.json'
    mismatch.write_text(json.dumps(dict(success=False, replace_status=None, restored_source=True, source_project=record(source), error=dict(message='Native export and active scalar-verified SDK world disagree beyond0.002mm'), steps=[dict(phase='post_source_export', passed=True)])))
    for k in ('RUN_ROOT', 'CREATION_ROOT', 'STAGE_ROOT'): monkeypatch.setattr(lash, k, str(root))
    digest = hashlib.sha256(json.dumps(FACES, separators=(',', ':')).encode()).hexdigest()
    monkeypatch.setattr(identity, 'TARGETS', {('5', NAME, 3): (1, digest)})
    def coords(): return [[.01 if state['mutated'] else 0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]
    def vectors(rows): return [types.SimpleNamespace(x=x, y=y, z=z) for x, y, z in rows]
    class Mesh:
        def GetName(self): return NAME
        def GetVerticesCount(self): return 3
        def GetFacesCount(self): return 1
        def GetFace(self, i): return FACES[i]
        def GetVertices(self, world): return vectors(coords())
        def GetVertex(self, i, world): return vectors(coords())[i]
        def ReplaceMesh(self, path, option, uv):
            calls.append(('replace', option, uv))
            assert uv is False
            if failure == 'mutation_after_replace': state['mutated'] = True
            return {'returned': True}
    mesh = Mesh()
    part = types.SimpleNamespace(GetAvatarPartType=lambda: '5', GetName=lambda: NAME, GetMeshes=lambda b: [mesh])
    avatar = types.SimpleNamespace(GetSubdivMeshLevel=lambda: 0, GetAvatarParts=lambda: [part])
    def full(a, api):
        assert not hasattr(api, 'force_avatar_scene_evaluation')
        return dict(meshes=[dict(owner='avatar/5:' + NAME, name=NAME, vertex_count=3, face_count=1,
            faces_sha256=digest, vertices=coords())], parts=[dict(owner='avatar', type='5', name=NAME)],
            owner_transforms=[], owner_transform_errors=[], working_subdivision=0, expression_count=379)
    monkeypatch.setattr(support, 'capture_geometry', full)
    monkeypatch.setattr(queries, 'query_support_levels', lambda a: dict(consistent=True))
    def body(a, api, include_world):
        assert not hasattr(api, 'force_avatar_scene_evaluation')
        return dict(local=[[0., 0., 0.]], world=[[0., 0., 0.]], scene_explicitly_settled=False)
    monkeypatch.setitem(sys.modules, 'cc_capture_assembly_geometry_v1', types.SimpleNamespace(capture_body_snapshot=body))
    def export(part, path, flags):
        assert part is avatar, 'No part export may be retried'
        assert flags == 48
        calls.append(('export', flags))
        if failure == 'unsupported_export': raise ValueError('part export not supported')
        Path(path).write_text(OBJ); return True
    def save(path): Path(path).write_bytes(b'project'); return True
    def load(path, label):
        if Path(path).name.startswith('immutable'): state['mutated'] = False
        return {}, {}
    R = types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=lambda a: None),
        RFileIO=types.SimpleNamespace(SaveProject=save, ExportObjFile=export),
        EExport3DFileOption_AllClothes=16, EExport3DFileOption_FullBodyPart=32, EReplaceMeshOption_ZUp=2)
    api = types.SimpleNamespace(RLPy=R, sha256_file=sha, bodyfit_freeze_file_record=record,
        read_json=lambda p: json.loads(Path(p).read_text()), write_json=lambda x, p: Path(p).write_text(json.dumps(x)),
        now=lambda: 'fixture', checked=lambda label, status: status, load_file_with_optional_undo_warning=load,
        _transform_data=lambda x: {}, capture_eye_integrity_state=lambda a: {}, capture_eye_part_morph_weights=lambda a: [],
        avatar_material_fingerprint=lambda a: {'digest': 'same', 'errors': [{'texture': 'pixels unavailable'}]},
        compare_neutral_eye_states=lambda *a, **kw: dict(matches=True), render_preview=lambda p: Path(p).write_bytes(b'image'))
    normal_evidence = root / 'normal_evidence.json'
    normal_evidence.write_text(json.dumps(dict(success=False,restored_source=True,source_project=record(source),error=dict(message='Identity changed re-exported UV/normals/material-corner assignment'),steps=[dict(phase=phase,passed=True)for phase in ('after_identity_raw','after_identity_render','after_identity_export')])))
    model_path = root / 'inverse_model.json'
    model_path.write_text(json.dumps(dict(source_project=record(source), target=dict(part_type='5', mesh_name=NAME, vertex_count=3), source_files=dict(report=record(evidence)), fitter=record(Path(inverse.__file__)), metrics={}, submitted_compensated_input_cm=coords())))
    monkeypatch.setattr(inverse, 'verify_model', lambda m: {'fixture': True})
    monkeypatch.setattr(inverse, 'verify_live_origin', lambda m, s: {'fixture': True})
    config = dict(identity_only=True, save_current_scene_backup=True, replace_uv=False, apply_lash_asset=False,
        source_project=record(source), persistence_diagnostic_report=record(evidence),
        single_part_failure_report=record(failed), export_strategy='whole_avatar_extract_inverse_affine_identity_v5',
        normal_validation='native_geometry_rebuild_one_display_unit_v1', normal_rebuild_evidence_report=record(normal_evidence),
        identity_input_space='source_bound_v3_empirical_inverse_affine_once', native_activeworld_mismatch_report=record(mismatch), inverse_affine_model=record(model_path),
        target=dict(part_type='5', mesh_name=NAME, vertex_count=3))
    result = identity.run({'refresh_eye_support_identity': config}, str(root / 'identity'), lambda x: None, api)
    report = json.loads(Path(result['report_path']).read_text())
    assert result['success'] is (failure is None)
    assert result['restored_source'] and not state['mutated'] and result['source_unchanged']
    assert result['geometry_repair_accepted'] is False and report['material_pixels_verified'] is False
    assert sum(c[0] == 'replace' for c in calls) == (0 if failure == 'unsupported_export' else 1)
    assert result['summary_path'] != result['report_path']
