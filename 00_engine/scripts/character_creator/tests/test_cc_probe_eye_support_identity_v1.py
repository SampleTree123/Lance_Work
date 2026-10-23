"""One identity call must preserve source geometry, normals and UV exactly."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_probe_eye_support_identity_v1 as identity
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
    with pytest.raises(ValueError, match='world disagree'):
        identity.write_identity_world_obj(parsed, [[0., .01, 0.], [1., 0., 0.], [0., 1., 0.]], tmp_path / 'bad.obj')


@pytest.mark.parametrize('text', [OBJ.replace('1/1/1', '1//1'), OBJ.replace('vn 0 0 1', 'vn 0 0 0'),
                                OBJ.replace(NAME, 'WrongMesh'), OBJ.replace('3/3/1', '3/4/1')])
def test_missing_or_invalid_native_corner_data_cannot_reach_replacement(tmp_path, text):
    path = tmp_path / 'native.obj'; path.write_text(text)
    with pytest.raises(ValueError): identity.parse_native_obj(path, NAME, 3, FACES)


@pytest.mark.parametrize('failure', [None, 'unsupported_export', 'mutation_after_replace'])
def test_complete_runtime_candidate_only_one_call_and_restores_source(tmp_path, monkeypatch, failure):
    root = tmp_path / 'refresh'; root.mkdir()
    source = root / 'source.ccProject'; source.write_bytes(b'original')
    state = {'mutated': False}; calls = []
    def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    record = lambda p: dict(path=str(p), sha256=sha(p), bytes=Path(p).stat().st_size)
    evidence = root / 'diagnostic.json'
    evidence.write_text(json.dumps(dict(capture_complete=True, geometry_accepted=False, source_project=record(source))))
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
        calls.append(('export', flags))
        if failure == 'unsupported_export': raise ValueError('part export not supported')
        Path(path).write_text(OBJ); return True
    def save(path): Path(path).write_bytes(b'project'); return True
    def load(path, label):
        if Path(path).name.startswith('immutable'): state['mutated'] = False
        return {}, {}
    R = types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=lambda a: None),
        RFileIO=types.SimpleNamespace(SaveProject=save, ExportObjFile=export),
        EExport3DFileOption__None=0, EReplaceMeshOption_ZUp=2)
    api = types.SimpleNamespace(RLPy=R, sha256_file=sha, bodyfit_freeze_file_record=record,
        read_json=lambda p: json.loads(Path(p).read_text()), write_json=lambda x, p: Path(p).write_text(json.dumps(x)),
        now=lambda: 'fixture', checked=lambda label, status: status, load_file_with_optional_undo_warning=load,
        _transform_data=lambda x: {}, capture_eye_integrity_state=lambda a: {}, capture_eye_part_morph_weights=lambda a: [],
        avatar_material_fingerprint=lambda a: {'digest': 'same', 'errors': [{'texture': 'pixels unavailable'}]},
        compare_neutral_eye_states=lambda *a, **kw: dict(matches=True), render_preview=lambda p: Path(p).write_bytes(b'image'))
    config = dict(identity_only=True, save_current_scene_backup=True, replace_uv=False, apply_lash_asset=False,
        source_project=record(source), persistence_diagnostic_report=record(evidence),
        target=dict(part_type='5', mesh_name=NAME, vertex_count=3))
    result = identity.run({'refresh_eye_support_identity': config}, str(root / 'identity'), lambda x: None, api)
    report = json.loads(Path(result['report_path']).read_text())
    assert result['success'] is (failure is None)
    assert result['restored_source'] and not state['mutated'] and result['source_unchanged']
    assert result['geometry_repair_accepted'] is False and report['material_pixels_verified'] is False
    assert sum(c[0] == 'replace' for c in calls) == (0 if failure == 'unsupported_export' else 1)
    assert result['summary_path'] != result['report_path']
