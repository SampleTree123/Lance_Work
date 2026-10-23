"""Evidence-bound, offline native lash corner rule; original operator immutable."""
import argparse
import json
from pathlib import Path

import numpy as np

from cc_headshot_geometry_solver_v1 import file_record, read_json, verify_record


def corner_identity_operator(model, faces, lash_indices, count):
    incidence = np.zeros(count, dtype=int)
    adjacency = [set() for _ in range(count)]
    for face in faces:
        polygon = [int(v) for v, _ in face]
        if any(v < 0 or v >= count for v in polygon):
            raise ValueError('Topology outside Body')
        for v in set(polygon):
            incidence[v] += 1
        for u, v in zip(polygon, polygon[1:] + polygon[:1]):
            adjacency[u].add(v)
            adjacency[v].add(u)
    lash = np.asarray(lash_indices, dtype=int)
    corners = lash[incidence[lash] == 1]
    if not len(corners):
        raise ValueError('No single-face native lash corners')
    rows, cols, values = (np.asarray(model[k]) for k in ('rows', 'cols', 'values'))
    for i in corners:
        indices = rows == i
        actual = dict(zip(cols[indices].tolist(), values[indices].tolist()))
        expected = {i: .75, **{j: .125 for j in adjacency[i]}}
        if len(adjacency[i]) != 2 or set(actual) != set(expected) or any(abs(actual[j] - expected[j]) > 1e-9 for j in expected):
            raise ValueError('Corner row is not the diagnosed .75/.125/.125 rule')
    keep = ~np.isin(rows, corners)
    changed = {'rows': np.concatenate((rows[keep], corners)),
               'cols': np.concatenate((cols[keep], corners)),
               'values': np.concatenate((values[keep], np.ones(len(corners))))}
    if 'offset' in model:
        changed['offset'] = np.asarray(model['offset']).copy()
    return changed, corners


def apply_operator(model, value):
    return np.column_stack([np.bincount(model['rows'],
        weights=model['values'] * value[model['cols'], axis], minlength=len(value)) for axis in range(3)])


def build_evidence(prior_state_path, output_dir):
    from cc_compare_headshot_geometry_v1 import read_obj
    state = read_json(prior_state_path)
    if state['status'] != 'failed' or '09_final_reload_capture' not in state['steps']:
        raise ValueError('Use the retained normalized/reloaded failed trial')
    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Refusing existing operator evidence output')
    root = Path(state['attempt_dir'])
    references = [state['inputs']['subdivision_operator'], state['inputs']['candidate_arrays'],
                  state['offline_outputs']['target_arrays']]
    for step_id, names in {'01_capture': ['before_body.obj'],
                           '02_calibrate_zero': ['after_mesh.json'],
                           '03_identity_roundtrip': ['return_0_local_and_bones.json'],
                           '09_final_reload_capture': ['before_mesh.json', 'before_world_mesh.json']}.items():
        references.extend(state['steps'][step_id]['outputs'][name] for name in names)
    for record in references:
        verify_record(record)
    with np.load(state['inputs']['subdivision_operator']['path'], allow_pickle=False) as op:
        original = {key: op[key].copy() for key in op.files}
    with np.load(state['inputs']['candidate_arrays']['path'], allow_pickle=False) as c:
        lash = c['lash_indices'].copy()
    _, _, faces = read_obj(root / '01_capture/before_body.obj')
    changed, corners = corner_identity_operator(original, faces, lash, 14164)
    if len(corners) != 16 or not np.array_equal(lash, np.arange(13411, 14115)):
        raise ValueError('Expected exactly16 corners in verified704 native lash vertices')
    with np.load(state['offline_outputs']['target_arrays']['path'], allow_pickle=False) as f:
        old_precomp = f['precomp'].copy()
    zero = np.asarray(read_json(root / '02_calibrate_zero/after_mesh.json')['vertices'])
    baseline = np.asarray(read_json(root / '03_identity_roundtrip/return_0_local_and_bones.json')['vertices'])
    actual = np.asarray(read_json(root / '09_final_reload_capture/before_mesh.json')['vertices'])
    correction = old_precomp - zero
    original_error = np.linalg.norm(actual - baseline - apply_operator(original, correction), axis=1) * 10
    corrected_error = np.linalg.norm(actual - baseline - apply_operator(changed, correction), axis=1) * 10
    if corrected_error.max() > .002 or original_error[corners].max() <= .01:
        raise ValueError('Observed trial does not support this bounded corner correction')
    report = {'schema_version': 2, 'status': 'offline_measured_operator_requires_new_CC_candidate',
              'prior_state': file_record(prior_state_path), 'implementation': file_record(__file__),
              'inputs': references, 'changed_row_indices': corners.tolist(), 'changed_row_count': len(corners),
              'rule_before': '0.75*self + 0.125*boundary_neighbor1 + 0.125*boundary_neighbor2',
              'rule_after': '1.0*self for single-face native lash corners only',
              'old_model_corner_max_error_mm': float(original_error[corners].max()),
              'new_model_corner_max_error_mm': float(corrected_error[corners].max()),
              'new_model_all_max_error_mm': float(corrected_error.max()),
              'evidence_fit_limit_mm': .002,
              'limits': ['Measured on WF003 fresh final normalization; not a new universal operator claim.',
                         'All noncorner rows and original offset retained; no original file changed.']}
    output.mkdir(parents=True)
    np.savez_compressed(output / 'corner_identity_operator.npz', **changed)
    report['operator'] = file_record(output / 'corner_identity_operator.npz')
    (output / 'corner_operator_evidence.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior-state', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(build_evidence(a.prior_state, a.output), indent=2))
