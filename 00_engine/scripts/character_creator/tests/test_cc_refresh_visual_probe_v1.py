"""SDK control flow, image validity and guaranteed source reload without CC."""
from pathlib import Path
import hashlib
import json
import sys
from types import SimpleNamespace as NS

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_visual_probe_v1 as visual


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(path):
    return {'path': str(path), 'sha256': sha(path), 'bytes': Path(path).stat().st_size}


def environment(tmp_path, monkeypatch, *, fail_image=None, level=0, expression_scale=1):
    creation, refresh, camera = (tmp_path / x for x in ('creation', 'refresh', 'camera'))
    for p in (creation, refresh, camera): p.mkdir()
    light = tmp_path / 'light.ccLightroom'
    source = creation / 'corrected.ccProject'
    cam = camera / 'Ref Cam Female L.ccCam'
    for p in (source, cam, light): p.write_bytes(b'fixture asset')
    for key, value in [('CREATION_ROOT', creation), ('RUN_ROOT', refresh), ('CAMERA_ROOT', camera), ('LIGHT', light)]:
        monkeypatch.setattr(visual, key, str(value))
    session = {'loads': [], 'renders': [], 'backup_count': 0}
    names = ['Eye_Blink_L', 'Eye_Blink_R', 'Eyelashes_Down_IN_L', 'Eyelashes_Down_OUT_L',
             'Eyelashes_Down_IN_R', 'Eyelashes_Down_OUT_R', 'C_BlinkL', 'C_BlinkR']
    class Face:
        def __init__(self): self.weights = dict.fromkeys(names, 0.)
        def GetExpressionNames(self, _): return names
        def GetExpressionSetUid(self): return 'fixture-profile'
        def GetExpressionWeights(self, time, given): return [self.weights[name] * expression_scale for name in given]
        def BeginKeyEditing(self): return True
        def EndKeyEditing(self): return True
        def AddExpressionKeys(self, t, given, weights, interval): self.weights.update(zip(given, weights)); return True
    class Avatar:
        def __init__(self): self.face = Face()
        def GetSubdivMeshLevel(self): return level
        def GetID(self): return 1
        def GetFaceComponent(self): return self.face
        def GetMeshes(self, _):
            return [NS(GetName=lambda: 'CC_Base_Body', GetVertices=lambda _: [NS(x=0., y=1., z=2.)])]
        def GetSkeletonComponent(self):
            return NS(GetSkinBones=lambda: [NS(GetName=lambda: 'CC_Base_Head', WorldTransform=lambda: None)])
    session['avatar'] = Avatar()
    def load(path, label):
        session['loads'].append((str(path), label))
        session['avatar'] = Avatar()
        return True, []
    def save(path):
        Path(path).write_bytes(b'current scene backup')
        session['backup_count'] += 1
        return True
    def render(path, t):
        session['renders'].append(Path(path).name)
        if Path(path).name == fail_image: raise RuntimeError('Injected render failure')
        Image.new('RGB', (64, 48), (80, 90, 100)).save(path)
    class QImage:
        def __init__(self, path): self.image = Image.open(path)
        def isNull(self): return False
        def width(self): return self.image.width
        def height(self): return self.image.height
    api = NS(RLPy=NS(
        RScene=NS(GetAvatars=lambda: [session['avatar']], SelectObject=lambda a: None),
        RFileIO=NS(SaveProject=save, LoadFile=lambda p: True),
        RGlobal=NS(GetStartTime=lambda: 0, GetFps=lambda: 60, SetTime=lambda t, force: True),
        IndexedFrameTime=lambda a, b: 0), QtGui=NS(QImage=QImage),
        checked=lambda label, value: value, sha256_file=sha, bodyfit_freeze_file_record=record,
        now=lambda: '2026-10-18T00:00:00+08:00',
        write_json=lambda value, path: Path(path).write_text(json.dumps(value), encoding='utf-8'),
        load_file_with_optional_undo_warning=load, force_avatar_scene_evaluation=lambda a: None,
        profile_upgrade_pose_specs=lambda names: ({'blink_bilateral_front': dict.fromkeys(names, 1.)}, {}),
        set_avatar_position=lambda a, *pos: None, set_avatar_yaw=lambda a, yaw: None,
        _transform_data=lambda t: {'translation': dict(x=0., y=0., z=0.)}, render_preview=render,
        expression_weights_at=lambda f, t, n: f.weights)
    config = {'case_id': 'fixture', 'sex': 'female', 'source_project': record(source),
              'camera': record(cam), 'light': record(light), 'poses': ['neutral', 'blink'],
              'views': ['front', 'side'], 'working_subdivision_level': 0, 'save_current_scene_backup': True,
              'blink_pose_mode': 'direct_six_channels_v3'}
    return api, session, {'refresh_visual_probe': config}, refresh / 'visual', source


