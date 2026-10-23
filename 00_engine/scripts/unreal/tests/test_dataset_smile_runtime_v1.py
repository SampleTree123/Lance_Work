"""Offline checks for production smile lookup, preserved assembly, and resume."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('_test_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


@pytest.fixture
def runtime(tmp_path):
    value = load('dataset_smile_runtime_v1')
    value.CATALOG = tmp_path / 'dataset_smile_v1.json'
    value.CATALOG.write_text(json.dumps({'face_id': 'smile', 'static': {
        'female': {'animation': '/Game/Smile/F'}, 'male': {'animation': '/Game/Smile/M'}},
        'motions': [{'sex': 'female', 'source_animation': '/Game/Body/A.A',
                     'animation': '/Game/Smile/A.A', 'duration_seconds': 10.}]}))
    return value


class Clip:
    def __init__(self, path, duration=10., skeleton='skeleton'):
        self.path, self.duration, self.skeleton = path, duration, skeleton
    def get_path_name(self): return self.path
    def get_skeleton(self): return self.skeleton
    def get_play_length(self): return self.duration


def scene(clip):
    calls = []
    mesh = NS(get_editor_property=lambda name: 'skeleton')
    body = NS(get_skeletal_mesh_asset=lambda: mesh,
              set_animation_mode=lambda mode: calls.append(('mode', mode)),
              override_animation_data=lambda *args: calls.append(('override', args)),
              play_animation=lambda *args: calls.append(('play', args)),
              set_position=lambda *args: calls.append(('position', args)),
              stop=lambda: calls.append(('stop',)))
    def assemble(u, actor, selected, t, motion, **kwargs):
        calls.append(('assembly', copy.deepcopy(selected), motion, kwargs))
        return {'selection': selected, 'animation_path': '/Game/Body/A.A',
                'components': {'Body': '/Game/Character.C'}, 'pair_revision': {'lashes': 4}}
    current = {'assembly': NS(apply_actor=assemble, fixed=NS(actor_components=lambda a: {'Body': body})),
               'data': {'catalog': True}}
    u = NS(AnimSequence=Clip, load_asset=lambda path: clip,
           AnimationMode=NS(ANIMATION_SINGLE_NODE='single'))
    return u, current, calls


def test_lookup_normalizes_paths_and_fails_closed(runtime):
    assert runtime.resolve('female', '/Game/Body/A')['animation'] == '/Game/Smile/A.A'
    assert runtime.resolve('male')['animation'] == '/Game/Smile/M.M'
    with pytest.raises(ValueError, match='Require one prebuilt'):
        runtime.resolve('male', '/Game/Body/A')
    document = json.loads(runtime.CATALOG.read_text())
    document['motions'] *= 2
    runtime.CATALOG.write_text(json.dumps(document))
    with pytest.raises(ValueError, match='Require one prebuilt'):
        runtime.resolve('female', '/Game/Body/A')


def test_missing_catalog_reports_exact_required_path(runtime):
    runtime.CATALOG.unlink()
    with pytest.raises(FileNotFoundError, match='Missing production smile catalog'):
        runtime.manifest_digest()


@pytest.mark.parametrize('moving', [False, True])
def test_apply_uses_neutral_assembly_then_prebuilt_smile_and_preserves_readback(runtime, moving):
    clip = Clip('/Game/Smile/A.A')
    u, current, calls = scene(clip)
    selected = {'sex': 'female', 'face_id': 'smile', 'choice': {'hair_id': 'H'}}
    source = Clip('/Game/Body/A.A') if moving else None
    result = runtime.apply(u, current, 'actor', selected, 0., source, body_action_id='walk')
    assert calls[0][0] == 'assembly' and calls[0][1]['face_id'] == 'none'
    assert calls[0][2] is source
    assert result['selection'] == selected and selected['face_id'] == 'smile'
    assert result['pair_revision'] == {'lashes': 4}
    assert result['components'] == {'Body': '/Game/Character.C'}
    assert result['animation_path'] == ('/Game/Smile/A.A' if moving else '/Game/Smile/F.F')
    assert result['face']['runtime_composition'] is False
    assert calls[-2:] == [('position', (0., False)), ('stop',)]
    assert calls[2] == ('override', (clip, False, False, 0., 1.))


def test_invalid_prebuilt_clip_rejected_before_assembly(runtime):
    u, current, calls = scene(Clip('/Game/Smile/A.A', duration=5.))
    with pytest.raises(ValueError, match='duration'):
        runtime.apply(u, current, 'actor', {'sex': 'female', 'face_id': 'smile'}, 0., Clip('/Game/Body/A.A'))
    assert not calls


def test_main_and_reference_resume_signatures_change_with_catalog(runtime):
    main = load('ue_dataset_render_v11')
    main.module = lambda name: runtime
    reference = load('ue_dataset_reference_v11')
    reference.module = lambda name: main
    job = {'job_id': 'example'}
    before = main.signature(job), reference.signature(job)
    document = json.loads(runtime.CATALOG.read_text())
    document['static']['female']['animation'] = '/Game/Smile/F_updated'
    runtime.CATALOG.write_text(json.dumps(document))
    after = main.signature(job), reference.signature(job)
    assert all(a != b for a, b in zip(before, after))
    assert main.VERSION == 3 and reference.VERSION == 3
    assert load('ue_dataset_reference_pilot_v11').VERSION == 6


def test_main_selection_requests_smile_before_contract_validation():
    main = load('ue_dataset_render_v11')
    contract = NS(default_selection=lambda data, sex: {'sex': sex},
                  validate_selection=lambda value, data, **kwargs: value)
    current = {'graph': NS(load=lambda name: contract), 'data': {}}
    job = {'state': {'sex': 'female', 'identity': 'F1', 'hair_color': 'black',
                     'wardrobe': {'slot': 'shirt'}, 'hair': 'H', 'action': 'walk'}}
    selected = main.selection(job, current)
    assert selected['face_id'] == 'smile'
    assert selected['choice'] == {'slot': 'shirt', 'hair_id': 'H'}
    assert 'hair_id' not in job['state']['wardrobe']
