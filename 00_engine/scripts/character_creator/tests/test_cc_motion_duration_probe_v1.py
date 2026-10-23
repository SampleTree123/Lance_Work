"""Bounded duration probe tests use extracted functions, never import RLPy/CC."""
import ast
import copy
import hashlib
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace as NS
import traceback

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'cc_validate_body_reconstruction.py'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(path):
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


@pytest.fixture
def setup(tmp_path):
    wanted = {'validate_motion_library_duration_request', 'probe_motion_library_durations'}
    tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    env = dict(os=os, math=math, traceback=traceback, ReconstructionError=ValueError, sha256_file=sha,
               SCRIPT_DIR=str(tmp_path/'scripts/character_creator'), ENGINE_ROOT=str(tmp_path), now=lambda: 'test-time')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), env)
    stage = tmp_path/'scripts/character_creator/runtime_staging/motion_library_expansion_20261009_v1'
    project = stage/'source_copies/CFD40_AM_001.ccProject'
    project.parent.mkdir(parents=True)
    project.write_bytes(b'isolated-native-carrier')
    motions = []
    for i, suffix in enumerate(('.rlMotion', '.iMotion')):
        p = stage/'motion_copies'/('motion'+str(i)+suffix)
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(('native-motion-'+str(i)).encode())
        motions.append({'candidate_id': 'MOTION_'+str(i), 'source': record(p)})
    env['MOTION_DURATION_CARRIER_SHA256'] = {project.name: sha(project)}
    library = {'motion_library_duration_probe': {'project_copy': record(project), 'motions': motions}}
    output = tmp_path/'outputs/character_creator_bridge/artifacts/motion_library_expansion_20261009_v1/probe01'
    return env, library, output, stage


def test_accepts_both_native_formats(setup):
    env, library, output, _ = setup
    project, motions, actual = env['validate_motion_library_duration_request'](library, str(output))
    assert len(motions) == 2 and actual == str(output) and project['sha256']


@pytest.mark.parametrize('mutation', ['empty', 'too_many', 'duplicate_id', 'duplicate_path', 'bad_id', 'outside', 'sibling_root', 'wrong_suffix', 'wrong_hash', 'wrong_size', 'bool_size', 'unknown_carrier', 'bad_carrier_hash', 'output_outside', 'output_nonempty'])
def test_rejects_before_application_access(setup, mutation):
    env, library, output, stage = setup
    payload = library['motion_library_duration_probe']
    source = payload['motions'][0]['source']
    if mutation == 'empty': payload['motions'] = []
    elif mutation == 'too_many': payload['motions'] *= 16
    elif mutation == 'duplicate_id': payload['motions'][1]['candidate_id'] = payload['motions'][0]['candidate_id']
    elif mutation == 'duplicate_path': payload['motions'][1]['source'] = source
    elif mutation == 'bad_id': payload['motions'][0]['candidate_id'] = '../escape'
    elif mutation in ('outside', 'sibling_root', 'wrong_suffix'):
        p = (stage/'motion_copies_bad/motion.rlMotion' if mutation == 'sibling_root' else stage/'outside.rlMotion' if mutation == 'outside' else stage/'motion_copies/motion.py')
        p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'other')
        payload['motions'][0]['source'] = record(p)
    elif mutation == 'wrong_hash': source['sha256'] = '0'*64
    elif mutation == 'wrong_size': source['bytes'] += 1
    elif mutation == 'bool_size': source['bytes'] = True
    elif mutation == 'unknown_carrier': env['MOTION_DURATION_CARRIER_SHA256'] = {}
    elif mutation == 'bad_carrier_hash': payload['project_copy']['sha256'] = 'f'*64
    elif mutation == 'output_outside': output = stage/'escape'
    elif mutation == 'output_nonempty': output.mkdir(parents=True); (output/'old.json').write_text('{}')
    with pytest.raises(ValueError):
        env['probe_motion_library_durations'](library, str(output), lambda _: None)
    assert 'RLPy' not in env


class Tick:
    def __init__(self, seconds): self.seconds = seconds
    def ToInt64(self): return round(self.seconds*6000)


