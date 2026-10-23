"""Expected protected violations must remain evidence, never acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_eye_support_diagnostic_v1 as diag
import cc_refresh_eyelash_probe_v2 as lash
import cc_repair_headshot_support_materials_v1 as support
import cc_compile_character_manifest as compiler


def vector(row):
    return types.SimpleNamespace(x=row[0], y=row[1], z=row[2])


class Mesh:
    def __init__(self, name, count, state): self.name, self.count, self.state = name, count, state
    def GetName(self): return self.name
    def GetVerticesCount(self): return self.count
    def GetFacesCount(self): return 1
    def GetFace(self, i): return [0, 1, 2]
    def GetVertices(self, world):
        assert world is False, 'Inactive high world must never be queried'
        shift = .01 if self.state['applied'] and self.count in (182, 190) else 0
        return [vector([shift, 0., 0.]) for _ in range(self.count)]
    def GetVertex(self, i, world):
        assert world is False
        shift = .01 if self.state['applied'] and self.count in (182, 190) else 0
        v = vector([shift, 0., 0.])
        if self.state.get('bad_scalar'): v.x += .001
        return v


class Avatar:
    def __init__(self, state): self.state = state
    def GetSubdivMeshLevel(self): return self.state.get('level', 0)
    def GetAvatarParts(self):
        result = []
        for kind, name, counts in [('5', 'CC_Base_EyeOcclusion', [182, 650]), ('6', 'CC_Base_TearLine', [190, 652])]:
            meshes = [Mesh(name, n, self.state) for n in counts]
            result.append(types.SimpleNamespace(GetAvatarPartType=lambda kind=kind: kind,
                GetName=lambda name=name: name, GetMeshes=lambda all, meshes=meshes: meshes))
        return result


def test_readback_crosschecks_all_four_levels_without_updates_or_world():
    state = {'applied': False}; avatar = Avatar(state)
    baseline = diag.query_support_levels(avatar)
    state['applied'] = True
    after = diag.query_support_levels(avatar)
    assert baseline['consistent'] and after['consistent']
    moved = [r for r in diag.support_deltas(baseline, after) if r['maximum_local_delta_mm'] > .002]
    assert [(r['name'], r['vertex_count']) for r in moved] == [('CC_Base_EyeOcclusion', 182), ('CC_Base_TearLine', 190)]
    assert moved[0]['maximum_local_delta_mm'] == pytest.approx(.1)
    assert len(moved[0]['over_protection_limit_indices']) == 182
    state['bad_scalar'] = True
    assert not diag.query_support_levels(avatar)['consistent']


def test_capture_complete_requires_exact_sequence_restoration_and_unchanged_source():
    assert diag.capture_complete(diag.PHASES, True, True)
    assert not diag.capture_complete(diag.PHASES[:-1], True, True)
    assert not diag.capture_complete(diag.PHASES, False, True)
    assert not diag.capture_complete(diag.PHASES, True, False)


@pytest.mark.parametrize('render_fails', [False, True])
def test_full_run_keeps_violation_false_acceptance_and_always_restores(tmp_path, monkeypatch, render_fails):
    state = {'applied': False}; avatar = Avatar(state); trace = []
    root = tmp_path / 'refresh'; root.mkdir()
    source = root / 'source.ccProject'; source.write_bytes(b'immutable source')
    registry = root / 'registry.json'; registry.write_text('{}')
    asset = root / 'Delicate.ccAvatarPreset'; asset.write_bytes(b'fixture asset')
    def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    record = lambda path: dict(path=str(path), sha256=sha(path), bytes=Path(path).stat().st_size)
    for name in ('CREATION_ROOT', 'RUN_ROOT', 'STAGE_ROOT'): monkeypatch.setattr(lash, name, str(root))
    monkeypatch.setattr(lash, 'REGISTRY', str(registry))
    monkeypatch.setattr(lash, 'validate_addition_evidence', lambda *args: {'fixture': True})
    entry = dict(asset_id=lash.DELICATE_ID, sha256=sha(asset), path=str(asset),
                 application_mode='character_preset_replace', slot='eyelashes')
    monkeypatch.setattr(compiler, 'facial_pool', lambda *args: dict({str(i): {} for i in range(8)}, **{lash.DELICATE_ID: entry}))
    def full_capture(current, api):
        queries = diag.query_support_levels(current)
        rows = [dict(owner=m['owner'], name=m['name'], vertex_count=m['vertex_count'],
            face_count=m['face_count'], faces_sha256=m['faces_sha256'], vertices=m['local']) for m in queries['levels']]
        parts = [dict(owner='avatar', type='5', name='CC_Base_EyeOcclusion'), dict(owner='avatar', type='6', name='CC_Base_TearLine')]
        transforms = []
        if state['applied']:
            for key in lash.DELICATE_ADDITIONS:
                rows.append(dict(zip(('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256'), key), vertices=[[0., 0., 0.]]))
                parts.append(dict(owner='avatar', type='9', name=key[1]))
        transform = {'translation': dict(x=0., y=0., z=0.), 'rotation': dict(x=0., y=0., z=0., w=1.)}
        for owner in ['avatar'] + sorted({r['owner'] for r in rows}):
            for space in ('local', 'world'): transforms.append(dict(owner=owner, space=space, value=copy.deepcopy(transform)))
        return dict(meshes=rows, parts=parts, owner_transforms=transforms, owner_transform_errors=[],
                    working_subdivision=0, expression_count=379)
    monkeypatch.setattr(support, 'capture_geometry', full_capture)
    def body_capture(current, api, include_world):
        assert not hasattr(api, 'force_avatar_scene_evaluation')
        rows = [[0., 0., 0.]] * lash.BODY_COUNT
        return dict(local=rows, world=rows, working_subdivision_level=0, scene_explicitly_settled=False)
    monkeypatch.setitem(sys.modules, 'cc_capture_assembly_geometry_v1', types.SimpleNamespace(capture_body_snapshot=body_capture))
    def save(path): trace.append('save:' + Path(path).name); Path(path).write_bytes(b'scene'); return True
    def load(path, label):
        trace.append('load:' + Path(path).name)
        state['applied'] = Path(path).name.startswith('DIAGNOSTIC_ONLY')
        return {}, {}
    def apply(*args, **kwargs):
        trace.append('apply'); state['applied'] = True
        return avatar, {'steps': [dict(character_preset_verified=True, eye_geometry_preserved=True, eye_support_preserved=True)]}
    def render(path):
        trace.append('render')
        if render_fails: raise ValueError('fixture render failure')
        Path(path).write_bytes(b'image')
    R = types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=lambda a: None),
        RFileIO=types.SimpleNamespace(SaveProject=save), EObjectModifiedType_MorphWeight='morph',
        RGlobal=types.SimpleNamespace(GetTime=lambda: 0, GetStartTime=lambda: 0,
            SetTime=lambda *a: trace.append('time') or True,
            ObjectModified=lambda *a: trace.append('notify') or True))
    api = types.SimpleNamespace(RLPy=R, sha256_file=sha, bodyfit_freeze_file_record=record,
        read_json=lambda path: json.loads(Path(path).read_text()),
        write_json=lambda value, path: Path(path).write_text(json.dumps(value)), now=lambda: 'fixture',
        checked=lambda label, status: status, load_file_with_optional_undo_warning=load,
        apply_appearance_assets=apply, _transform_data=lambda x: {}, capture_eye_integrity_state=lambda a: {},
        capture_eye_part_morph_weights=lambda a: [], compare_neutral_eye_states=lambda *a, **kw: {'matches': True},
        render_preview=render, QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(processEvents=lambda: None)),
        QtGui=types.SimpleNamespace(QImage=lambda path: types.SimpleNamespace(isNull=lambda: False, width=lambda: 10, height=lambda: 10)))
    config = dict(diagnostic_only=True, save_current_scene_backup=True, allow_expected_protected_violation_capture=True,
        source_project=record(source), registry=record(registry), eyelash_asset_id=lash.DELICATE_ID, case_id='fixture')
    result = diag.run({'refresh_eye_support_diagnostic': config}, str(root / 'diagnostic'), lambda s: None, api)
    report = json.loads(Path(result['report_path']).read_text())
    assert report['geometry_accepted'] is False and report['protected_violation_observed'] is True
    assert report['restoration']['restored'] and not state['applied']
    assert result['success'] is (not render_fails)
    assert ('notify' in trace) is (not render_fails)
    if not render_fails:
        assert [r['label'] for r in report['captures']] == list(diag.PHASES)
        assert trace.index('apply') < trace.index('time') < trace.index('render') < trace.index('notify')
        assert not report['captures'][1]['protected_geometry_check']['passed']
    assert result['summary_path'] != result['report_path']
