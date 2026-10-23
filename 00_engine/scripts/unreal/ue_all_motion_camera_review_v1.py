"""Isolated 30-action common-camera adapter; only the coordinator invokes UE."""
from pathlib import Path
import importlib.util
import hashlib
import json
import math

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_all_motions_portrait115_20261014_v1'
ASSETS = '/Game/DataMake/Validation/AllMotionCameraPortrait11520261014'
PLAN_NAME = 'camera_trial_plan_v1.json'


def check_plan(expected_sha256):
    actual = hashlib.sha256((RUN / PLAN_NAME).read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValueError('Frozen all-motion plan changed')


def adapter():
    spec = importlib.util.spec_from_file_location('_all_motion_camera_adapter', S / 'ue_camera_alignment_review_v1.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    result.RUN, result.ASSETS, result.PLAN_NAME = RUN, ASSETS, PLAN_NAME
    original = result.configured_module

    def configured(name):
        module = original(name)
        if name == 'ue_motion_scene_sequence_v1':
            original_keys = module.key_rows

            def review_keys(shot):
                if shot.get('status') == 'geometry_review_required':
                    document = json.loads((RUN / PLAN_NAME).read_text(encoding='utf-8-sig'))
                    matches = [s for s in document['shots'] if s['shot_id'] == shot['shot_id']]
                    if (document.get('schema') != 'camera_all_motions_portrait115_trial_v1'
                            or len(matches) != 1 or matches[0] != shot):
                        raise ValueError('Review exception must be an exact frozen all-motion shot')
                    for row in shot['frames'] + [shot['endpoint_validation_frame']]:
                        values = row['position'] + row['rotation_pitch_yaw_roll'] + [row['horizontal_fov_degrees']]
                        values += row.get('look_at', [])
                        if not all(math.isfinite(float(value)) for value in values):
                            raise ValueError('Nonfinite review camera key')
                    # Only the local key validator sees this copy; all persisted
                    # plan/preparation metadata retains geometry_review_required.
                    return original_keys(dict(shot, status='geometry_pass'))
                return original_keys(shot)

            module.key_rows = review_keys
        if name == 'ue_motion_scene_render_v1':
            module.LIVE_ATTRIBUTE = '_dm_all_motion_camera_portrait115_20261014'
        return module

    result.configured_module = configured
    return result


def prepare(u, ids, plan_sha256):
    check_plan(plan_sha256)
    result = adapter().prepare(u, ids)
    check_plan(plan_sha256)
    return {'success': True, 'prepared': len(ids)}


def render(u, attempt, ids, width, height, plan_sha256):
    check_plan(plan_sha256)
    result = adapter().render(u, attempt, ids, width=width, height=height)
    # Do not return the complete input pins/jobs receipt over the remote bridge.
    receipt = result.get('receipt') or {}
    return {'attempt_id': attempt, 'status': receipt.get('status'),
            'receipt_path': result.get('receipt_path'), 'selected': len(ids)}


def status(u):
    result = adapter().status(u)
    receipt = result.pop('receipt', None)
    if receipt:
        result['receipt_status'] = receipt.get('status')
        result['success'] = receipt.get('success')
    return result
