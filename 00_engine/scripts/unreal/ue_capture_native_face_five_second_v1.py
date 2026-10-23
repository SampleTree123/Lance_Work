"""Capture one verified five-second composition at 30 fps (151 endpoint samples).

Keeps the original capture's 16 render ticks per sample, restore behavior and
shared capture lock. Import is offline-safe; run requires explicit UE dispatch.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

_spec = importlib.util.spec_from_file_location('_dm_five_second_contract', Path(__file__).with_name('ue_native_face_five_second_v1.py'))
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)
RUN = contract.RUN
SAMPLE_COUNT = 151
CAPTURE_FPS = 30


def validate_task(task):
    if not isinstance(task, dict) or set(task) != {'sex', 'animation', 'composition_report', 'times', 'output_dir'}:
        raise ValueError('Expected one five-second capture task')
    if task['sex'] not in ('female', 'male'):
        raise ValueError('Invalid capture sex')
    contract.inside_run(task['output_dir'])
    contract.inside_run(task['composition_report'])
    times = task['times']
    if not isinstance(times, list) or len(times) != SAMPLE_COUNT or any(
            not contract.finite(value) or not math.isclose(value, i/CAPTURE_FPS, abs_tol=1e-10, rel_tol=0)
            for i, value in enumerate(times)):
        raise ValueError('Require all 151 ordered samples from 0 to 5 seconds at 30 fps')
    animation = task['animation']
    if not isinstance(animation, str) or not animation.startswith(contract.ASSET_ROOT + '/' + task['sex'] + '/A_') or '..' in animation or '\\' in animation:
        raise ValueError('Capture requires an isolated five-second composite')
    return task


def run(task):
    validate_task(task)
    report = json.loads(Path(task['composition_report']).read_text(encoding='utf-8'))
    source_task = contract.validate_task(report['task'])
    verification = report.get('verification', {})
    if report.get('success') is not True or report.get('sources_unchanged') is not True or report.get('destination') != task['animation'].split('.')[0] or source_task['sex'] != task['sex']:
        raise ValueError('Capture requires the matching successful composition report')
    if set(report.get('face_bones', [])) != contract.EXPECTED_FACE_BONES or not math.isclose(verification.get('duration_seconds', -1), 5, abs_tol=1e-6, rel_tol=0):
        raise ValueError('Composition must preserve ten support bones for five seconds')
    if verification.get('all_frame_count') != round(5 * verification.get('fps', 0)) + 1:
        raise ValueError('Composition lacks the complete all-frame source comparison')
    module = contract.load_isolated('ue_capture_native_face_review_v1.py', '_dm_five_second_capture')
    module.RUN = RUN
    module.MAX_CAPTURE_FRAMES = SAMPLE_COUNT
    return module.run(task)


if __name__ == '__main__':
    path = globals().get('DM_NATIVE_FACE_FIVE_SECOND_CAPTURE_TASK')
    if not isinstance(path, str):
        raise ValueError('Set DM_NATIVE_FACE_FIVE_SECOND_CAPTURE_TASK to task JSON path')
    run(json.loads(Path(path).read_text(encoding='utf-8')))
