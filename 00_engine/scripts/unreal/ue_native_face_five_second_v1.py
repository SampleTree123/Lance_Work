"""Isolated, unretimed five-second native face samples; no UE work on import.

Run in UE with DM_NATIVE_FACE_FIVE_SECOND_TASK pointing to a task JSON.
Offline --prepare writes the initial tasks only. The existing composer retains
ownership of all-frame curve/bone validation and source preservation checks.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import re

SCRIPTS = Path(__file__).resolve().parent
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/native_face_five_second_20261008_v1')
OLD_RUN = RUN.parent / 'character_runtime_face_library_20261007_v1'
ASSET_ROOT = '/Game/DataMake/Validation/NativeFaceFiveSecond20261008/Composites'
DURATION = 5.0
EXPECTED_FACE_BONES = frozenset(('facialbone', 'jawroot', 'upperjaw', 'l_eye', 'r_eye',
                               'teeth01', 'teeth02', 'tongue01', 'tongue02', 'tongue03'))
TASK_FIELDS = frozenset(('sex', 'composite_id', 'body_animation', 'face_animation',
                        'reference_mesh', 'allowed_face_curve_names', 'face_start_seconds',
                        'face_end_seconds', 'face_rate', 'face_playback', 'body_mode',
                        'static_use_reference_pose', 'report_path'))


def load_isolated(filename, name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def inside_run(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Expected an output path in the five-second run')
    path = Path(value).resolve()
    if not path.is_relative_to(RUN.resolve()) or path == RUN.resolve():
        raise ValueError('Output must remain inside the five-second run')
    return path


def validate_task(task):
    if not isinstance(task, dict) or set(task) != TASK_FIELDS:
        raise ValueError('Exact five-second task fields required; envelopes and overrides are forbidden')
    if task['sex'] not in ('female', 'male') or not isinstance(task['composite_id'], str) or not re.fullmatch('[a-z][a-z0-9_]{0,95}', task['composite_id']):
        raise ValueError('Invalid sample identity')
    if task['body_mode'] != 'static' or task['static_use_reference_pose'] is not True:
        raise ValueError('Five-second samples require static reference body pose')
    if not finite(task['face_rate']) or task['face_rate'] != 1 or task['face_playback'] != 'hold':
        raise ValueError('Native face must play at rate 1 with hold endpoint, never loop')
    start, end = task['face_start_seconds'], task['face_end_seconds']
    if not all(finite(v) for v in (start, end)) or start < 0 or not math.isclose(end-start, DURATION, abs_tol=1e-9, rel_tol=0):
        raise ValueError('Native source window must be exactly five seconds')
    for key in ('body_animation', 'face_animation', 'reference_mesh'):
        value = task[key]
        if not isinstance(value, str) or not value.startswith('/Game/') or '..' in value or '\\' in value:
            raise ValueError('Expected /Game source asset: ' + key)
    curves = task['allowed_face_curve_names']
    if not isinstance(curves, list) or not curves or any(not isinstance(n, str) or not re.fullmatch('[A-Za-z0-9_]+', n) for n in curves):
        raise ValueError('Approved native curve names required')
    if inside_run(task['report_path']).suffix != '.json':
        raise ValueError('Expected JSON report path')
    return task


def composer_module():
    module = load_isolated('ue_compose_native_face_body_v1.py', '_dm_five_second_composer')
    module.RUN, module.ASSET_ROOT = RUN, ASSET_ROOT
    if module.FACE_BONES != EXPECTED_FACE_BONES:
        raise ValueError('Composer facial support scope changed')
    return module


def run(task):
    validate_task(task)  # Reject retiming/loop/envelope before loading Unreal.
    import unreal as u
    body = u.load_asset(task['body_animation'])
    if not isinstance(body, u.AnimSequence):
        raise ValueError('Expected native body sequence for sampling rate')
    rate = body.data_model_interface.get_frame_rate()
    fps = float(rate.numerator) / float(rate.denominator)
    if not math.isfinite(fps) or fps <= 0 or not math.isclose(DURATION*fps, round(DURATION*fps), abs_tol=1e-8, rel_tol=0):
        raise ValueError('Body sampling rate cannot represent an exact five-second clip')
    return composer_module().run(task)


def write_new_or_identical(path, data):
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != data:
            raise ValueError('Refusing to overwrite different task: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def prepare_initial_tasks():
    """Reuse audited meshes/curve allowlists and existing reference-body sources."""
    meshes = json.loads((OLD_RUN / 'runtime_face_inputs.json').read_text(encoding='utf-8'))['meshes']
    rows = []
    for sex in ('female', 'male'):
        mesh = next(m for m in meshes if m['sex'] == sex and '/cc_base_body.' in m['path'])
        previous = json.loads((OLD_RUN / 'compositions/final_v3' / (sex + '_review_dramatic_sad_static_v2_task.json')).read_text(encoding='utf-8'))
        slug = 'gentle_0535_1035_static_reference_v1'
        path = RUN / 'compositions' / (sex + '_' + slug + '_task.json')
        report = path.with_name(sex + '_' + slug + '.json')
        native = '/Game/DataMake/Validation/NativeFaceLibrary20261007/' + sex + '/gentle_full_v1/A_Native_gentle_full_v1'
        task = {'sex': sex, 'composite_id': slug, 'body_animation': previous['body_animation'],
                'face_animation': native + '.A_Native_gentle_full_v1', 'reference_mesh': mesh['path'],
                'allowed_face_curve_names': mesh['morph_names'], 'face_start_seconds': 5.35,
                'face_end_seconds': 10.35, 'face_rate': 1, 'face_playback': 'hold',
                'body_mode': 'static', 'static_use_reference_pose': True, 'report_path': str(report)}
        validate_task(task)
        write_new_or_identical(path, task)
        capture_path = path.with_name(sex + '_' + slug + '_capture_task.json')
        capture = {'sex': sex, 'animation': ASSET_ROOT + '/' + sex + '/A_' + slug,
                   'composition_report': str(report), 'times': [i/30 for i in range(151)],
                   'output_dir': str(RUN / 'captures' / (sex + '_' + slug))}
        write_new_or_identical(capture_path, capture)
        rows.append({'sex': sex, 'task': str(path), 'report': str(report), 'capture_task': str(capture_path)})
    write_new_or_identical(RUN / 'compositions/initial_gentle_manifest.json', {'entries': rows})
    return rows


if __name__ == '__main__':
    import sys
    task_path = globals().get('DM_NATIVE_FACE_FIVE_SECOND_TASK')
    if task_path is not None:
        if not isinstance(task_path, str):
            raise ValueError('Expected task JSON path')
        run(json.loads(Path(task_path).read_text(encoding='utf-8')))
    elif sys.argv[1:] == ['--prepare']:
        print(json.dumps(prepare_initial_tasks(), indent=2))
    else:
        raise ValueError('Set DM_NATIVE_FACE_FIVE_SECOND_TASK in UE, or use --prepare offline')
