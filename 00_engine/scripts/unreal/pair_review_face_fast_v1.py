"""Session-local face reuse for the interactive 19 October pair panel.

Successful receipts bind an actual body clip, accepted face clip, sex and output
root. Reuse does not rehash source packages or rerun numerical acceptance. A new
combination delegates generation to the existing assembler exactly once.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path


def _path(asset):
    if asset is None:
        return None
    value = asset if isinstance(asset, str) else asset.get_path_name()
    return value if '.' in value else value + '.' + value.rsplit('/', 1)[-1]


def install(assembly):
    """Call before replacing assembly.prepare; no UE calls or source reads."""
    if not hasattr(assembly, '_pair_fast_faces'):
        assembly._pair_fast_faces = {
            'prepare': assembly.prepare, 'choices': None, 'selection_record': None,
            'indexes': {}, 'resolved': {},
        }
    return assembly


def _faces(assembly, state):
    if state['choices'] is None:
        formal = assembly.contract.formal_runtime()
        if formal is None:
            raise ValueError('The pair face preview requires the published face catalog')
        state['choices'], state['selection_record'] = formal[0].accepted_faces()
    return state['choices']


def _index(folder, target_root):
    result = {}
    for path in sorted(folder.glob('*.json')):
        receipt = json.loads(path.read_text(encoding='utf-8-sig'))
        if receipt.get('schema') != 'full_motion_loop_cache_v1' or receipt.get('success') is not True:
            continue
        spec = receipt['spec']
        sources = spec['sources']
        destination = _path(receipt['animation_path'])
        # Earlier panels share this receipt folder. Never use another root's
        # output, even when body/face inputs have the same names.
        if not destination.split('.', 1)[0].startswith(target_root.rstrip('/') + '/'):
            continue
        key = (spec['sex'], spec['face_id'], _path(sources[0]['asset']),
               _path(sources[1]['asset']))
        item = (receipt, str(path))
        previous = result.get(key)
        if previous is not None and _path(previous[0]['animation_path']) != destination:
            raise ValueError('Multiple face composites bind the same preview inputs: ' + str(key))
        result[key] = item
    return result


def resolve(u, assembly, selection, motion, body_action_id=None, *, data=None, path_overlay=None):
    """Return (clip, face receipt); None face preserves the body clip unchanged.

    The caller handles clearing morph targets and applying/positioning the clip.
    Call install before replacing prepare so cold generation retains the existing
    formal composition behavior. Errors loading/generating clips propagate.
    """
    if selection['face_id'] == 'none':
        return motion, None
    install(assembly)
    state = assembly._pair_fast_faces
    sex, face_id = selection['sex'], selection['face_id']
    choice, _report = _faces(assembly, state)[(sex, face_id)]
    target_root = assembly.COMPOSITE_ROOT.rstrip('/') + '/Composites'
    folder = Path(assembly.contract.ROOT).parent / 'appearance_composites' / 'cache'
    key = (sex, face_id, _path(motion), _path(choice['asset']), target_root, str(folder))
    if key in state['resolved']:
        clip, face = state['resolved'][key]
        return clip, copy.deepcopy(face)
    if motion is None:
        clip = u.load_asset(choice['asset'])
        if clip is None:
            raise RuntimeError('Accepted static face could not load: ' + choice['asset'])
        face = {'kind': 'accepted_static_face', 'face_id': face_id,
                'accepted_selection': copy.deepcopy(state['selection_record']),
                'animation_path': _path(clip)}
    else:
        index_key = (str(folder), target_root)
        if index_key not in state['indexes']:
            state['indexes'][index_key] = _index(folder, target_root)
        cached = state['indexes'][index_key].get(key[:4])
        if cached is not None:
            receipt, receipt_path = cached
            clip = u.load_asset(receipt['animation_path'])
            if clip is None:
                raise RuntimeError('Cached face composite could not load: ' + receipt['animation_path'])
            spec = receipt['spec']
            face = {'kind': 'full_body_repeated_face', 'face_id': face_id,
                    'duration_seconds': spec['duration_seconds'],
                    'fullbody_duration_seconds': spec['duration_seconds'],
                    'original_body': copy.deepcopy(spec['sources'][0]),
                    'accepted_face': copy.deepcopy(spec['sources'][1]),
                    'cache_receipt': {'path': receipt_path},
                    'animation_path': receipt['animation_path'],
                    'interactive_cache_reused': True}
        else:
            prepared = state['prepare'](u, selection, motion, body_action_id=body_action_id,
                                        data=data, path_overlay=path_overlay)
            clip, face = prepared['motion'], prepared['face']
    state['resolved'][key] = (clip, copy.deepcopy(face))
    return clip, copy.deepcopy(face)