def fake_runtime(env, library, *, props_on_second=False, fail_second=False):
    state = {'body': 1, 'face': 1, 'loads': [], 'motion_index': -1, 'cleanups': 0}
    clip = NS(GetLength=lambda: Tick(6.25 if state['motion_index'] == 0 else 4.25),
              GetClipLength=lambda: Tick(6.25 if state['motion_index'] == 0 else 4.25), GetSpeed=lambda: 1, GetLoopCount=lambda: 1)
    skeleton = NS(GetClipCount=lambda: state['body'], GetClip=lambda _: clip)
    face = NS(GetClipCount=lambda: state['face'])
    avatar = NS(GetSkeletonComponent=lambda: skeleton, GetFaceComponent=lambda: face)
    def load(path, undo):
        assert undo is False
        state['loads'].append(path)
        if path != library['motion_library_duration_probe']['project_copy']['path']:
            assert state['body'] == state['face'] == 0
            state['motion_index'] += 1
            if fail_second and state['motion_index'] == 1:
                raise ValueError('native load failed')
            state['body'] = 1
        return True
    def clear(_):
        before = {'body': state['body'], 'face': state['face']}
        state.update(body=0, face=0, cleanups=state['cleanups']+1)
        return {'before': before, 'after': {'body': 0, 'face': 0}}
    fps = NS(ToFloat=lambda: 60., GetFrameIndex=lambda t: round(t.seconds*60))
    env.update(RLPy=NS(RFileIO=NS(LoadFile=load), RScene=NS(SelectObject=lambda _: None),
        RGlobal=NS(GetTime=lambda: Tick(0), GetStartTime=lambda: Tick(0), GetEndTime=lambda: Tick(1), IsPlaying=lambda: False,
                   GetFps=lambda: fps, SetTime=lambda *_: True, SetStartTime=lambda _: True, SetEndTime=lambda _: True),
        IndexedFrameTime=lambda i, f: Tick(i/60), RTick=NS(ToSecond=lambda ticks: ticks/6000)),
        QtWidgets=NS(QApplication=NS(processEvents=lambda: None)), resolve_avatar=lambda: (avatar, [avatar]),
        scene_object_id=lambda _: 'same-avatar', clear_avatar_motion=clear,
        checked=lambda label, value: value, write_json=lambda d, p: Path(p).write_text(json.dumps(d), encoding='utf8'),
        _motion_scene_prop_inventory=lambda: {'available': True, 'objects': ['new prop'] if props_on_second and state['motion_index'] == 1 else []})
    return state


def test_loads_carrier_once_records_true_seconds_and_cleans_each_clip(setup):
    env, library, output, _ = setup
    state = fake_runtime(env, library)
    result = env['probe_motion_library_durations'](library, str(output), lambda _: None)
    report = json.loads((output/'motion_duration_probe.json').read_text())
    assert result['success'] and len(state['loads']) == 3
    assert report['carrier_load_count'] == 1
    assert [r['duration_seconds'] for r in report['results']] == [6.25, 4.25]
    assert [r['native_five_second_candidate'] for r in report['results']] == [True, False]
    assert state['body'] == state['face'] == 0 and report['sources_unchanged']
    assert report['exported'] is report['rendered'] is report['project_saved'] is False


def test_failure_stops_batch_records_partial_results_and_cleans(setup):
    env, library, output, _ = setup
    state = fake_runtime(env, library, fail_second=True)
    with pytest.raises(ValueError): env['probe_motion_library_durations'](library, str(output), lambda _: None)
    report = json.loads((output/'motion_duration_probe.json').read_text())
    assert not report['success'] and report['sources_unchanged']
    assert len(report['results']) == 1 and state['body'] == state['face'] == 0


@pytest.mark.parametrize('observation', ['unavailable', 'existing', 'added'])
def test_prop_observation_never_masquerades_as_visual_acceptance_or_blocks_duration(setup, observation):
    env, library, output, _ = setup
    state = fake_runtime(env, library, props_on_second=observation=='added')
    if observation == 'unavailable': env['_motion_scene_prop_inventory'] = lambda: {'available': False, 'objects': []}
    elif observation == 'existing': env['_motion_scene_prop_inventory'] = lambda: {'available': True, 'objects': ['carrier prop']}
    env['probe_motion_library_durations'](library, str(output), lambda _: None)
    report = json.loads((output/'motion_duration_probe.json').read_text())
    assert report['success'] and len(report['results']) == 2
    assert all(r['prop_free_visual_acceptance'] is False for r in report['results'])
    assert report['results'][-1]['scene_prop_observation'] == {'unavailable': 'props_unobservable', 'existing': 'unchanged', 'added': 'changed_requires_review'}[observation]


def test_dispatch_only_new_explicit_mode_and_no_guard_for_new_mode():
    text = SOURCE.read_text(encoding='utf-8-sig')
    tree = ast.parse(text)
    dispatch = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_run_library_without_dialog_guard')
    branches = [n for n in dispatch.body if isinstance(n, ast.If) and 'motion_library_duration_probe' in ast.unparse(n.test)]
    assert len(branches) == 1 and 'probe_motion_library_durations' in ast.unparse(branches[0])
    outer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_library')
    assert 'motion_library_duration_probe' in ast.unparse(outer.body[0].test)