def test_four_valid_images_and_actual_subd0_scope_with_neutral_reload(tmp_path, monkeypatch):
    api, session, library, output, source = environment(tmp_path, monkeypatch)
    original = source.read_bytes()
    result = visual.run(library, str(output), lambda _: None, api)
    assert result['success'] and len(result['captures']) == 4
    report = json.loads((output / 'refresh_visual_report.json').read_text())
    assert report['working_subdivision_level'] == 0
    assert report['render_subdivision_verified'] is False and report['render_subdivision_level'] is None
    assert report['restoration']['success'] and report['restoration']['maximum_local_mesh_error_mm'] == 0
    assert source.read_bytes() == original and len(session['loads']) == 2 and session['backup_count'] == 1
    assert all(value == 0 for value in session['avatar'].face.weights.values())
    assert [(c['pose'], c['view']) for c in result['captures']] == [
        ('neutral', 'front'), ('neutral', 'side'), ('blink', 'front'), ('blink', 'side')]
    assert all((c['image']['width'], c['image']['height']) == (64, 48) for c in result['captures'])


def test_render_failure_still_reloads_independent_source_and_preserves_original(tmp_path, monkeypatch):
    api, session, library, output, source = environment(tmp_path, monkeypatch, fail_image='blink_side.png')
    original = sha(source)
    result = visual.run(library, str(output), lambda _: None, api)
    report = json.loads((output / 'refresh_visual_report.json').read_text())
    assert not result['success'] and len(result['captures']) == 3
    assert report['restoration']['success'] and report['source_unchanged']
    assert len(session['loads']) == 2 and all(value == 0 for value in session['avatar'].face.weights.values())
    assert sha(source) == original


def test_wrong_actual_level_is_rejected_without_switching_levels(tmp_path, monkeypatch):
    api, session, library, output, source = environment(tmp_path, monkeypatch, level=1)
    result = visual.run(library, str(output), lambda _: None, api)
    assert not result['success'] and not result['captures'] and session['backup_count'] == 1
    report = json.loads((output / 'refresh_visual_report.json').read_text())
    assert 'actually be active SubD0' in report['error']['message']


def test_invalid_png_or_restored_layout_is_not_reported_valid(tmp_path):
    bad = tmp_path / 'bad.png'; bad.write_bytes(b'not a PNG')
    with pytest.raises(ValueError, match='valid IHDR'): visual.png_dimensions(bad)
    with pytest.raises(ValueError, match='layout'):
        visual.maximum_mesh_error_mm([{'name': 'body', 'vertices': [[0, 0, 0]]}], [])


def test_name_mapping_and_status_tuple_are_aligned_without_assuming_sequence_order():
    face = NS(GetExpressionWeights=lambda t, n: {'right': .5, 'left': 1.})
    readback = visual.expression_readback(face, 0, ['left', 'right'], {'left': 1., 'right': .5})
    assert readback['passed'] and readback['evaluated_weights'] == {'left': 1., 'right': .5}
    face.GetExpressionWeights = lambda t, n: (NS(status=True), [1., .5])
    assert visual.expression_readback(face, 0, ['left', 'right'], {'left': 1., 'right': .5})['passed']


def test_percent_like_sdk_values_fail_and_outer_summary_rewrite_preserves_full_report(tmp_path, monkeypatch):
    api, session, library, output, source = environment(tmp_path, monkeypatch, expression_scale=100)
    summary = visual.run(library, str(output), lambda _: None, api)
    report_path = output / 'refresh_visual_report.json'
    report = json.loads(report_path.read_text())
    assert not summary['success'] and len(report['captures']) == 3
    readback = report['captures'][-1]['expression_readback']
    assert readback['numeric_max'] == 100 and readback['maximum_error'] == 99
    assert not readback['passed'] and readback['evaluated_weights']['Eye_Blink_L'] == 100
    assert report['restoration']['success'] and report['error']
    assert summary['summary_path'] != summary['report_path']
    old_bytes = report_path.read_bytes()
    # Exactly the outer dispatcher's observed post-return write.
    summary['undo_warning_guard'] = {'matched_count': 0}
    api.write_json(summary, summary['summary_path'])
    assert report_path.read_bytes() == old_bytes


def test_direct_pose_requires_six_controls_and_never_keys_derived_correctives():
    names = ['Eye_Blink_L', 'Eye_Blink_R', 'Eyelashes_Down_IN_L', 'Eyelashes_Down_OUT_L',
             'Eyelashes_Down_IN_R', 'Eyelashes_Down_OUT_R', 'C_BlinkL', 'C_BlinkR', 'Jaw_Open']
    selected, keyed, derived = visual.direct_blink_pose(names)
    assert len(selected) == 6 and set(selected.values()) == {1.}
    assert derived == ['C_BlinkL', 'C_BlinkR'] and not set(derived).intersection(keyed)
    assert 'Jaw_Open' in keyed and 'Jaw_Open' not in selected
    with pytest.raises(ValueError, match='Missing required'):
        visual.direct_blink_pose(['Eye_Blink_L', 'Eye_Blink_R'])
